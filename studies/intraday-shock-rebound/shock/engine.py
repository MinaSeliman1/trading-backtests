"""Past-only matched-clock shock normalization and conservative minute execution."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))
SIGNAL_FIELDS=('shock_return','history_mean','history_std','shock_z','shock_end','confirmation','signal_low','signal_high')

@dataclass(frozen=True)
class Config:
    mode:str='long'
    slippage:float=.01
    quality:str='complete_days'
    z_threshold:float=2.
    confirmation:bool=True
    z_filter:bool=True
    target_r:float=2.
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('long','short'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(v) and v>0 for v in (self.z_threshold,self.target_r,self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/threshold')

def valid_ohlc(a,i,n):
    p=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1)
    return np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))

def prepare(market,cash=None):
    a=market.arrays;N=len(market.dates);ends=np.arange(29,330,5)
    good=np.zeros((N,390),dtype=bool)
    for i,n in enumerate(market.lengths):good[i,:int(n)]=valid_ohlc(a,i,int(n))
    bad=np.column_stack([np.zeros(N,int),np.cumsum(~good,axis=1)])
    features=[dict(index=i,date=str(day.date()),session_minutes=int(market.lengths[i]),bars=[]) for i,day in enumerate(market.dates)]
    for end in ends:
        opened=market.lengths>end;ok=opened&((bad[:,end+1]-bad[:,end-29])==0)
        returns=np.full(N,np.nan);returns[ok]=np.log(a['close'][ok,end]/a['open'][ok,end-29])
        indices=np.flatnonzero(opened);series=pd.Series(returns[indices]);rolling=series.rolling(20,min_periods=20)
        means=rolling.mean().shift(1).to_numpy();stds=rolling.std(ddof=1).shift(1).to_numpy()
        for position,i in enumerate(indices):
            count=min(position,20);mu=float(means[position]);sd=float(stds[position]);raw=float(returns[i])
            reason='warmup_initial' if count<20 else 'unknown_history' if not math.isfinite(mu) or not math.isfinite(sd) else 'zero_variance' if sd<=1e-12 else 'ready'
            features[i]['bars'].append(dict(shock_end=int(end),valid=bool(ok[i]),state_reason=reason,prior_count=count,
                shock_return=raw,history_mean=mu,history_std=sd,shock_z=(raw-mu)/sd if reason=='ready' else np.nan,
                shock_close=float(a['close'][i,end]),shock_low=float(np.min(a['low'][i,end-29:end+1])),shock_high=float(np.max(a['high'][i,end-29:end+1])),
                confirmation_valid=bool(good[i,end+1:end+6].all()),confirmation_open=float(a['open'][i,end+1]),confirmation_close=float(a['close'][i,end+5]),
                confirmation_low=float(np.min(a['low'][i,end+1:end+6])),confirmation_high=float(np.max(a['high'][i,end+1:end+6]))))
    return features

def signal(market,f,cfg):
    warming=ready=False;side=1 if cfg.mode=='long' else -1
    for b in f['bars']:
        slot=b['shock_end']+(6 if cfg.confirmation else 1)
        if slot>f['session_minutes']-60:break
        state=b['state_reason']
        if state=='warmup_initial':warming=True;continue
        if state=='zero_variance':ready=True;continue
        if not b['valid']:return dict(reason='unknown_signal')
        if side*b['shock_return']>=0:ready=True;continue
        if state=='unknown_history':return dict(reason='unknown_history')
        ready=True
        if cfg.z_filter and side*b['shock_z']>-cfg.z_threshold+1e-10:continue
        low=b['shock_low'];high=b['shock_high'];price=b['shock_close']
        if cfg.confirmation:
            if not b['confirmation_valid']:return dict(reason='unknown_confirmation')
            price=b['confirmation_close']
            if side*(price-b['confirmation_open'])<=0 or side*(price-b['shock_close'])<=0:continue
            low=min(low,b['confirmation_low']);high=max(high,b['confirmation_high'])
        stop=float((D(low)-D('.01') if side>0 else D(high)+D('.01')).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING))
        if stop<=0 or side*(D(price)-D(stop))<=0:continue
        return dict(reason='eligible',sign=side,signal_slot=slot-1,entry_slot=slot,sizing_price=price,stop_price=stop,
            **{k:b[k] for k in ('shock_return','history_mean','history_std','shock_z','shock_end')},confirmation=cfg.confirmation,signal_low=low,signal_high=high)
    return dict(reason='warmup_initial' if warming and not ready else 'no_rebound')

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


TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','shock_return','history_mean','history_std','shock_z','shock_end','confirmation','signal_low','signal_high',
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
                        **{k:s[k] for k in SIGNAL_FIELDS},**p,entry_price=entry,exit_price=exit_price,price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),
                        friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,
                        entry_leverage=q*p['entry_reference']/before,entry_risk_pct=q*p['entry_risk_unit']/before*100,mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,equity=capital,
            trades=int(q>0),quantity=q,signal_sign=s.get('sign',0),commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
