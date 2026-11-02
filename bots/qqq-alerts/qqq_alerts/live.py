"""Allowlisted read-only view of existing bot state; never imports their services."""
from pathlib import Path
import ctypes,json,os,sqlite3
import pandas as pd
from .policy import NY,session

def process_alive(pid):
 if not isinstance(pid,int) or pid<=0:return False
 if os.name!='nt':
  try:os.kill(pid,0);return True
  except OSError:return False
 api=ctypes.WinDLL('kernel32',use_last_error=True);api.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];api.OpenProcess.restype=ctypes.c_void_p
 api.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];api.CloseHandle.argtypes=[ctypes.c_void_p]
 handle=api.OpenProcess(0x1000,False,pid)
 if not handle:return False
 try:
  code=ctypes.c_ulong();return bool(api.GetExitCodeProcess(handle,ctypes.byref(code)) and code.value==259)
 finally:api.CloseHandle(handle)

def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def meta(db,key,default=None):
 row=db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
 return json.loads(row[0]) if row else default

def read_one(bots,bot,now,alive):
 day=str(now.tz_convert(NY).date());root=Path(bots)/('qqq-noise-area' if bot=='noise' else 'qqq-orb')/'runtime'
 value=dict(bot=bot,mode='shadow',feed='sip',state=None,stamp=None,alive=False,stop=(root/'STOP_SHADOW.flag').exists(),paused=False,position=False,open_day=None,pending=False,decisions=[],phase=None,notes=[],last_bar=None,read_error=False)
 try:
  status=read_json(root/('shadow-sip/status.json' if bot=='noise' else 'status.json'))
  value.update({k:status.get(v) for k,v in [('state','state'),('stamp','utc'),('mode','mode'),('feed','feed')]})
  pid=read_json(root/'windows/status.json').get('pid') if bot=='noise' else status.get('pid');value['alive']=bool(alive(pid))
  path=root/('shadow-sip/state.sqlite' if bot=='noise' else 'state.sqlite')
  db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
  try:
   db.execute('PRAGMA query_only=ON');db.execute('BEGIN');config=meta(db,'configuration',{});account=meta(db,'account',{})
   if config.get('mode')!='shadow' or config.get('feed')!='sip':value.update(mode=config.get('mode'),feed=config.get('feed'))
   if bot=='noise':
    value['position']=bool(account.get('position'));at=account.get('entry_timestamp');value['open_day']=str(pd.Timestamp(at).tz_convert(NY).date()) if at and value['position'] else None
    # paused is free text; only read presence, never include its contents in snapshots.
    pause=db.execute("SELECT value FROM meta WHERE key='paused'").fetchone();paused_day=db.execute("SELECT value FROM meta WHERE key='paused_day'").fetchone();value['paused']=bool(pause and pause[0]) or bool(paused_day and paused_day[0]==day)
    raw=[json.loads(r[0]) for r in db.execute('SELECT data FROM decisions WHERE key LIKE ?',(day+':%',))]
    value['decisions']=[{k:d[k] for k in ('status','decision_time','observed_at') if k in d} for d in raw]
    pending=db.execute("SELECT day,clock FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected')").fetchall()
    for order_day,clock in pending:
     try:at=pd.Timestamp(order_day+' '+str(clock)[:2]+':'+str(clock)[2:4],tz=NY);old=now-pd.Timedelta(minutes=16)-at>pd.Timedelta(minutes=2)
     except (ValueError,TypeError):old=True
     value['pending']=value['pending'] or old
   else:
    value['open_day']=account.get('open_day');value['position']=bool(value['open_day']);row=db.execute('SELECT data FROM days WHERE day=?',(day,)).fetchone();data=json.loads(row[0]) if row else {}
    value['phase']=data.get('phase');value['notes']=[c for c in data.get('notes',[]) if c in ('late_start','missed_entry','late_observation','process_restart','data_gap')]
    bar_keys=[int(k) for k in data.get('bars',{})];s=session(day)
    if bar_keys and s is not None:value['last_bar']=str(s['open']+pd.Timedelta(minutes=max(bar_keys)+1))
  finally:db.close()
 except Exception:value['read_error']=True
 return value

def read_all(bots,now,alive=process_alive):
 now=pd.Timestamp(now).tz_convert('UTC');return {bot:read_one(bots,bot,now,alive) for bot in ('noise','orb')}
