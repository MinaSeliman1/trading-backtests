"""Projection causale de barres fermees ; sorties reutilisent le moteur historique gele."""
from copy import deepcopy
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
from pathlib import Path
import hashlib,math
import numpy as np
import pandas as pd
from orb.engine import Config,feature,trade_path,UnresolvedExecution
from . import REPO
MODEL=REPO/'studies/opening-range-5m/orb/engine.py'
MODEL_SHA='0ee6f0f9e7b7f1080d444e90a055aeb4ed2dc63349cfc7ab05f66d1d4f5f1810'
PARAMETERS=Config()
D=lambda x:Decimal(str(x))
KEYS=('open','high','low','close','volume')


def verify_model():
    if hashlib.sha256(MODEL.read_bytes()).hexdigest()!=MODEL_SHA:raise RuntimeError('frozen ORB engine changed')


def account(capital=100000):
    if not math.isfinite(capital) or capital<=0:raise ValueError('capital')
    return dict(initial_equity=float(capital),balance=float(capital),marked_equity=float(capital),open_day=None,peak=float(capital),max_drawdown_pct=0.)


def market(rows,s):
    n=int((s.close-s.open).total_seconds()/60);a={k:np.full((1,390),np.nan) for k in KEYS}
    for slot,row in rows.items():
        for k,v in zip(KEYS,row):a[k][0,int(slot)]=np.nan if v is None else v
    return SimpleNamespace(dates=pd.DatetimeIndex([s.open.date()]),arrays=a,lengths=np.array([n]),valid=np.array([False]),symbol='QQQ',
        quality=pd.DataFrame([dict(session_open=str(s.open),session_close=str(s.close))]))


def note(day,reason):
    if reason not in day['notes']:day['notes'].append(reason)
    day['prospective']=False


def mark(acct,day,offsets):
    values=day['capital_before']+np.asarray(offsets,dtype=float);peaks=np.maximum.accumulate(np.r_[day['peak_before'],values])[1:]
    acct['peak']=float(max(day['peak_before'],values.max()));acct['max_drawdown_pct']=max(day['dd_before'],float(np.max((peaks-values)/peaks)*100));acct['marked_equity']=float(values[-1])


def advance(acct,day,bars,session,asof):
    asof=pd.Timestamp(asof)
    if asof.tz is None or bars.index.tz is None:raise ValueError('timezone required')
    if bars.index.has_duplicates:raise ValueError('duplicate timestamps')
    date=str(session.open.date());a=deepcopy(acct);d=deepcopy(day)
    if a['open_day'] and (a['open_day']!=date or d is None):raise RuntimeError('unresolved old position')
    if d is None:
        d=dict(day=date,phase='waiting_opening',entry_done=False,fully_observed=False,prospective=True,notes=[],bars={},last_processed=4,
            capital_before=a['balance'],peak_before=a['peak'],dd_before=a['max_drawdown_pct'])
        if asof>session.open+pd.Timedelta(minutes=7):d.update(phase='skipped',reason='late_start');note(d,'late_start');return a,d
    if d['day']!=date:raise ValueError('wrong session ledger')
    if d['phase'] in ('closed','flat','skipped','unresolved'):return a,d
    # Only bars that have fully closed on the delayed logical clock are visible.
    last=min(int((session.close-session.open).total_seconds()/60)-1,int((asof-session.open).total_seconds()//60)-1)
    rows=dict(d['bars']);visible=bars.loc[(bars.index>=session.open)&(bars.index<session.open+pd.Timedelta(minutes=last+1))]
    for at,row in visible.iterrows():
        offset=(at-session.open).total_seconds()/60
        if offset!=int(offset):raise ValueError('off-grid bar')
        key=str(int(offset));value=[float(row[k]) if pd.notna(row[k]) else None for k in KEYS]
        if key in rows:
            if rows[key]!=value:note(d,'source_revision')
        else:rows[key]=value
    deadline=session.open+pd.Timedelta(minutes=7)
    if not d['entry_done'] and asof>deadline:
        d.update(phase='skipped',reason='missing_entry_or_opening');note(d,'missed_entry');return a,d
    if 'intent' not in d:
        if last<4 or any(str(j) not in rows for j in range(5)):return a,d
        m=market(rows,session);f=feature(m,0)
        if f['eligibility']!='eligible':
            d.update(phase='skipped',reason='invalid_opening');note(d,'invalid_opening');return a,d
        d['bars']={str(j):rows[str(j)] for j in range(5)}
        sign=f['signal_sign'];stop=f['range_low' if sign>0 else 'range_high'];risk=sign*(D(f['sizing_price'])-D(stop)) if sign else D(0)
        q=int(min(D(a['balance'])/D(f['sizing_price']),D(a['balance'])*D('.01')/risk).to_integral_value(rounding=ROUND_FLOOR)) if sign and risk>0 and a['balance']>0 else 0
        d['intent']=dict(sign=sign,quantity=q,stop=stop,sizing_price=f['sizing_price'],observed_at=str(asof));d['phase']='pending_entry'
        if not q:d.update(phase='flat',reason='no_signal_or_quantity',fully_observed=d['prospective']);return a,d
    q=d['intent']['quantity'];sign=d['intent']['sign'];entryrow=rows.get('5');entry=entryrow[0] if entryrow else None
    if not d['entry_done']:
        if entry is None or not math.isfinite(entry) or entry<=0:return a,d
        fee=max(.35,q*.0035);a['balance']-=fee;a['open_day']=date;d.update(entry_done=True,phase='active',entry_fee=fee,entry_reference=entry,entry_price=entry+sign*.01,entry_observed_at=str(asof))
    m=market(rows,session)
    try:p=trade_path(m,0,sign,q,PARAMETERS)
    except UnresolvedExecution as error:
        used=error.minute-1
        reason=error.reason;age=(asof-(session.open+pd.Timedelta(minutes=error.minute+1))).total_seconds()
        if reason not in ('missing_active_open','missing_entry_open') or age>120:
            d['phase']='unresolved';d['reason']=reason;note(d,'data_gap')
        offsets=[0.,-d['entry_fee']-q*.01]
        fill=entry+sign*.01
        for j in range(5,used+1):offsets.append(-d['entry_fee']+q*sign*(m.arrays['close'][0,j]-fill))
        mark(a,d,offsets)
    else:
        used=p['exit_slot'];offsets=p.pop('equity_offsets');mark(a,d,offsets)
        a['balance']=d['capital_before']+p['net_pnl'];a['open_day']=None
        d.update(phase='closed',trade=dict(day=date,capital_before=d['capital_before'],capital_after=a['balance'],**p))
    for j in range(5,used+1):
        key=str(j)
        if key in rows:
            if key not in d['bars'] and (asof-(session.open+pd.Timedelta(minutes=j+1))).total_seconds()>120:note(d,'late_observation')
            d['bars'][key]=rows[key]
    d['last_processed']=max(d['last_processed'],used)
    d['fully_observed']=d['phase']=='closed' and d['prospective']
    return a,d
