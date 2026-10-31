"""Verify exact paired-study delivery, frozen financial code and export membership."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,argparse,sys,math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def cleanfiles():return [p for p in ROOT.rglob('*') if p.is_file() and not any(x.startswith(('.test_tmp','__pycache__','.pytest_cache','.mplconfig')) for x in p.parts)]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');p.add_argument('--seal',action='store_true');p.add_argument('--raw',action='store_true');a=p.parse_args();out=a.out.resolve()
 frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'));matrix=pd.read_csv(out/'comparison_all.csv')
 assert len(matrix)==42 and set(matrix.label)=={f'{p}_{v}' for p in frozen['periods'] for v in frozen['specifications']} and matrix.label.is_unique
 for rel,h in frozen['code_sha256'].items():assert sha(ROOT/rel)==sha(out/'code_snapshot'/rel)==h,rel
 for rel,h in frozen['dependencies_sha256'].items():assert sha(REPO/rel)==sha(out/'dependency_snapshot'/rel)==h,rel
 for rel,v in frozen['protocols'].items():assert sha(ROOT/rel)==v['sha256'],rel
 for r in matrix.itertuples():
  assert [r.start,r.end]==frozen['periods'][r.period]
  for k,v in frozen['specifications'][r.variant].items():assert getattr(r,k)==v,(r.label,k)
 audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text());assert audit['status']=='passed' and audit['scenarios']==42 and not audit['failures'];assert audit['run_id']==out.relative_to(ROOT).as_posix()
 for rel,h in audit['export_sha256'].items():assert sha(ROOT/rel)==h,rel
 stats=json.loads((ROOT/'audit/STATISTICS_CHECK.json').read_text());assert stats['status']=='passed' and stats['scenarios']==42 and stats['bootstrap_intervals']==6
 tests=json.loads((out/'TESTS.json').read_text());assert tests['exit_code']==0 and tests['passed']>=41
 assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==42
 if a.raw:
  sys.path.insert(0,str(ROOT));from relative.data import load_sources
  _,_,profile=load_sources();assert profile==frozen['source']
 manifest=out/'FILE_MANIFEST.json'
 if a.seal:
  assert not manifest.exists(),'Refusing to replace sealed evidence'
  files=cleanfiles()
  for f in files:assert f.suffix not in ('.pkl','.sqlite','.gz','.key','.pem','.pyc'),f
  manifest.write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),relative_to='repository root',files={p.relative_to(REPO).as_posix():sha(p) for p in sorted(files)}),indent=2)+'\n',encoding='utf-8')
 value=json.loads(manifest.read_text())
 for rel,h in value['files'].items():assert sha(REPO/rel)==h,rel
 actual={p.relative_to(REPO).as_posix() for p in cleanfiles() if p!=manifest};assert actual==set(value['files']),'unlisted/missing study files'
 print(f'PASS: {len(actual)} fingerprints;42audited portfolios;{tests["passed"]}tests;raw={a.raw}.')
if __name__=='__main__':main()
