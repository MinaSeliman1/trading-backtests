"""Local report only: read-only SQLite, no vault, network or orders."""
from pathlib import Path
import argparse,json,sqlite3
import pandas as pd
import exchange_calendars as xcals
from qqq_paper.runtime import session_for
from qqq_paper.monitor import power_report


def collect(runtime,now=None):
    root=Path(runtime);now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now).tz_convert('UTC')
    db=sqlite3.connect((root/'state.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta')}
        days=[json.loads(v) for v, in db.execute('SELECT data FROM days ORDER BY day')]
        trades=[json.loads(v) for v, in db.execute('SELECT data FROM trades ORDER BY day')]
    finally:db.close()
    a=meta['account'];first=meta.get('first_session');alerts=[];expected=[]
    good=[d['day'] for d in days if d.get('fully_observed') and d['phase'] in ('closed','flat') and (first is None or d['day']>=first)]
    prospective=[t for t in trades if t['day'] in good]
    if first and now.date()>=pd.Timestamp(first).date():
        cal=xcals.get_calendar('XNYS',start=pd.Timestamp(first)-pd.Timedelta(days=1),end=now.date()+pd.Timedelta(days=1))
        expected=[str(d.date()) for d,row in cal.schedule.loc[first:str(now.date())].iterrows() if now>=pd.Timestamp(row['close'])+pd.Timedelta(minutes=18)]
    gaps=sorted(set(expected)-set(good))
    if gaps:alerts.append('coverage_gaps')
    try:
        status=json.loads((root/'status.json').read_text(encoding='utf-8-sig'));stamp=pd.Timestamp(status['utc']);age=(now-stamp).total_seconds()
        if not pd.notna(age) or age>180 or age < -60:alerts.append('engine_stale')
        if status['state'] in ('unresolved','error_no_new_entries','startup_retry','stopped'):alerts.append('engine_'+status['state'])
    except (OSError,ValueError,KeyError,TypeError):status={};age=None;alerts.append('engine_unavailable')
    if a['open_day']:
        s=session_for(a['open_day'])
        if s is None or now>=s.close+pd.Timedelta(minutes=18):alerts.append('virtual_position_unresolved_after_close')
    if root.joinpath('STOP_SHADOW.flag').exists():alerts.append('operator_stop')
    stage='extended_review' if len(good)>=60 and len(prospective)>=50 else 'operational_review' if len(good)>=20 else 'waiting'
    power=power_report(root,now,alerts)
    return dict(utc=str(now),mode='shadow',feed='sip',delay_minutes=16,first_session=first,balance=a['balance'],marked_equity=a['marked_equity'],power_protection=power,
        realized_net_pnl=a['balance']-a['initial_equity'],closed_trades=len(trades),fully_observed_sessions=len(good),prospective_closed_trades=len(prospective),
        prospective_net_pnl=sum(t['net_pnl'] for t in prospective),closed_commission=sum(t['commission'] for t in trades),closed_friction=sum(t['friction_cost'] for t in trades),
        closed_borrow=sum(t['borrow_fee'] for t in trades),open_day=a['open_day'],observed_drawdown_pct=a['max_drawdown_pct'],coverage_gaps=gaps,
        unresolved_days=[d['day'] for d in days if d['phase']=='unresolved'],engine_state=status.get('state'),engine_error_type=status.get('error_type'),engine_network_reason=status.get('network_reason'),engine_age_seconds=age,alerts=alerts,stage=stage,
        limitation='Delayed local shadow fills, no broker orders. Historical replay does not count as prospective evidence.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,default=Path('runtime'));a=p.parse_args()
    print(json.dumps(collect(a.runtime),indent=2,allow_nan=False))


if __name__=='__main__':main()
