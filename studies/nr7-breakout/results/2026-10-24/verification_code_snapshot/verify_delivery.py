"""Verify original frozen execution and final delivery hashes; no data/API needed."""
from pathlib import Path
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24');out=p.parse_args().out
    initial=json.loads((out/'MANIFEST.json').read_text());freeze=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());delivery=json.loads((out/'DELIVERY_MANIFEST.json').read_text());post=json.loads((out/'POST_EXECUTION_CHECKS.json').read_text())
    for name,want in initial['files'].items():assert sha(out/name)==want,('initial financial file',name)
    for name,want in freeze['code_sha256'].items():
        assert sha(out/'code_snapshot'/name)==want,('original snapshot',name)
        if name.startswith(('nr7/','tests/')) or name=='scripts/run_study.py':assert sha(ROOT/name)==want,('protected model',name)
    for name,want in freeze['dependencies_sha256'].items():assert sha(ROOT.parents[1]/name)==want,('dependency',name)
    assert sha(ROOT/'PROTOCOL_EXECUTION.md')==freeze['protocols']['PROTOCOL_EXECUTION.md']['sha256']
    for name,want in post['final_source_sha256'].items():assert sha(ROOT/name)==want,('final verification source',name)
    for name,want in delivery['files'].items():assert sha(out/name)==want,('delivery',name)
    assert initial['executions']==48
    assert json.loads((out/'AUDIT_INDEPENDENT.json').read_text())['status']=='passed'
    assert json.loads((out/'AUDIT_RAW_SAMPLES.json').read_text())['status']=='passed'
    print(json.dumps(dict(status='passed',initial_files=len(initial['files']),dependencies=len(freeze['dependencies_sha256']),protected_code_unchanged=True,delivery_files=len(delivery['files']))))


if __name__=='__main__':main()
