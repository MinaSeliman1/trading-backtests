"""Vérifie les acquisitions et met en cache uniquement les séances brutes contrôlées."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import csv
import gzip
import hashlib
import json
import pickle
from datetime import datetime,timezone
from noise_area.data import read_market


def audit_acquisition(manifest_path):
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    path=Path(manifest['path'])
    if not path.is_absolute(): path=manifest_path.parent/path.name
    assert manifest['status']=='complete'
    assert manifest['parameters']['feed']=='sip' and manifest['parameters']['adjustment']=='raw'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256']
    count=0
    with path.open(newline='',encoding='utf-8') as stream:
        rows=csv.DictReader(stream)
        for page in manifest['pages']:
            page_path=Path(page['path'])
            if not page_path.is_absolute(): page_path=manifest_path.parent/page_path.parent.name/page_path.name
            assert hashlib.sha256(page_path.read_bytes()).hexdigest()==page['sha256']
            with gzip.open(page_path,'rt',encoding='utf-8') as source:
                bars=json.load(source)['bars'] or []
            assert len(bars)==page['rows']
            for bar in bars:
                row=next(rows)
                assert row['timestamp']==bar['t']
                assert all(float(row[key])==float(bar[short]) for key,short in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')])
                count+=1
        assert next(rows,None) is None
    assert count==manifest['rows']
    return path,dict(manifest=str(manifest_path.resolve()),path=str(path.resolve()),sha256=manifest['sha256'],rows=count,pages=len(manifest['pages']),raw_pages_reconciled=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=Path('data/prepared'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    receipts=[];profiles=[]
    folder=args.workspace/'data/noise_area_extension/corporate_actions'
    for symbol in ['SPY','QQQ']:
        sources=[]
        for window in ['noise_area_extension/2016_2022','alpaca_sip_2023_2026','noise_area_extension/recent']:
            path=args.workspace/'data'/window/f'{symbol}_manifest.json'
            csv_path,receipt=audit_acquisition(path)
            sources.append(csv_path);receipts.append(receipt)
            print(f'{symbol} {window}: {receipt["rows"]} lignes rapprochees',flush=True)
        market=read_market(sources,symbol)
        resolved=args.workspace/'data/noise_area_sources'/f'{symbol}_dividends_resolved.json'
        assert resolved.exists(), 'Run resolve_dividends.py before preparation; missing dividends must not become zero.'
        dividends=json.loads(resolved.read_text(encoding='utf-8'))
        profile=dict(symbol=symbol,first=str(market.dates[0].date()),last=str(market.dates[-1].date()),
                     calendar_sessions=len(market.dates),valid_sessions=int(market.valid.sum()),
                     excluded_sessions=int((~market.valid).sum()),raw_rows=sum(r['rows'] for r in receipts if Path(r['path']).name==f'{symbol}_1m.csv'),
                     cash_dividend_count=len(dividends),last_cash_dividend=max(dividends))
        market.quality.to_csv(args.out/f'{symbol}_quality.csv',index=False)
        with (args.out/f'{symbol}_market.pkl').open('wb') as stream: pickle.dump(market,stream,protocol=5)
        (args.out/f'{symbol}_dividends.json').write_text(json.dumps(dividends,indent=2),encoding='utf-8')
        profiles.append(profile);print(json.dumps(profile),flush=True)
    result=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),profiles=profiles,acquisitions=receipts,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                corporate_actions_source=str(folder.resolve()),
                prepared_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.glob('*')
                                       if p.suffix in ('.pkl','.csv') or p.name.endswith('_dividends.json')})
    (args.out/'DATA_VALIDATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__': main()
