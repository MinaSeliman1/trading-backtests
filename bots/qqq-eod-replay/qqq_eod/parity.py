"""Capital-matched economic diagnostic, conditional on replay signals and prices.

This is not a second statistical account or an indicator replay on live prices.
"""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
import tempfile,math

def capital_matched(statistical,capital):
 if statistical.get('status')!='complete' or not math.isfinite(capital) or capital<=0:raise ValueError('resolved replay and positive known capital required')
 out=deepcopy(statistical);out.update(capital_before=capital,capital_after=capital,net_pnl=0.,diagnostic_only=True,assumption='same replay signals and reference fill prices; full live-input parity not established')
 if statistical['bot']=='noise':
  from qqq_paper.strategy import Parameters,day_size
  from qqq_paper.ledger import Store
  first=next((d for d in out.get('decisions',[]) if 'opening' in d and 'volatility' in d),None)
  q=day_size(capital,first['opening'],first['volatility']) if first else 0
  if q<=0 and out.get('fills'):raise ValueError('rebased quantity unavailable')
  for d in out.get('decisions',[]):
   if 'quantity' in d:d['quantity']=q
  with tempfile.TemporaryDirectory(prefix='qqq-eod-revalue-') as folder,closing(Store(Path(folder)/'engine.sqlite',Parameters(initial_capital=capital),'shadow','sip')) as store:
   for i,f in enumerate(out.get('fills',[])):
    action=f['action'];count=q if action=='open' else abs(store.position);cid='diagnostic-'+str(i)
    store.intent(cid,str(f['timestamp'])[:10],action,int(f['sign']),int(count),str(i))
    store.apply(dict(client_order_id=cid,status='filled',filled_qty=count,filled_avg_price=f['actual'],filled_at=f['timestamp']))
   out.update(capital_after=store.balance,net_pnl=store.balance-capital,fills=store.fills(),trades=[])
 else:
  from orb.engine import Config
  p=Config();D=lambda x:Decimal(str(x));intent=next(iter(out.get('decisions',[])),None)
  if intent and intent.get('sign'):
   risk=intent['sign']*(D(intent['sizing_price'])-D(intent['stop']))
   q=int(min(D(capital)/D(intent['sizing_price']),D(capital)*D(p.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR)) if risk>0 else 0
   intent['quantity']=q
   for t in out.get('trades',[]):
    fee=2*max(p.minimum_commission,q*p.commission) if q else 0.;borrow=q*t['entry_price']*p.borrow_rate/360 if t['sign']<0 else 0.
    net=q*t['sign']*(t['exit_price']-t['entry_price'])-fee-borrow;t.update(quantity=q,commission=fee,borrow_fee=borrow,net_pnl=net,capital_before=capital,capital_after=capital+net)
    out.update(net_pnl=net,capital_after=capital+net)
 return out
