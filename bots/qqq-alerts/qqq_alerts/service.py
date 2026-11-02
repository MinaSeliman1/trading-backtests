"""Independent read-only watcher. Only its runtime and ntfy are written."""
from pathlib import Path
import json,time,os,ctypes
import pandas as pd
from .policy import evaluate,guard_deadline,observation_window
from .live import read_all
from .outbox import Outbox,atomic

class Watcher:
 def __init__(self,runtime,client,reader):
  self.runtime=Path(runtime);self.client=client;self.reader=reader;self.box=Outbox(self.runtime/'outbox.json')
  path=self.runtime/'cadence.json';self.cadence=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
 def tick(self,now):
  now=pd.Timestamp(now).tz_convert('UTC');stamp=now.isoformat();snapshots=self.reader(now);issues={b:evaluate(snapshots[b],now) for b in ('noise','orb')}
  self.box.observe(issues,stamp);sent=self.box.flush(self.client.notice,stamp);errors=[]
  def elapsed(key):return key not in self.cadence or now-pd.Timestamp(self.cadence[key])>=pd.Timedelta(minutes=5)
  if 'health_utc' not in self.cadence or (observation_window(now) and elapsed('health_utc')):
   try:self.client.health(stamp,issues);self.cadence['health_utc']=stamp
   except Exception:errors.append('health_send_failed')
  at=guard_deadline(now);registered=self.cadence.get('guard_deadline');desired=at.isoformat() if at is not None else None
  if desired and (not registered or (observation_window(now) and elapsed('guard_utc')) or (not observation_window(now) and registered!=desired)):
   try:self.client.guard(desired);self.cadence.update(guard_deadline=desired,guard_utc=stamp)
   except Exception:errors.append('guard_send_failed')
  elif desired is None and registered:
   try:self.client.cancel_guard();self.cadence.update(guard_deadline=None,guard_utc=stamp)
   except Exception:errors.append('guard_cancel_failed')
  atomic(self.runtime/'cadence.json',self.cadence)
  value=dict(state='watching',utc=stamp,simulation_only=True,read_only_live=True,issues={b:sorted(v) for b,v in issues.items()},sent=sent,pending_notifications=len(self.box.pending),delivery='pending' if self.box.pending or errors else 'current',errors=errors,guard_deadline=self.cadence.get('guard_deadline'))
  atomic(self.runtime/'status.json',value);return value

def serve(root):
 root=Path(root);runtime=root/'runtime';runtime.mkdir(parents=True,exist_ok=True)
 # Dedicated singleton, never claims either trading engine lock.
 api=ctypes.WinDLL('kernel32',use_last_error=True);api.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];api.CreateMutexW.restype=ctypes.c_void_p;api.CloseHandle.argtypes=[ctypes.c_void_p]
 handle=api.CreateMutexW(None,False,'Local\\TradingBacktests.QQQAlerts.v1')
 if not handle:raise RuntimeError('notification singleton unavailable')
 if ctypes.get_last_error()==183:api.CloseHandle(handle);return 0
 try:
  from .setup import TopicStore
  from .transport import Ntfy
  topics=TopicStore().load()
  if topics is None:raise RuntimeError('notification configuration unavailable')
  client=Ntfy(**topics);watcher=Watcher(runtime,client,lambda now:read_all(root.parent,now))
  while not (runtime/'STOP_ALERTS.flag').exists():
   try:watcher.tick(pd.Timestamp.now(tz='UTC'))
   except Exception as e:
    atomic(runtime/'status.json',dict(state='watcher_error',utc=pd.Timestamp.now(tz='UTC').isoformat(),error_type=type(e).__name__,read_only_live=True))
    raise RuntimeError('watcher iteration failed; details omitted') from None
   time.sleep(30)
  client.cancel_guard();return 0
 finally:api.CloseHandle(handle)
