from pathlib import Path
import importlib.util,base64,types,pytest,os,uuid

def script():
 path=Path(__file__).resolve().parents[1]/'scripts/configure_cloud.py';spec=importlib.util.spec_from_file_location('cloud_setup',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_secret_values_only_travel_over_stdin_and_child_output_is_suppressed(capsys):
 m=script();value='DUMMY-PRIVATE-VALUE';calls=[]
 def run(args,**kwargs):calls.append((args,kwargs));return types.SimpleNamespace(returncode=0,stdout=value.encode(),stderr=value.encode())
 out=m.publish_secret('ALPACA_PAPER_KEY_ID',value,run=run)
 assert value not in str(calls[0][0]) and calls[0][1]['input']==value.encode() and calls[0][1]['capture_output']
 assert calls[0][1]['env']['GH_HOST']=='github.com'
 assert value not in str(out)+capsys.readouterr().out
 def bad(*args,**kwargs):return types.SimpleNamespace(returncode=1,stdout=value.encode(),stderr=value.encode())
 with pytest.raises(m.SetupError) as e:m.publish_secret('ALPACA_PAPER_KEY_ID',value,run=bad)
 assert value not in str(e.value)

def test_existing_remote_key_without_local_backup_cannot_be_rotated():
 m=script();writes=[]
 class Store:
  def load(self):return None
  def save(self,value):writes.append(value)
 with pytest.raises(m.SetupError):m.state_key({'QQQ_EOD_STATE_KEY'},Store())
 assert writes==[]

def test_state_key_is_reused_and_only_new_key_is_generated():
 m=script();value=base64.b64encode(b'x'*32).decode();writes=[]
 class Store:
  existing=value
  def load(self):return self.existing
  def save(self,v):writes.append(v);self.existing=v
 store=Store();assert m.state_key({'QQQ_EOD_STATE_KEY'},store)==(value,False) and not writes
 store.existing=None;new,publish=m.state_key(set(),store)
 assert publish and len(base64.b64decode(new))==32 and writes==[new]

@pytest.mark.skipif(os.name!='nt',reason='native Windows credential test uses an isolated dummy slot')
def test_native_state_key_slot_is_roundtrip_and_rotation_protected():
 m=script();store=m.StateKeyStore('TradingBacktests.Tests/QQQEOD/'+uuid.uuid4().hex);a=base64.b64encode(b'a'*32).decode();b=base64.b64encode(b'b'*32).decode()
 try:
  assert store.load() is None;store.save(a);assert store.load()==a
  with pytest.raises(m.SetupError):store.save(b)
 finally:store.delete_test_slot()
