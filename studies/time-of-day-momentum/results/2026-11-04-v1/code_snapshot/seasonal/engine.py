"""Past-session same-clock mean; one causal short-lived trade per session."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from types import SimpleNamespace
import hashlib,math
import numpy as np
import pandas as pd

D=lambda x:Decimal(str(x))
CLOCKS=np.arange(30,331,30,dtype=int)
MODES=('both','long_only','inverse','control_same_clock_long','control_fixed_clock','control_random_clock')

@dataclass(frozen=True)
class Config:
    lookback:int=40
    threshold:float=1.5
    stop_multiple:float=2.
    mode:str='both'
    quality:str='complete_days'
    slippage:float=.01
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    seed:int=20261104
    def __post_init__(self):
        if not isinstance(self.lookback,int) or self.lookback<2:raise ValueError('lookback')
        if self.mode not in MODES:raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('slippage')
        if not all(math.isfinite(v) and v>0 for v in (self.threshold,self.stop_multiple,self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('config')

class Unresolved(Exception):
    def __init__(self,reason,slot):self.reason=reason;self.slot=slot;super().__init__(reason)


def valid_bars(a,i,n):
    o,h,l,c,v=[a[k][i,:n] for k in ('open','high','low','close','volume')]
    return np.isfinite([o,h,l,c,v]).all(axis=0)&(o>0)&(l>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(v>=0)


def source_ok(m,i):
    return set(str(m.quality.iloc[i].get('reason','')).split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'})


def training(m,lookback):
    n=len(m.dates);returns=np.full((n,len(CLOCKS)),np.nan)
    for i in range(n):
        if not source_ok(m,i):continue
        good=valid_bars(m.arrays,i,int(m.lengths[i]))
        for col,k in enumerate(CLOCKS):
            if k+31<int(m.lengths[i]) and good[k+1:k+32].all():
                returns[i,col]=m.arrays['open'][i,k+31]/m.arrays['open'][i,k+1]-1.
    frame=pd.DataFrame(returns);roll=frame.rolling(lookback,min_periods=lookback)
    mean=roll.mean().shift(1).to_numpy();std=roll.std(ddof=1).shift(1).to_numpy()
    count=frame.rolling(lookback,min_periods=1).count().shift(1).fillna(0).to_numpy()
    std=np.where(np.isfinite(std)&(std<=1e-12),0.,std)
    t=np.divide(mean*np.sqrt(lookback),std,out=np.full_like(mean,np.nan),where=std>0)
    return dict(returns=returns,mean=mean,std=std,count=count,t=t,lookback=lookback)


def historical_candidate(m,i,c,h):
    if i<c.lookback:return dict(reason='warmup',historical_slot=None,reference_sign=0)
    available=[int(k) for k in CLOCKS if k+31<int(m.lengths[i])]
    if not source_ok(m,i):return dict(reason='unknown_source',historical_slot=None,reference_sign=0)
    for k in available:
        col=int(k//30-1)
        if h['count'][i,col]!=c.lookback or not np.isfinite(h['std'][i,col]):
            return dict(reason='unknown_history',historical_slot=None,reference_sign=0)
        if h['std'][i,col]>0 and abs(h['t'][i,col])>=c.threshold:
            return dict(reason='candidate',historical_slot=k,reference_sign=1 if h['mean'][i,col]>0 else -1,historical_t=float(h['t'][i,col]))
    return dict(reason='no_signal',historical_slot=None,reference_sign=0)


def random_clock(symbol,date,available,seed):
    raw=hashlib.sha256(f'{seed}|{symbol}|{date}'.encode()).digest()
    return available[int.from_bytes(raw,'big')%len(available)]


def select(m,i,c,h):
    f=dict(index=i,date=str(m.dates[i].date()),symbol=m.symbol,session_minutes=int(m.lengths[i]),historical_slot=None,reference_sign=0,
           historical_t=None,decision_slot=None,entry_slot=None,scheduled_exit_slot=None,sizing_price=None,stop_price=None,history_mean=None,history_sigma=None,history_t=None,sign=0)
    candidate=historical_candidate(m,i,c,h);f.update(candidate)
    if candidate['reason']!='candidate':return f
    k=candidate['historical_slot'];sign=candidate['reference_sign']
    if c.mode=='long_only' and sign<0:return dict(f,reason='direction_filtered')
    if c.mode=='inverse':sign=-sign
    if c.mode=='control_same_clock_long':sign=1
    if c.mode=='control_fixed_clock':k=30
    if c.mode=='control_random_clock':k=random_clock(m.symbol,f['date'],[int(x) for x in CLOCKS if x+31<int(m.lengths[i])],c.seed)
    return feature_at(m,i,c,h,f,k,sign)


def feature_at(m,i,c,h,f,k,sign):
    f=dict(f);col=int(k//30-1);f.update(decision_slot=k,entry_slot=k+1,scheduled_exit_slot=k+31,sign=sign)
    if h['count'][i,col]!=c.lookback or not np.isfinite(h['std'][i,col]):return dict(f,reason='unknown_control_history')
    if not valid_bars(m.arrays,i,k).all():return dict(f,reason='unknown_current_context')
    price=float(m.arrays['close'][i,k-1]);sigma=float(h['std'][i,col]);width=max(D('.02'),D(c.stop_multiple)*D(sigma)*D(price))
    stop=(D(price)-sign*width).quantize(D('.01'),rounding=ROUND_FLOOR if sign>0 else ROUND_CEILING)
    f.update(sizing_price=price,stop_price=float(stop),history_mean=float(h['mean'][i,col]),history_sigma=sigma,history_t=float(h['t'][i,col]) if np.isfinite(h['t'][i,col]) else None)
    return dict(f,reason='eligible' if stop>0 else 'invalid_stop')


def prepare(m,c,history=None):
    h=training(m,c.lookback) if history is None else history
    if h['lookback']!=c.lookback:raise ValueError('history/config mismatch')
    return [select(m,i,c,h) for i in range(len(m.dates))]


def trace(m,f,c):
    i=f['index'];a=m.arrays;left=f['entry_slot'];end=f['scheduled_exit_slot'];stop=f['stop_price'];sign=f['sign']
    entry=float(a['open'][i,left]);good=valid_bars(a,i,int(m.lengths[i]));closes=[];lows=[];highs=[];resolution='bar_open'
    if not math.isfinite(entry) or entry<=0:raise Unresolved('missing_entry_open',left)
    for j in range(left,end+1):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:raise Unresolved('missing_active_open',j)
        if sign*(op-stop)<=0:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==end:ref=op;why='scheduled_open';break
        if not good[j]:raise Unresolved('invalid_active_bar',j)
        hit=a['low'][i,j]<=stop if sign>0 else a['high'][i,j]>=stop
        if hit:ref=stop;why='stop_intrabar';resolution='intrabar_minute_unknown';break
        closes.append(float(a['close'][i,j]));lows.append(float(a['low'][i,j]));highs.append(float(a['high'][i,j]))
    opened=pd.Timestamp(m.quality.iloc[i].session_open)
    return dict(exit_slot=j,entry_reference=entry,exit_reference=float(ref),entry_time=str(opened+pd.Timedelta(minutes=left)),exit_time=str(opened+pd.Timedelta(minutes=j)),
                exit_reason=why,exit_resolution=resolution,ambiguous_bar=False,holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=closes,lows=lows,highs=highs)


def quantity(capital,price,stop,sign,c):
    risk=sign*(D(price)-D(stop))
    if risk<=0:return 0
    return int(min(D(capital)*D(c.leverage_cap)/D(price),D(capital)*D(c.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))

FEATURES=('historical_slot','reference_sign','historical_t','decision_slot','entry_slot','scheduled_exit_slot','sizing_price','stop_price','history_mean','history_sigma','history_t')
TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity',*FEATURES,'exit_slot','entry_reference','exit_reference','entry_time','exit_time','exit_reason','exit_resolution','ambiguous_bar','holding_minutes_upper','entry_price','exit_price','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_fill_leverage','entry_risk_pct','modeled_stop_net_risk_pct','mae_observed_usd','mfe_observed_usd','half_session']
UNKNOWN_COLUMNS=['date','symbol','quantity','sign','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']


def priced_path(p,f,q,c):
    sign=f['sign'];entry=p['entry_reference']+sign*c.slippage;exit_price=p['exit_reference']-sign*c.slippage
    if min(entry,exit_price)<=0:raise ValueError('nonpositive modeled fill')
    fee=2*max(.35,q*.0035);friction=2*q*c.slippage;borrow=q*entry*.01/360 if sign<0 else 0.;gross=q*sign*(exit_price-entry);net=gross-fee-borrow
    return dict(entry_price=entry,exit_price=exit_price,price_move_pnl=q*sign*(p['exit_reference']-p['entry_reference']),friction_cost=friction,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000)


def simulate(m,features,c,start,end):
    capital=c.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unknown=[]
    for f in features:
        if not start<=f['date']<=end:continue
        i=f['index'];date=f['date'];why=f['reason'];excluded=why.startswith('unknown_');before=capital;qty=minutes=0;net=fee=friction=borrow=0.;marks=[capital]
        if why=='eligible' and c.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            q=quantity(capital,f['sizing_price'],f['stop_price'],f['sign'],c)
            if q<=0:why='zero_quantity'
            else:
                try:p=trace(m,f,c)
                except Unresolved as e:
                    why='unresolved_execution';excluded=True;entry=float(m.arrays['open'][i,f['entry_slot']]);known=math.isfinite(entry) and entry>0
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,sign=f['sign'],reason=e.reason,first_unknown_slot=e.slot,entry_reference=entry if known else None,known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*c.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=p['holding_minutes_upper'];v=priced_path(p,f,q,c);net=v['net_pnl'];fee=v['commission'];friction=v['friction_cost'];borrow=v['borrow_fee'];capital+=net;sign=f['sign'];entry=v['entry_price']
                    marks=[before,before-fee/2-q*c.slippage,*[before-fee/2+q*sign*(x-entry) for x in p.pop('closes')],capital]
                    adverse=p.pop('lows' if sign>0 else 'highs');favorable=p.pop('highs' if sign>0 else 'lows')
                    mae=min(0.,*([q*sign*(x-entry) for x in [entry,v['exit_price'],p['entry_reference'],*adverse]]));mfe=max(0.,*([q*sign*(x-entry) for x in [entry,v['exit_price'],p['entry_reference'],*favorable]]))
                    worst_exit=(min(f['stop_price'],p['entry_reference']) if sign>0 else max(f['stop_price'],p['entry_reference']))-sign*c.slippage
                    trades.append(dict(date=date,symbol=m.symbol,mode=c.mode,quality=c.quality,direction='LONG' if sign>0 else 'SHORT',sign=sign,quantity=q,**{k:f[k] for k in FEATURES},**p,**v,equity_before=before,equity_after=capital,
                                       entry_leverage=q*p['entry_reference']/before,entry_fill_leverage=q*entry/before,entry_risk_pct=q*max(0.,sign*(p['entry_reference']-f['stop_price']))/before*100,
                                       modeled_stop_net_risk_pct=(max(0.,q*sign*(entry-worst_exit))+fee+borrow)/before*100,mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(m.lengths[i])!=390))
        vals=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,vals])[1:];dd=max(dd,float(np.max((peaks-vals)/peaks)));usd=max(usd,float(np.max(peaks-vals)));peak=max(peak,float(vals.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,borrow_fee=borrow,holding_minutes_upper=minutes,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unknown,columns=UNKNOWN_COLUMNS),initial_capital=c.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
