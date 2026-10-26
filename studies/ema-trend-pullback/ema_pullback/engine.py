"""Causal EMA pullback; frozen next-open sizing and conservative minute fills."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
import math
import numpy as np
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))
EPS=1e-10

@dataclass(frozen=True)
class Config:
    mode:str='both'
    slippage:float=.01
    quality:str='complete_days'
    bar_minutes:int=5
    earliest:int=15
    cutoff:int=270
    target_r:float=2.
    require_slope:bool=True
    momentum_fraction:float=.7
    allow_deep:bool=False
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('both','long_only','short_only'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if self.bar_minutes!=5 or not 0<self.earliest<self.cutoff<=390:raise ValueError('window')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not math.isfinite(self.momentum_fraction) or not 0<=self.momentum_fraction<=1:raise ValueError('momentum')
        if not all(math.isfinite(v) and v>0 for v in (self.target_r,self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/capital')

def valid_ohlc(a,i,n):
    p=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1)
    return np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))

def prepare(market,cash,bar_minutes=5):
    if bar_minutes!=5:raise ValueError('only5min')
    if any(not math.isfinite(float(x)) or float(x)<0 for x in cash.values()):raise ValueError('cash')
    a=market.arrays;features=[];history=[];count=0;previous=np.nan;ever=False;origin='warmup_initial'
    for i,day in enumerate(market.dates):
        n=int(market.lengths[i]);date=str(day.date());div=float(cash.get(date,0))
        if history:
            history=[(x-div,y-div) for x,y in history];previous-=div
            if any(min(pair)<=0 for pair in history) or previous<=0:history=[];count=0;previous=np.nan;origin='unknown_indicator_history'
        start=dict(opening_fast=history[-1][0] if history else np.nan,opening_slow=history[-1][1] if history else np.nan,starting_count=count)
        valid=valid_ohlc(a,i,n);bars=[]
        for left in range(0,n,5):
            end=left+5;ok=bool(valid[left:end].all());fast,slow=history[-1] if history else (np.nan,np.nan)
            slopes=(fast-history[-4][0],slow-history[-4][1]) if len(history)>=4 else (np.nan,np.nan)
            reason='ready' if count>=60 else origin
            bar=dict(left=left,entry_slot=end,valid=ok,state_reason=reason,ema_fast=fast,ema_slow=slow,slope_fast=slopes[0],slope_slow=slopes[1],previous_close=previous,
                open=float(a['open'][i,left]),high=float(np.max(a['high'][i,left:end])),low=float(np.min(a['low'][i,left:end])),close=float(a['close'][i,end-1]))
            bars.append(bar)
            if not ok:
                history=[];count=0;previous=np.nan
                if ever:origin='unknown_indicator_history'
                continue
            close=bar['close'];updated=(.2*close+.8*fast,(2/21)*close+(19/21)*slow) if history else (close,close)
            history=(history+[updated])[-4:];previous=close;count+=1;ever=True
        features.append(dict(index=i,date=date,bar_minutes=5,session_minutes=n,cash_dividend=div,**start,ending_count=count,invalid_bars=sum(not b['valid'] for b in bars),bars=bars))
    return features

def signal(market,f,cfg):
    if f['bar_minutes']!=cfg.bar_minutes:raise ValueError('feature window mismatch')
    warming=False;ready=False
    for b in f['bars']:
        end=b['entry_slot']
        if end<cfg.earliest:continue
        if end>=min(cfg.cutoff,f['session_minutes']-1):break
        if not b['valid']:return dict(reason='unknown_signal')
        if b['state_reason']=='warmup_initial':warming=True;continue
        if b['state_reason']!='ready':return dict(reason='unknown_indicator_history')
        ready=True;fast=b['ema_fast'];slow=b['ema_slow'];close=b['close'];low=b['low'];high=b['high']
        for side in (1,-1):
            if side*(fast-slow)<=EPS or side*(b['previous_close']-fast)<=EPS:continue
            if cfg.require_slope and (side*b['slope_fast']<=EPS or side*b['slope_slow']<=EPS):continue
            if side*(close-fast)<=EPS or side*(D(close)-D(b['open']))<=0:continue
            if side>0:
                touch=low<=fast+EPS and (cfg.allow_deep or low>=slow-EPS)
                force=D(close)-D(low)
            else:
                touch=high>=fast-EPS and (cfg.allow_deep or high<=slow+EPS)
                force=D(high)-D(close)
            if not touch or high<=low or force<D(cfg.momentum_fraction)*(D(high)-D(low)):continue
            if cfg.mode=='long_only' and side<0 or cfg.mode=='short_only' and side>0:return dict(reason='direction_filtered')
            stop=(D(low)-D('.01') if side>0 else D(high)+D('.01')).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING)
            return dict(reason='eligible',sign=side,signal_slot=end-1,entry_slot=end,sizing_price=close,stop_price=float(stop),signal_low=low,signal_high=high,
                **{k:b[k] for k in ('ema_fast','ema_slow','slope_fast','slope_slow','previous_close')})
    return dict(reason='warmup_initial' if warming and not ready else 'no_pullback')

from types import SimpleNamespace
import pandas as pd

def trace(market,f,s,cfg):
    import pandas as pd
    a=market.arrays;i=f['index'];n=int(market.lengths[i]);side=s['sign'];left=s['entry_slot'];stop=s['stop_price']
    entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise UnresolvedExecution('missing_entry_open',left)
    risk=side*(D(entry)-D(stop));target=float((D(entry)+side*D(cfg.target_r)*max(D(0),risk)).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING))
    good=valid_ohlc(a,i,n);held=[];adverse=[entry];favorable=[entry];resolution='bar_open';ambiguous=False
    for j in range(left,n):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:raise UnresolvedExecution('missing_active_open',j)
        if side*(D(op)-D(stop))<=0:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';break
        if side*(D(op)-D(target))>=0:ref=target;why='target_gap';break
        if j==n-1:ref=op;why='eod_open';break
        if not good[j]:raise UnresolvedExecution('invalid_active_bar',j)
        sh=a['low'][i,j]<=stop if side>0 else a['high'][i,j]>=stop
        th=a['high'][i,j]>=target if side>0 else a['low'][i,j]<=target
        ambiguous=bool(sh and th)
        if sh or th:ref=stop if sh else target;why='stop_intrabar' if sh else 'target_intrabar';resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]));adverse.append(float(a['low' if side>0 else 'high'][i,j]));favorable.append(float(a['high' if side>0 else 'low'][i,j]))
    adverse.append(ref);favorable.append(ref);op=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(entry_slot=left,exit_slot=j,entry_reference=entry,exit_reference=float(ref),stop_price=stop,target_price=target,entry_risk_unit=max(0.,float(risk)),sign=side,
        entry_time=str(op+pd.Timedelta(minutes=left)),exit_time=str(op+pd.Timedelta(minutes=j)),exit_reason=why,exit_resolution=resolution,ambiguous_bar=ambiguous,
        holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,adverse=adverse,favorable=favorable)

from types import SimpleNamespace
import pandas as pd

TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','cash_dividend','ema_fast','ema_slow','slope_fast','slope_slow','previous_close','signal_low','signal_high',
    'entry_slot','exit_slot','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','stop_price','target_price','entry_risk_unit','exit_reason','exit_resolution',
    'holding_minutes_upper','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_risk_pct',
    'mae_observed_usd','mfe_observed_usd','half_session','ambiguous_bar']

def simulate(market,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unresolved=[]
    for f in features:
        date=f['date'];i=f['index']
        if not start<=date<=end:continue
        s=signal(market,f,cfg);why=s['reason'];excluded=why.startswith('unknown_');before=capital;net=fee=borrow=0.;q=upper=0;marks=[before]
        if why=='eligible' and cfg.quality=='complete_days' and not market.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            side=s['sign'];risk=side*(D(s['sizing_price'])-D(s['stop_price']))
            quantity=int(min(D(capital)*D(cfg.leverage_cap)/D(s['sizing_price']),D(capital)*D(cfg.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))
            if quantity<=0:why='zero_quantity'
            else:
                try:p=trace(market,f,s,cfg)
                except UnresolvedExecution as e:
                    why='unresolved_execution';excluded=True;ref=float(market.arrays['open'][i,s['entry_slot']]);known=math.isfinite(ref) and ref>0
                    unresolved.append(dict(date=date,symbol=market.symbol,sign=side,quantity=quantity,reason=e.reason,first_unknown_slot=e.minute,
                        entry_reference=ref if known else None,known_entry_commission=max(.35,quantity*.0035) if known else 0.,known_entry_friction=quantity*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    q=quantity;entry=p['entry_reference']+side*cfg.slippage;exit_price=p['exit_reference']-side*cfg.slippage
                    if min(entry,exit_price)<=0:raise ValueError('nonpositive modeled fill')
                    fee=2*max(.35,q*.0035);borrow=q*entry*.01/360 if side<0 else 0.;gross=q*side*(exit_price-entry);net=gross-fee-borrow;capital+=net;upper=p['holding_minutes_upper']
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*side*(c-entry) for c in p.pop('closes')],capital]
                    mae=min(0.,min(q*side*(x-entry) for x in p.pop('adverse')));mfe=max(0.,max(q*side*(x-entry) for x in p.pop('favorable')))
                    trades.append(dict(date=date,symbol=market.symbol,mode=cfg.mode,quality=cfg.quality,direction='LONG' if side>0 else 'SHORT',quantity=q,signal_slot=s['signal_slot'],sizing_price=s['sizing_price'],
                        cash_dividend=f['cash_dividend'],**{k:s[k] for k in ('ema_fast','ema_slow','slope_fast','slope_slow','previous_close','signal_low','signal_high')},**p,entry_price=entry,exit_price=exit_price,price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),
                        friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,
                        entry_leverage=q*p['entry_reference']/before,entry_risk_pct=q*p['entry_risk_unit']/before*100,mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,equity=capital,
            trades=int(q>0),quantity=q,signal_sign=s.get('sign',0),commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
