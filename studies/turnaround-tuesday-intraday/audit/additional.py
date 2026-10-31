"""Post-run independent interval arithmetic and A+B/ALL date/price checks."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
 counts={'reference_trade_dates':0,'bootstrap_intervals':0,'annual_cluster_intervals':0}
 for symbol in ['SPY','QQQ']:
  tables={p:pd.read_csv(out/f'{symbol}_{p}_reference/trades.csv') for p in ['ALL','A','B']}
  union=pd.concat([tables['A'],tables['B']]).sort_values('date').reset_index(drop=True);whole=tables['ALL'].sort_values('date').reset_index(drop=True)
  assert whole.date.tolist()==union.date.tolist()
  for field in ['entry_reference','exit_reference','stop_price','signal_slot','entry_slot','exit_slot']:np.testing.assert_allclose(whole[field],union[field],rtol=0,atol=1e-12)
  counts['reference_trade_dates']+=len(whole)
  for period in ['ALL','A','B']:
   u=json.loads((out/f'{symbol}_{period}_uncertainty.json').read_text());d=pd.read_csv(out/f'{symbol}_{period}_reference/daily.csv');t=tables[period]
   r=d.return_net.to_numpy();n=len(r);rng=np.random.default_rng(u['seed']);rep=u['repetitions'];cumsum=np.r_[0.,np.cumsum(np.r_[r,r])]
   for block in [5,20]:
    k=int(np.ceil(n/block));starts=rng.integers(0,n,size=(rep,k));sums=np.zeros(rep)
    for j in range(k):
     length=min(block,n-j*block);sums+=cumsum[starts[:,j]+length]-cumsum[starts[:,j]]
    want=np.quantile(sums/n,[.025,.975]);actual=u['blocks'][str(block)]['conditional_daily_mean_ci95'];np.testing.assert_allclose(actual,want,atol=1e-15,rtol=1e-10);counts['bootstrap_intervals']+=1
   years=sorted(pd.to_datetime(d.date).dt.year.unique());trade_year=pd.to_datetime(t.date).dt.year
   nums=np.array([t.loc[trade_year==y,'net_bps'].sum() for y in years]);denoms=np.array([(trade_year==y).sum() for y in years]);choices=rng.integers(0,len(years),size=(rep,len(years)));den=denoms[choices].sum(axis=1);samples=nums[choices].sum(axis=1)[den>0]/den[den>0]
   want=np.quantile(samples,[.025,.975]);actual=u['annual_cluster']['mean_trade_bps_ci95'];np.testing.assert_allclose(actual,want,atol=1e-10);counts['annual_cluster_intervals']+=1
 counts['status']='passed';counts['method']='Exported returns and same RNG seed, independent prefix-sum bootstrap; no strategy/statistics helper. A+B vs ALL prices/dates, not quantities.'
 (ROOT/'audit/ADDITIONAL_CHECKS.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8');print(json.dumps(counts))
if __name__=='__main__':main()
