"""Verify preregistration and exact study bytes without freezing mutable global index."""
from pathlib import Path
import hashlib,json,argparse
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-26-v1');p.add_argument('--seal',action='store_true');p.add_argument('--raw',action='store_true');args=p.parse_args();out=args.out.resolve()
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'))
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==72
    assert len(list(out.glob('*/summary.json')))==72
    for rel,h in frozen['code_sha256'].items():assert sha(ROOT/rel)==sha(out/'code_snapshot'/rel)==h,rel
    for rel,h in frozen['dependencies_sha256'].items():assert sha(REPO/rel)==sha(out/'dependency_snapshot'/rel)==h,rel
    for rel,info in frozen['protocols'].items():assert sha(ROOT/rel)==info['sha256'],rel
    audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text());assert audit['status']=='passed' and not audit['failures'] and audit['scenario_count']==72
    assert audit['run_id']==out.relative_to(ROOT).as_posix()
    for rel,h in audit['export_sha256'].items():assert sha(ROOT/rel)==h,rel
    tests=json.loads((out/'TESTS.json').read_text());assert tests['exit_code']==0 and tests['passed']>=28
    manifest=out/'FILE_MANIFEST.json'
    if args.seal:
        assert not manifest.exists(),'Refusing to replace sealed evidence'
        files=[p for p in ROOT.rglob('*') if p.is_file() and p!=manifest and not any(x.startswith(('.test_tmp','__pycache__','.pytest_cache','.mplconfig')) for x in p.parts)]
        for f in files:assert f.suffix not in ('.pkl','.sqlite','.gz','.key','.pem','.pyc'),f
        manifest.write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),relative_to='repository root',files={f.relative_to(REPO).as_posix():sha(f) for f in sorted(files)}),indent=2)+'\n',encoding='utf-8')
    value=json.loads(manifest.read_text())
    for rel,h in value['files'].items():assert sha(REPO/rel)==h,rel
    if args.raw:
        import sys
        sys.path.insert(0,str(ROOT))
        from pdr.data import load_sources
        _,_,profile=load_sources();assert profile==frozen['source']
    print(f'PASS: {len(value["files"])} fingerprints; 72 audited scenarios; {tests["passed"]} tests; raw={args.raw}.')
if __name__=='__main__':main()
