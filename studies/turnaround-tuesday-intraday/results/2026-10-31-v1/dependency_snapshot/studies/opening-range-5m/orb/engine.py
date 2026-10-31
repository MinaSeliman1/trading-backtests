"""ORB 5m : decisions causales, performances conditionnelles a la couverture."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))


@dataclass(frozen=True)
class Config:
    mode:str='both'
    slippage:float=.01
    priority:str='stop_first'
    quality:str='complete_days'
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    target_r:float=10.
    commission:float=.0035
    minimum_commission:float=.35
    borrow_rate:float=.01

    def __post_init__(self):
        if self.mode not in ('both','long_only','short_only','inverse'):raise ValueError('mode')
        if self.priority not in ('stop_first','target_first'):raise ValueError('priority')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not all(math.isfinite(v) and v>0 for v in (self.initial_capital,self.risk_budget,self.leverage_cap,self.target_r)):raise ValueError('capital/risk')
        if not all(math.isfinite(v) and v>=0 for v in (self.slippage,self.commission,self.minimum_commission,self.borrow_rate)):raise ValueError('cost')


class UnresolvedExecution(Exception):
    def __init__(self,reason,minute):self.reason=reason;self.minute=minute;super().__init__(reason)


def valid_bars(a,i,n):
    p=np.column_stack([a[k][i,:n] for k in ('open','high','low','close')]);v=a['volume'][i,:n]
    return np.isfinite(p).all(axis=1)&np.isfinite(v)&(p.min(axis=1)>0)&(v>=0)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))


def feature(m,i):
    a=m.arrays;good=valid_bars(a,i,5);opening=float(a['open'][i,0]);close=float(a['close'][i,4])
    why='eligible' if good.all() and np.sum(a['volume'][i,:5])>0 else 'invalid_opening_window'
    sign=(1 if D(close)>D(opening) else -1 if D(close)<D(opening) else 0) if why=='eligible' else 0
    return dict(index=i,date=str(m.dates[i].date()),opening=opening,sizing_price=close,signal_sign=sign,
        range_low=float(np.min(a['low'][i,:5])),range_high=float(np.max(a['high'][i,:5])),eligibility=why)


def opening_features(market):return pd.DataFrame([feature(market,i) for i in range(len(market.dates))])


def trade_path(market,index,sign,quantity,config):
    if sign not in (-1,1) or quantity<=0 or int(quantity)!=quantity:raise ValueError('sign/quantity')
    a=market.arrays;i=index;q=int(quantity);f=feature(market,i);n=int(market.lengths[i]);left=5
    if f['eligibility']!='eligible':raise UnresolvedExecution('invalid_opening_window',0)
    entry_ref=float(a['open'][i,left]);stop=f['range_low' if sign>0 else 'range_high']
    if not math.isfinite(entry_ref) or entry_ref<=0:raise UnresolvedExecution('missing_entry_open',left)
    entry=entry_ref+sign*config.slippage
    if entry<=0:raise ValueError('nonpositive modeled entry')
    risk=float(sign*(D(entry_ref)-D(stop)));target=float(D(entry_ref)+sign*D(config.target_r)*D(risk))
    fee=max(config.minimum_commission,q*config.commission);borrow=q*entry*config.borrow_rate/360 if sign<0 else 0.
    marks=[0.,-fee-q*config.slippage];adverse=[entry_ref];favorable=[entry_ref];valid=valid_bars(a,i,n);ambiguous=False;resolution='bar_open'
    if risk<=0:
        j=left;exit_ref=entry_ref;reason='entry_marketable_stop'
    else:
        for j in range(left,n):
            opening=float(a['open'][i,j])
            if not math.isfinite(opening) or opening<=0:raise UnresolvedExecution('missing_active_open',j)
            if sign*(opening-stop)<=0:exit_ref=opening;reason='stop_gap';break
            if sign*(opening-target)>=0:exit_ref=target;reason='target_gap';break
            if j==n-1:exit_ref=opening;reason='eod_open';break
            if not valid[j]:raise UnresolvedExecution('invalid_active_bar',j)
            stop_hit=a['low'][i,j]<=stop if sign>0 else a['high'][i,j]>=stop
            target_hit=a['high'][i,j]>=target if sign>0 else a['low'][i,j]<=target
            ambiguous=bool(stop_hit and target_hit)
            if stop_hit or target_hit:
                choose_stop=bool(stop_hit and (not target_hit or config.priority=='stop_first'))
                exit_ref=stop if choose_stop else target;reason='stop_intrabar' if choose_stop else 'target_intrabar';resolution='intrabar_minute_unknown';break
            marks.append(-fee+q*sign*(float(a['close'][i,j])-entry))
            adverse.append(float(a['low' if sign>0 else 'high'][i,j]));favorable.append(float(a['high' if sign>0 else 'low'][i,j]))
        else:raise UnresolvedExecution('no_exit',n-1)
    exit_price=exit_ref-sign*config.slippage
    if exit_price<=0:raise ValueError('nonpositive modeled exit')
    gross=q*sign*(exit_price-entry);net=gross-2*fee-borrow;marks.append(net)
    adverse.append(exit_ref);favorable.append(exit_ref)
    opening=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(quantity=q,sign=sign,direction='LONG' if sign>0 else 'SHORT',entry_reference=entry_ref,exit_reference=float(exit_ref),entry_price=entry,exit_price=exit_price,
        stop_price=stop,target_price=target,entry_risk_unit=max(0.,risk),entry_time=str(opening+pd.Timedelta(minutes=left)),exit_time=str(opening+pd.Timedelta(minutes=j)),
        exit_reason=reason,exit_resolution=resolution,exit_slot=j,ambiguous_bar=ambiguous,holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),
        price_move_pnl=q*sign*(exit_ref-entry_ref),friction_cost=2*q*config.slippage,gross_pnl=gross,commission=2*fee,borrow_fee=borrow,net_pnl=net,net_bps=net/(q*entry)*10000,
        mae_observed_usd=float(min(0.,np.min(q*sign*(np.array(adverse)-entry)))),mfe_observed_usd=float(max(0.,np.max(q*sign*(np.array(favorable)-entry)))),equity_offsets=marks)


TRADE_COLUMNS=['date','symbol','mode','quality','priority','direction','sign','opening','sizing_price','range_low','range_high','signal_sign','quantity','entry_time','exit_time',
    'entry_reference','exit_reference','entry_price','exit_price','stop_price','target_price','entry_risk_unit','entry_risk_pct','exit_reason','exit_resolution','exit_slot',
    'ambiguous_bar','holding_minutes_upper','price_move_pnl','friction_cost','gross_pnl','commission','borrow_fee','net_pnl','net_bps','equity_before','equity_after','entry_leverage',
    'mae_observed_usd','mfe_observed_usd','half_session']


def simulate(market,config,start,end):
    capital=config.initial_capital;peak=capital;dd=dd_usd=0.;trades=[];daily=[];unresolved=[]
    for i,day in enumerate(market.dates):
        date=str(day.date())
        if not start<=date<=end:continue
        f=feature(market,i);why=f['eligibility'];excluded=why!='eligible';sign=f['signal_sign'];before=capital;net=commission=borrow=0.;qty=0;upper=0;marks=[before]
        if why=='eligible' and config.quality=='complete_days' and not market.valid[i]:why='excluded_incomplete_day';excluded=True
        if config.mode=='long_only':sign=max(0,sign)
        elif config.mode=='short_only':sign=min(0,sign)
        elif config.mode=='inverse':sign=-sign
        if capital<=0:why='insolvent'
        if why=='eligible' and sign:
            stop=f['range_low' if sign>0 else 'range_high'];risk=sign*(D(f['sizing_price'])-D(stop))
            if risk<=0:why='zero_known_risk'
            else:
                target=min(D(capital)*D(config.leverage_cap)/D(f['sizing_price']),D(capital)*D(config.risk_budget)/risk)
                quantity=int(target.to_integral_value(rounding=ROUND_FLOOR))
                if quantity<=0:why='zero_quantity'
                else:
                    try:path=trade_path(market,i,sign,quantity,config)
                    except UnresolvedExecution as error:
                        why='unresolved_execution';excluded=True
                        ref=float(market.arrays['open'][i,5]);known=math.isfinite(ref) and ref>0
                        unresolved.append(dict(date=date,symbol=market.symbol,sign=sign,quantity=quantity,reason=error.reason,first_unknown_slot=error.minute,
                            entry_reference=ref if known else None,known_entry_commission=max(config.minimum_commission,quantity*config.commission) if known else 0.,
                            known_entry_friction=quantity*config.slippage if known else 0.,omitted_entire_trade=True))
                    else:
                        qty=quantity;net=path['net_pnl'];commission=path['commission'];borrow=path['borrow_fee'];upper=path['holding_minutes_upper'];capital=before+net
                        marks=[before+x for x in path.pop('equity_offsets')]
                        row=dict(date=date,symbol=market.symbol,mode=config.mode,quality=config.quality,priority=config.priority,**{k:f[k] for k in ('opening','sizing_price','range_low','range_high','signal_sign')},**path,
                            equity_before=before,equity_after=capital,entry_leverage=qty*path['entry_reference']/before,entry_risk_pct=qty*path['entry_risk_unit']/before*100,half_session=int(market.lengths[i])==210)
                        trades.append(row)
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));dd_usd=max(dd_usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        conditional_return=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else conditional_return,
            return_net=conditional_return,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,signal_sign=f['signal_sign'],commission=commission,borrow_fee=borrow,
            holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=100*dd))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=config.initial_capital,observed_close_drawdown_pct=100*dd,observed_close_drawdown_usd=dd_usd)
