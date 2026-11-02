"""Read-only local companion. Writes only the separate operational ledger."""
from pathlib import Path
import sys,json,argparse,subprocess,zipfile,io,os,uuid,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qqq_eod.live import read_noise,read_orb,OperationalJournal,compare
from qqq_eod.schedule import due_sessions
import pandas as pd

REPO='MinaSeliman1/trading-backtests'
def gh(*args,binary=False):
 executable=os.environ.get('QQQ_EOD_GH_EXE','gh');r=subprocess.run([executable,*args,'--repo',REPO] if args and args[0]=='run' else [executable,*args],capture_output=True,check=False,timeout=60)
 if r.returncode:raise RuntimeError('GitHub summary read failed')
 return r.stdout if binary else json.loads(r.stdout)

def cloud_summary(bot):
 activation=json.loads((bot/'activation.json').read_text(encoding='utf-8'))
 if not activation.get('enabled'):return None
 runs=gh('run','list','--workflow','qqq-eod-replay.yml','--branch','main','--limit','30','--json','databaseId,headSha,status')
 for r in runs:
  root='/repos/'+REPO+'/actions/runs/'+str(r['databaseId'])
  listing=gh('api',root+'/jobs?filter=all&per_page=100');jobs=listing['jobs']
  if listing['total_count']>len(jobs):raise ValueError('incomplete active job history; stale fallback refused')
  active=[j for j in jobs if any(s['name']=='Active generation checkpoint' and s.get('conclusion')=='success' for s in j.get('steps',[]))]
  if not active:continue
  job=max(active,key=lambda j:j.get('run_attempt',1));attempt=job.get('run_attempt',1)
  if job['status']!='completed':return None
  artifacts=gh('api',root+'/artifacts?per_page=100')['artifacts'];name=f"qqq-eod-summary-{r['databaseId']}-{attempt}"
  matches=[a for a in artifacts if a['name']==name and not a['expired'] and a['workflow_run']['head_sha']==r['headSha']]
  if len(matches)!=1:raise RuntimeError('latest active summary unavailable; stale fallback refused')
  raw=gh('api','/repos/'+REPO+'/actions/artifacts/'+str(matches[0]['id'])+'/zip',binary=True)
  if len(raw)>4*1024*1024:raise ValueError('summary archive too large')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   if len(z.infolist())!=1 or z.infolist()[0].filename!='summary.json' or z.infolist()[0].file_size>16*1024*1024:raise ValueError('unexpected summary layout')
   data=json.loads(z.read('summary.json'))
  if data['identity']['generation']!=activation['generation']:raise ValueError('summary generation mismatch')
  rule=(bot.parents[1]/activation['rule_path']).read_bytes()
  if data['first_day']!=activation['first_statistical_session'] or data['identity']['rule']['rule_sha256']!=hashlib.sha256(rule).hexdigest():raise ValueError('summary rule/cohort mismatch')
  return data
 raise RuntimeError('no active statistical summary')

def main():
 p=argparse.ArgumentParser();p.add_argument('--first',default='2026-10-21');p.add_argument('--through');p.add_argument('--summary',type=Path);p.add_argument('--github',action='store_true');p.add_argument('--output',type=Path);args=p.parse_args()
 bot=Path(__file__).resolve().parents[1];bots=bot.parent;output=args.output or bot/'runtime'/'operational';output.mkdir(parents=True,exist_ok=True)
 dates=due_sessions(args.first,pd.Timestamp.now(tz='UTC'))
 if args.through:dates=[d for d in dates if d<=args.through]
 if args.github and args.summary:raise ValueError('choose one summary source')
 errors=[];activation=json.loads((bot/'activation.json').read_text())
 try:stats=json.loads(args.summary.read_text(encoding='utf-8')) if args.summary else cloud_summary(bot) if args.github else None
 except Exception as e:stats=None;errors.append(dict(component='cloud_summary',error_type=type(e).__name__))
 first=activation.get('first_statistical_session')
 if stats and stats['first_day']!=first:stats=None;errors.append(dict(component='cloud_summary',error_type='CohortMismatch'))
 statrows={(r['bot'],r['day']):r for r in stats.get('sessions',[])} if stats else {};comparisons=[]
 with OperationalJournal(output/'operational.sqlite',first_day=first) as journal:
  for day in dates:
   for name,reader,path in [('noise',read_noise,bots/'qqq-noise-area/runtime/shadow-sip/state.sqlite'),('orb',read_orb,bots/'qqq-orb/runtime/state.sqlite')]:
    if name=='orb' and day<'2026-10-26':continue
    try:record=reader(path,day)
    except Exception as e:
     errors.append(dict(bot=name,day=day,error_type=type(e).__name__));continue
    journal.record(record)
    row=statrows.get((name,day))
    if row:
     entry=dict(bot=name,day=day,original_comparison=compare(row,record))
     if row.get('status')=='complete' and record.get('capital_before') and record.get('position_before',0)==0:
      from qqq_eod.source import freeze_sources,activate_sources
      from qqq_eod.parity import capital_matched
      lock=json.loads((bot/'ENGINE_LOCK.json').read_text());activate_sources(freeze_sources(bot.parents[1],lock,bot/'runtime/frozen-sources'),lock)
      try:
       matched=capital_matched(row,record['capital_before']);entry['capital_matched']=dict(net_pnl=matched['net_pnl'],assumption=matched['assumption'],comparison=compare(matched,record))
      except (ValueError,KeyError) as e:entry['capital_match_unavailable']=type(e).__name__
     if day>=stats['first_day']:
      from qqq_eod.risk_policy import assess_parity
      activation=json.loads((bot/'activation.json').read_text());relative=activation.get('rule_path')
      if relative:
       rule_file=bot.parents[1]/relative;raw=rule_file.read_bytes();expected=stats.get('identity',{}).get('rule',{}).get('rule_sha256')
       if hashlib.sha256(raw).hexdigest()!=expected:entry['rule_assessment_unavailable']='rule_version_mismatch'
       else:
        comparison=entry.get('capital_matched',{}).get('comparison',entry['original_comparison'])
        if row.get('source_conflict'):comparison['context'].append('source_conflict')
        entry['registered_parity_assessment']=assess_parity(comparison,json.loads(raw))
     comparisons.append(entry)
  latest=journal.latest();qualified=journal.latest(qualified_only=True)
 legacy=[r for r in latest if first is None or r['day']<first]
 report=dict(generated_utc=pd.Timestamp.now(tz='UTC').isoformat(),mode='read_only_live_journals',statistical_first=first,cloud_summary_available=stats is not None,legacy_observations=legacy,legacy_qualified_sessions={b:sum(r['bot']==b and r.get('qualified',False) for r in legacy) for b in ('noise','orb')},qualified_sessions={b:sum(r['bot']==b for r in qualified) for b in ('noise','orb')},operational_ledger=qualified,coverage_observations=[r for r in latest if first is not None and r['day']>=first],observations=latest,comparisons=comparisons,errors=errors)
 if stats is not None:
  cache=output/'cloud_summary.json';temp=cache.with_suffix('.tmp-'+uuid.uuid4().hex);temp.write_text(json.dumps(stats,indent=2,allow_nan=False),encoding='utf-8');temp.replace(cache)
 target=output/'comparison.json';temp=target.with_suffix('.tmp-'+uuid.uuid4().hex);temp.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');temp.replace(target)
 print(json.dumps(dict(observations=len(latest),qualified=report['qualified_sessions'],comparisons=len(comparisons),errors=len(errors),output=str(target))))
 return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
