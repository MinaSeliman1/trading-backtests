"""First opening-range breakout, first later touch, confirmed next-open entry."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from orb.engine import UnresolvedExecution
D=lambda x:Decimal(str(x))
EPS=1e-10
SIGNAL_FIELDS=('range_high','range_low','breakout_slot','breakout_level','wait_bars','signal_low','signal_high')

@dataclass(frozen=True)
class Config:
    mode:str='both'
    slippage:float=.01
    quality:str='complete_days'
    bar_minutes:int=5
    range_minutes:int=15
    cutoff:int=120
    max_wait_bars:int=6
    entry_mode:str='retest'
    target_r:float=2.
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('both','long_only','short_only'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if self.entry_mode not in ('retest','breakout'):raise ValueError('entry_mode')
        if self.bar_minutes!=5 or self.range_minutes!=15 or not self.range_minutes<self.cutoff<390 or self.cutoff%5:raise ValueError('windows')
        if not isinstance(self.max_wait_bars,int) or self.max_wait_bars<1:raise ValueError('wait')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('cost')
        if not all(math.isfinite(v) and v>0 for v in (self.target_r,self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('risk/capital')

def valid_ohlc(a,i,n):
    p=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1)
    return np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))

def prepare(market,cash=None):
    a=market.arrays;features=[]
    for i,day in enumerate(market.dates):
        n=int(market.lengths[i]);good=valid_ohlc(a,i,n);bars=[]
        for left in range(0,n,5):
            end=left+5
            bars.append(dict(left=left,entry_slot=end,valid=bool(good[left:end].all()),open=float(a['open'][i,left]),
                high=float(np.max(a['high'][i,left:end])),low=float(np.min(a['low'][i,left:end])),close=float(a['close'][i,end-1])))
        features.append(dict(index=i,date=str(day.date()),session_minutes=n,bars=bars))
    return features

def signal(market,f,cfg):
    opening=f['bars'][:cfg.range_minutes//5]
    if not all(b['valid'] for b in opening):return dict(reason='unknown_range')
    high=max(b['high'] for b in opening);low=min(b['low'] for b in opening)
    if high<=low:return dict(reason='zero_range')
    armed=None
    def eligible(b,side,breakslot,level,delay):
        stop=float((D(b['low'])-D('.01') if side>0 else D(b['high'])+D('.01')).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING))
        if stop<=0 or side*(D(b['close'])-D(stop))<=0:return dict(reason='invalid_stop')
        return dict(reason='eligible',sign=side,signal_slot=b['entry_slot']-1,entry_slot=b['entry_slot'],sizing_price=b['close'],stop_price=stop,
            range_high=high,range_low=low,breakout_slot=breakslot,breakout_level=level,wait_bars=delay,signal_low=b['low'],signal_high=b['high'])
    for b in f['bars'][cfg.range_minutes//5:]:
        end=b['entry_slot']
        if end>min(cfg.cutoff,f['session_minutes']-1):break
        if armed is not None and end>armed['end']+5*cfg.max_wait_bars:return dict(reason='retest_expired')
        if not b['valid']:return dict(reason='unknown_signal')
        if armed is None:
            side=1 if b['close']>high+EPS else -1 if b['close']<low-EPS else 0
            if not side:continue
            if cfg.mode=='long_only' and side<0 or cfg.mode=='short_only' and side>0:return dict(reason='direction_filtered')
            level=high if side>0 else low
            if cfg.entry_mode=='breakout':return eligible(b,side,end-1,level,0)
            armed=dict(sign=side,end=end,level=level)
            continue
        side=armed['sign'];level=armed['level'];touch=b['low']<=level+EPS if side>0 else b['high']>=level-EPS
        if touch:
            if side*(b['close']-level)<=EPS or side*(b['close']-b['open'])<=EPS:return dict(reason='retest_failed')
            return eligible(b,side,armed['end']-1,level,(end-armed['end'])//5)
        if end==armed['end']+5*cfg.max_wait_bars:return dict(reason='retest_expired')
    return dict(reason='entry_cutoff' if armed is not None else 'no_breakout')

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


TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','range_high','range_low','breakout_slot','breakout_level','wait_bars','signal_low','signal_high',
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
