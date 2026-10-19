"""Archive locale de l'étude longue terminée, sans variables ni identifiants API."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json


def main():
    root=Path(__file__).resolve().parents[1]
    report=root/'results/alpaca_sip_long'
    assert (report/'RAPPORT_FINAL.md').exists()
    audit=json.loads((report/'audit_validation.json').read_text(encoding='utf-8'))
    validation=json.loads((report/'OUTPUT_VALIDATION.json').read_text(encoding='utf-8'))
    figures=json.loads((report/'FIGURES_PROVENANCE.json').read_text(encoding='utf-8'))
    assert audit['status']==validation['status']=='passed'
    assert validation['scenarios_checked']==116
    for name,expected in [('audit_long_history.py',audit['auditor_sha256']),
                          ('verify_long_outputs.py',validation['verifier_sha256']),
                          ('render_long_figures.py',figures['script_sha256'])]:
        assert hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest()==expected
    selected=[]
    for directory in ['fvg_backtest','scripts','tests','tradingview','docs',
                      'data/alpaca_sip_2023_2026','results/alpaca_sip_long','results/source_audit_2026-10-19']:
        selected.extend(p for p in (root/directory).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    selected.extend(root/p for p in ['README.md','requirements.txt','requirements-lock.txt','run.ps1'])
    target=root/'First_Candle_FVG_Alpaca_2023_2026.zip'
    checksums={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in selected}
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=6) as archive:
        for p in sorted(selected): archive.write(p,p.relative_to(root))
        archive.writestr('ARCHIVE_CONTENT_SHA256.json',json.dumps(checksums,indent=2))
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(checksum+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps(dict(archive=str(target),files=len(selected)+1,bytes=target.stat().st_size,sha256=checksum)))


if __name__=='__main__': main()
