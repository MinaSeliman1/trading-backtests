"""Verify exact published bytes and pre-performance code/source provenance."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24-v1');parser.add_argument('--seal',action='store_true');parser.add_argument('--raw',action='store_true');args=parser.parse_args();out=args.out
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'))
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==72
    assert len(list(out.glob('*/summary.json')))==72
    for rel,want in frozen['code_sha256'].items():
        assert sha(ROOT/rel)==want,rel
        assert sha(out/'code_snapshot'/rel)==want,rel
    for rel,want in frozen['dependencies_sha256'].items():
        assert sha(REPO/rel)==want,rel
        assert sha(out/'dependency_snapshot'/rel)==want,rel
    for rel,info in frozen['protocols'].items():assert sha(ROOT/rel)==info['sha256']
    audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text(encoding='utf-8'))
    assert audit['status']=='passed' and not audit['failures'] and audit['scenario_count']==72
    tests=json.loads((out/'TESTS.json').read_text(encoding='utf-8'))
    assert tests['exit_code']==0 and tests['passed']==25
    manifest=out/'FILE_MANIFEST.json'
    if args.seal:
        assert not manifest.exists(),'Refusing to overwrite archived manifest'
        files=[p for p in ROOT.rglob('*') if p.is_file() and p!=manifest and not any(part.startswith(('.test_tmp','__pycache__','.pytest_cache')) for part in p.parts)]
        files += [REPO/'README.md',REPO/'docs/research/2026-10-24-pistes-et-bots.md',REPO/'docs/superpowers/plans/2026-10-24-rsi2-intraday.md']
        for p in files:
            assert p.suffix not in ('.npz','.pkl','.gz','.sqlite','.key','.pem','.pyc') and '/runtime/' not in p.as_posix(),p
        value=dict(sealed_utc=datetime.now(timezone.utc).isoformat(),algorithm='SHA256',relative_to='repository root',files={p.relative_to(REPO).as_posix():sha(p) for p in sorted(set(files))})
        manifest.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    sealed=json.loads(manifest.read_text(encoding='utf-8'))
    for rel,want in sealed['files'].items():assert sha(REPO/rel)==want,rel
    if args.raw:
        import sys
        sys.path.insert(0,str(ROOT))
        from rsi2.data import load_sources
        _,_,profile=load_sources()
        assert profile==frozen['source'],'Verified source profile changed'
    print(f'PASS: {len(sealed["files"])} published fingerprints; 72 audited scenarios; 25 tests; raw_sources_verified={args.raw}.')


if __name__=='__main__':main()
