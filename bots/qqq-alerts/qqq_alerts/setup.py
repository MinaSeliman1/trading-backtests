"""Only a new ntfy credential slot and two notification Actions secrets."""
import ctypes,os,json,re,secrets,subprocess
from ctypes import wintypes
from .transport import validate_topics
TARGET='TradingBacktests/QQQ/Alerts/ntfy/v1'
class SetupError(Exception):pass
class Credential(ctypes.Structure):
 _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),('CredentialBlob',ctypes.POINTER(wintypes.BYTE)),('Persist',wintypes.DWORD),('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]
class TopicStore:
 def __init__(self,target=TARGET):
  if os.name!='nt' or (target!=TARGET and not target.startswith('TradingBacktests.Tests/QQQAlerts/')):raise SetupError('unapproved notification store')
  self.target=target;self.api=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
  self.api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))];self.api.CredReadW.restype=wintypes.BOOL
  self.api.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD];self.api.CredWriteW.restype=wintypes.BOOL;self.api.CredFree.argtypes=[ctypes.c_void_p]
 def load(self):
  pointer=ctypes.POINTER(Credential)()
  if not self.api.CredReadW(self.target,1,0,ctypes.byref(pointer)):
   if ctypes.get_last_error()==1168:return None
   raise SetupError('notification credential read failed')
  try:
   if not 1<=pointer.contents.CredentialBlobSize<=512:raise SetupError('invalid notification blob')
   data=json.loads(ctypes.string_at(pointer.contents.CredentialBlob,pointer.contents.CredentialBlobSize).decode('ascii'))
   return validate_topics(data['alert'],data['health'])
  finally:self.api.CredFree(pointer)
 def save(self,value):
  validate_topics(value['alert'],value['health']);old=self.load()
  if old is not None and old!=value:raise SetupError('subscription rotation refused')
  raw=json.dumps(value).encode('ascii');buffer=ctypes.create_string_buffer(raw);row=Credential();row.Type=1;row.TargetName=self.target;row.Comment='QQQ ntfy technical alerts; no broker credentials';row.CredentialBlobSize=len(raw);row.CredentialBlob=ctypes.cast(buffer,ctypes.POINTER(wintypes.BYTE));row.Persist=2;row.UserName='QQQ simulation alerts'
  try:
   if not self.api.CredWriteW(ctypes.byref(row),0):raise SetupError('notification credential write failed')
  finally:ctypes.memset(ctypes.addressof(buffer),0,len(buffer))

def configuration(remote_names,store):
 value=store.load()
 if remote_names.intersection({'QQQ_ALERT_TOPIC','QQQ_HEALTH_TOPIC'}) and value is None:raise SetupError('remote topics exist without local backup; rotation refused')
 if value is None:
  value=dict(alert='qsim_'+secrets.token_hex(24),health='qsim_'+secrets.token_hex(24));store.save(value)
 return validate_topics(value['alert'],value['health'])

def publish_secret(name,value,run=subprocess.run,gh='gh'):
 if name not in ('QQQ_ALERT_TOPIC','QQQ_HEALTH_TOPIC') or not re.fullmatch(r'qsim_[a-f0-9]{48}',value):raise SetupError('unapproved notification secret')
 env={k:v for k,v in os.environ.items() if k not in ('GH_DEBUG','GIT_TRACE','GIT_CURL_VERBOSE','CURL_VERBOSE')};env['GH_HOST']='github.com'
 r=run([gh,'secret','set',name,'--repo','MinaSeliman1/trading-backtests','--app','actions'],input=value.encode('ascii'),capture_output=True,timeout=90,env=env)
 if r.returncode:raise SetupError('notification secret write failed')
