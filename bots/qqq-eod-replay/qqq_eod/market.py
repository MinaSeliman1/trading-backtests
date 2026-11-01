"""Acquire exact day inputs and replay independent accounts in date order."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tempfile
import pandas as pd
from .source import canonical_frame,capture_pack
from . import replay

def unavailable(bot,capital,error):
 return dict(bot=bot,status='unresolved',capital_before=capital,capital_after=None,net_pnl=None,known_balance=capital,open_position=None,known_commission=0.,known_borrow=0.,known_friction=0.,decisions=[],trades=[],fills=[],operationally_observed=False,observation_kind='input_unavailable',error_type=type(error).__name__,api_status=getattr(error,'status',None),evaluated_utc=datetime.now(timezone.utc).isoformat())

def acquire(client,folder,session,bot,current_cache):
 day=str(session.open.date());metadata=dict(day=day,bot=bot,feed='sip',adjustment='raw',timeframe='1Min')
 if day not in current_cache:current_cache[day]=canonical_frame(client.bars(session.open,session.close,'sip'))
 current=current_cache[day];frames={'current':current};dividend=0.
 if bot=='noise':
  end=session.open.normalize();frames['history']=canonical_frame(client.bars(end-pd.Timedelta(days=100),end,'sip'));dividend=float(client.dividend(day))
  if not pd.notna(dividend) or dividend<0:raise ValueError('invalid ex-date dividend')
 metadata['dividend']=dividend;pack=capture_pack(folder,frames,metadata)
 input_sha=hashlib.sha256(json.dumps(dict(roles=pack['roles'],dividend=dividend),sort_keys=True).encode()).hexdigest()
 inputs=dict(sha=input_sha,receipt_path=pack['receipt_path'],captured_utc=pack['captured_utc'],dividend=dividend,roles=pack['roles'],feed='sip')
 return frames,inputs

def run_due(journal,client,input_folder,through,max_days=20):
 from qqq_paper.runtime import session_for
 from noise_area.data import read_market
 input_folder=Path(input_folder);cache={};processed=[]
 for bot in ('noise','orb'):
  for _ in range(max_days):
   day=journal.next_due(bot,through)
   if day is None:break
   capital=journal.balance(bot);session=session_for(day)
   if session is None:raise RuntimeError('journal date not an XNYS session')
   try:frames,inputs=acquire(client,input_folder,session,bot,cache)
   except Exception as error:
    result=unavailable(bot,capital,error);inputs=dict(captured_utc=datetime.now(timezone.utc).isoformat(),error_type=type(error).__name__,api_status=getattr(error,'status',None))
   else:
    if bot=='orb':result=replay.orb(frames['current'],session,capital)
    else:
     with tempfile.TemporaryDirectory(prefix='qqq-eod-noise-') as work:
      path=Path(work)/'warmup.csv';frames['history'].to_csv(path,index_label='timestamp',lineterminator='\n',float_format='%.17g')
      try:history=read_market([path],'QQQ')
      except ValueError as error:result=unavailable(bot,capital,error)
      else:
       previous=__import__('qqq_paper.runtime',fromlist=['calendar']).calendar(day).previous_session(pd.Timestamp(day))
       if not len(history.dates) or pd.Timestamp(history.dates[-1]).date()!=pd.Timestamp(previous).date():result=unavailable(bot,capital,ValueError('missing previous session'))
       else:result=replay.noise(history,frames['current'],session,capital,inputs['dividend'],Path(work)/'engine')
   changed=journal.record(bot,day,result,inputs);processed.append(dict(bot=bot,day=day,status=result['status'],changed=changed))
   if result['status']!='complete':break
 return processed
