"""Generic cloud assessments; never copy arbitrary summary/exception text."""
import json
import pandas as pd
from .transport import CODES

def assess_summary(summary):
 issues={b:set() for b in ('noise','orb')}
 for row in summary.get('sessions',[]):
  if row.get('bot') in issues and row.get('status') in ('unresolved','pending'):issues[row['bot']].add('cloud_unresolved')
 for bot in issues:
  risk=summary.get('risk_status',{}).get(bot,{})
  if risk.get('stop'):issues[bot].add('risk_stop')
  if risk.get('data_blocked'):issues[bot].add('cloud_unresolved')
 return issues

def health_labels(events,now,session_day):
 if not session_day:return {b:'hors seance' for b in ('noise','orb')}
 now=pd.Timestamp(now).tz_convert('UTC');candidates=[]
 for event in events:
  try:
   if event.get('event')!='message':continue
   data=json.loads(event['message']);stamp=pd.Timestamp(data['utc']);age=(now-stamp).total_seconds()
   if data.get('version')!=1 or not 0<=age<=720 or set(data['issues'])!={'noise','orb'}:continue
   if any(not isinstance(v,list) or not set(v)<=CODES.keys() for v in data['issues'].values()):continue
   candidates.append((stamp,data))
  except (KeyError,ValueError,TypeError):continue
 if not candidates:return {b:'non verifie' for b in ('noise','orb')}
 data=max(candidates,key=lambda x:x[0])[1]
 return {b:'attention' if data['issues'][b] else 'controle recent sain' for b in ('noise','orb')}


def trusted_run(run):
 return bool(run.get('name')=='QQQ EOD replay' and run.get('path')=='.github/workflows/qqq-eod-replay.yml' and run.get('head_branch')=='main' and run.get('repository',{}).get('full_name')=='MinaSeliman1/trading-backtests' and run.get('head_repository',{}).get('full_name')=='MinaSeliman1/trading-backtests')
