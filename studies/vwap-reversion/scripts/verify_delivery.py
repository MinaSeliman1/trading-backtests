"""Integrite des performances initiales et de la livraison sans archives de donnees."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def verify_initial(out):
    manifest=json.loads((out/'MANIFEST.json').read_text(encoding='utf-8'));freeze=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'))
    for name,want in manifest['files'].items():assert sha(out/name)==want,name
    for name,want in freeze['dependencies_sha256'].items():assert sha(ROOT.parents[1]/name)==want,name
    for name,want in freeze['code_sha256'].items():assert sha(ROOT/name)==want,name
    for name,v in freeze['protocols'].items():assert hashlib.sha256(v['text'].encode('utf-8')).hexdigest()==v['sha256'],name
    return dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),initial_files=len(manifest['files']),dependencies=len(freeze['dependencies_sha256']),frozen_current_code_files=len(freeze['code_sha256']),
        scope='All original financial files, freeze, source profile and code snapshots unchanged; frozen engine/stats/data/tests/runner and historical helpers unchanged. README has post-result presentation only.')


def files():
    allowed={'.md','.py','.csv','.json','.png','.ini','.txt'}
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in allowed and not any(x.startswith('.') or x in ('__pycache__','data','runtime') for x in p.relative_to(ROOT).parts) and p.name!='DELIVERY_MANIFEST.json')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');p.add_argument('--write',action='store_true');a=p.parse_args();out=a.out;initial=verify_initial(out)
    if a.write:
        write(out/'FINANCIAL_INTEGRITY.json',initial);write(out/'DELIVERY_MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),root='studies/vwap-reversion',files={p.relative_to(ROOT).as_posix():sha(p) for p in files()}))
    delivery=json.loads((out/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'));expected=set(delivery['files']);actual={p.relative_to(ROOT).as_posix() for p in files()}
    assert expected==actual,'delivery inventory mismatch'
    for name,want in delivery['files'].items():assert sha(ROOT/name)==want,name
    print(json.dumps(dict(status='passed',original_files=initial['initial_files'],dependencies=initial['dependencies'],delivery_files=len(expected)),indent=2))


if __name__=='__main__':main()
