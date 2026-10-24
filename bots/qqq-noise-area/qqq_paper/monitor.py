"""Bilan prospectif local : aucune cle ni requete reseau, SQLite en lecture seule."""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import sqlite3
import pandas as pd
import exchange_calendars as xcals
from .power import protection_window


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_store(runtime):
    path=(Path(runtime)/'shadow-sip/state.sqlite').resolve()
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
    return db


def now_utc(now):
    value=pd.Timestamp(now if now is not None else datetime.now(timezone.utc))
    if value.tz is None:raise ValueError('timezone-aware observation required')
    return value.tz_convert('UTC')


def coverage_detail(day,records,completed):
    late=[];on_time=0;unknown=0
    for row in records:
        if not row['key'].startswith(day+':'):continue
        data=json.loads(row['data'])
        try:
            at=pd.Timestamp(data['decision_time']);observed=pd.Timestamp(data['observed_at'])
            delay=(observed-at).total_seconds()
            if at.tz is None or observed.tz is None or not pd.notna(delay):raise ValueError('invalid timing')
        except (KeyError,TypeError,ValueError):
            unknown+=1;continue
        if data.get('status')=='processed' and 0<=delay<=120:on_time+=1
        elif delay>120:late.append((at.strftime('%H:%M'),delay))
        else:unknown+=1
    marker=next((s for s in completed if s['day']==day),None)
    return dict(day=day,session_completed=marker is not None,on_time_decisions=on_time,
        late_decisions=len(late),unknown_or_unprocessed_decisions=unknown,
        first_late_decision=min((clock for clock,_ in late),default=None),
        last_late_decision=max((clock for clock,_ in late),default=None),
        largest_delay_seconds=max((delay for _,delay in late),default=None))


def power_report(runtime,now,alerts):
    path=runtime/'windows/power_status.json'
    if not path.exists():
        try:
            supervisor=read_json(runtime/'windows/status.json')
            if isinstance(supervisor,dict) and supervisor.get('power_guard') is True:
                alerts.append('power_protection_unavailable')
        except (OSError,TypeError,ValueError):pass
        return None  # older installations have no power worker
    try:
        value=read_json(path);age=(now-pd.Timestamp(value['utc'])).total_seconds()
        if not math.isfinite(age):raise ValueError('invalid power timestamp')
        if value.get('state')=='error':alerts.append('power_protection_error')
        if protection_window(now):
            if age>90 or age < -60:alerts.append('power_protection_stale')
            elif value.get('on_ac') is False:alerts.append('power_on_battery_during_session')
            elif value.get('state')!='protected' or value.get('system_required') is not True or value.get('on_ac') is not True:alerts.append('power_protection_inactive')
        keys=('state','utc','on_ac','system_required','in_session_window','last_gap_seconds','last_gap_utc')
        return {key:value[key] for key in keys if key in value}
    except (OSError,KeyError,TypeError,ValueError):
        alerts.append('power_protection_unavailable');return None


def initialize(runtime,now=None):
    runtime=Path(runtime);path=runtime/'windows/prospective_baseline.json'
    if path.exists():return read_json(path)
    now=now_utc(now);day=now.tz_convert('America/New_York').normalize().tz_localize(None)
    cal=xcals.get_calendar('XNYS',start=day,end=day+pd.Timedelta(days=20))
    first=next(d for d in cal.sessions if d>day)
    with read_store(runtime) as db:
        account=json.loads(db.execute("SELECT value FROM meta WHERE key='account'").fetchone()[0])
        seq=db.execute('SELECT COALESCE(MAX(seq),0) FROM fills').fetchone()[0]
    db.close()
    value=dict(first_session=str(first.date()),initial_realized_equity=account['balance'],baseline_fill_seq=seq,
        initialized_utc=now.isoformat(),operational_sessions=20,extended_sessions=60,extended_closed_trades=50,
        note='Count only complete on-time shadow sessions; milestones do not establish profitability.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,allow_nan=False)
    return value


def collect_report(runtime,now=None):
    runtime=Path(runtime);now=now_utc(now);baseline=read_json(runtime/'windows/prospective_baseline.json')
    first=baseline['first_session'];alerts=[]
    with read_store(runtime) as db:
        meta={r['key']:r['value'] for r in db.execute('SELECT key,value FROM meta')}
        account=json.loads(meta['account'])
        configuration=json.loads(meta['configuration'])
        if configuration.get('mode')!='shadow' or configuration.get('feed')!='sip':alerts.append('unexpected_configuration')
        completed=[json.loads(value) for key,value in meta.items() if key.startswith('completed_session:') and key.split(':',1)[1]>=first]
        good=sorted(s['day'] for s in completed if s.get('fully_prospective'))
        rows=list(db.execute('''SELECT o.day,o.action,o.status,o.cid,f.seq,f.realized,f.commission,f.borrow
            FROM fills f JOIN orders o ON o.cid=f.cid WHERE o.day>=? AND f.seq>?''',(first,baseline['baseline_fill_seq'])))
        prospective=[r for r in rows if r['day'] in good]
        closed=len({r['cid'] for r in prospective if r['action']=='close' and r['status']=='filled'})
        pending=db.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected')").fetchone()[0]
        decisions=list(db.execute('SELECT key,data FROM decisions WHERE key>=? ORDER BY key',(first,)))
    db.close()
    if meta.get('paused'):alerts.append('ledger_paused')
    if pending:alerts.append('pending_orders')
    if meta.get('paused_day')==str(now.tz_convert('America/New_York').date()):alerts.append('current_session_paused')
    if runtime.joinpath('STOP_SHADOW.flag').exists():alerts.append('operator_stop_requested')
    try:
        status=read_json(runtime/'shadow-sip/status.json')
        age=(now-pd.Timestamp(status['utc'])).total_seconds()
        if age>180 or age < -60:alerts.append('engine_status_stale')
        if status.get('state') not in ('running','waiting_for_regular_session','flat_after_session'):alerts.append('engine_'+status.get('state','unknown'))
    except (OSError,KeyError,ValueError,TypeError):status={};age=None;alerts.append('engine_status_unavailable')
    today=now.tz_convert('America/New_York').normalize().tz_localize(None)
    expected=[]
    if str(today.date())>=first:
        cal=xcals.get_calendar('XNYS',start=pd.Timestamp(first)-pd.Timedelta(days=1),end=today+pd.Timedelta(days=1))
        for day,row in cal.schedule.loc[first:str(today.date())].iterrows():
            if now>=pd.Timestamp(row['close'])+pd.Timedelta(minutes=18):expected.append(str(day.date()))
    gaps=sorted(set(expected)-set(good))
    if gaps:alerts.append('prospective_coverage_gaps')
    details=[coverage_detail(day,decisions,completed) for day in gaps]
    power=power_report(runtime,now,alerts)
    stage='waiting_for_observations'
    if len(good)>=baseline['operational_sessions']:stage='operational_bilan_ready'
    if len(good)>=baseline['extended_sessions'] and closed>=baseline['extended_closed_trades']:stage='extended_bilan_ready'
    net=lambda records:sum(r['realized']-r['commission']-r['borrow'] for r in records)
    return dict(utc=now.isoformat(),mode='shadow',feed='sip',data_delay_minutes=16,first_session=first,
        initial_realized_equity=baseline['initial_realized_equity'],current_realized_equity=account['balance'],managed_qty=account['position'],
        completed_sessions=len(completed),fully_prospective_sessions=len(good),prospective_days=good,coverage_gaps=gaps,
        coverage_details=details,power_protection=power,
        prospective_closed_trades=closed,prospective_realized_pnl=net(prospective),all_period_realized_pnl=net(rows),pending_orders=pending,
        engine_state=status.get('state'),engine_status_age_seconds=age,alerts=alerts,stage=stage,
        operational_sessions_target=baseline['operational_sessions'],extended_sessions_target=baseline['extended_sessions'],
        extended_closed_trades_target=baseline['extended_closed_trades'],
        limitation='Local delayed-data simulation, no broker fills. Counts alone do not prove a profitable strategy.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,default=Path('runtime'));p.add_argument('--initialize',action='store_true');a=p.parse_args(argv)
    value=initialize(a.runtime) if a.initialize else collect_report(a.runtime)
    print(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
