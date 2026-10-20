"""Vérifie les pièces livrées et construit une archive locale, sans données minute."""
from pathlib import Path
import argparse
import ast
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
import re
import zipfile


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    p.add_argument('--prepared',type=Path,default=Path('data/prepared'))
    p.add_argument('--archive',type=Path)
    args=p.parse_args();root=Path('.').resolve();out=args.results
    manifest=read(out/'manifest.json');assert manifest['status']=='completed'
    for name,expected in manifest['code_sha256'].items():
        path=Path(name) if name.startswith('noise_area/') else Path('scripts')/name
        assert sha(path)==expected,('code',name)
    for name,expected in manifest['protocol_sha256'].items():assert sha(Path(name))==expected,('protocol',name)
    for name,expected in manifest['data_validation']['prepared_files_sha256'].items():
        assert sha(args.prepared/name)==expected,('prepared',name)
    historical=read(out/'AUDIT_HISTORIQUE.json');risk=read(out/'INTRADAY_RISK_AUDIT.json')
    assert historical['status']==risk['status']=='passed'
    assert sha(Path('scripts/audit_study.py'))==historical['auditor_sha256']
    assert sha(Path('scripts/audit_intraday_risk.py'))==risk['script_sha256']
    assert all(Path(path).exists() and sha(Path(path))==expected for path,expected in risk['source_files_sha256'].items())
    figures=read(out/'FIGURES_PROVENANCE.json')
    assert figures['figures']==73 and sha(Path('scripts/render_figures.py'))==figures['script_sha256']
    for name,expected in figures['sha256'].items():assert sha(out/name)==expected,('figure',name)
    report=read(out/'REPORT_PROVENANCE.json')
    assert sha(out/'RAPPORT_FINAL.md')==report['report_sha256']
    assert sha(Path('scripts/write_report.py'))==report['script_sha256']
    assert report['manual_checks']>=10
    with (out/'comparison_all.csv').open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==220
    for row in rows:
        folder=out/row['instrument']/row['label'];summary=read(folder/'summary.json')
        with (folder/'trades.csv').open(newline='',encoding='utf-8') as stream:trades=list(csv.DictReader(stream))
        with (folder/'daily.csv').open(newline='',encoding='utf-8') as stream:daily=list(csv.DictReader(stream))
        pnl=float(row['net_pnl'])
        assert abs(math.fsum(float(t['net_pnl']) for t in trades)-pnl)<1e-6
        assert abs(math.fsum(float(d['net_pnl']) for d in daily)-pnl)<1e-6
        assert abs(float(daily[-1]['equity'])-100000-pnl)<1e-6
        assert len(trades)==int(row['trades'])==summary['trades']
    reproduction=read(out/'DATA_REPRODUCTION_VALIDATION.json')
    assert reproduction['prepared_files_sha256']==manifest['data_validation']['prepared_files_sha256']
    links=0;generated=[out/'FINAL_VALIDATION.json',out/'DELIVERY_FILES_SHA256.json']
    for path in [Path('README.md'),Path('data/README.md'),Path('tradingview/README.md'),out/'RAPPORT_FINAL.md',out/'EXAMEN_MANUEL.md',out/'VALIDATION.md']:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            target=target.split('#')[0]
            resolved=(path.parent/target).resolve()
            if resolved not in [x.resolve() for x in generated]:
                assert resolved.exists(),('broken local link',path,target)
            links+=1
    code=list(Path('noise_area').glob('*.py'))+list(Path('scripts').glob('*.py'))+list(Path('tests').glob('*.py'))
    for path in code:ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    verification=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),scenarios=220,figures=73,
        source_and_protocol_hashes_unchanged=True,prepared_hashes_reproduced=6,historical_audit=historical['status'],
        risk_audit=risk['status'],local_links_checked=links,python_sources_parsed=len(code),manual_trades=report['manual_checks'],
        unit_tests=dict(passed=32,seconds=9.15,command='python -m pytest -q --basetemp=.test_tmp_delivery',
                        evidence='Observed final tool output: 32 passed in 9.15s. Verification script does not rerun pytest.'),
        previous_study_snapshot=dict(files=1977,evidence='Observed tools/verify_snapshot.py: all SHA-256 identical.'),
        limitations=['No real fills, margin liquidation or annual Pine/Python signal parity verified.','Backtest data stops 2026-10-16.'])
    (out/'FINAL_VALIDATION.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    approved=[]
    for path in root.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(root)
        if any(part.startswith(('.test_tmp','.pytest_cache','__pycache__','.venv')) for part in rel.parts):continue
        if rel.parts[0]=='data' and rel.as_posix()!='data/README.md':continue
        if path.suffix in ('.pyc','.zip') or path.name=='DELIVERY_FILES_SHA256.json':continue
        assert path.suffix.lower() not in ('.env','.key','.pem')
        approved.append(path)
    hashes={p.relative_to(root).as_posix():sha(p) for p in sorted(approved)}
    (out/'DELIVERY_FILES_SHA256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    assert all(path.exists() for path in generated)
    approved.append(out/'DELIVERY_FILES_SHA256.json')
    if args.archive:
        assert not args.archive.exists(),'Refusing to overwrite an existing archive.'
        args.archive.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for path in sorted(approved):archive.write(path,arcname='Noise_Area/'+path.resolve().relative_to(root).as_posix())
        with zipfile.ZipFile(args.archive) as archive:assert archive.testzip() is None
        args.archive.with_suffix(args.archive.suffix+'.sha256').write_text(sha(args.archive)+'  '+args.archive.name+'\n',encoding='utf-8')
        print(f'PASS: archive {args.archive.name}, {args.archive.stat().st_size} octets, CRC et SHA-256 contrôlés.')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
