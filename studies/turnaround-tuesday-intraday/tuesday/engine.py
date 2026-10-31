"""Calendar-conditioned intraday long; same frozen stop/EOD execution helper."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from .data import source
from ibs.engine import trace,valid_ohlc
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))
SIGNAL_FIELDS=('weekday','previous_weekday','previous_return','adr','previous_close','before_previous_close')

@dataclass(frozen=True)
class Config:
    weekday:int|None=1
    require_down:bool=True
    require_monday:bool=True
    drop:float=0.
    mode:str='long_only'
    slippage:float=.01
    quality:str='complete_days'
    entry_slot:int=1
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.weekday is not None and self.weekday not in range(5):raise ValueError('weekday')
        if self.mode!='long_only':raise ValueError('mode')
        if not math.isfinite(self.drop) or not 0<=self.drop<1:raise ValueError('drop')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if self.entry_slot not in (1,5):raise ValueError('entry_slot')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(v) and v>0 for v in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/capital')

def prepare(market,cash=None):
    a=market.arrays;high=[];low=[];close=[]
    for i,n in enumerate(market.lengths):
        good=bool(market.valid[i]) and bool(valid_ohlc(a,i,int(n)).all())
        high.append(float(np.max(a['high'][i,:n])) if good else np.nan)
        low.append(float(np.min(a['low'][i,:n])) if good else np.nan)
        close.append(float(a['close'][i,n-1]) if good else np.nan)
    close=pd.Series(close);width=pd.Series(np.array(high)-np.array(low))
    adr=width.rolling(14,min_periods=14).mean().shift(1);last=close.shift(1);prior=close.shift(2)
    return [dict(index=i,date=str(d.date()),session_minutes=int(market.lengths[i]),weekday=d.weekday(),previous_weekday=market.dates[i-1].weekday() if i else -1,
        adr=float(adr.iloc[i]),previous_close=float(last.iloc[i]),before_previous_close=float(prior.iloc[i]),previous_return=float(last.iloc[i]/prior.iloc[i]-1)) for i,d in enumerate(market.dates)]

def signal(market,f,cfg):
    if f['index']<14:return dict(reason='warmup')
    if cfg.weekday is not None and f['weekday']!=cfg.weekday or cfg.require_monday and f['previous_weekday']!=0:return dict(reason='no_signal')
    if not np.isfinite([f['adr'],f['previous_close'],f['before_previous_close']]).all():return dict(reason='unknown_history')
    if f['adr']<=0:return dict(reason='zero_range_history')
    if cfg.require_down:
        change=D(f['previous_close'])-D(f['before_previous_close'])*(1-D(cfg.drop))
        fails=change>=D('-0.0000000001') if cfg.drop==0 else change>D('0.0000000001')
        if fails:return dict(reason='no_signal')
    i=f['index'];left=cfg.entry_slot
    if not valid_ohlc(market.arrays,i,int(market.lengths[i]))[left-1]:return dict(reason='unknown_sizing')
    price=float(market.arrays['close'][i,left-1]);stop=float((D(price)-D(f['adr']).quantize(D('.00000001'))).quantize(D('.01'),rounding=ROUND_FLOOR))
    if stop<=0 or D(price)-D(stop)<=0:return dict(reason='invalid_stop')
    return dict(reason='eligible',sign=1,signal_slot=left-1,entry_slot=left,sizing_price=price,stop_price=stop,**{k:f[k] for k in SIGNAL_FIELDS})

TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','weekday','previous_weekday','previous_return','adr','previous_close','before_previous_close',
    'entry_slot','exit_slot','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','stop_price','target_price','entry_risk_unit','exit_reason','exit_resolution',
    'holding_minutes_upper','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_fill_leverage','entry_risk_pct','modeled_stop_net_risk_pct',
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
                    adverse=[entry,*p.pop('adverse')[1:-1],exit_price];favorable=[entry,*p.pop('favorable')[1:-1],exit_price]
                    mae=min(0.,min(q*side*(x-entry) for x in adverse));mfe=max(0.,max(q*side*(x-entry) for x in favorable))
                    trades.append(dict(date=date,symbol=market.symbol,mode=cfg.mode,quality=cfg.quality,direction='LONG' if side>0 else 'SHORT',quantity=q,signal_slot=s['signal_slot'],sizing_price=s['sizing_price'],
                        **{k:s[k] for k in SIGNAL_FIELDS},**p,entry_price=entry,exit_price=exit_price,price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),
                        friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,
                        entry_leverage=q*p['entry_reference']/before,entry_fill_leverage=q*entry/before,entry_risk_pct=q*p['entry_risk_unit']/before*100,modeled_stop_net_risk_pct=(q*(entry-(min(p['stop_price'],p['entry_reference'])-cfg.slippage))+fee)/before*100,mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,equity=capital,
            trades=int(q>0),quantity=q,signal_sign=s.get('sign',0),commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
