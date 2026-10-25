"""Seal/check the delivered Python study; optionally verify local raw archives.

The seal covers derived outputs, code, tests, audit, and documentation. Raw price
histories are never copied into the seal or uploaded by this command.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='2026-10-24-python-v1')
    parser.add_argument('--seal', action='store_true')
    parser.add_argument('--raw', action='store_true')
    args = parser.parse_args()
    run = ROOT/'results'/args.run_id
    record = run/'FILE_MANIFEST.json'
    manifest = json.loads((run/'RUN_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['complete']
    for rel, expected in manifest['code_sha256'].items():
        assert digest(ROOT/rel) == expected, 'Changed execution source: '+rel
        assert digest(run/'code_snapshot'/rel) == expected, 'Changed snapshot: '+rel
    dep = json.loads((run/'DEPENDENCY_PROVENANCE.json').read_text(encoding='utf-8'))
    assert digest(ROOT/dep['dependency']) == dep['snapshot_sha256']
    assert digest(run/'code_snapshot'/dep['dependency']) == dep['snapshot_sha256']
    source = ROOT/'results/2026-10-24-python/source_manifest.json'
    assert digest(source) == manifest['source_manifest_sha256']
    summaries = list(run.glob('*/*/*/summary.json'))
    assert len(summaries) == 126, 'Expected 3 pairs x 3 periods x 14 variants'
    threshold = json.loads((run/'MINIMUM_100.json').read_text(encoding='utf-8'))
    assert threshold['all_three_pass']
    for pair in ['GBPUSD','USDJPY','AUDUSD']:
        s = json.loads((run/pair/'ALL/reference/summary.json').read_text(encoding='utf-8'))
        assert s['resolved_closed_trades'] >= 100 and not s['open_position_end']
        assert threshold['pairs'][pair]['resolved_closed_trades'] == s['resolved_closed_trades']
    audit_path = ROOT/'audit/independent_audit_v1.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    assert audit['run_complete_at_audit'], 'Only a final audit is acceptable'
    assert not audit['errors'], 'Audit has unresolved findings'
    assert len(audit['financial_audits']) == 126, 'All exported portfolios require an audit'
    assert digest(ROOT/'audit/independent_audit.py') == audit['audit_script_sha256']
    if args.seal:
        assert not record.exists(), 'Refusing to overwrite a prior publication seal'
        files = [ROOT/x for x in ['README.md','MISSION.md','PYTHON_PROTOCOL.md','VALIDATION_PYTHON.md',
                                  'fx_data.py','fx_engine.py','fx_metrics.py','reference.py','requirements-python-lock.txt','data/README.md']]
        files += [ROOT/'scripts'/x for x in ['download_fxcm.py','run_python.py','make_python_figures.py',
                                           'build_python_report.py','verify_python_publication.py']]
        files += sorted((ROOT/'tests').glob('*.py'))
        files += sorted(p for p in (ROOT/'audit').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        files += sorted(p for p in run.rglob('*') if p.is_file() and p != record and '__pycache__' not in p.parts)
        files += [source]
        hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(files))}
        record.write_text(json.dumps({'sealed_utc':datetime.now(timezone.utc).isoformat(),
                                     'algorithm':'SHA256','paths_relative_to':'studies/nowick-compensation',
                                     'files':hashes},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    sealed = json.loads(record.read_text(encoding='utf-8'))
    for rel, expected in sealed['files'].items():
        assert digest(ROOT/rel) == expected, 'Publication fingerprint mismatch: '+rel
    raw_count = 0
    if args.raw:
        provenance = json.loads(source.read_text(encoding='utf-8'))
        for archive in provenance['archives']:
            if archive.get('status') == 200:
                assert digest(ROOT/archive['path']) == archive['sha256']
                raw_count += 1
        for pair, info in provenance['prepared'].items():
            assert digest(ROOT/'data/prepared'/f'{pair}_m1.npz') == info['sha256']
    print(f'PASS: {len(sealed["files"])} published fingerprints, 126 summaries, '
          f'3 pairs >=100 resolved trades, final independent audit; raw archives checked={raw_count}.')


if __name__=='__main__':
    main()
