import importlib,sys,json
from pathlib import Path
from copy import deepcopy
import pandas as pd
import pytest
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
def module(name):
 assert (BASE/'qqq_alerts'/(name+'.py')).is_file(),name+' implementation missing'
 return importlib.import_module('qqq_alerts.'+name)
def snapshot(bot='noise',**changes):
 value=dict(bot=bot,state='running',mode='shadow',feed='sip',stamp='2026-11-02T15:17:00Z',alive=True,stop=False,paused=False,position=False,open_day=None,pending=False,decisions=[],phase=None,notes=[],last_bar=None)
 value.update(changes);return value

def test_regular_waiting_and_non_session_have_no_false_data_outage():
 p=module('policy')
 assert p.evaluate(snapshot(stamp='2026-11-01T15:00:00Z',state='waiting_for_regular_session'),pd.Timestamp('2026-11-01T15:00:30Z'))==set()
 assert p.evaluate(snapshot('orb',state='flat',phase='flat',stamp='2026-11-02T15:17:00Z'),pd.Timestamp('2026-11-02T15:17:30Z'))==set()

def test_dead_pid_stale_engine_and_stop_are_detected_without_broker_action():
 p=module('policy');now=pd.Timestamp('2026-11-02T14:20:00Z')
 assert p.evaluate(snapshot(alive=False,stamp='2026-11-02T14:20:00Z'),now)=={'process_stopped'}
 assert p.evaluate(snapshot(stamp='2026-11-02T14:16:59Z'),now)=={'engine_stale'}
 assert p.evaluate(snapshot(stop=True,stamp='2026-11-01T15:00:00Z'),pd.Timestamp('2026-11-01T15:00:30Z'))=={'operator_stop'}

def test_noise_deadlines_use_delayed_clock_and_observation_time():
 p=module('policy');s=snapshot()
 assert p.evaluate(s,pd.Timestamp('2026-11-02T15:17:59Z'))==set()
 assert 'decision_missing' in p.evaluate(s,pd.Timestamp('2026-11-02T15:18:01Z'))
 s['decisions']=[dict(status='processed',decision_time='2026-11-02T15:00:00Z',observed_at='2026-11-02T15:02:01Z')]
 assert 'decision_late' in p.evaluate(s,pd.Timestamp('2026-11-02T15:18:01Z'))
 s['decisions'][0]['observed_at']='2026-11-02T15:01:59Z'
 assert p.evaluate(s,pd.Timestamp('2026-11-02T15:18:01Z'))==set()

def test_orb_no_signal_is_healthy_but_late_start_and_unresolved_are_not():
 p=module('policy');now=pd.Timestamp('2026-11-02T14:54:00Z')
 assert p.evaluate(snapshot('orb',stamp=str(now),phase='flat',state='flat'),now)==set()
 assert 'orb_missed_entry' in p.evaluate(snapshot('orb',stamp=str(now)),now)
 assert 'position_unresolved' in p.evaluate(snapshot('orb',stamp=str(now),phase='unresolved',state='unresolved',position=True,open_day='2026-11-02'),now)

def test_halfday_guard_and_dst_are_calendar_based():
 p=module('policy')
 assert p.observation_window(pd.Timestamp('2026-11-27T18:19:00Z'))
 assert not p.observation_window(pd.Timestamp('2026-11-27T18:21:00Z'))
 assert p.observation_window(pd.Timestamp('2026-11-02T14:10:00Z'))
 assert not p.observation_window(pd.Timestamp('2026-11-02T14:09:00Z'))

def test_old_open_position_is_alerted_on_weekends_and_invalid_config_is_rejected():
 p=module('policy');now=pd.Timestamp('2026-11-01T15:00:00Z')
 assert 'position_unresolved' in p.evaluate(snapshot(position=True,open_day='2026-10-30',stamp=str(now)),now)
 assert 'unexpected_configuration' in p.evaluate(snapshot(mode='paper',stamp=str(now)),now)

def test_outbox_retries_then_deduplicates_and_records_one_recovery(tmp_path):
 m=module('outbox');path=tmp_path/'state.json';box=m.Outbox(path)
 box.observe({'noise':{'process_stopped'},'orb':set()},'2026-11-02T14:20:00Z')
 def fail(*a,**k):raise OSError('secret response must not be persisted')
 assert box.flush(fail,'2026-11-02T14:20:00Z')==0
 assert len(m.Outbox(path).pending)==1
 sent=[];box=m.Outbox(path);box.observe({'noise':{'process_stopped'},'orb':set()},'2026-11-02T14:20:30Z')
 assert box.flush(lambda *a,**k:sent.append((a,k)),'2026-11-02T14:20:30Z')==1
 box.observe({'noise':{'process_stopped'},'orb':set()},'2026-11-02T14:21:00Z');assert not box.pending
 box.observe({'noise':set(),'orb':set()},'2026-11-02T14:22:00Z');assert len(box.pending)==1
 assert box.flush(lambda *a,**k:sent.append((a,k)),'2026-11-02T14:22:00Z')==1
 assert len(sent)==2 and 'secret response' not in path.read_text()

def test_sender_rejects_foreign_topics_and_sanitizes_network_errors():
 m=module('transport')
 with pytest.raises(ValueError):m.Ntfy('https://evil.invalid','qsim_'+'b'*48)
 def fail(*a,**k):raise OSError('qsim_'+'a'*48)
 client=m.Ntfy('qsim_'+'a'*48,'qsim_'+'b'*48,open_request=fail)
 with pytest.raises(m.SendError) as e:client.notice('noise',{'process_stopped'},'2026-11-02T14:20:00Z','incident-test')
 assert 'qsim_' not in str(e.value)

def test_ntfy_payload_only_contains_generic_state_and_fixed_https_destination():
 m=module('transport');seen=[]
 class Response:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self,n=-1):return b'{"id":"abcdefghijk","event":"message"}'
 def opened(request,timeout):seen.append(request);return Response()
 client=m.Ntfy('qsim_'+'a'*48,'qsim_'+'b'*48,open_request=opened)
 client.notice('noise',{'process_stopped'},'2026-11-02T14:20:00Z','incident-test')
 req=seen[0];assert req.full_url.startswith('https://ntfy.sh/');assert req.method=='POST'
 assert b'98041' not in req.data and b'process' in req.data
 client.guard('2026-11-02T14:32:00Z');assert seen[-1].headers.get('At')=='2026-11-02T14:32:00Z'
 client.cancel_guard();assert seen[-1].method=='DELETE'


def test_watchdog_arms_guard_and_health_only_on_bounded_schedule(tmp_path):
 m=module('service');calls=[]
 class Client:
  def notice(self,*a):calls.append(('notice',a))
  def health(self,*a):calls.append(('health',a))
  def guard(self,*a):calls.append(('guard',a))
  def cancel_guard(self):calls.append(('cancel',()))
 watcher=m.Watcher(tmp_path,Client(),reader=lambda now:{'noise':snapshot(stamp=str(now)),'orb':snapshot('orb',stamp=str(now),phase='flat',state='flat')})
 now=pd.Timestamp('2026-11-02T14:20:00Z');watcher.tick(now)
 assert [c[0] for c in calls]==['health','guard']
 watcher.tick(now+pd.Timedelta(seconds=30));assert len(calls)==2
 watcher.tick(now+pd.Timedelta(minutes=5));assert [c[0] for c in calls]==['health','guard','health','guard']
 assert 'qsim_' not in (tmp_path/'status.json').read_text()


def test_watchdog_sends_failure_before_health_without_clearing_failed_delivery(tmp_path):
 m=module('service')
 class Client:
  def notice(self,*a):raise OSError('private URL omitted')
  def health(self,*a):pass
  def guard(self,*a):pass
  def cancel_guard(self):pass
 w=m.Watcher(tmp_path,Client(),reader=lambda now:{'noise':snapshot(stamp=str(now),alive=False),'orb':snapshot('orb',stamp=str(now),phase='flat')})
 r=w.tick(pd.Timestamp('2026-11-02T14:20:00Z'));assert r['pending_notifications']==1
 assert r['delivery']=='pending' and 'private URL' not in json.dumps(r)


def test_cloud_trigger_rejects_foreign_branch_fork_or_workflow():
 m=module('cloud');good=dict(name='QQQ EOD replay',path='.github/workflows/qqq-eod-replay.yml',head_branch='main',head_repository={'full_name':'MinaSeliman1/trading-backtests'},repository={'full_name':'MinaSeliman1/trading-backtests'})
 assert m.trusted_run(good)
 for change in ({'head_branch':'evil'},{'head_repository':{'full_name':'other/fork'}},{'path':'.github/workflows/untrusted.yml'}):
  assert not m.trusted_run(dict(good,**change))


def test_dead_bot_does_not_recover_when_observation_window_closes():
 p=module('policy');now=pd.Timestamp('2026-11-02T21:21:00Z')
 assert 'process_stopped' in p.evaluate(snapshot(alive=False,stamp=str(now)),now)
 assert 'engine_stale' in p.evaluate(snapshot(stamp='2026-11-02T21:17:59Z'),now)


def test_calendar_diagnostic_expiry_is_not_announced_as_recovery(tmp_path):
 m=module('outbox');box=m.Outbox(tmp_path/'state.json')
 box.observe({'noise':{'decision_late'}},'2026-11-02T21:18:00Z');box.flush(lambda *a:None,'2026-11-02T21:18:00Z')
 box.observe({'noise':set()},'2026-11-02T21:21:00Z');assert not box.pending


def test_cloud_state_persists_stop_deduplication_and_real_recovery(tmp_path):
 m=module('cloud_state');o=module('outbox');path=tmp_path/'outbox.json'
 box=o.Outbox(path);box.observe({'noise':{'risk_stop'},'orb':set(),'cloud':set()},'2026-11-02T22:23:00Z')
 sent=[];box.flush(lambda *a:sent.append(a),'2026-11-02T22:23:00Z');raw=path.read_bytes()
 # A later independent Actions job restores the prior artifact, not an in-memory singleton.
 m.restore_bytes(raw,tmp_path/'later.json');later=o.Outbox(tmp_path/'later.json')
 later.observe({'noise':{'risk_stop'},'orb':set(),'cloud':set()},'2026-11-02T23:23:00Z');assert not later.pending
 later.observe({'noise':set(),'orb':set(),'cloud':set()},'2026-11-03T22:23:00Z');assert len(later.pending)==1
 later.flush(lambda *a:sent.append(a),'2026-11-03T22:23:00Z');assert len(sent)==2


def test_subscription_window_can_render_text_without_qr_dependencies(monkeypatch):
 import importlib.util,builtins,types
 path=BASE/'scripts/show_subscription.py';spec=importlib.util.spec_from_file_location('subscription_test',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 setup=module('setup');monkeypatch.setattr(setup.TopicStore,'load',lambda self:{'alert':'qsim_'+'a'*48,'health':'qsim_'+'b'*48});monkeypatch.setattr(setup.TopicStore,'__init__',lambda self:None)
 rendered=[]
 class Widget:
  def __init__(self,*a,**kw):rendered.append(kw.get('text',''))
  def pack(self,*a,**kw):pass
 class App(Widget):
  def title(self,*a):pass
  def geometry(self,*a):pass
  def resizable(self,*a):pass
  def mainloop(self):rendered.append('rendered')
 fake=types.SimpleNamespace(Tk=App,Label=Widget,Button=Widget,Entry=Widget,StringVar=lambda **kw:object(),messagebox=types.SimpleNamespace(showerror=lambda *a:None))
 original=builtins.__import__
 def imported(name,*a,**kw):
  if name=='tkinter':return fake
  if name=='qrcode' or name.startswith('PIL'):raise ImportError('optional dependency absent')
  return original(name,*a,**kw)
 monkeypatch.setattr(builtins,'__import__',imported);out=module('outbox');monkeypatch.setattr(out,'atomic',lambda *a:None)
 mod.main();assert 'rendered' in rendered
