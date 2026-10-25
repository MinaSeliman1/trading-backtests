"""Causal minute-resolution Nowick engine. Integer quote ticks, no broker calls."""
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import numpy as np
import pandas as pd
from fx_data import scale_for

NY=ZoneInfo('America/New_York')

@dataclass(frozen=True)
class Config:
    trend: str='structure'
    midpoint: bool=False
    rr: float=1.0
    cost_pips: float=1.0
    penetration: int=10
    front_run: str='cancel_first'
    swing: bool=False
    sr: bool=False
    double: bool=False
    ttl: int=9
    gap_policy: str='penalty'

@dataclass
class Market:
    pair: str
    t: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    features: pd.DataFrame

def entry_time_allowed(t):
    dt=datetime.fromtimestamp(int(t),NY)
    return 120 <= dt.hour*60+dt.minute < 480

def fee_cash(qty,pair,cost_pips):
    return qty*10/scale_for(pair)*cost_pips

def risk_quantity(balance,distance,pair):
    return max(0,math.floor(balance*.01/(distance/scale_for(pair)))) if balance>0 and distance>0 else 0

def stop_valid(distance):
    return 50<=distance<=300

def pending_expired(bar,signal_bar,ttl):
    return bar-signal_bar>=ttl

def levels(d,o,c,pivot,rr,midpoint):
    e=(o+c+1)//2 if midpoint else int(o)
    sl=int(pivot)-d*30
    dist=d*(e-sl)
    tp=math.floor(e+rr*dist) if d==1 else math.ceil(e-rr*dist)
    return int(e),int(sl),int(tp)

def pending_event(p,q,penetration,mode):
    o,h,l,c=map(int,q)
    d,e,x=p['d'],p['entry'],p['extreme']
    if mode!='off' and d*(o-x)>0:
        return 'cancel',False,False
    at_open=d*(e-o)>=penetration
    if at_open:
        return 'fill',False,True
    hit=(l<=e-penetration if d==1 else h>=e+penetration)
    breached=mode!='off' and (h>x if d==1 else l<x)
    ambiguous=hit and breached
    if breached and (not hit or mode=='cancel_first'):
        return 'cancel',ambiguous,False
    return ('fill' if hit else 'wait'),ambiguous,False

def position_event(p,q,penetration,new_intramin=False):
    o,h,l,c=map(int,q)
    d,sl,tp=p['d'],p['sl'],p['tp']
    # Known opening quote comes first, except when entry was later in this minute.
    if not new_intramin:
        if d*(o-sl)<=0:
            return ('SL_GAP' if o!=sl else 'SL'),o,False
        if d*(o-tp)>=penetration:
            return 'TP',tp,False
    stop=(l<=sl if d==1 else h>=sl)
    target=(h>=tp+penetration if d==1 else l<=tp-penetration)
    if stop:
        return 'SL',sl,bool(target)
    if target and (not new_intramin or d*(c-tp)>=penetration):
        return 'TP',tp,False
    return None,None,False

def confirm_pivots(high,low,complete,t,length=5):
    h=pd.Series(high,dtype=float); l=pd.Series(low,dtype=float)
    win=2*length+1
    clean=pd.Series(complete).rolling(win,min_periods=win).sum().eq(win)
    clean &= pd.Series(t).sub(pd.Series(t).shift(2*length)).eq(2*length*900)
    centre_h=h.shift(length); centre_l=l.shift(length)
    ph=centre_h.where(clean & centre_h.ge(h.rolling(length+1).max().shift(length)) & centre_h.gt(h.rolling(length).max()))
    pl=centre_l.where(clean & centre_l.le(l.rolling(length+1).min().shift(length)) & centre_l.lt(l.rolling(length).min()))
    return ph.to_numpy(),pl.to_numpy()

def prepare_market(raw,pair):
    good=raw['valid_bid']
    t=raw['t'][good].astype(np.int64)
    bid=raw['bid'][good].astype(np.int64); ask=raw['ask'][good].astype(np.int64)
    if len(t)==0 or (np.diff(t)<=0).any():
        raise ValueError('Invalid source chronology')
    idx=pd.to_datetime(t,unit='s',utc=True).as_unit('ns')
    frame=pd.DataFrame(bid,index=idx,columns=['o','h','l','c'])
    frame['i']=np.arange(len(t))
    f=frame.resample('15min').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),count=('o','count'),i0=('i','min'),i1=('i','max'))
    f=f[f['count']>0].copy()
    for col in ['o','h','l','c','i0','i1']:
        f[col]=f[col].astype(np.int64)
    f['t']=f.index.as_unit('ns').asi8//1000000000
    f['complete']=f['count']==15
    f['ph'],f['pl']=confirm_pivots(f.h.to_numpy(),f.l.to_numpy(),f.complete.to_numpy(),f.t.to_numpy())
    ph1=ph0=pl1=pl0=-1
    hp=[]; hp0=[]; lp=[]; lp0=[]
    for ph,pl in zip(f.ph,f.pl):
        if not np.isnan(ph): ph0,ph1=ph1,int(ph)
        if not np.isnan(pl): pl0,pl1=pl1,int(pl)
        hp.append(ph1); hp0.append(ph0); lp.append(pl1); lp0.append(pl0)
    f['lastPH']=hp; f['prevPH']=hp0; f['lastPL']=lp; f['prevPL']=lp0
    f['trend_a']=np.where((f.prevPH>0)&(f.prevPL>0)&(f.lastPH>f.prevPH)&(f.lastPL>f.prevPL),1,np.where((f.prevPH>0)&(f.prevPL>0)&(f.lastPH<f.prevPH)&(f.lastPL<f.prevPL),-1,0))
    f['lo10']=f.l.rolling(10,min_periods=10).min()
    f['hi10']=f.h.rolling(10,min_periods=10).max()
    hours=f.resample('1h').agg(c=('c','last'),n=('complete','sum'),count=('complete','count'))
    hours=hours[(hours.n==4)&(hours['count']==4)].copy()
    hours['fast']=hours.c.ewm(span=50,adjust=False).mean()
    hours['slow']=hours.c.ewm(span=200,adjust=False).mean()
    htimes=hours.index.as_unit('ns').asi8//1000000000+3600
    j=np.searchsorted(htimes,f.t.to_numpy()+900,side='right')-1
    trend_b=np.zeros(len(f),np.int8)
    valid=j>=199
    if len(hours):
        safe=np.maximum(j,0)
        valid &= (f.t.to_numpy()+900-htimes[safe])<3600
        direction=np.sign(hours.fast.to_numpy()-hours.slow.to_numpy()).astype(np.int8)
        trend_b[valid]=direction[j[valid]]
    f['trend_b']=trend_b
    local=pd.to_datetime(f.t+900,unit='s',utc=True).dt.tz_convert(NY)
    f['next_minute']=local.dt.hour*60+local.dt.minute
    local0=pd.to_datetime(f.t,unit='s',utc=True).dt.tz_convert(NY)
    f['current_minute']=local0.dt.hour*60+local0.dt.minute
    return Market(pair,t,bid,ask,f.reset_index(drop=True))

def simulate(market,config,start,end,initial=100000.0):
    t,q,f=market.t,market.bid,market.features
    scale=scale_for(market.pair)
    balance=float(initial); pending=None; position=None
    trades=[]; setups=[]; marks=[]
    counters={'front_run_ambiguous_setups':0,'cancel_front_run':0,'cancel_gap':0,'cancel_expiry':0,'cancel_session':0,'reject_margin':0,'reject_stop':0,'candidate_nowicks':0}
    last_long=last_short=-1000000
    sr_high=[]; sr_low=[]
    peak=float(initial); max_dd=0.0
    def mark(ts,price):
        nonlocal peak,max_dd
        equity=balance+(position['qty']*position['d']*(int(price)-position['entry'])/scale if position else 0)
        peak=max(peak,equity)
        max_dd=max(max_dd,(peak-equity)/peak if peak>0 else 0)
        marks.append((int(ts),float(equity)))
    def cancel(reason):
        nonlocal pending
        setups[pending['setup_index']]['status']='CANCEL_'+reason
        counters['cancel_'+reason.lower()]+=1
        pending=None
    def close(ts,price,reason,dual=False,gap_minutes=0):
        nonlocal balance,position
        p=position
        gross=p['qty']*p['d']*(int(price)-p['entry'])/scale
        commission=fee_cash(p['qty'],market.pair,config.cost_pips)
        net=gross-commission
        balance+=gross-commission/2
        trade={k:v for k,v in p.items() if k!='record'}
        trade.update(entry_ticks=p['entry'],exit_time=int(ts),exit_ticks=int(price),exit_reason=reason,gross_pnl=float(gross),commission=float(commission),net_pnl=float(net),net_r=float(net/p['risk_cash']),ending_balance=float(balance),dual_touch=bool(dual),gap_minutes=int(gap_minutes),holding_minutes=(int(ts)-p['entry_time'])/60)
        trades.append(trade)
        setups[p['setup_index']]['status']='CLOSED'
        position=None
        mark(ts,price)
    for bar_index,b in enumerate(f.itertuples(index=False)):
        bt=int(b.t); close_time=bt+900
        if not np.isnan(b.ph): sr_high.append((bar_index,int(b.ph)))
        if not np.isnan(b.pl): sr_low.append((bar_index,int(b.pl)))
        sr_high=[x for x in sr_high if bar_index-x[0]<=100]
        sr_low=[x for x in sr_low if bar_index-x[0]<=100]
        if close_time<start:
            continue
        if bt>=end and position is None and pending is None:
            break
        closed_bar=False
        current_allowed=start<=bt<end and 120<=b.current_minute<480
        if pending is not None and not current_allowed:
            cancel('session')
        if pending is not None or position is not None:
            for k in range(int(b.i0),int(b.i1)+1):
                ts=int(t[k]); quote=q[k]; prev=int(t[k-1]) if k>0 else ts-60
                gap=ts-prev>60
                if gap and pending is not None:
                    cancel('gap')
                if gap and position is not None:
                    position['crossed_gap']=True
                    if config.gap_policy=='penalty':
                        price=min(position['sl'],int(quote[0])) if position['d']==1 else max(position['sl'],int(quote[0]))
                        close(ts,price,'COVERAGE_GAP_STOP',gap_minutes=(ts-prev)//60-1)
                        closed_bar=True
                new_intramin=False
                if pending is not None:
                    event,ambiguous,at_open=pending_event(pending,quote,config.penetration,config.front_run)
                    if ambiguous:
                        counters['front_run_ambiguous_setups']+=1
                        pending['ambiguous_front_run']=True
                        setups[pending['setup_index']]['ambiguous_front_run']=True
                    if event=='cancel':
                        cancel('front_run')
                    elif event=='fill':
                        position=pending
                        pending=None
                        position['entry_time']=ts
                        position['entry_at_open']=bool(at_open)
                        position['crossed_gap']=False
                        balance-=fee_cash(position['qty'],market.pair,config.cost_pips)/2
                        setups[position['setup_index']]['status']='FILLED'
                        new_intramin=not at_open
                        mark(ts,position['entry'])
                if position is not None:
                    reason,price,dual=position_event(position,quote,config.penetration,new_intramin)
                    if reason:
                        close(ts,price,reason,dual)
                        closed_bar=True
                mark(ts+60,quote[3])
                if pending is None and position is None:
                    break
        mark(int(t[int(b.i1)])+60,b.c)
        next_allowed=start<=close_time<end and 120<=b.next_minute<480
        if pending is not None:
            if pending_expired(bar_index,pending['signal_bar'],config.ttl): cancel('expiry')
            elif not next_allowed: cancel('session')
        if position is not None or pending is not None or closed_bar or not next_allowed or not b.complete:
            continue
        direction=int(b.trend_a if config.trend=='structure' else b.trend_b)
        d=1 if direction==1 and b.c>b.o and b.o==b.l else -1 if direction==-1 and b.c<b.o and b.h==b.o else 0
        if not d:
            continue
        counters['candidate_nowicks']+=1
        pivot=int(b.lastPL if d==1 else b.lastPH)
        if pivot<=0:
            continue
        e,sl,tp=levels(d,int(b.o),int(b.c),pivot,config.rr,config.midpoint)
        dist=d*(e-sl)
        if not stop_valid(dist):
            counters['reject_stop']+=1
            continue
        if config.swing and (np.isnan(b.lo10) or (b.o<=b.lo10 if d==1 else b.o>=b.hi10)):
            continue
        last=last_long if d==1 else last_short
        if config.double and 2<=bar_index-last<=4:
            continue
        if config.sr and any((e<v<tp if d==1 else tp<v<e) for _,v in (sr_high if d==1 else sr_low)):
            continue
        qty=risk_quantity(balance,dist,market.pair)
        if qty<=0 or qty*e/scale/100>balance:
            counters['reject_margin']+=1
            continue
        record={'setup_index':len(setups),'signal_bar':bar_index,'signal_time':close_time,'d':d,'entry':e,'sl':sl,'tp':tp,'extreme':int(b.h if d==1 else b.l),'pivot':pivot,'qty':qty,'risk_cash':qty*dist/scale,'stop_pips':dist/10,'ambiguous_front_run':False}
        setups.append(record|{'status':'PENDING'})
        pending=record.copy()
        if d==1: last_long=bar_index
        else: last_short=bar_index
    if pending is not None:
        setups[pending['setup_index']]['status']='OPEN_PENDING_END'
    last_price=int(q[min(len(q)-1,int(f.iloc[-1].i1)),3])
    if marks:
        ending_equity=marks[-1][1]
    else:
        ending_equity=balance
    return {'trades':trades,'setups':setups,'marks':marks,'ending_balance':balance,'ending_equity':ending_equity,'open_position':position,'pending':pending,'counters':counters,'max_marked_dd_pct':100*max_dd}

def fixture_minutes(n):
    t=int(pd.Timestamp('2024-01-03T00:00Z').timestamp())+np.arange(n,dtype=np.int64)*60
    c=100000+np.rint(100*np.sin(np.arange(n)/17)).astype(np.int64)
    o=np.r_[c[0],c[:-1]]
    bid=np.column_stack([o,np.maximum(o,c)+3,np.minimum(o,c)-3,c])
    return {'t':t,'bid':bid,'ask':bid+10,'valid_bid':np.ones(n,bool),'valid_ask':np.ones(n,bool)}

def fixture_trade_market(gap=False,no_exit=False):
    raw=fixture_minutes(45)
    raw['t']=int(pd.Timestamp('2024-01-03T06:45Z').timestamp())+np.arange(45,dtype=np.int64)*60
    raw['bid'][:]=[100020,100030,100010,100020]
    raw['bid'][0]=[100000,100020,100000,100020]
    raw['bid'][15]=[100020,100025,99990,100005]
    if not no_exit: raw['bid'][16]=[100005,100140,100000,100130]
    raw['ask']=raw['bid']+10
    if gap: raw={k:np.delete(v,16,axis=0) for k,v in raw.items()}
    m=prepare_market(raw,'GBPUSD')
    m.features['trend_a']=0
    m.features.loc[0,'trend_a']=1
    m.features.loc[0,'lastPL']=99900
    return m
