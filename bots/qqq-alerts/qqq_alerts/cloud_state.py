"""Small public artifact stores only notification transitions, never trading state."""
from pathlib import Path
import json,io,re,zipfile
from .transport import CODES
from .outbox import atomic
PREFIX='/repos/MinaSeliman1/trading-backtests/actions/'
LIMIT=262144

def restore_bytes(raw,path):
 if len(raw)>LIMIT:raise ValueError('notification state oversized')
 data=json.loads(raw)
 if not isinstance(data,dict) or not {'observed','pending','sent_dates'}<=data.keys():raise ValueError('invalid notification state')
 for bot,codes in data['observed'].items():
  if bot not in ('noise','orb','cloud','watchdog') or not isinstance(codes,list) or not set(codes)<=CODES.keys():raise ValueError('invalid notification transition')
 for row in data['pending']:
  if row['bot'] not in ('noise','orb','cloud','watchdog') or not set(row['codes'])<=CODES.keys() or not re.fullmatch(r'incident-[a-f0-9]{32}',row['key']):raise ValueError('invalid pending notification')
  from datetime import datetime
  if datetime.fromisoformat(row['stamp']).tzinfo is None:raise ValueError('notification timestamp requires timezone')
 if any(not re.fullmatch(r'\d{4}-\d{2}-\d{2}',d) or not isinstance(n,int) or n<0 or n>250 for d,n in data['sent_dates'].items()):raise ValueError('invalid notification counters')
 # Rebuild from allowlisted fields so an artifact cannot smuggle arbitrary payloads.
 clean=dict(observed=data['observed'],pending=[{k:v[k] for k in ('bot','codes','stamp','key')} for v in data['pending']],sent_dates=data['sent_dates'])
 if data.get('last_life_day'):
  from datetime import date
  date.fromisoformat(data['last_life_day']);clean['last_life_day']=data['last_life_day']
 atomic(path,clean)

def restore_latest(api,current_run,path):
 listing=api(PREFIX+'workflows/qqq-alerts.yml/runs?branch=main&per_page=50')
 for run in listing['workflow_runs']:
  if run['id']==current_run or run.get('head_branch')!='main':continue
  name='qqq-alert-delivery-'+str(run['id'])+'-'+str(run['run_attempt'])
  artifacts=api(PREFIX+'runs/'+str(run['id'])+'/artifacts?per_page=100')
  if artifacts['total_count']>len(artifacts['artifacts']):raise ValueError('notification artifact listing truncated')
  found=[a for a in artifacts['artifacts'] if a['name']==name and not a['expired'] and a['workflow_run']['head_sha']==run['head_sha']]
  if len(found)>1:raise ValueError('ambiguous notification state')
  if found:
   raw=api(PREFIX+'artifacts/'+str(found[0]['id'])+'/zip',True)
   if len(raw)>LIMIT:raise ValueError('notification archive oversized')
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    if len(z.infolist())!=1 or z.infolist()[0].filename!='outbox.json' or z.infolist()[0].file_size>LIMIT:raise ValueError('invalid notification archive')
    restore_bytes(z.read('outbox.json'),path)
   return run['id']
 if listing['total_count']>len(listing['workflow_runs']):raise ValueError('no retained notification state in bounded history')
 return None
