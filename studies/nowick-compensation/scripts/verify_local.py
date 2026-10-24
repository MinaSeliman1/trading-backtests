"""Record local verification, explicitly distinct from Pine/market validation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
out=root/'validation/2026-10-24'
out.mkdir(parents=True,exist_ok=True)
run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
log=run.stdout+run.stderr
(out/'unit_tests.txt').write_text(log,encoding='utf-8',newline='\n')
if run.returncode:
    raise SystemExit(log)
count=int(re.search(r'Ran (\d+) tests',log).group(1))
usd=(root/'tradingview/nowick_compensation_usd.pine').read_text(encoding='utf-8')
jpy=(root/'tradingview/nowick_compensation_jpy.pine').read_text(encoding='utf-8')
expected=usd
for a,b in [
    ('// GBPUSD / AUDUSD. For USDJPY use the generated JPY file (different cash fee).','// USDJPY. Generated from USD source; identical rules, JPY-denominated cash fee.'),
    ('Nowick Compensation — USD quote — audit v1','Nowick Compensation — JPY quote — audit v1'),
    ('commission_value=0.00005','commission_value=0.005'),
    ('EXPECTED_QUOTE = "USD"','EXPECTED_QUOTE = "JPY"'),
]:
    if expected.count(a)!=1:
        raise SystemExit(f'Expected unique substitution: {a}')
    expected=expected.replace(a,b)
if jpy!=expected:
    raise SystemExit('JPY rules differ from USD source')
files={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in {'.py','.pine','.md'} and 'validation' not in p.relative_to(root).parts}
record={
    'verified_at_utc':datetime.now(timezone.utc).isoformat(),
    'python':sys.version.split()[0],
    'controlled_unit_tests':{'status':'passed','count':count,'command':'python -m unittest discover -s tests -v'},
    'usd_jpy_variant_equivalence':True,
    'pine_compilation':'not_confirmed',
    'pine_runtime':'not_confirmed',
    'fx_market_backtest':'not_executed',
    'profitability':'not_evaluated',
    'fx_market_data_used':[],
    'files_sha256':files,
    'limitations':['Python fixtures do not execute or compile Pine.','Native front-run cancellation is evaluated at 15m close.','Stress column uses native trade sizes; it is not an alternate executable portfolio or a guaranteed bound.'],
}
(out/'verification.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
print(f'{count} controlled tests PASS; variants equivalent; {len(files)} files hashed. Pine compilation/runtime and FX backtest NOT CONFIRMED.')
