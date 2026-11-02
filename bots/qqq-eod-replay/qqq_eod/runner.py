"""Actions runtime: approved policy, pinned code, authenticated checkpoint, GET data."""
from pathlib import Path
from datetime import datetime,timezone
from importlib.metadata import version
import os,sys,json,re,hashlib,subprocess,tempfile
import pandas as pd
from .source import freeze_sources,activate_sources,QQQDataOnly,sha
from .state import seal_folder,open_folder
from .cloud import GitHubReadOnly,may_initialize,REPOSITORY,sequence_is_newer
from .schedule import due_sessions
from .journal import Journal
from .market import run_due

def dump(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def output(name,value):
 path=os.environ.get('GITHUB_OUTPUT')
 if path:
  with open(path,'a',encoding='utf-8') as stream:stream.write(name+'='+str(value)+'\n')

def verify_package(bot,commit):
 if not re.fullmatch('[0-9a-f]{40}',commit or ''):raise ValueError('registered release SHA required')
 repo=bot.parents[1];prefix=bot.relative_to(repo).as_posix();paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--',prefix+'/qqq_eod',prefix+'/scripts/run_replay.py',prefix+'/requirements.txt',prefix+'/ENGINE_LOCK.json'],cwd=repo,text=True).splitlines();hashes={}
 for name in paths:
  if not name.endswith(('.py','.json','.txt')):continue
  raw=subprocess.check_output(['git','show',commit+':'+name],cwd=repo);digest=hashlib.sha256(raw).hexdigest()
  if sha(repo/name)!=digest:raise ValueError('worker release changed')
  hashes[name]=digest
 if not hashes:raise ValueError('empty release refused')
 return hashlib.sha256(dump(hashes).encode()).hexdigest()

def dependencies(bot):
 result={}
 for line in (bot/'requirements.txt').read_text(encoding='utf-8').splitlines():
  if not line.strip():continue
  name,expected=line.split('==');actual=version(name)
  if actual!=expected:raise ValueError('dependency version differs from validated release')
  result[name]=actual
 return dict(python=sys.version.split()[0],packages=result)

def public_summary(data,identity):
 rows=[]
 for row in data['sessions']:
  result=row.get('result') or {};inputs=row.get('inputs') or {}
  fields=('status','reason','capital_before','capital_after','net_pnl','known_balance','open_position','known_commission','known_borrow','known_friction','decisions','trades','fills','price_prefix_sha256','operationally_observed')
  result=dict(result);result.setdefault('status',row['status'])
  rows.append(dict(bot=row['bot'],day=row['day'],**{k:result[k] for k in fields if k in result},input_sha=inputs.get('sha'),captured_utc=inputs.get('captured_utc'),capture_kind=inputs.get('capture_kind'),source_conflict=row.get('source_conflict',False)))
 return dict(identity=identity,first_day=data['first_day'],accounts=data['accounts'],sessions=rows,observation_kind='pre_registered_archived_bar_replay',operationally_observed=False,generated_utc=datetime.now(timezone.utc).isoformat())

def run_registered(bot):
 bot=Path(bot).resolve();repo=bot.parents[1]
 if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:raise ValueError('statistical runs require trusted main Actions context')
 if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('dispatch a new run instead of replaying an old attempt')
 a=json.loads((bot/'activation.json').read_text(encoding='utf-8'));lock=json.loads((bot/'ENGINE_LOCK.json').read_text(encoding='utf-8'))
 if not a.get('enabled') or os.environ.get('QQQ_EOD_ENABLED','').lower()!='true':raise ValueError('activation remains disabled')
 dep=dependencies(bot);release_hash=verify_package(bot,a.get('replay_release_commit'))
 temp=Path(os.environ['RUNNER_TEMP']);models=freeze_sources(repo,lock,temp/('qqq-models-'+lock['strategy_commit']));activate_sources(models,lock)
 # Task7 supplies this approved policy adapter and fixed numeric bands before activation.
 from .risk_policy import load_policy
 policy=load_policy(repo=repo,activation=a,engine_lock=lock)
 if policy.identity['strategy_commit']!=lock['strategy_commit']:raise ValueError('rule/model mismatch')
 first=policy.first_session;generation=a['generation']
 if not re.fullmatch('[a-z0-9-]{1,32}',generation or ''):raise ValueError('invalid registered generation')
 identity=dict(generation=generation,strategy_commit=lock['strategy_commit'],release_commit=a['replay_release_commit'],release_files_sha256=release_hash,dependencies=dep,rule=policy.identity,first_session=first)
 run_id=int(os.environ['GITHUB_RUN_ID']);attempt=int(os.environ['GITHUB_RUN_ATTEMPT']);head=os.environ['GITHUB_SHA']
 root=temp/'qqq-eod-state';out=temp/'qqq-eod-output';out.mkdir(exist_ok=True)
 reader=GitHubReadOnly(os.environ['GH_TOKEN']);client=None;ready=False;fatal=None
 try:
  previous,_=reader.prior_state(run_id,generation)
  if previous and not sequence_is_newer(os.environ['GITHUB_RUN_NUMBER'],previous['run']['run_number']):raise ValueError('out-of-order state writer refused; dispatch a new run')
  state_key=os.environ['QQQ_EOD_STATE_KEY']
  if previous:
   old=previous['run'];aad=dict(identity,checkpoint_run_id=old['id'],checkpoint_attempt=old['run_attempt'],checkpoint_head_sha=old['head_sha'])
   open_folder(reader.artifact_bytes(previous['id']),state_key,aad,root)
   oldmeta=json.loads((root/'checkpoint.json').read_text(encoding='utf-8'))
   if oldmeta['identity']!=identity or oldmeta['run_id']!=old['id']:raise ValueError('restored checkpoint identity mismatch')
  else:
   initialize=os.environ.get('QQQ_INITIALIZE','').lower()=='true'
   if not initialize or not may_initialize(first,pd.Timestamp.now(tz='UTC'),False):raise ValueError('missing state; initialization/reset refused')
   root.mkdir(parents=True,exist_ok=False)
  ready=True
  from qqq_paper.alpaca import Transport,DataClient
  key=os.environ['ALPACA_PAPER_KEY_ID'];secret=os.environ['ALPACA_PAPER_SECRET_KEY'];transport=QQQDataOnly(Transport(key,secret));del key,secret
  client=DataClient(transport)
  with Journal(root/'statistical.sqlite',identity,first) as journal:
   dates=due_sessions(first,pd.Timestamp.now(tz='UTC'))
   if dates:run_due(journal,client,root/'inputs',dates[-1],policy=policy)
   data=journal.export()
  (out/'summary.json').write_text(json.dumps(public_summary(data,identity),indent=2,allow_nan=False),encoding='utf-8')
 except Exception as error:
  fatal=error
 finally:
  if client:client.transport.clear()
  reader.clear()
  if ready:
   meta=dict(identity=identity,run_id=run_id,run_attempt=attempt,head_sha=head,previous_run_id=previous['run']['id'] if previous else None,captured_utc=datetime.now(timezone.utc).isoformat(),last_error_type=type(fatal).__name__ if fatal else None)
   (root/'checkpoint.json').write_text(json.dumps(meta,indent=2,allow_nan=False),encoding='utf-8')
   aad=dict(identity,checkpoint_run_id=run_id,checkpoint_attempt=attempt,checkpoint_head_sha=head)
   (out/'state.enc').write_bytes(seal_folder(root,os.environ['QQQ_EOD_STATE_KEY'],aad))
   output('state_artifact',f'qqq-eod-state-{generation}-{run_id}-{attempt}');output('state_ready','true')
 if fatal:raise fatal
 print(json.dumps(dict(state='checkpoint_ready',generation=generation,statistical_start=first,operationally_observed=False)))
 return 0
