"""Generate the JPY quote-fee variant; never alter strategy rules."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=(root/'tradingview/nowick_compensation_usd.pine').read_text(encoding='utf-8')
replacements={
    '// GBPUSD / AUDUSD. For USDJPY use the generated JPY file (different cash fee).':'// USDJPY. Generated from USD source; identical rules, JPY-denominated cash fee.',
    'Nowick Compensation — USD quote — audit v1':'Nowick Compensation — JPY quote — audit v1',
    'commission_value=0.00005':'commission_value=0.005',
    'EXPECTED_QUOTE = "USD"':'EXPECTED_QUOTE = "JPY"',
}
for old,new in replacements.items():
    if source.count(old)!=1:
        raise ValueError(f'Expected unique replacement: {old}')
    source=source.replace(old,new)
(root/'tradingview/nowick_compensation_jpy.pine').write_text(source,encoding='utf-8',newline='\n')
print('JPY variant generated; four declared text changes, identical strategy logic.')
