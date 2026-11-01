"""Signal connu le matin, taille sur minute terminee, maintien des 29 dernieres minutes."""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Config:
    mode:str='momentum'
    slippage:float=.01
    initial_capital:float=100000.
    commission:float=.0035
    minimum_commission:float=.35
    borrow_rate:float=.01

    def __post_init__(self):
        if self.mode not in ('momentum','long_only','always_long','opposite'):raise ValueError('invalid mode')
        if not math.isfinite(self.initial_capital) or self.initial_capital<=0:raise ValueError('invalid capital')
        if not all(math.isfinite(v) and v>=0 for v in (self.slippage,self.commission,self.minimum_commission,self.borrow_rate)):
            raise ValueError('invalid cost')


def valid_bars(arrays,index,slots):
    prices=np.column_stack([arrays[k][index,slots] for k in ('open','high','low','close')])
    volume=np.atleast_1d(arrays['volume'][index,slots])
    return np.isfinite(prices).all(axis=1)&np.isfinite(volume)&(prices.min(axis=1)>0)&(volume>=0)&(prices[:,1]>=prices.max(axis=1))&(prices[:,2]<=prices.min(axis=1))


def prepare(market,dividends):
    if not market.dates.is_unique or not market.dates.is_monotonic_increasing:raise ValueError('nonunique or unsorted sessions')
    if any(not math.isfinite(float(v)) or float(v)<0 for v in dividends.values()):raise ValueError('invalid dividend')
    a=market.arrays;rows=[]
    for i,day in enumerate(market.dates):
        reason=str(market.quality.iloc[i].reason or '')
        if set(reason.split('|'))&{'conflicting_duplicates','off_minute_timestamps'}:raise ValueError('ambiguous source timestamps')
        length=int(market.lengths[i]);entry_slot=length-30;exit_slot=length-1
        if length not in (210,390):raise ValueError('unsupported NYSE session length')
        date=str(day.date());dividend=float(dividends.get(date,0.));why='eligible'
        previous=float(a['close'][i-1,int(market.lengths[i-1])-1]) if i else np.nan
        adjusted_decimal=Decimal(str(previous))-Decimal(str(dividend)) if np.isfinite(previous) else None
        adjusted=float(adjusted_decimal) if adjusted_decimal is not None else np.nan
        morning=float(a['close'][i,29]);sign=0;ret=np.nan
        if i==0 or not valid_bars(a,i-1,slice(int(market.lengths[i-1])-1,int(market.lengths[i-1]))).all():why='invalid_previous_close'
        elif not np.isfinite(adjusted) or adjusted<=0:why='invalid_adjusted_previous_close'
        elif not valid_bars(a,i,slice(0,30)).all() or np.sum(a['volume'][i,:30])<=0:why='invalid_morning_window'
        elif not valid_bars(a,i,slice(entry_slot-1,entry_slot)).all():why='invalid_sizing_minute'
        elif not np.isfinite(a['open'][i,entry_slot]) or a['open'][i,entry_slot]<=0:why='invalid_entry_price'
        if np.isfinite(morning) and morning>0 and np.isfinite(adjusted) and adjusted>0:
            value=Decimal(str(morning));sign=1 if value>adjusted_decimal else -1 if value<adjusted_decimal else 0
            ret=float(value/adjusted_decimal-1)
        rows.append(dict(index=i,date=date,session_minutes=length,entry_slot=entry_slot,exit_slot=exit_slot,
            session_open=str(market.quality.iloc[i].session_open),session_close=str(market.quality.iloc[i].session_close),
            morning_close=morning,previous_close=previous,dividend=dividend,previous_adjusted=adjusted,
            morning_return=ret,signal_sign=sign,eligibility=why,sizing_price=float(a['close'][i,entry_slot-1]),
            entry_reference=float(a['open'][i,entry_slot]),exit_reference=float(a['open'][i,exit_slot]),
            missing_holding_minutes=int((~valid_bars(a,i,slice(entry_slot,exit_slot))).sum()),complete_day=bool(market.valid[i])))
    return pd.DataFrame(rows)


TRADE_COLUMNS=['date','symbol','mode','direction','sign','morning_return','morning_close','previous_close','dividend','previous_adjusted',
    'sizing_price','quantity','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','price_move_pnl',
    'friction_cost','gross_pnl','commission','borrow_fee','net_pnl','net_bps','equity_before','equity_after','entry_leverage',
    'mae_observed_usd','mfe_observed_usd','missing_holding_minutes','half_session','complete_day']


def simulate(market,prepared,config,start,end,fixed_quantities=None):
    capital=config.initial_capital;peak=capital;max_dd=0.;max_dd_usd=0.;trades=[];daily=[];a=market.arrays
    for row in prepared.to_dict('records'):
        date=row['date']
        if not start<=date<=end:continue
        i=row['index'];before=capital;why=row['eligibility'];qty=0;target_qty=0;fee=borrow=0.;marks=[before]
        sign=row['signal_sign']
        if config.mode=='long_only':sign=max(0,sign)
        elif config.mode=='opposite':sign=-sign
        elif config.mode=='always_long':sign=1
        if capital<=0:why='insolvent'
        if why=='eligible':
            target_qty=math.floor(capital/row['sizing_price'])
            if fixed_quantities is not None:
                value=fixed_quantities[date]
                if not math.isfinite(value) or value<0 or value!=int(value):raise ValueError('invalid fixed quantity')
                target_qty=int(value)
            if target_qty<=0:why='zero_quantity'
            elif sign:
                qty=target_qty;entry_ref=row['entry_reference'];exit_ref=row['exit_reference']
                if not math.isfinite(exit_ref) or exit_ref<=0:raise ValueError('unresolved exit: '+date)
                entry=entry_ref+sign*config.slippage;exit_price=exit_ref-sign*config.slippage
                if min(entry,exit_price)<=0:raise ValueError('nonpositive simulated fill')
                fee=max(config.minimum_commission,qty*config.commission);borrow=qty*entry*config.borrow_rate/360 if sign<0 else 0.
                price_move=qty*sign*(exit_ref-entry_ref);friction=2*qty*config.slippage
                gross=qty*sign*(exit_price-entry);net=gross-2*fee-borrow;capital=before+net
                left=row['entry_slot'];right=row['exit_slot'];valid=valid_bars(a,i,slice(left,right))
                closes=a['close'][i,left:right][valid]
                marks.extend([before-fee+qty*sign*(entry_ref-entry),*(before-fee+qty*sign*(closes-entry)),capital])
                adverse=np.r_[entry_ref,a['low' if sign>0 else 'high'][i,left:right][valid],exit_ref]
                favorable=np.r_[entry_ref,a['high' if sign>0 else 'low'][i,left:right][valid],exit_ref]
                closing=pd.Timestamp(row['session_close']);at=closing-pd.Timedelta(minutes=30);until=closing-pd.Timedelta(minutes=1)
                trades.append(dict(date=date,symbol=market.symbol,mode=config.mode,direction='LONG' if sign>0 else 'SHORT',sign=sign,
                    morning_return=row['morning_return'],morning_close=row['morning_close'],previous_close=row['previous_close'],dividend=row['dividend'],previous_adjusted=row['previous_adjusted'],
                    sizing_price=row['sizing_price'],quantity=qty,entry_time=str(at),exit_time=str(until),entry_reference=entry_ref,exit_reference=exit_ref,entry_price=entry,exit_price=exit_price,
                    price_move_pnl=price_move,friction_cost=friction,gross_pnl=gross,commission=2*fee,borrow_fee=borrow,net_pnl=net,net_bps=net/(qty*entry)*10000,
                    equity_before=before,equity_after=capital,entry_leverage=qty*entry_ref/before,
                    mae_observed_usd=float(min(0.,np.min(qty*sign*(adverse-entry)))),mfe_observed_usd=float(max(0.,np.max(qty*sign*(favorable-entry)))),
                    missing_holding_minutes=row['missing_holding_minutes'],half_session=row['session_minutes']==210,complete_day=row['complete_day']))
        curve=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,curve])[1:]
        max_dd=max(max_dd,float(np.max((peaks-curve)/peaks)));max_dd_usd=max(max_dd_usd,float(np.max(peaks-curve)));peak=max(peak,float(curve.max()))
        daily.append(dict(date=date,session_minutes=row['session_minutes'],eligibility=why,signal_sign=row['signal_sign'],trades=int(qty>0),quantity=qty,target_quantity=target_qty,
            net_pnl=capital-before,return_net=(capital-before)/before if before>0 else 0.,equity=capital,commission=2*fee,borrow_fee=borrow,
            missing_holding_minutes=row['missing_holding_minutes'] if qty else 0,observed_close_drawdown_pct_so_far=100*max_dd))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),initial_capital=config.initial_capital,
        observed_close_drawdown_pct=100*max_dd,observed_close_drawdown_usd=max_dd_usd)
