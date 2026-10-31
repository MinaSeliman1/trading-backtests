"""Bollinger re-entry: causal completed bars and one conservative intraday attempt."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))
FIELDS=('bar_index','decision_slot','signal_slot','entry_slot','sizing_price','stop_price','target_price','middle','lower','previous_lower','previous_close')
@dataclass(frozen=True)
class Config:
    lookback:int=20
    band:float=2.
    bar_minutes:int=5
    start_minute:int=105
    end_minute:int=300
    entry_rule:str='reentry'
    target_kind:str='middle'
    entry_delay:int=1
    quality:str='complete_days'
    slippage:float=.01
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if not isinstance(self.lookback,int) or self.lookback<2:raise ValueError('lookback')
        if self.bar_minutes not in (5,10):raise ValueError('bar size')
        if not math.isfinite(self.band) or self.band<=0:raise ValueError('band')
        if not 0<=self.start_minute<self.end_minute<=360:raise ValueError('time window')
        if self.entry_rule not in ('reentry','outside_touch'):raise ValueError('entry rule')
        if self.target_kind not in ('middle','one_r'):raise ValueError('target')
        if self.entry_delay not in (0,1):raise ValueError('delay')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk')

class Unresolved(Exception):
    def __init__(self,reason,slot):self.reason=reason;self.slot=slot;super().__init__(reason)

def valid_bars(a,i,n):
    o,h,l,c,v=[a[k][i,:n] for k in ('open','high','low','close','volume')]
    return np.isfinite([o,h,l,c,v]).all(axis=0)&(o>0)&(l>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(v>=0)

def select(m,i,c):
    base=dict(index=i,date=str(m.dates[i].date()),session_minutes=int(m.lengths[i]),**{k:None for k in FIELDS})
    if m.lengths[i]!=390:return dict(base,reason='half_session')
    flag=str(m.quality.iloc[i].get('reason',''))
    if not set(flag.split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'}):return dict(base,reason='unknown_source')
    n=390;b=c.bar_minutes;a=m.arrays;count=n//b
    closes=a['close'][i,:count*b].reshape(count,b)[:,-1]
    lows=a['low'][i,:count*b].reshape(count,b).min(axis=1)
    mean=pd.Series(closes).rolling(c.lookback,min_periods=c.lookback).mean().to_numpy()
    std=pd.Series(closes).rolling(c.lookback,min_periods=c.lookback).std(ddof=0).to_numpy()
    lower=mean-c.band*std;bad=np.cumsum(~valid_bars(a,i,n))
    first=max(c.lookback,math.ceil(c.start_minute/b)-1)
    for j in range(first,count):
        end=(j+1)*b
        if end>c.end_minute:break
        if bad[end-1]:return dict(base,reason='unknown_scan')
        setup=(closes[j-1]<lower[j-1]-1e-10 and closes[j]>lower[j]+1e-10) if c.entry_rule=='reentry' else closes[j]<lower[j]-1e-10
        if not setup:continue
        stop=float(D(float(min(lows[j-1:j+1]))).quantize(D('.01'),rounding=ROUND_FLOOR)-D('.01'))
        target=float((D(float(mean[j])).quantize(D('.00000001')) if c.target_kind=='middle' else 2*D(float(closes[j]))-D(stop)).quantize(D('.01'),rounding=ROUND_FLOOR))
        if not D(0)<D(stop)<D(float(closes[j]))<D(target):continue
        return dict(base,reason='eligible',bar_index=j,decision_slot=end,signal_slot=end-1,entry_slot=end+c.entry_delay,
           sizing_price=float(closes[j]),stop_price=stop,target_price=target,middle=float(mean[j]),lower=float(lower[j]),previous_lower=float(lower[j-1]),previous_close=float(closes[j-1]))
    return dict(base,reason='no_signal')

def prepare(m,c):return [select(m,i,c) for i in range(len(m.dates))]

def trace(m,f,c):
    i=f['index'];a=m.arrays;left=f['entry_slot'];stop=f['stop_price'];target=f['target_price'];n=int(m.lengths[i])
    entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise Unresolved('missing_entry_open',left)
    good=valid_bars(a,i,n);held=[];lows=[];highs=[];amb=False;resolution='bar_open'
    for j in range(left,n):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:raise Unresolved('missing_active_open',j)
        if op<=stop:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';break
        if op>=target:ref=op;why='entry_marketable_target' if j==left else 'target_gap';break
        if j==n-1:ref=op;why='eod_open';break
        if not good[j]:raise Unresolved('invalid_active_bar',j)
        sh=a['low'][i,j]<=stop;th=a['high'][i,j]>=target
        if sh or th:
            ref=stop if sh else target;why='stop_intrabar' if sh else 'target_intrabar'
            amb=bool(sh and th);resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]));lows.append(float(a['low'][i,j]));highs.append(float(a['high'][i,j]))
    opened=pd.Timestamp(m.quality.iloc[i].session_open)
    return dict(exit_slot=j,entry_reference=entry,exit_reference=float(ref),entry_time=str(opened+pd.Timedelta(minutes=left)),
       exit_time=str(opened+pd.Timedelta(minutes=j)),exit_reason=why,exit_resolution=resolution,ambiguous_bar=amb,
       holding_minutes=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,lows=lows,highs=highs)

TRADE_COLUMNS=['date','symbol','quality','direction','quantity',*FIELDS,'exit_slot','entry_reference','exit_reference','entry_time','exit_time','exit_reason','exit_resolution','ambiguous_bar',
 'holding_minutes','entry_price','exit_price','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after',
 'entry_leverage','entry_fill_leverage','entry_risk_pct','modeled_stop_net_risk_pct','mae_price_usd','mfe_price_usd']
UNKNOWN_COLUMNS=['date','symbol','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']
def simulate(m,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unknown=[]
    for f in features:
        if not start<=f['date']<=end:continue
        i=f['index'];date=f['date'];why=f['reason'];excluded=why.startswith('unknown_')
        before=capital;net=fee=friction=0.;qty=minutes=0;marks=[capital]
        if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            risk=D(f['sizing_price'])-D(f['stop_price'])
            q=int(min(D(capital)*D(cfg.leverage_cap)/D(f['sizing_price']),D(capital)*D(cfg.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))
            if q<=0:why='zero_quantity'
            else:
                try:p=trace(m,f,cfg)
                except Unresolved as e:
                    why='unresolved_execution';excluded=True;ref=float(m.arrays['open'][i,f['entry_slot']]);known=math.isfinite(ref) and ref>0
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,reason=e.reason,first_unknown_slot=e.slot,entry_reference=ref if known else None,
                        known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=p['holding_minutes'];entry=p['entry_reference']+cfg.slippage;exit_price=p['exit_reference']-cfg.slippage
                    if min(entry,exit_price)<=0:raise ValueError('nonpositive fill')
                    fee=2*max(.35,q*.0035);friction=2*q*cfg.slippage;gross=q*(exit_price-entry);net=gross-fee;capital+=net
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*(x-entry) for x in p.pop('closes')],capital]
                    mae=q*(min([entry,exit_price,*p.pop('lows')])-entry);mfe=q*(max([entry,exit_price,*p.pop('highs')])-entry)
                    trades.append(dict(date=date,symbol=m.symbol,quality=cfg.quality,direction='LONG',quantity=q,**{k:f[k] for k in FIELDS},**p,
                       entry_price=entry,exit_price=exit_price,price_move_pnl=q*(p['exit_reference']-p['entry_reference']),friction_cost=friction,commission=fee,borrow_fee=0.,
                       gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,
                       entry_fill_leverage=q*entry/before,entry_risk_pct=q*max(0,p['entry_reference']-f['stop_price'])/before*100,
                       modeled_stop_net_risk_pct=(q*max(0,entry-(min(f['stop_price'],p['entry_reference'])-cfg.slippage))+fee)/before*100,mae_price_usd=mae,mfe_price_usd=mfe))
        vals=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,vals])[1:];dd=max(dd,float(np.max((peaks-vals)/peaks)));usd=max(usd,float(np.max(peaks-vals)));peak=max(peak,float(vals.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,
            return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,holding_minutes=minutes,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unknown,columns=UNKNOWN_COLUMNS),
      initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
