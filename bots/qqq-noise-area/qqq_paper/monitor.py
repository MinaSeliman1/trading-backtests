"""Bilan prospectif local : aucune cle ni requete reseau, SQLite en lecture seule."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import pandas as pd
import exchange_calendars as xcals


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
    stage='waiting_for_observations'
    if len(good)>=baseline['operational_sessions']:stage='operational_bilan_ready'
    if len(good)>=baseline['extended_sessions'] and closed>=baseline['extended_closed_trades']:stage='extended_bilan_ready'
    net=lambda records:sum(r['realized']-r['commission']-r['borrow'] for r in records)
    return dict(utc=now.isoformat(),mode='shadow',feed='sip',data_delay_minutes=16,first_session=first,
        initial_realized_equity=baseline['initial_realized_equity'],current_realized_equity=account['balance'],managed_qty=account['position'],
        completed_sessions=len(completed),fully_prospective_sessions=len(good),prospective_days=good,coverage_gaps=gaps,
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
