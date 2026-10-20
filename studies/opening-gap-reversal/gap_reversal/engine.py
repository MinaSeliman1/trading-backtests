from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Config:
    slippage:float=.01
    direction:str='reversal'
    initial_capital:float=100000.
    commission:float=.0035
    minimum_commission:float=.35
    borrow_rate:float=.01

    def __post_init__(self):
        if self.direction not in ('reversal','momentum'):raise ValueError('direction')
        if not all(math.isfinite(v) and v>=0 for v in (self.slippage,self.commission,self.minimum_commission,self.borrow_rate)) or self.initial_capital<=0:
            raise ValueError('invalid cost or capital')


def prepare(market,dividends,profile='endpoints'):
    if profile not in ('endpoints','complete_days'):raise ValueError('quality profile')
    if any(not math.isfinite(float(v)) or float(v)<0 for v in dividends.values()):raise ValueError('invalid dividend')
    a=market.arrays;rows=[]
    reasons=market.quality.reason.fillna('').tolist()
    for i,day in enumerate(market.dates):
        date=str(day.date());opening=float(a['open'][i,0]);dividend=float(dividends.get(date,0.))
        previous=float(a['close'][i-1,int(market.lengths[i-1])-1]) if i else np.nan
        adjusted_decimal=Decimal(str(previous))-Decimal(str(dividend)) if np.isfinite(previous) else None
        adjusted=float(adjusted_decimal) if adjusted_decimal is not None else np.nan
        gap=opening/adjusted-1 if np.isfinite(opening) and np.isfinite(adjusted) and adjusted>0 else np.nan
        # Decimal subtraction and comparison preserve exact post-dividend boundaries.
        event=bool(np.isfinite(gap) and (Decimal(str(opening))>adjusted_decimal*Decimal('1.02') or Decimal(str(opening))<adjusted_decimal*Decimal('.98')))
        why='eligible'
        required=np.array([opening,a['open'][i,1],a['open'][i,30],previous,adjusted])
        if not np.isfinite(required).all() or (required<=0).any():why='missing_required_prices'
        elif (a['volume'][i,[0,1,30]]<=0).any():why='nonpositive_required_volume'
        elif any(x and x!='missing_minutes' for x in str(reasons[i]).split('|')) or (i and any(x and x!='missing_minutes' for x in str(reasons[i-1]).split('|'))):why='ambiguous_source_quality'
        else:
            p=np.column_stack([a[k][i,:31] for k in ('open','high','low','close')]);v=a['volume'][i,:31]
            observed=np.isfinite(p).any(axis=1)|np.isfinite(v)
            bad=(~np.isfinite(p).all(axis=1))|(~np.isfinite(v))|(p.min(axis=1)<=0)|(v<0)
            bad|=(p[:,1]<p.max(axis=1))|(p[:,2]>p.min(axis=1))
            if (bad&observed).any():why='invalid_early_ohlcv'
            elif profile=='complete_days' and not (i and market.valid[i] and market.valid[i-1]):why='excluded_complete_day'
        rows.append(dict(index=i,date=date,opening=opening,previous_close=previous,dividend=dividend,
            previous_adjusted=adjusted,gap=gap,event=event,gap_sign=1 if opening>adjusted else -1,
            eligibility=why,complete_day=bool(market.valid[i]),previous_complete_day=bool(i and market.valid[i-1]),
            missing_holding_minutes=int(np.isnan(a['close'][i,1:30]).sum())))
    return pd.DataFrame(rows)


TRADE_COLUMNS=['date','symbol','direction','sign','gap','opening','previous_close','dividend','previous_adjusted',
    'quantity','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price',
    'price_move_pnl','friction_cost','gross_pnl','commission','borrow_fee','net_pnl','net_bps',
    'equity_before','equity_after','entry_leverage','mae_observed_usd','mfe_observed_usd',
    'missing_holding_minutes','complete_day']


def simulate(market,prepared,config,start,end):
    capital=config.initial_capital;peak=capital;max_dd_usd=0.;max_dd_pct=0.;daily=[];trades=[]
    a=market.arrays
    for row in prepared.to_dict('records'):
        date=row['date']
        if date<start or date>end:continue
        i=row['index'];before=capital;fee=0.;borrow=0.;qty=0;count=0
        why=row['eligibility'];marks=[capital]
        if capital<=0:why='insolvent'
        elif why=='eligible' and row['event']:
            qty=math.floor(capital/row['opening'])
            if qty<=0:why='zero_quantity'
            else:
                sign=row['gap_sign']*(-1 if config.direction=='reversal' else 1)
                entry_ref=float(a['open'][i,1]);exit_ref=float(a['open'][i,30])
                entry=entry_ref+sign*config.slippage;exit_price=exit_ref-sign*config.slippage
                if min(entry,exit_price)<=0:raise ValueError('nonpositive simulated fill')
                fee=max(config.minimum_commission,qty*config.commission)
                borrow=qty*entry*config.borrow_rate/360 if sign<0 else 0.
                price_move=qty*sign*(exit_ref-entry_ref);friction=2*qty*config.slippage
                gross=qty*sign*(exit_price-entry);net=gross-2*fee-borrow
                marks.append(before-fee+qty*sign*(entry_ref-entry))
                closes=a['close'][i,1:30];closes=closes[np.isfinite(closes)]
                marks.extend(before-fee+qty*sign*(closes-entry))
                capital=before+net;marks.append(capital)
                adverse=a['low' if sign>0 else 'high'][i,1:30]
                favorable=a['high' if sign>0 else 'low'][i,1:30]
                adverse=np.r_[entry_ref,adverse[np.isfinite(adverse)],exit_ref]
                favorable=np.r_[entry_ref,favorable[np.isfinite(favorable)],exit_ref]
                at=pd.Timestamp(date+' 09:31',tz='America/New_York');until=pd.Timestamp(date+' 10:00',tz='America/New_York')
                trades.append(dict(date=date,symbol=market.symbol,direction='LONG' if sign>0 else 'SHORT',sign=sign,
                    gap=row['gap'],opening=row['opening'],previous_close=row['previous_close'],dividend=row['dividend'],previous_adjusted=row['previous_adjusted'],quantity=qty,
                    entry_time=str(at),exit_time=str(until),entry_reference=entry_ref,exit_reference=exit_ref,entry_price=entry,exit_price=exit_price,
                    price_move_pnl=price_move,friction_cost=friction,gross_pnl=gross,commission=2*fee,borrow_fee=borrow,net_pnl=net,net_bps=net/(qty*entry)*10000,
                    equity_before=before,equity_after=capital,entry_leverage=qty*entry_ref/before,
                    mae_observed_usd=float(min(0.,np.min(qty*sign*(adverse-entry)))),mfe_observed_usd=float(max(0.,np.max(qty*sign*(favorable-entry)))),
                    missing_holding_minutes=row['missing_holding_minutes'],complete_day=row['complete_day']))
                count=1
        curve=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,curve])[1:]
        max_dd_usd=max(max_dd_usd,float(np.max(peaks-curve)));max_dd_pct=max(max_dd_pct,float(np.max((peaks-curve)/peaks)))
        peak=max(peak,float(curve.max()))
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,event=row['event'],trades=count,quantity=qty,
            net_pnl=capital-before,return_net=(capital-before)/before if before>0 else 0.,equity=capital,
            commission=2*fee,borrow_fee=borrow,gap=row['gap'],missing_holding_minutes=row['missing_holding_minutes'],
            observed_close_drawdown_pct_so_far=100*max_dd_pct))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),
        observed_close_drawdown_usd=max_dd_usd,observed_close_drawdown_pct=100*max_dd_pct)
