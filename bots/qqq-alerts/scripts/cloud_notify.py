"""Read trusted Actions metadata/summary and send generic ntfy notices only."""
from pathlib import Path
import os,sys,json,subprocess,io,zipfile
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from qqq_alerts.transport import Ntfy
from qqq_alerts.cloud import trusted_run,assess_summary,health_labels
from qqq_alerts.policy import NY,session
REPO='MinaSeliman1/trading-backtests'

def api(path,binary=False):
 if not path.startswith('/repos/'+REPO+'/actions/'):raise ValueError('unapproved Actions route')
 env=dict(os.environ,GH_HOST='github.com');env.pop('GH_DEBUG',None)
 r=subprocess.run(['gh','api',path],capture_output=True,timeout=45,env=env)
 if r.returncode:raise RuntimeError('Actions metadata unavailable')
 return r.stdout if binary else json.loads(r.stdout)

def summary_for(run):
 prefix='/repos/'+REPO+'/actions/';name='qqq-eod-summary-'+str(run['id'])+'-'+str(run['run_attempt'])
 listing=api(prefix+'runs/'+str(run['id'])+'/artifacts?per_page=100')
 if listing['total_count']>len(listing['artifacts']):raise ValueError('incomplete artifact listing')
 matches=[a for a in listing['artifacts'] if a['name']==name and not a['expired'] and a['workflow_run']['head_sha']==run['head_sha']]
 if len(matches)!=1:raise ValueError('latest run summary unavailable')
 raw=api(prefix+'artifacts/'+str(matches[0]['id'])+'/zip',True)
 if len(raw)>4*1024*1024:raise ValueError('summary archive too large')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if len(z.infolist())!=1 or z.infolist()[0].filename!='summary.json' or z.infolist()[0].file_size>16*1024*1024:raise ValueError('unexpected summary layout')
  summary=json.loads(z.read('summary.json'))
 activation=json.loads((ROOT.parent/'qqq-eod-replay/activation.json').read_text(encoding='utf-8'))
 if summary['identity']['generation']!=activation['generation'] or summary['first_day']!=activation['first_statistical_session']:raise ValueError('summary identity mismatch')
 return summary

def main():
 if os.environ.get('GITHUB_REPOSITORY')!=REPO or os.environ.get('GITHUB_REF')!='refs/heads/main':raise ValueError('trusted main required')
 if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('use new dispatch instead of rerunning old notification')
 from qqq_alerts.cloud_state import restore_latest
 from qqq_alerts.outbox import Outbox,atomic
 folder=Path(os.environ['RUNNER_TEMP'])/'qqq-alert-state';folder.mkdir(parents=True,exist_ok=True);path=folder/'outbox.json'
 restored=restore_latest(api,int(os.environ['GITHUB_RUN_ID']),path);box=Outbox(path)
 client=Ntfy(os.environ['QQQ_ALERT_TOPIC'],os.environ['QQQ_HEALTH_TOPIC']);now=pd.Timestamp.now(tz='UTC');stamp=now.isoformat();event=os.environ['GITHUB_EVENT_NAME'];messages=0;failed=False
 try:
  if event=='workflow_run':
   trigger=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))['workflow_run'];run=api('/repos/'+REPO+'/actions/runs/'+str(int(trigger['id'])))
   if not trusted_run(run):raise ValueError('untrusted replay event refused')
   if run['status']!='completed':raise ValueError('incomplete replay event')
   changes={'cloud':set() if run['conclusion']=='success' else {'cloud_failed'}}
   try:changes.update(assess_summary(summary_for(run)))
   except Exception:changes['cloud'].add('cloud_summary_unavailable');failed=True
   box.observe(changes,stamp)
  elif event in ('schedule','workflow_dispatch'):
   if os.environ.get('QQQ_SEND_TEST')=='true':client.test();messages+=1
   else:
    from qqq_alerts.policy import observation_window
    today=str(now.tz_convert(NY).date());is_session=session(today) is not None;expected=observation_window(now)
    if box.data.get('last_life_day')!=today:
     try:events=client.read_health()
     except Exception:events=[]
     labels=health_labels(events,now,is_session and expected);client.life(stamp,labels,is_session);messages+=1;box.data['last_life_day']=today
     # A missing PC before trading is an incident; outside the observation window is expected.
     box.observe({'watchdog':{'watchdog_unavailable'} if expected and any(v=='non verifie' for v in labels.values()) else set()},stamp)
  else:return 0
  messages+=box.flush(client.notice,stamp)
  if box.pending:failed=True
 finally:atomic(path,box.data)
 print(json.dumps(dict(state='notification_attention' if failed else 'notifications_accepted',generic_messages=messages,pending=len(box.pending),restored_notification_state_from=restored,simulation_only=True,credential_values_output=False)))
 return 1 if failed else 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(dict(state='notification_failed',error_type=type(e).__name__,details_omitted=True)));raise SystemExit(1)
