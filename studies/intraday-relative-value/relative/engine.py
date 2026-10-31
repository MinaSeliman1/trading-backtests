"""Intraday dollar-neutral QQQ/SPY spread; no market-data or broker transport."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))
SYMBOLS=('QQQ','SPY')

@dataclass(frozen=True)
class Config:
 lookback:int=20
 entry_z:float=2.
 stop_z:float=3.
 slippage:float=.01
 delay:int=1
 direction:str='both'
 quality:str='complete_days'
 cost_gate:bool=False
 initial_capital:float=100000.
 risk_budget:float=.01
 leverage_cap:float=1.
 def __post_init__(self):
  if not isinstance(self.lookback,int) or self.lookback<2:raise ValueError('lookback')
  if not 0<self.entry_z<self.stop_z or not math.isfinite(self.stop_z):raise ValueError('z')
  if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('slippage')
  if self.delay not in (1,2):raise ValueError('delay')
  if self.direction not in ('both','long_spread_only','short_spread_only'):raise ValueError('direction')
  if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
  if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk')

class Unresolved(Exception):
 def __init__(self,reason,minute,known=None):self.reason=reason;self.minute=minute;self.known=known or {};super().__init__(reason)

def positive(x):return math.isfinite(float(x)) and float(x)>0

def prepare(markets,cfg):
 q,s=[markets[x] for x in SYMBOLS]
 if not q.dates.equals(s.dates) or not np.array_equal(q.lengths,s.lengths):raise ValueError('pair calendar alignment')
 valid=q.valid&s.valid;n=len(q.dates);slots=np.arange(390)
 with np.errstate(divide='ignore',invalid='ignore'):
  r=np.log(q.arrays['close']/q.arrays['open'][:,0,None])-np.log(s.arrays['close']/s.arrays['open'][:,0,None])
 r=np.where(slots[None,:]<q.lengths[:,None],r,np.nan);features=[]
 for i,date in enumerate(q.dates):
  reason='warmup' if i<cfg.lookback else 'unknown_history' if not valid[i-cfg.lookback:i].all() else 'ready'
  mu=np.full(390,np.nan);sd=mu.copy();count=np.zeros(390,dtype=int)
  if reason=='ready':
   history=r[i-cfg.lookback:i];finite=np.isfinite(history);count=finite.sum(axis=0)
   mu=np.divide(np.nansum(history,axis=0),count,out=mu,where=count>0)
   variance=np.divide(np.nansum((history-mu)**2,axis=0),count-1,out=np.full(390,np.nan),where=count>1);sd=np.sqrt(variance)
   enough=count>=math.ceil(.75*cfg.lookback);mu=np.where(enough,mu,np.nan);sd=np.where(enough,sd,np.nan)
  features.append(dict(index=i,date=str(date.date()),n=int(q.lengths[i]),reason=reason,mean=mu,sd=sd,count=count))
 return features

def spread(markets,i,j,kind='close'):
 values=[]
 for symbol in SYMBOLS:
  a=markets[symbol].arrays;op=float(a['open'][i,0]);value=float(a[kind][i,j])
  if not positive(op) or not positive(value):return math.nan
  values.append(math.log(value/op))
 return values[0]-values[1]

def anticipated(order,cfg):
 q,s=order['quantity_qqq'],order['quantity_spy'];sign=order['sign'];pq,ps=order['sizing_qqq'],order['sizing_spy']
 fee=2*(max(.35,q*.0035)+max(.35,s*.0035));friction=2*cfg.slippage*(q+s)
 short_qty,short_price=(s,ps) if sign>0 else (q,pq)
 borrow=short_qty*max(0.,short_price-cfg.slippage)*.01/360
 return fee+friction+borrow

def choose(markets,f,cfg,capital):
 if f['reason']!='ready':return dict(reason=f['reason'])
 i=f['index'];n=f['n']
 if not all(positive(markets[s].arrays['open'][i,0]) for s in SYMBOLS):return dict(reason='unknown_anchor')
 last_reason='no_signal'
 for j in range(29,min(299,n-2-cfg.delay)+1,5):
  mu,sd=float(f['mean'][j]),float(f['sd'][j])
  if not math.isfinite(mu) or not math.isfinite(sd):return dict(reason='unknown_history',unknown_slot=j)
  if sd<=1e-8:continue
  x=spread(markets,i,j)
  if not math.isfinite(x):return dict(reason='unknown_signal',unknown_slot=j)
  z=(x-mu)/sd
  if abs(z)<cfg.entry_z-1e-12 or abs(z)>=cfg.stop_z-1e-12:continue
  sign=1 if z<0 else -1
  if cfg.direction=='long_spread_only' and sign<0 or cfg.direction=='short_spread_only' and sign>0:continue
  prices={s:float(markets[s].arrays['close'][i,j]) for s in SYMBOLS};distance=D(sd)*(D(cfg.stop_z)-abs(D(z)))
  notional=min(D(capital)*D(cfg.leverage_cap)/2,D(capital)*D(cfg.risk_budget)/distance)
  qty={s:int((notional/D(prices[s])).to_integral_value(rounding=ROUND_FLOOR)) for s in SYMBOLS}
  if min(qty.values())<=0:last_reason='zero_quantity';continue
  gross=sum(qty[s]*prices[s] for s in SYMBOLS)
  order=dict(reason='eligible',signal_slot=j,entry_slot=j+cfg.delay,sign=sign,z=z,mean=mu,sd=sd,stop_spread=mu-sign*cfg.stop_z*sd,
    quantity_qqq=qty['QQQ'],quantity_spy=qty['SPY'],sizing_qqq=prices['QQQ'],sizing_spy=prices['SPY'],gross_sizing=gross,
    proxy_risk_usd=gross/2*float(distance),expected_reversion_gross=gross/2*abs(x-mu))
  order['anticipated_cost']=anticipated(order,cfg)
  if cfg.cost_gate and order['expected_reversion_gross']<2*order['anticipated_cost']:last_reason='cost_filtered';continue
  return order
 return dict(reason=last_reason)

def execute(markets,f,o,cfg):
 i=f['index'];n=f['n'];left=o['entry_slot'];sign=o['sign'];qty={'QQQ':o['quantity_qqq'],'SPY':o['quantity_spy']};sides={'QQQ':sign,'SPY':-sign}
 entry={s:float(markets[s].arrays['open'][i,left]) for s in SYMBOLS}
 known=dict(known_entry_commission=0.,known_entry_friction=0.,known_borrow=0.,entry_legs_known=0)
 for s in SYMBOLS:
  if positive(entry[s]):
   known['entry_legs_known']+=1;known['known_entry_commission']+=max(.35,qty[s]*.0035);known['known_entry_friction']+=qty[s]*cfg.slippage
   if sides[s]<0:known['known_borrow']+=qty[s]*max(0.,entry[s]-cfg.slippage)*.01/360
 if not all(positive(x) for x in entry.values()):raise Unresolved('missing_entry_open',left,known)
 fills={s:entry[s]+sides[s]*cfg.slippage for s in SYMBOLS}
 if not all(positive(x) for x in fills.values()):raise ValueError('nonpositive modeled fill')
 exit_slot=n-1;why='eod_open'
 for j in range(left,n-1):
  x=spread(markets,i,j)
  if not math.isfinite(x):raise Unresolved('missing_active_close',j,known)
  signed=sign*(x-o['mean'])
  if signed<=-cfg.stop_z*o['sd'] or signed>=0:
   why='eod_open' if j+cfg.delay>n-1 else 'spread_stop' if signed<=-cfg.stop_z*o['sd'] else 'mean_cross';exit_slot=min(j+cfg.delay,n-1);break
 # Require all close marks while held, including any wait between exit decision and its fill.
 price_marks=[-known['known_entry_friction']]
 for j in range(left,exit_slot):
  if not all(positive(markets[s].arrays['close'][i,j]) for s in SYMBOLS):raise Unresolved('missing_active_close',j,known)
  price_marks.append(sum(qty[s]*sides[s]*(float(markets[s].arrays['close'][i,j])-fills[s]) for s in SYMBOLS))
 exits={s:float(markets[s].arrays['open'][i,exit_slot]) for s in SYMBOLS}
 if not all(positive(x) for x in exits.values()):raise Unresolved('missing_exit_open',exit_slot,known)
 legs=[]
 for s in SYMBOLS:
  ep=exits[s]-sides[s]*cfg.slippage
  if not positive(ep):raise ValueError('nonpositive modeled fill')
  fee=2*max(.35,qty[s]*.0035);friction=2*qty[s]*cfg.slippage;borrow=qty[s]*fills[s]*.01/360 if sides[s]<0 else 0.;move=qty[s]*sides[s]*(exits[s]-entry[s]);gross=qty[s]*sides[s]*(ep-fills[s]);net=gross-fee-borrow
  legs.append(dict(symbol=s,side=sides[s],quantity=qty[s],entry_reference=entry[s],exit_reference=exits[s],entry_price=fills[s],exit_price=ep,price_move_pnl=move,friction_cost=friction,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net))
 totals={k:sum(x[k] for x in legs) for k in ['price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl']}
 price_marks.append(totals['gross_pnl']);marks=[-known['known_entry_commission']-known['known_borrow']+v for v in price_marks[:-1]]+[totals['net_pnl']]
 opening=pd.Timestamp(markets['QQQ'].quality.iloc[i].session_open)
 return dict(**totals,entry_slot=left,exit_slot=exit_slot,entry_time=str(opening+pd.Timedelta(minutes=left)),exit_time=str(opening+pd.Timedelta(minutes=exit_slot)),exit_reason=why,
   entry_reference_qqq=entry['QQQ'],entry_reference_spy=entry['SPY'],exit_reference_qqq=exits['QQQ'],exit_reference_spy=exits['SPY'],
   gross_entry_reference=sum(qty[s]*entry[s] for s in SYMBOLS),gross_entry_fill=sum(qty[s]*fills[s] for s in SYMBOLS),holding_minutes=exit_slot-left,
   mae_price_usd=min(0.,min(price_marks)),mfe_price_usd=max(0.,max(price_marks)),legs=legs,marks=marks)

TRADE_COLUMNS=['date','signal_slot','entry_slot','exit_slot','entry_time','exit_time','exit_reason','sign','z','mean','sd','stop_spread','quantity_qqq','quantity_spy','sizing_qqq','sizing_spy','gross_sizing','proxy_risk_usd','expected_reversion_gross','anticipated_cost',
 'entry_reference_qqq','entry_reference_spy','exit_reference_qqq','exit_reference_spy','gross_entry_reference','gross_entry_fill','entry_leverage','entry_fill_leverage','proxy_risk_pct','holding_minutes','mae_price_usd','mfe_price_usd','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','equity_before','equity_after']
LEG_COLUMNS=['date','entry_time','exit_time','symbol','side','quantity','entry_reference','exit_reference','entry_price','exit_price','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl']
UNRESOLVED_COLUMNS=['date','reason','first_unknown_slot','sign','quantity_qqq','quantity_spy','known_entry_commission','known_entry_friction','known_borrow','entry_legs_known']

def simulate(markets,features,cfg,start,end):
 capital=cfg.initial_capital;peak=capital;dd=ddusd=0.;daily=[];trades=[];legs=[];unresolved=[]
 for f in features:
  if not start<=f['date']<=end:continue
  before=capital;order=choose(markets,f,cfg,capital);why=order['reason'];excluded=why.startswith('unknown_');marks=[capital];net=fees=borrow=friction=0.;held=0;done=0
  if capital<=0:why='insolvent'
  if why=='eligible' and cfg.quality=='complete_days' and not all(markets[s].valid[f['index']] for s in SYMBOLS):why='excluded_incomplete_day';excluded=True
  if why=='eligible':
   try:out=execute(markets,f,order,cfg)
   except Unresolved as e:
    why='unresolved_execution';excluded=True;unresolved.append(dict(date=f['date'],reason=e.reason,first_unknown_slot=e.minute,sign=order['sign'],quantity_qqq=order['quantity_qqq'],quantity_spy=order['quantity_spy'],**e.known))
   else:
    net=out['net_pnl'];capital+=net;done=1;held=out['holding_minutes'];fees=out['commission'];borrow=out['borrow_fee'];friction=out['friction_cost'];marks+=[before+v for v in out.pop('marks')]
    legs.extend(dict(date=f['date'],entry_time=out['entry_time'],exit_time=out['exit_time'],**x) for x in out.pop('legs'))
    trades.append(dict(date=f['date'],**{k:v for k,v in order.items() if k!='reason'},**{k:v for k,v in out.items() if k!='entry_slot'},entry_leverage=out['gross_entry_reference']/before,entry_fill_leverage=out['gross_entry_fill']/before,proxy_risk_pct=order['proxy_risk_usd']/before*100,equity_before=before,equity_after=capital))
  for v in marks:peak=max(peak,v);dd=max(dd,(peak-v)/peak*100);ddusd=max(ddusd,peak-v)
  daily.append(dict(date=f['date'],session_minutes=f['n'],eligibility=why,conditionally_excluded=excluded,observed_return=math.nan if excluded else net/before if before>0 else 0.,return_net=net/before if before>0 else 0.,net_pnl=net,equity=capital,trades=done,signal_sign=order.get('sign',0),commission=fees,borrow_fee=borrow,friction_cost=friction,holding_minutes=held,observed_drawdown_pct_so_far=dd))
 return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),legs=pd.DataFrame(legs,columns=LEG_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=UNRESOLVED_COLUMNS),initial_capital=cfg.initial_capital,observed_drawdown_pct=dd,observed_drawdown_usd=ddusd)
