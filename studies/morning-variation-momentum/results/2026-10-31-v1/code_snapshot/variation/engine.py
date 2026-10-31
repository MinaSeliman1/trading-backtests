"""Causal morning variation signal; local long-only hold-to-close execution."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))

@dataclass(frozen=True)
class Config:
    observation_minutes:int=60
    sampling_minutes:int=2
    min_history:int=252
    quantile:float=.90
    history_mode:str='expanding'
    metric:str='variation'
    exit_kind:str='open'
    quality:str='complete_days'
    slippage:float=.01
    initial_capital:float=100000.
    leverage_cap:float=1.
    def __post_init__(self):
        if self.sampling_minutes not in (1,2,5):raise ValueError('sampling')
        if not 2<=self.observation_minutes<=360 or self.observation_minutes%self.sampling_minutes:raise ValueError('observation')
        if not isinstance(self.min_history,int) or self.min_history<2:raise ValueError('history length')
        if not 0<self.quantile<1:raise ValueError('quantile')
        if self.history_mode not in ('expanding','rolling'):raise ValueError('history mode')
        if self.metric not in ('variation','return','always'):raise ValueError('metric')
        if self.exit_kind not in ('open','close'):raise ValueError('exit')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('friction')
        if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.leverage_cap)):raise ValueError('capital')

class Unresolved(Exception):
    def __init__(self,reason,slot):
        self.reason=reason;self.slot=slot
        super().__init__(reason)

def valid_bars(a,i,n):
    o,h,l,c,v=[a[k][i,:n] for k in ('open','high','low','close','volume')]
    return np.isfinite([o,h,l,c,v]).all(axis=0)&(o>0)&(l>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(v>=0)

def morning(m,i,cfg):
    n=cfg.observation_minutes
    x=dict(index=i,date=str(m.dates[i].date()),session_minutes=int(m.lengths[i]),signal_slot=n-1,
           sizing_price=None,log_return=None,variation=None,score=None)
    if m.lengths[i]!=390:return dict(x,reason='half_session')
    flag=str(m.quality.iloc[i].get('reason',''))
    if not set(flag.split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'}) or not valid_bars(m.arrays,i,n).all():return dict(x,reason='unknown_morning')
    prices=np.r_[m.arrays['open'][i,0],m.arrays['close'][i,cfg.sampling_minutes-1:n:cfg.sampling_minutes]]
    rr=np.diff(np.log(prices));v=float(np.sqrt(np.sum(rr*rr)));r=float(math.log(prices[-1]/prices[0]))
    x.update(sizing_price=float(prices[-1]),log_return=r,variation=v)
    if v<=1e-12:return dict(x,reason='zero_variation')
    return dict(x,score=r/v,reason='ready_morning')

def prepare(m,cfg):
    pool=[];features=[]
    for i in range(len(m.dates)):
        f=morning(m,i,cfg);used=pool if cfg.history_mode=='expanding' else pool[-cfg.min_history:]
        f.update(training_count=len(used),total_previous_eligible=len(pool),threshold=float(np.quantile(used,cfg.quantile,method='linear')) if len(used)>=cfg.min_history else None,
                 selection_value=f['log_return'] if cfg.metric=='return' else f['score'])
        if f['reason']=='ready_morning':
            f['reason']='ready' if len(used)>=cfg.min_history else 'warmup'
            pool.append(f['selection_value'])
        features.append(f)
    return features

def signal(f,cfg):
    reason=f['reason']
    if reason=='ready':
        reason='eligible' if cfg.metric=='always' or f['selection_value']>f['threshold']+1e-12 else 'no_signal'
    return dict(f,reason=reason)

def execute(m,f,cfg):
    i=f['index'];entry=cfg.observation_minutes+1;last=int(m.lengths[i])-1;a=m.arrays
    ref=float(a['open'][i,entry])
    if not math.isfinite(ref) or ref<=0:raise Unresolved('missing_entry_open',entry)
    stop=last if cfg.exit_kind=='open' else last+1
    valid=valid_bars(a,i,stop)
    bad=np.flatnonzero(~valid[entry:stop])
    if len(bad):raise Unresolved('missing_active_ohlcv',entry+int(bad[0]))
    out=float(a[cfg.exit_kind][i,last])
    if not math.isfinite(out) or out<=0:raise Unresolved('missing_exit_reference',last)
    if out-cfg.slippage<=0:raise ValueError('nonpositive fill')
    opened=pd.Timestamp(m.quality.iloc[i].session_open)
    return dict(entry_slot=entry,exit_slot=last,entry_reference=ref,exit_reference=out,
      entry_time=str(opened+pd.Timedelta(minutes=entry)),exit_time=str(opened+pd.Timedelta(minutes=last+(cfg.exit_kind=='close'))),
      holding_minutes=stop-entry,closes=a['close'][i,entry:stop].tolist(),
      lows=a['low'][i,entry:stop].tolist(),highs=a['high'][i,entry:stop].tolist())

TRADE_COLUMNS=['date','symbol','quality','direction','quantity','signal_slot','sizing_price','score','log_return','variation','threshold','training_count',
 'entry_slot','exit_slot','entry_reference','exit_reference','entry_time','exit_time','holding_minutes','entry_price','exit_price',
 'price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage',
 'entry_fill_leverage','mae_price_usd','mfe_price_usd']
UNKNOWN_COLUMNS=['date','symbol','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']

def simulate(m,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unknown=[]
    for f in features:
        if not start<=f['date']<=end:continue
        i=f['index'];date=f['date'];s=signal(f,cfg);why=s['reason'];excluded=why.startswith('unknown_')
        before=capital;net=fee=friction=0.;qty=minutes=0;marks=[capital]
        if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            q=int((D(capital)*D(cfg.leverage_cap)/D(f['sizing_price'])).to_integral_value(rounding=ROUND_FLOOR))
            if q<=0:why='zero_quantity'
            else:
                try:p=execute(m,f,cfg)
                except Unresolved as e:
                    why='unresolved_execution';excluded=True;ref=float(m.arrays['open'][i,cfg.observation_minutes+1]);known=math.isfinite(ref) and ref>0
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,reason=e.reason,first_unknown_slot=e.slot,entry_reference=ref if known else None,
                        known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=p['holding_minutes'];entry=p['entry_reference']+cfg.slippage;exit_price=p['exit_reference']-cfg.slippage
                    fee=2*max(.35,q*.0035);friction=2*q*cfg.slippage;gross=q*(exit_price-entry);net=gross-fee;capital+=net
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*(x-entry) for x in p.pop('closes')],capital]
                    mae=q*(min([entry,exit_price,*p.pop('lows')])-entry);mfe=q*(max([entry,exit_price,*p.pop('highs')])-entry)
                    trades.append(dict(date=date,symbol=m.symbol,quality=cfg.quality,direction='LONG',quantity=q,signal_slot=f['signal_slot'],sizing_price=f['sizing_price'],
                       **{k:f[k] for k in ('score','log_return','variation','threshold','training_count')},**p,entry_price=entry,exit_price=exit_price,
                       price_move_pnl=q*(p['exit_reference']-p['entry_reference']),friction_cost=friction,commission=fee,borrow_fee=0.,gross_pnl=gross,net_pnl=net,
                       net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,
                       entry_fill_leverage=q*entry/before,mae_price_usd=mae,mfe_price_usd=mfe))
        vals=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,vals])[1:]
        dd=max(dd,float(np.max((peaks-vals)/peaks)));usd=max(usd,float(np.max(peaks-vals)));peak=max(peak,float(vals.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,
            return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,holding_minutes=minutes,
            observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unknown,columns=UNKNOWN_COLUMNS),
       initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
