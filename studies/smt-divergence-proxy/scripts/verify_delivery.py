"""Verify frozen code, numerical receipts and delivery hashes; optional final seal."""
from pathlib import Path
import sys,json,hashlib,argparse,ast
import pandas as pd
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true');ap.add_argument('--raw',action='store_true');a=ap.parse_args()
 frozen=read(R/'FREEZE.json')
 for name,h in frozen['files'].items():assert sha(R/name)==h,'frozen code/source changed: '+name
 if a.raw:
  for name,h in frozen['input_hashes'].items():assert sha(name)==h,'private input changed'
 run=read(R/'results/run_receipt.json');expected=set(run['files']);actual={p.name for p in (R/'results').iterdir() if p.is_file() and p.name!='run_receipt.json'}
 assert expected==actual,'unexpected/missing result file'
 for name,h in run['files'].items():assert sha(R/'results'/name)==h,'result changed: '+name
 assert run['freeze_sha256']==sha(R/'FREEZE.json')
 oracle=read(R/'audit/oracle_receipt.json');rec=read(R/'audit/reconciliation_receipt.json')
 assert oracle['oracle_sha256']==sha(R/'audit/verify.py') and rec['oracle_sha256']==sha(R/'audit/reconcile.py')
 assert oracle['run_receipt_sha256']==rec['run_receipt_sha256']==sha(R/'results/run_receipt.json')
 assert oracle['freeze_sha256']==sha(R/'FREEZE.json')
 assert oracle['candidate_rows']==2*86864 and rec['random_portfolios']==36000
 assert not oracle['engine_imported'] and not rec['engine_imported'] and not rec['stats_imported']
 proof=read(R/'audit/final_tests.json');assert proof['exit_code']==0 and '32 passed' in (R/'audit/final_tests.txt').read_text(encoding='utf-8')
 gates=read(R/'results/gates.json');assert {(g['model'],g['bias']) for g in gates}=={(m,b) for m in ('H1','H2') for b in ('A','B','C')}
 assert all(g['passes_proxy_phase2']==all(g['checks'].values()) for g in gates)
 for p in R.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
 for p in (R/'results').glob('ledger_*.csv'):
  d=pd.read_csv(p);assert not d.duplicated(['date','policy']).any(),str(p)
  assert ((d.gross_price_pnl-d.commission-d.friction_cost-d.net_pnl).abs()<1e-7).all(),str(p)
 for p in ('README.md','RAPPORT_COMPLET.md','INTERPRETATION.md','REPRODUCTION.md'):
  assert (R/p).stat().st_size>100
 assert str(sum(g['passes_proxy_phase2'] for g in gates))+'/6' in (R/'README.md').read_text(encoding='utf-8')
 paths=sorted(p for p in R.rglob('*') if p.is_file() and p.name!='MANIFEST.json')
 assert not any('__pycache__' in p.parts or '.pytest_cache' in p.parts for p in paths)
 files={p.relative_to(R).as_posix():sha(p) for p in paths}
 extras={'../../README.md':sha(R.parents[1]/'README.md'),'../../docs/superpowers/plans/2026-10-31-smt-divergence-proxy.md':sha(R.parents[1]/'docs/superpowers/plans/2026-10-31-smt-divergence-proxy.md')}
 manifest=dict(files=files,repository_files=extras,principal_variants=6,delivery_file_count=len(files)+1)
 if a.seal:(R/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
 stored=read(R/'MANIFEST.json');assert manifest==stored,'delivery manifest differs'
 print(json.dumps(dict(verified_files=len(files),frozen_files=len(frozen['files']),numeric_outputs=len(run['files']),candidate_rows=oracle['candidate_rows'],random_portfolios=rec['random_portfolios'],passes=sum(g['passes_proxy_phase2'] for g in gates),raw_verified=a.raw)))
if __name__=='__main__':main()
