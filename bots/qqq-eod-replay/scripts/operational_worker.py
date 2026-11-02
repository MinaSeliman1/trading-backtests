"""Silent one-shot collector; never starts a trading engine or reads PAPER keys."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,os,json,argparse,uuid
BOT=Path(__file__).resolve().parents[1]

def write_status(folder,value):
 target=Path(folder)/'worker_status.json';target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.tmp-'+uuid.uuid4().hex);temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8');temp.replace(target)

def collect_once(output,gh_executable,run=subprocess.run):
 started=datetime.now(timezone.utc).isoformat();write_status(output,dict(state='collecting',started_utc=started,read_only_live=True))
 env={k:v for k,v in os.environ.items() if not k.startswith(('ALPACA_','APCA_')) and k not in ('QQQ_EOD_STATE_KEY','GH_DEBUG','GIT_TRACE','GIT_CURL_VERBOSE')}
 env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',QQQ_EOD_GH_EXE=str(gh_executable),PYTHONPATH=os.pathsep.join([str(BOT/'runtime/vendor'),str(BOT.parents[2]/'.python_packages')]))
 python=Path(sys.executable).with_name('python.exe') if os.name=='nt' else Path(sys.executable)
 try:
  result=run([str(python),str(BOT/'scripts/collect_live.py'),'--github','--output',str(output)],cwd=BOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=720,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  data=json.loads(result.stdout);safe={k:data[k] for k in ('observations','qualified','comparisons','errors')};ok=result.returncode==0 and safe['errors']==0
  write_status(output,dict(state='collected' if ok else 'attention',started_utc=started,completed_utc=datetime.now(timezone.utc).isoformat(),read_only_live=True,exit_code=result.returncode,**safe));return 0 if ok else 1
 except Exception as e:
  write_status(output,dict(state='failed',started_utc=started,completed_utc=datetime.now(timezone.utc).isoformat(),read_only_live=True,error_type=type(e).__name__));return 1

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--gh-executable',default='gh');a=p.parse_args();raise SystemExit(collect_once(BOT/'runtime/operational',a.gh_executable))
