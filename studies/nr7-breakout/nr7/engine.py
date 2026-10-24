"""Frozen NR7/next-open experiment; historical accounts are coverage-conditional."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from orb.engine import valid_bars,UnresolvedExecution
D=lambda x:Decimal(str(x))


@dataclass(frozen=True)
class Config:
    mode:str='both'
    slippage:float=.01
    quality:str='complete_days'
    require_nr7:bool=True
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('both','long_only','short_only'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk')


def prepare(m,cash):
    a=m.arrays;history=[];features=[]
    for i,day in enumerate(m.dates):
        n=int(m.lengths[i]);valid=valid_bars(a,i,n)
        complete=bool(m.valid[i] and valid.all() and a['volume'][i,:n].sum()>0)
        history.append((D(np.max(a['high'][i,:n])),D(np.min(a['low'][i,:n]))) if complete else None)
        f=dict(index=i,date=str(day.date()),history_reason='eligible',nr7=False,prior_high=np.nan,prior_low=np.nan,
            high_decimal=None,low_decimal=None,signal_reason='no_breakout',signal_sign=0,signal_slot=None,sizing_price=np.nan)
        previous=history[max(0,i-7):i]
        if i<7:f['history_reason']='warmup7'
        elif any(v is None for v in previous):f['history_reason']='invalid_prior7'
        else:
            ranges=[h-l for h,l in previous];div=D(cash.get(f['date'],0))
            if not div.is_finite() or div<0:raise ValueError('dividend')
            high,low=previous[-1][0]-div,previous[-1][1]-div
            if low<=0:raise ValueError('nonpositive adjusted level')
            f.update(nr7=all(ranges[-1]<v for v in ranges[:-1]),prior_high=float(high),prior_low=float(low),high_decimal=str(high),low_decimal=str(low))
            for j in range(n-2):
                if not valid[j]:f['signal_reason']='unknown_signal';break
                close=D(a['close'][i,j]);side=1 if close>high else -1 if close<low else 0
                if side:
                    f.update(signal_reason='eligible',signal_sign=side,signal_slot=j,sizing_price=float(close));break
        features.append(f)
    return pd.DataFrame(features)


def trace(m,i,f):
    a=m.arrays;n=int(m.lengths[i]);side=int(f['signal_sign']);left=int(f['signal_slot'])+1
    entry=D(a['open'][i,left]);stop=D(f['low_decimal' if side>0 else 'high_decimal'])
    if not entry.is_finite() or entry<=0:raise UnresolvedExecution('missing_entry_open',left)
    valid=valid_bars(a,i,n);closes=[];adverse=[float(entry)];favorable=[float(entry)];resolution='bar_open'
    for j in range(left,n):
        o=D(a['open'][i,j])
        if not o.is_finite() or o<=0:raise UnresolvedExecution('missing_active_open',j)
        if side*(o-stop)<=0:ref=o;reason='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==n-1:ref=o;reason='eod_open';break
        if not valid[j]:raise UnresolvedExecution('invalid_active_bar',j)
        hit=D(a['low'][i,j])<=stop if side>0 else D(a['high'][i,j])>=stop
        if hit:ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        closes.append(float(a['close'][i,j]));adverse.append(float(a['low' if side>0 else 'high'][i,j]));favorable.append(float(a['high' if side>0 else 'low'][i,j]))
    adverse.append(float(ref));favorable.append(float(ref));opening=pd.Timestamp(m.quality.iloc[i].session_open)
    return dict(entry_slot=left,exit_slot=j,entry_reference=float(entry),exit_reference=float(ref),stop_price=float(stop),entry_time=str(opening+pd.Timedelta(minutes=left)),
        exit_time=str(opening+pd.Timedelta(minutes=j)),exit_reason=reason,exit_resolution=resolution,holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),
        closes=closes,adverse=adverse,favorable=favorable)


TRADE_COLUMNS=['date','symbol','mode','quality','require_nr7','direction','sign','quantity','signal_slot','sizing_price','prior_high','prior_low','entry_slot','exit_slot',
    'entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','stop_price','exit_reason','exit_resolution','holding_minutes_upper','price_move_pnl',
    'friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_risk_pct','mae_observed_usd','mfe_observed_usd','half_session','ambiguous_bar']


def simulate(m,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unresolved=[]
    for f in features.to_dict('records'):
        date=f['date'];i=int(f['index']);side=int(f['signal_sign'])
        if not start<=date<=end:continue
        why=f['history_reason'];excluded=False;before=capital;net=fee=borrow=0.;q=upper=0;marks=[before]
        if why=='eligible':
            if cfg.require_nr7 and not f['nr7']:why='not_nr7'
            else:
                why=f['signal_reason'];excluded=why=='unknown_signal'
                if why=='eligible' and ((cfg.mode=='long_only' and side<0) or (cfg.mode=='short_only' and side>0)):why='direction_filtered'
                if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            stop=D(f['low_decimal' if side>0 else 'high_decimal']);risk=side*(D(f['sizing_price'])-stop)
            quantity=int(min(D(capital)*D(cfg.leverage_cap)/D(f['sizing_price']),D(capital)*D(cfg.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))
            if quantity<=0:why='zero_quantity'
            else:
                try:p=trace(m,i,f)
                except UnresolvedExecution as e:
                    why='unresolved_execution';excluded=True;ref=m.arrays['open'][i,int(f['signal_slot'])+1];known=math.isfinite(ref) and ref>0
                    unresolved.append(dict(date=date,symbol=m.symbol,sign=side,quantity=quantity,reason=e.reason,first_unknown_slot=e.minute,entry_reference=ref if known else None,
                        known_entry_commission=max(.35,quantity*.0035) if known else 0.,known_entry_friction=quantity*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    q=quantity;entry=p['entry_reference']+side*cfg.slippage;exit_price=p['exit_reference']-side*cfg.slippage
                    if min(entry,exit_price)<=0:raise ValueError('modeled fill')
                    fee=2*max(.35,q*.0035);borrow=q*entry*.01/360 if side<0 else 0.;gross=q*side*(exit_price-entry);net=gross-fee-borrow;capital+=net;upper=p['holding_minutes_upper']
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*side*(c-entry) for c in p.pop('closes')],capital]
                    mae=min(0.,min(q*side*(x-entry) for x in p.pop('adverse')));mfe=max(0.,max(q*side*(x-entry) for x in p.pop('favorable')))
                    trades.append(dict(date=date,symbol=m.symbol,mode=cfg.mode,quality=cfg.quality,require_nr7=cfg.require_nr7,direction='LONG' if side>0 else 'SHORT',sign=side,quantity=q,
                        signal_slot=int(f['signal_slot']),sizing_price=f['sizing_price'],prior_high=f['prior_high'],prior_low=f['prior_low'],**p,entry_price=entry,exit_price=exit_price,
                        price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,
                        net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,entry_risk_pct=float(q*max(D(0),side*(D(p['entry_reference'])-stop))/D(before)*100),
                        mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(m.lengths[i])==210,ambiguous_bar=False))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,
            equity=capital,trades=int(q>0),quantity=q,signal_sign=side,commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
