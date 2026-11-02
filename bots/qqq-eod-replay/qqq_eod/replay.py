"""Causal adapters around the hash-locked bots; no trading API constructed."""
from pathlib import Path
from contextlib import closing
from datetime import datetime,timezone
import json,math,tempfile
import pandas as pd

def base(capital):
 if not math.isfinite(capital) or capital<=0:raise ValueError('positive finite virtual capital required')
 return dict(capital_before=float(capital),operationally_observed=False,evaluated_utc=datetime.now(timezone.utc).isoformat(),observation_kind='archived_bar_replay')

def noise(history,bars,session,capital,dividend=0.,workdir=None):
 from qqq_paper.strategy import Parameters,decision_times,verify_frozen_strategy
 from qqq_paper.runner import Controller
 from qqq_paper.ledger import Store
 verify_frozen_strategy();out=base(capital)
 if workdir is None:
  with tempfile.TemporaryDirectory(prefix='qqq-noise-replay-') as folder:return noise(history,bars,session,capital,dividend,folder)
 root=Path(workdir);root.mkdir(parents=True,exist_ok=True);path=root/'engine.sqlite'
 if path.exists():raise ValueError('fresh replay workspace required')
 with closing(Store(path,Parameters(initial_capital=float(capital)),'shadow','sip')) as store:
  controller=Controller(store,mode='shadow')
  times=[at+pd.Timedelta(minutes=1) for at in decision_times(session)]+[session.close]
  for at in times:
   prefix=bars.loc[(bars.index>=session.open)&(bars.index<at)]
   try:controller.step(history,prefix,session,at,dividend)
   except (ValueError,KeyError):break
  decisions=[]
  for row in store.db.execute('SELECT data FROM decisions ORDER BY key'):
   value=json.loads(row[0]);value['engine_asof']=value.pop('observed_at',None);decisions.append(value)
  fills=store.fills();orders={r['cid']:dict(r) for r in store.db.execute('SELECT * FROM orders')};trades=[];opened=None
  for f in fills:f['action']=orders[f['cid']]['action']
  for f in fills:
   order=orders[f['cid']]
   if order['action']=='open':opened=f
   elif opened is not None:
    trades.append(dict(direction=opened['sign'],quantity=opened['qty'],entry_time=opened['timestamp'],exit_time=f['timestamp'],entry_reference=opened['actual'],exit_reference=f['actual'],entry_price=opened['modeled'],exit_price=f['modeled'],commission=opened['commission']+f['commission'],borrow_fee=f['borrow'],net_pnl=f['realized']-opened['commission']-f['commission']-f['borrow']))
    opened=None
  complete=(len(decisions)==len(decision_times(session)) and all(d.get('status')=='processed' for d in decisions) and store.position==0 and not store.get('paused') and store.get('paused_day')!=str(session.open.date()))
  out.update(bot='noise',status='complete' if complete else 'unresolved',capital_after=store.balance if complete else None,net_pnl=store.balance-capital if complete else None,known_balance=store.balance,open_position=store.position,
   known_commission=sum(f['commission'] for f in fills),known_borrow=sum(f['borrow'] for f in fills),known_friction=sum(f['qty']*.01 for f in fills),decisions=decisions,fills=fills,trades=trades)
 return out

def orb(bars,session,capital):
 from orb_shadow.core import account,advance,verify_model
 verify_model();out=base(capital);a=account(capital);day=None;n=int((session.close-session.open).total_seconds()/60)
 for slot in range(5,n+1):
  at=session.open+pd.Timedelta(minutes=slot);left=session.open if slot==5 else at-pd.Timedelta(minutes=1);prefix=bars.loc[(bars.index>=left)&(bars.index<at)]
  a,day=advance(a,day,prefix,session,at)
  if day['phase'] in ('closed','flat','skipped','unresolved'):break
 complete=bool(day and day['phase'] in ('closed','flat'))
 trades=[day['trade']] if day and 'trade' in day else []
 intent=dict((day or {}).get('intent') or {});engine_asof=intent.pop('observed_at',None)
 decisions=[dict(intent,engine_asof=engine_asof)] if intent else []
 position=int(intent.get('quantity',0))*int(intent.get('sign',0)) if a['open_day'] else 0
 commission=sum(t['commission'] for t in trades) if complete else float((day or {}).get('entry_fee',0.))
 borrow=sum(t['borrow_fee'] for t in trades)
 friction=sum(t['quantity']*.02 for t in trades) if complete else abs(position)*.01
 from .source import rows_sha
 out.update(bot='orb',price_prefix_sha256=rows_sha((day or {}).get('bars',{})),status='complete' if complete else 'unresolved',capital_after=a['balance'] if complete else None,net_pnl=a['balance']-capital if complete else None,known_balance=a['balance'],open_position=position,
  known_commission=commission,known_borrow=borrow,known_friction=friction,decisions=decisions,trades=trades,fills=[],engine_phase=(day or {}).get('phase'),engine_notes=(day or {}).get('notes',[]))
 return out
