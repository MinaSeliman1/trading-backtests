"""Previous-session IBS; causal sizing, fixed ADR stop and same-day exit."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))
SIGNAL_FIELDS=('ibs_previous','adr','previous_close','sma200')

@dataclass(frozen=True)
class Config:
    mode:str='long_only'
    slippage:float=.01
    quality:str='complete_days'
    threshold:float=.2
    trend_filter:bool=False
    entry_slot:int=1
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('long_only','short_only','both','always_long'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.threshold) or not 0<self.threshold<.5:raise ValueError('threshold')
        if self.entry_slot not in (1,5):raise ValueError('entry_slot')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(v) and v>0 for v in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/capital')

def valid_ohlc(a,i,n):
    p=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1)
    return np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))

def prepare(market,cash=None):
    a=market.arrays;high=[];low=[];close=[]
    for i,n in enumerate(market.lengths):
        n=int(n);good=bool(valid_ohlc(a,i,n).all())
        high.append(float(np.max(a['high'][i,:n])) if good else np.nan)
        low.append(float(np.min(a['low'][i,:n])) if good else np.nan)
        close.append(float(a['close'][i,n-1]) if good else np.nan)
    high=np.array(high);low=np.array(low);close=np.array(close);width=high-low
    with np.errstate(invalid='ignore',divide='ignore'):ibs=np.where(width==0,.5,(close-low)/width)
    prev=pd.Series(ibs).shift(1).to_numpy();adr=pd.Series(width).rolling(14,min_periods=14).mean().shift(1).to_numpy()
    sma=pd.Series(close).rolling(200,min_periods=200).mean().shift(1).to_numpy();last=pd.Series(close).shift(1).to_numpy()
    return [dict(index=i,date=str(d.date()),session_minutes=int(market.lengths[i]),ibs_previous=float(prev[i]),adr=float(adr[i]),previous_close=float(last[i]),sma200=float(sma[i])) for i,d in enumerate(market.dates)]

def signal(market,f,cfg):
    if f['index']<max(14,200 if cfg.trend_filter else 14):return dict(reason='warmup')
    if not np.isfinite([f['ibs_previous'],f['adr'],f['previous_close']]).all() or cfg.trend_filter and not math.isfinite(f['sma200']):return dict(reason='unknown_history')
    if f['adr']<=0:return dict(reason='zero_range_history')
    ibs=f['ibs_previous'];side=1 if cfg.mode=='always_long' or cfg.mode in ('long_only','both') and ibs<=cfg.threshold+1e-12 else -1 if cfg.mode in ('short_only','both') and ibs>=1-cfg.threshold-1e-12 else 0
    if not side:return dict(reason='no_signal')
    if cfg.trend_filter and side*(f['previous_close']-f['sma200'])<=1e-10:return dict(reason='trend_filtered')
    i=f['index'];left=cfg.entry_slot
    if not valid_ohlc(market.arrays,i,int(market.lengths[i]))[left-1]:return dict(reason='unknown_sizing')
    price=float(market.arrays['close'][i,left-1]);stop=float((D(price)-side*D(f['adr']).quantize(D('.00000001'))).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING))
    if stop<=0 or side*(D(price)-D(stop))<=0:return dict(reason='invalid_stop')
    return dict(reason='eligible',sign=side,signal_slot=left-1,entry_slot=left,sizing_price=price,stop_price=stop,**{k:f[k] for k in SIGNAL_FIELDS})

def trace(market,f,s,cfg):
    a=market.arrays;i=f['index'];n=int(market.lengths[i]);side=s['sign'];left=s['entry_slot'];stop=s['stop_price']
    entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise UnresolvedExecution('missing_entry_open',left)
    risk=side*(D(entry)-D(stop));good=valid_ohlc(a,i,n);held=[];adverse=[entry];favorable=[entry];resolution='bar_open'
    for j in range(left,n):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:raise UnresolvedExecution('missing_active_open',j)
        if side*(D(op)-D(stop))<=0:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==n-1:ref=op;why='eod_open';break
        if not good[j]:raise UnresolvedExecution('invalid_active_bar',j)
        sh=a['low'][i,j]<=stop if side>0 else a['high'][i,j]>=stop
        if sh:ref=stop;why='stop_intrabar';resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]));adverse.append(float(a['low' if side>0 else 'high'][i,j]));favorable.append(float(a['high' if side>0 else 'low'][i,j]))
    adverse.append(ref);favorable.append(ref);op=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(entry_slot=left,exit_slot=j,entry_reference=entry,exit_reference=float(ref),stop_price=stop,target_price=np.nan,entry_risk_unit=max(0.,float(risk)),sign=side,
        entry_time=str(op+pd.Timedelta(minutes=left)),exit_time=str(op+pd.Timedelta(minutes=j)),exit_reason=why,exit_resolution=resolution,ambiguous_bar=False,
        holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,adverse=adverse,favorable=favorable)



TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','ibs_previous','adr','previous_close','sma200',
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
