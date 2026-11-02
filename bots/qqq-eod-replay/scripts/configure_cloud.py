"""Explicit approved PAPER-to-Actions setup; never output credential values."""
from pathlib import Path
from functools import lru_cache
import os,sys,json,base64,ctypes,subprocess,hashlib,importlib.util,argparse
BOT=Path(__file__).resolve().parents[1];REPO=BOT.parents[1];REPOSITORY='MinaSeliman1/trading-backtests'
TARGET='TradingBacktests/QQQ/EOD/StateKey/v1';TEST_PREFIX='TradingBacktests.Tests/QQQEOD/'
NAMES={'ALPACA_PAPER_KEY_ID','ALPACA_PAPER_SECRET_KEY','QQQ_EOD_STATE_KEY'}
GH=os.environ.get('QQQ_EOD_GH_EXE','gh')

class SetupError(Exception):pass

@lru_cache(maxsize=1)
def approved_vault():
 relative='bots/qqq-noise-area/qqq_paper/windows_vault.py';path=REPO/relative;lock=json.loads((BOT/'ENGINE_LOCK.json').read_text())
 if hashlib.sha256(path.read_bytes()).hexdigest()!=lock['source_files'][relative]:raise SetupError('paper_vault_source_changed')
 spec=importlib.util.spec_from_file_location('approved_paper_vault',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_state(value):
 try:
  if not isinstance(value,str) or len(base64.b64decode(value,validate=True))!=32:raise ValueError()
 except (ValueError,TypeError):raise SetupError('invalid_state_key') from None
 return value

class StateKeyStore:
 def __init__(self,target=TARGET):
  if os.name!='nt' or not (target==TARGET or target.startswith(TEST_PREFIX)):raise SetupError('unapproved_state_key_store')
  m=approved_vault();self.target=target;self.Credential=m.Credential;self.api=m.WindowsVault().api
 def load(self):
  pointer=ctypes.POINTER(self.Credential)()
  if not self.api.CredReadW(self.target,1,0,ctypes.byref(pointer)):
   if ctypes.get_last_error()==1168:return None
   raise SetupError('state_key_read_failed')
  try:
   if not 1<=pointer.contents.CredentialBlobSize<=256:raise SetupError('invalid_state_key_blob')
   return validate_state(ctypes.string_at(pointer.contents.CredentialBlob,pointer.contents.CredentialBlobSize).decode('ascii'))
  finally:self.api.CredFree(pointer)
 def save(self,value):
  validate_state(value);old=self.load()
  if old is not None and old!=value:raise SetupError('state_key_rotation_refused')
  raw=value.encode('ascii');buffer=ctypes.create_string_buffer(raw);row=self.Credential();row.Type=1;row.TargetName=self.target;row.Comment='QQQ EOD state encryption; no Alpaca credential';row.CredentialBlobSize=len(raw);row.CredentialBlob=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte));row.Persist=2;row.UserName='QQQ EOD encryption'
  try:
   if not self.api.CredWriteW(ctypes.byref(row),0):raise SetupError('state_key_write_failed')
  finally:ctypes.memset(ctypes.addressof(buffer),0,len(buffer))
 def delete_test_slot(self):
  if not self.target.startswith(TEST_PREFIX):raise SetupError('real_state_key_deletion_refused')
  if not self.api.CredDeleteW(self.target,1,0) and ctypes.get_last_error()!=1168:raise SetupError('test_slot_cleanup_failed')

def state_key(remote_names,store):
 value=store.load()
 if 'QQQ_EOD_STATE_KEY' in remote_names and value is None:raise SetupError('remote_state_key_exists_local_backup_missing')
 if value is None:value=base64.b64encode(os.urandom(32)).decode('ascii');store.save(value)
 return validate_state(value),'QQQ_EOD_STATE_KEY' not in remote_names

def clean_env():
 env={k:v for k,v in os.environ.items() if k not in ('GH_DEBUG','GIT_TRACE','GIT_CURL_VERBOSE','CURL_VERBOSE')};env['GH_HOST']='github.com';return env
def publish_secret(name,value,run=subprocess.run):
 if name not in NAMES or not isinstance(value,str) or not value or any(c in value for c in '\r\n\x00'):raise SetupError('unapproved_secret_input')
 result=run([GH,'secret','set',name,'--repo',REPOSITORY,'--app','actions'],input=value.encode('utf-8'),capture_output=True,check=False,timeout=90,env=clean_env())
 if result.returncode:raise SetupError(name+'_write_failed')
 return dict(name=name,configured=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 if not args.apply:print(json.dumps(dict(state='plan_only',repository=REPOSITORY,secret_names=sorted(NAMES),values_read=False)));return 0
 inventory=subprocess.run([GH,'secret','list','--repo',REPOSITORY,'--app','actions','--json','name'],capture_output=True,check=False,timeout=60,env=clean_env())
 if inventory.returncode:raise SetupError('secret_inventory_unavailable')
 remote={r['name'] for r in json.loads(inventory.stdout)};store=StateKeyStore()
 # Refuse a lost encryption key before reading the PAPER slot.
 if 'QQQ_EOD_STATE_KEY' in remote and store.load() is None:raise SetupError('remote_state_key_exists_local_backup_missing')
 key,secret=approved_vault().WindowsVault().load()
 from probe_data import probe
 probe_receipt=probe(key,secret)
 encryption,publish=state_key(remote,store);configured=[]
 for name,value in [('ALPACA_PAPER_KEY_ID',key),('ALPACA_PAPER_SECRET_KEY',secret)]:configured.append(publish_secret(name,value)['name'])
 if publish:configured.append(publish_secret('QQQ_EOD_STATE_KEY',encryption)['name'])
 del key,secret,encryption,value
 receipt=dict(state='actions_secrets_configured',repository=REPOSITORY,configured_names=configured,state_key_protected_copy='Windows Credential Manager dedicated slot',state_key_reused=not publish,probe=probe_receipt,credential_values_output=False)
 folder=BOT/'runtime/cloud';folder.mkdir(parents=True,exist_ok=True);(folder/'setup_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt));return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(dict(state='setup_failed',error_type=type(e).__name__,values_output=False)));raise SystemExit(1)
