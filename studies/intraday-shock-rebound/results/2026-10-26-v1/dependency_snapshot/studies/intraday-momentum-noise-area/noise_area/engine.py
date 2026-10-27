from dataclasses import dataclass
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from .features import desired_position


@dataclass(frozen=True)
class Config:
    execution: str='next_open'
    slippage: float=.001
    leverage_cap: float=4.
    frequency: int=30
    stop: str='combined'
    borrow_rate: float=.01


def simulate(market,features,config,start=None,end=None):
    if config.execution not in ('close','next_open'): raise ValueError('execution')
    if config.frequency not in (15,30,60): raise ValueError('frequency')
    if config.slippage<0 or config.borrow_rate<0: raise ValueError('negative cost')
    capital=100000.;peak=capital;max_dd_usd=0.;max_dd_pct=0.
    trades=[];daily=[];decisions=[]
    for i,day in enumerate(market.dates):
        date=str(day.date())
        if (start and date<start) or (end and date>end): continue
        volatility=features['volatility'][i]
        n=int(market.lengths[i]);opening=market.arrays['open'][i,0]
        indices=np.arange(config.frequency-1,n-1,config.frequency)
        eligible=market.valid[i] and np.isfinite(volatility) and np.isfinite(features['upper'][i,indices]).all()
        if not eligible:
            daily.append(dict(date=date,net_pnl=0.,return_net=0.,equity=capital,trades=0,commission=0.,borrow_fee=0.,
                              target_leverage=0.,daily_volatility=volatility,quantity=0,min_equity=capital,max_equity=capital,
                              max_drawdown_usd_so_far=max_dd_usd,max_drawdown_pct_so_far=max_dd_pct,session_minutes=n,
                              eligibility='excluded_data' if not market.valid[i] else 'unavailable_past_indicators'))
            continue
        if capital<=0: break
        target_leverage=min(config.leverage_cap,.02/volatility) if volatility>0 else config.leverage_cap
        quantity=math.floor(capital*target_leverage/opening)
        if quantity<=0: continue
        start_capital=capital;balance=capital;side=0;entry=None;cursor=0;marks=[capital]
        day_trades=[];opening_time=pd.Timestamp(date+' 09:30',tz='America/New_York')
        closes=market.arrays['close'][i,:n]

        def append_closes(until):
            nonlocal cursor
            if until>cursor:
                if side:
                    marks.extend(balance+side*quantity*(closes[cursor:until]-entry['entry_price']))
                else:
                    marks.extend(np.full(until-cursor,balance))
                cursor=until

        def change_position(new_side,bar,phase,reference,decision_index,reason):
            nonlocal side,entry,balance
            append_closes(bar+(1 if phase=='close' else 0))
            time=opening_time+pd.Timedelta(minutes=bar+(1 if phase=='close' else 0))
            fee=max(.35,quantity*.0035)
            if side:
                fill=reference-side*config.slippage
                gross=(fill-entry['entry_price'])*side*quantity
                borrow=quantity*entry['entry_price']*config.borrow_rate/360 if side<0 else 0.
                balance+=gross-fee-borrow
                record={**entry,'exit_time':str(time),'exit_price':fill,'exit_reference':reference,
                        'exit_bar':bar,'exit_phase':phase,'exit_decision_index':decision_index,'exit_reason':reason,
                        'gross_pnl':gross,'commission':2*fee,'borrow_fee':borrow,
                        'net_pnl':gross-2*fee-borrow,'holding_minutes':(time-pd.Timestamp(entry['entry_time'])).total_seconds()/60}
                record['net_bps']=record['net_pnl']/(quantity*record['entry_price'])*10000
                trades.append(record);day_trades.append(record)
                side=0;entry=None;marks.append(balance)
            if new_side:
                fill=reference+new_side*config.slippage
                side=new_side;balance-=fee
                entry=dict(date=date,instrument=market.symbol,direction='LONG' if side==1 else 'SHORT',sign=side,
                           entry_time=str(time),entry_price=fill,entry_reference=reference,entry_bar=bar,entry_phase=phase,
                           entry_decision_index=decision_index,quantity=quantity,equity_at_day_start=start_capital,
                           target_leverage=target_leverage,entry_leverage=quantity*fill/(balance+fee),
                           daily_volatility=volatility,upper=features['upper'][i,decision_index],
                           lower=features['lower'][i,decision_index],vwap=features['vwap'][i,decision_index],
                           decision_price=closes[decision_index],opening_price=opening)
                marks.append(balance+side*quantity*(reference-fill))

        for j in indices:
            price=closes[j]
            ub=features['upper'][i,j];lb=features['lower'][i,j];vwap=features['vwap'][i,j]
            before=side;target=desired_position(side,price,ub,lb,vwap,config.stop)
            bar=int(j+1 if config.execution=='next_open' else j)
            phase='open' if config.execution=='next_open' else 'close'
            reference=float(market.arrays['open'][i,bar] if phase=='open' else price)
            decisions.append(dict(date=date,decision_index=int(j),decision_time=str(opening_time+pd.Timedelta(minutes=int(j)+1)),
                                  price=price,upper=ub,lower=lb,vwap=vwap,position_before=before,target=target,
                                  execution_reference=reference,quantity=quantity))
            if target!=side:
                change_position(target,bar,phase,reference,int(j),'reversal' if target and side else 'trailing_exit')
        if side:
            change_position(0,n-1,'open',float(market.arrays['open'][i,n-1]),None,'session_end')
        append_closes(n)
        capital=balance
        curve=np.array(marks);peaks=np.maximum.accumulate(np.r_[peak,curve])[1:]
        dd=peaks-curve;dd_pct=dd/peaks
        peak=max(peak,float(curve.max()))
        max_dd_usd=max(max_dd_usd,float(dd.max()));max_dd_pct=max(max_dd_pct,float(dd_pct.max()))
        net=capital-start_capital
        assert abs(net-sum(t['net_pnl'] for t in day_trades))<1e-6
        daily.append(dict(date=date,net_pnl=net,return_net=net/start_capital,equity=capital,
                          trades=len(day_trades),commission=sum(t['commission'] for t in day_trades),
                          borrow_fee=sum(t['borrow_fee'] for t in day_trades),target_leverage=target_leverage,
                          daily_volatility=volatility,quantity=quantity,min_equity=float(curve.min()),
                          max_equity=float(curve.max()),max_drawdown_usd_so_far=max_dd_usd,
                          max_drawdown_pct_so_far=max_dd_pct,session_minutes=n,eligibility='eligible'))
    trade_columns=['date','instrument','direction','sign','entry_time','entry_price','entry_reference','entry_bar','entry_phase',
                   'entry_decision_index','quantity','equity_at_day_start','target_leverage','entry_leverage','daily_volatility',
                   'upper','lower','vwap','decision_price','opening_price','exit_time','exit_price','exit_reference','exit_bar',
                   'exit_phase','exit_decision_index','exit_reason','gross_pnl','commission','borrow_fee','net_pnl','holding_minutes','net_bps']
    return SimpleNamespace(trades=pd.DataFrame(trades,columns=trade_columns),daily=pd.DataFrame(daily),decisions=pd.DataFrame(decisions),
                           summary=dict(max_drawdown_usd=max_dd_usd,max_drawdown_pct=max_dd_pct,final_equity=capital))
