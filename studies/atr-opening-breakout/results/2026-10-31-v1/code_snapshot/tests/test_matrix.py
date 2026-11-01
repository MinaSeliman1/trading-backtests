from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_study import specifications
def test_fixed_14_variants_costs_and_risk():
 specs=specifications();assert len(specs)==14 and len(set(n for n,c in specs))==14 and specs[0][0]=='reference'
 for n,c in specs:
  assert c.initial_capital==100000 and c.risk_budget==.01 and c.leverage_cap==1
  assert c.slippage==(.02 if n=='cost_0.02' else .03 if n=='cost_0.03' else .05 if n=='cost_0.05' else .01)
