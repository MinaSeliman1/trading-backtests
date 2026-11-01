"""Verify frozen computation, audited export bytes and final study manifest."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,argparse
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');p.add_argument('--raw',action='store_true');args=p.parse_args();out=ROOT/'results/2026-10-31-v1'
 frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'));audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text(encoding='utf-8'));extra=json.loads((ROOT/'audit/ADDITIONAL_CHECKS.json').read_text(encoding='utf-8'))
 assert audit['passed'] and audit['executions']==84 and extra['passed']
 assert json.loads((out/'RUN_COMPLETE.json').read_text(encoding='utf-8'))['executions']==84 and len(list(out.glob('*/summary.json')))==84
 for rel,h in frozen['code_sha256'].items():assert sha(ROOT/rel)==sha(out/'code_snapshot'/rel)==h,rel
 for rel,h in frozen['dependencies_sha256'].items():assert sha(REPO/rel)==sha(out/'dependency_snapshot'/rel)==h,rel
 for rel,v in frozen['protocols'].items():assert sha(ROOT/rel)==v['sha256'],rel
 for rel,h in audit['export_sha256'].items():assert sha(ROOT/rel)==h,rel
 tests=json.loads((out/'TESTS.json').read_text(encoding='utf-8'));assert tests['exit_code']==0 and tests['passed']>=51
 files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x.startswith(('__pycache__','.pytest_cache','.mplconfig')) for x in p.parts)]
 manifest=out/'FILE_MANIFEST.json';files=[p for p in files if p!=manifest]
 for f in files:assert f.suffix not in ('.pkl','.sqlite','.gz','.key','.pem','.pyc'),f
 if args.seal:
  assert not manifest.exists(),'Refuse overwriting sealed manifest'
  manifest.write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),relative_to='repository root',files={p.relative_to(REPO).as_posix():sha(p) for p in sorted(files)}),indent=2)+'\n',encoding='utf-8')
 stored=json.loads(manifest.read_text(encoding='utf-8'))['files'];assert set(stored)=={p.relative_to(REPO).as_posix() for p in files}
 for rel,h in stored.items():assert sha(REPO/rel)==h,rel
 if args.raw:
  sys.path.insert(0,str(ROOT))
  from lunch.data import load_sources
  _,_,profile=load_sources();assert profile==frozen['source']
 print(f'PASS: {len(stored)} fingerprints; 84 audited accounts; {tests["passed"]} tests; raw={args.raw}')
if __name__=='__main__':main()
