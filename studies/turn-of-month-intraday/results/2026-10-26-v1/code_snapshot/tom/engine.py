"""Calendar-only intraday LONG with fixed signal-close sizing and optional stop."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))

@dataclass(frozen=True)
class Config:
    mode:str='tom'
    slippage:float=.01
    quality:str='complete_days'
    stop_pct:float=.01
    stop_enabled:bool=True
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('tom','first1','last1','first3','first5_last1','other_days','all_days'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not math.isfinite(self.stop_pct) or not 0<self.stop_pct<1:raise ValueError('stop')
        if not all(math.isfinite(v) and v>0 for v in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/capital')

def valid_ohlc(a,i,n):
    p=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1)
    return np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))

def make_calendar(dates):
    start=pd.Timestamp(min(dates)).to_period('M').start_time-pd.DateOffset(months=1)
    end=pd.Timestamp(max(dates)).to_period('M').start_time+pd.DateOffset(months=2)-pd.Timedelta(days=1)
    calendar=xcals.get_calendar('XNYS',start=start,end=end).sessions
    if calendar.tz is not None:calendar=calendar.tz_localize(None)
    frame=pd.DataFrame({'date':calendar.strftime('%Y-%m-%d'),'month':calendar.strftime('%Y-%m')})
    frame['month_ordinal']=frame.groupby('month').cumcount()+1
    frame['month_sessions']=frame.groupby('month').date.transform('size')
    frame['sessions_to_end']=frame.month_sessions-frame.month_ordinal
    frame['is_tom']=(frame.month_ordinal<=3)|(frame.sessions_to_end==0)
    return frame

def prepare(market,cash=None,calendar=None):
    calendar=make_calendar(market.dates) if calendar is None else calendar
    lookup=calendar.set_index('date').to_dict('index')
    return [dict(index=i,date=str(day.date()),session_minutes=int(market.lengths[i]),**lookup[str(day.date())]) for i,day in enumerate(market.dates)]

def signal(market,f,cfg):
    ordinal=f['month_ordinal'];last=f['sessions_to_end']==0
    selected={'tom':f['is_tom'],'first1':ordinal==1,'last1':last,'first3':ordinal<=3,'first5_last1':ordinal<=5 or last,
        'other_days':not f['is_tom'],'all_days':True}[cfg.mode]
    if not selected:return dict(reason='calendar_filtered')
    i=f['index'];a=market.arrays
    if not valid_ohlc(a,i,5)[4]:return dict(reason='unknown_sizing_bar')
    close=float(a['close'][i,4]);stop=float((D(close)*(1-D(cfg.stop_pct))).quantize(D('.01'),rounding=ROUND_FLOOR))
    return dict(reason='eligible',sign=1,signal_slot=4,entry_slot=5,sizing_price=close,stop_price=stop)

def trace(market,f,s,cfg):
    a=market.arrays;i=f['index'];n=int(market.lengths[i]);left=5;stop=s['stop_price'];entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise UnresolvedExecution('missing_entry_open',left)
    good=valid_ohlc(a,i,n);ops=a['open'][i,:n];bad_open=~np.isfinite(ops)|(ops<=0)
    stop_open=(ops<=stop)&cfg.stop_enabled;stop_low=(a['low'][i,:n]<=stop)&cfg.stop_enabled
    event=bad_open|stop_open|~good|stop_low;event[n-1]=True
    j=left+int(np.flatnonzero(event[left:])[0]);op=float(ops[j]);resolution='bar_open'
    if bad_open[j]:raise UnresolvedExecution('missing_active_open',j)
    if stop_open[j]:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap'
    elif j==n-1:ref=op;why='eod_open'
    elif not good[j]:raise UnresolvedExecution('invalid_active_bar',j)
    else:ref=stop;why='stop_intrabar';resolution='intrabar_minute_unknown'
    held=a['close'][i,left:j].tolist();adverse=[entry,*a['low'][i,left:j].tolist(),ref];favorable=[entry,*a['high'][i,left:j].tolist(),ref]
    opening=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(entry_slot=left,exit_slot=j,entry_reference=entry,exit_reference=float(ref),stop_price=stop,target_price=np.nan,entry_risk_unit=max(0.,float(D(entry)-D(stop))),sign=1,
        entry_time=str(opening+pd.Timedelta(minutes=left)),exit_time=str(opening+pd.Timedelta(minutes=j)),exit_reason=why,exit_resolution=resolution,ambiguous_bar=False,
        holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,adverse=adverse,favorable=favorable)

TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','month','month_ordinal','sessions_to_end','month_sessions','is_tom','stop_enabled',
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
                        **{k:f[k] for k in ('month','month_ordinal','sessions_to_end','month_sessions','is_tom')},stop_enabled=cfg.stop_enabled,**p,entry_price=entry,exit_price=exit_price,price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),
                        friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,
                        entry_leverage=q*p['entry_reference']/before,entry_risk_pct=q*p['entry_risk_unit']/before*100,mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,equity=capital,
            trades=int(q>0),quantity=q,signal_sign=s.get('sign',0),commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
