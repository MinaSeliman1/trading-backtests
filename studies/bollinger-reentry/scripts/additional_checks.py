"""Post-run independent aggregation and uncertainty checks."""
from pathlib import Path
import sys,json,math
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from bb.data import source
def main():
 matrix=pd.read_csv(OUT/'comparison_all.csv');checks=0;boot=0
 def near(a,b):
  nonlocal checks
  assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=3e-6),(a,b);checks+=1
 for row in matrix.itertuples():
  folder=OUT/row.label;d=pd.read_csv(folder/'daily.csv');t=pd.read_csv(folder/'trades.csv');rs=d.return_net.tolist();eq=100000.;peak=eq;maxdd=0.
  for r in rs:eq*=1+r;peak=max(peak,eq);maxdd=max(maxdd,1-eq/peak)
  near(row.total_return_pct,(eq/100000-1)*100);near(row.max_daily_close_drawdown_pct,maxdd*100)
  years=((pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1)/365.2425;near(row.cagr_pct,((eq/100000)**(1/years)-1)*100)
  near(row.daily_mean,math.fsum(rs)/len(rs));near(row.sharpe,np.mean(rs)/np.std(rs,ddof=1)*math.sqrt(252))
  pos=t.loc[t.net_pnl>0,'net_pnl'];neg=t.loc[t.net_pnl<0,'net_pnl']
  near(row.win_rate_pct,len(pos)/len(t)*100);near(row.profit_factor,pos.sum()/-neg.sum())
  near(row.net_pnl,math.fsum(t.net_pnl));near(row.regular_time_exposure_pct,math.fsum(d.holding_minutes)/math.fsum(d.session_minutes)*100)
  top=set(d.loc[d.net_pnl>0].nlargest(3,'net_pnl').index);near(row.return_without_top3_days_pct,(math.prod(1+r for j,r in enumerate(rs) if j not in top)-1)*100)
  if row.variant=='reference':
   u=json.loads((OUT/f'{row.symbol}_{row.period}_uncertainty.json').read_text(encoding='utf-8'));rng=np.random.default_rng(20261031);n=len(rs);arr=np.array(rs)
   for block in (5,20):
    starts=rng.integers(0,n,size=(3000,math.ceil(n/block)));means=[]
    for sample in starts:
     indices=[(int(start)+offset)%n for start in sample for offset in range(block)][:n];means.append(float(arr[indices].mean()))
    expected=np.quantile(means,[.025,.975]);actual=u['blocks'][str(block)]['conditional_daily_mean_ci95']
    for a,b in zip(actual,expected):near(a,b)
   boot+=1
  if row.period=='ALL' and row.variant=='reference':
   parts=[pd.read_csv(OUT/f'{row.symbol}_{p}_reference/trades.csv') for p in ('A','B')]
   other=pd.concat(parts);assert t.date.tolist()==other.date.tolist()
   for k in ('entry_reference','exit_reference','stop_price','target_price','entry_slot','sizing_price'):assert np.allclose(t[k],other[k],rtol=1e-10,atol=1e-10)
 source.write_json(ROOT/'audit/ADDITIONAL_CHECKS.json',dict(utc=datetime.now(timezone.utc).isoformat(),passed=True,numeric_checks=checks,bootstrap_accounts=boot,
   note='Independent daily aggregation, cost concentration, PF/WR/CAGR and block5/20 CI. ALL/A/B dates/features/fills reconcile, quantities compound in separate accounts.'))
 print('ADDITIONAL PASS',checks,'numeric checks',boot,'bootstrap accounts')
if __name__=='__main__':main()
