"""Verify pre-PnL source freeze, financial reconciliations and sealed delivery."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from seasonal.data import source



def execution_folder(out,root=ROOT):
    out=Path(out).resolve()
    if not out.is_relative_to(root.resolve()):raise ValueError('execution must stay inside study directory')
    relative=out.relative_to(root.resolve())
    if not relative.parts or relative.parts[0]!='results':raise ValueError('real delivery execution must stay under results/')
    return out


def verify_freeze(f,out,root=ROOT,repo=REPO):
    for name,item in f.get('protocols',{}).items():
        assert hashlib.sha256(item['text'].encode('utf-8')).hexdigest()==item['sha256'],('frozen protocol text',name)
        assert source.sha(root/name)==item['sha256'],('current protocol',name)
    for name,want in f['code_sha256'].items():
        assert source.sha(out/'code_snapshot'/name)==want,('frozen code',name)
        assert source.sha(root/name)==want,('current code',name)
    for name,want in f['dependencies_sha256'].items():
        assert source.sha(out/'dependency_snapshot'/name)==want,('frozen dependency',name)
        assert source.sha(repo/name)==want,('current dependency',name)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--seal',action='store_true');a=p.parse_args();out=execution_folder(a.out);f=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());verify_freeze(f,out)
    c=pd.read_csv(out/'comparison_all.csv');assert len(c)==96
    for r in c.to_dict('records'):
        folder=out/r['label'];t=pd.read_csv(folder/'trades.csv');d=pd.read_csv(folder/'daily.csv')
        assert len(t)==r['trades'] and abs(d.net_pnl.sum()-t.net_pnl.sum())<1e-6
        assert abs(t.price_move_pnl.sum()-t.friction_cost.sum()-t.commission.sum()-t.borrow_fee.sum()-t.net_pnl.sum())<1e-6
        assert abs(100000+t.net_pnl.sum()-d.equity.iloc[-1])<1e-6
    audit=json.loads((out/'INDEPENDENT_AUDIT.json').read_text());assert audit['all_matched'] and audit['accounts']==96
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ('__pycache__','.pytest_cache','runtime')) and p.name!='FILE_MANIFEST.json']
    if a.seal:
        if (out/'FILE_MANIFEST.json').exists():raise ValueError('refuse overwriting final manifest')
        source.write_json(out/'FILE_MANIFEST.json',dict(relative_to='repository root',files={p.relative_to(REPO).as_posix():source.sha(p) for p in sorted(files)}))
    manifest=out/'FILE_MANIFEST.json'
    if manifest.exists():
        for name,want in json.loads(manifest.read_text())['files'].items():assert source.sha(REPO/name)==want,name
    print('Verified frozen sources, 96 account reconciliations, independent audit and final manifest if present.')
if __name__=='__main__':main()
