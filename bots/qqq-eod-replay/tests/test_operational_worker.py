from pathlib import Path
import importlib.util,json,types

def script():
 path=Path(__file__).resolve().parents[1]/'scripts/operational_worker.py';spec=importlib.util.spec_from_file_location('op_worker',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_worker_only_runs_readonly_collector_and_keeps_sanitized_status(tmp_path):
 m=script();calls=[]
 def run(args,**kwargs):
  calls.append((args,kwargs));return types.SimpleNamespace(returncode=0,stdout=json.dumps(dict(observations=2,qualified={'noise':1,'orb':0},comparisons=1,errors=0,unapproved='DUMMY-DO-NOT-STORE')),stderr='DUMMY-DO-NOT-STORE')
 assert m.collect_once(tmp_path,'gh',run=run)==0
 args=calls[0][0];assert args[1].endswith('collect_live.py') and '--github' in args and '--initialize' not in args
 record=json.loads((tmp_path/'worker_status.json').read_text());assert record['state']=='collected' and record['qualified']['noise']==1
 assert 'DUMMY' not in (tmp_path/'worker_status.json').read_text()
