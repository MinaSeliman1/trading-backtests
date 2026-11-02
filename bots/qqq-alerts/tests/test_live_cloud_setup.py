import importlib,sys,json,sqlite3,hashlib
from pathlib import Path
import pandas as pd
import pytest
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
def module(name):
 assert (BASE/'qqq_alerts'/(name+'.py')).is_file(),name+' implementation missing'
 return importlib.import_module('qqq_alerts.'+name)
def fixture(root):
 n=root/'qqq-noise-area/runtime';o=root/'qqq-orb/runtime';(n/'shadow-sip').mkdir(parents=True);(n/'windows').mkdir();o.mkdir(parents=True)
 status=dict(utc='2026-11-02T15:18:30Z',state='running',mode='shadow',feed='sip',reason='DO_NOT_PUBLISH_THIS_SECRET')
 (n/'shadow-sip/status.json').write_text(json.dumps(status));(n/'windows/status.json').write_text(json.dumps(dict(pid=111)))
 (o/'status.json').write_text(json.dumps(dict(status,pid=222,state='flat')))
 for path,orb in [(n/'shadow-sip/state.sqlite',False),(o/'state.sqlite',True)]:
  with sqlite3.connect(path) as c:
   c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
   for k,v in [('account',dict(position=0,open_day=None)),('configuration',dict(mode='shadow',feed='sip'))]:c.execute('INSERT INTO meta VALUES(?,?)',(k,json.dumps(v)))
   c.execute('CREATE TABLE days(day TEXT PRIMARY KEY,data TEXT)') if orb else c.execute('CREATE TABLE decisions(key TEXT PRIMARY KEY,data TEXT)')
   if orb:c.execute('INSERT INTO days VALUES(?,?)',('2026-11-02',json.dumps(dict(phase='flat',notes=[],bars={}))))
   else:
    c.execute('CREATE TABLE orders(day TEXT,status TEXT,clock TEXT)')
    c.execute('INSERT INTO decisions VALUES(?,?)',('2026-11-02:1000',json.dumps(dict(status='processed',decision_time='2026-11-02T15:00:00Z',observed_at='2026-11-02T15:01:30Z'))))
 return n,o

def test_live_adapter_reads_current_day_and_never_publishes_private_fields_or_writes_db(tmp_path):
 m=module('live');n,o=fixture(tmp_path);paths=[n/'shadow-sip/state.sqlite',o/'state.sqlite'];before=[hashlib.sha256(p.read_bytes()).digest() for p in paths]
 data=m.read_all(tmp_path,pd.Timestamp('2026-11-02T15:18:30Z'),alive=lambda pid:pid in (111,222))
 assert data['noise']['alive'] and data['orb']['phase']=='flat' and len(data['noise']['decisions'])==1
 assert 'DO_NOT_PUBLISH_THIS_SECRET' not in json.dumps(data)
 assert [hashlib.sha256(p.read_bytes()).digest() for p in paths]==before
 (n/'STOP_SHADOW.flag').touch();assert m.read_all(tmp_path,pd.Timestamp('2026-11-02T15:18:30Z'),alive=lambda pid:True)['noise']['stop']

def test_missing_or_malformed_live_state_is_never_healthy(tmp_path):
 m=module('live');data=m.read_all(tmp_path,pd.Timestamp('2026-11-02T15:18:30Z'),alive=lambda pid:False)
 assert all(d['read_error'] for d in data.values())

def test_cloud_assessment_only_accepts_known_status_fields_not_exception_text():
 m=module('cloud');d=dict(first_day='2026-11-02',sessions=[dict(bot='noise',day='2026-11-02',status='unresolved',reason='SECRET')],risk_status={'noise':{'stop':True},'orb':{'stop':False}})
 assert m.assess_summary(d)=={'noise':{'cloud_unresolved','risk_stop'},'orb':set()}
 assert 'SECRET' not in json.dumps({k:sorted(v) for k,v in m.assess_summary(d).items()})

def test_cloud_health_never_treats_stale_or_malformed_receipts_as_alive():
 m=module('cloud');now=pd.Timestamp('2026-11-02T14:20:00Z')
 healthy=dict(version=1,utc='2026-11-02T14:19:00Z',issues={'noise':[],'orb':[]})
 assert m.health_labels([dict(event='message',message=json.dumps(healthy))],now,True)=={'noise':'controle recent sain','orb':'controle recent sain'}
 healthy['utc']='2026-11-02T14:00:00Z'
 assert set(m.health_labels([dict(event='message',message=json.dumps(healthy))],now,True).values())=={'non verifie'}
 assert set(m.health_labels([],now,False).values())=={'hors seance'}

def test_topic_setup_never_rotates_existing_remote_subscription_without_backup():
 m=module('setup')
 class Store:
  def load(self):return None
  def save(self,value):raise AssertionError('must refuse before writing')
 with pytest.raises(m.SetupError):m.configuration({'QQQ_ALERT_TOPIC'},Store())

def test_secret_publish_uses_stdin_and_does_not_return_child_output():
 m=module('setup');seen=[]
 class Result:returncode=0;stdout=b'SECRET';stderr=b'SECRET'
 def run(command,**kw):seen.append((command,kw));return Result()
 topic='qsim_'+'a'*48;m.publish_secret('QQQ_ALERT_TOPIC',topic,run=run)
 assert topic not in ' '.join(seen[0][0]);assert seen[0][1]['input']==topic.encode()
 assert seen[0][1]['capture_output']
 with pytest.raises(m.SetupError):m.publish_secret('ALPACA_PAPER_KEY_ID',topic,run=run)


def test_standalone_watchdog_check_needs_no_inherited_pythonpath_or_vault():
 import subprocess,os
 env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','ALPACA_PAPER_KEY_ID','ALPACA_PAPER_SECRET_KEY','QQQ_EOD_STATE_KEY')};env['PYTHONDONTWRITEBYTECODE']='1'
 r=subprocess.run([sys.executable,str(BASE/'scripts/watch.py'),'--check'],env=env,capture_output=True,text=True,timeout=90)
 assert r.returncode==0, 'standalone diagnostic entrypoint must run without reading the notification vault'
 data=json.loads(r.stdout);assert data['read_only_live'] and data['credentials_read'] is False


def test_notification_state_rejects_invalid_artifact_payload_without_writing(tmp_path):
 m=module('cloud_state');target=tmp_path/'outbox.json'
 with pytest.raises(ValueError):m.restore_bytes(json.dumps({'observed':{'noise':['PRIVATE_TEXT']},'pending':[],'sent_dates':{}}).encode(),target)
 assert not target.exists()


@pytest.mark.skipif(sys.platform!='win32',reason='Windows credential manager only; isolated synthetic slot')
def test_native_notification_slot_roundtrips_and_refuses_rotation():
 import ctypes,uuid
 from ctypes import wintypes
 m=module('setup');store=m.TopicStore('TradingBacktests.Tests/QQQAlerts/'+uuid.uuid4().hex)
 value={'alert':'qsim_'+'a'*48,'health':'qsim_'+'b'*48}
 try:
  assert store.load() is None;store.save(value);assert store.load()==value;store.save(value)
  with pytest.raises(m.SetupError):store.save({'alert':'qsim_'+'c'*48,'health':'qsim_'+'d'*48})
 finally:
  store.api.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD];store.api.CredDeleteW.restype=wintypes.BOOL
  store.api.CredDeleteW(store.target,1,0)
