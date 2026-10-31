"""Post-run independent descriptive statistics and interval arithmetic."""
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve();matrix=pd.read_csv(out/'comparison_all.csv');checks=0
 def near(a,b):
  nonlocal checks
  checks+=1
  assert math.isclose(float(a),float(b),rel_tol=1e-8,abs_tol=2e-6),(a,b)
 for cfg in matrix.itertuples():
  d=pd.read_csv(out/cfg.label/'daily.csv');r=d.return_net.tolist();n=len(r);mean=math.fsum(r)/n;var=math.fsum((v-mean)**2 for v in r)/(n-1);sd=math.sqrt(var)
  near(cfg.sharpe,mean/sd*math.sqrt(252));near(cfg.volatility_annual_pct,sd*math.sqrt(252)*100);near(cfg.daily_mean,mean)
  down=math.sqrt(math.fsum(min(v,0)**2 for v in r)/n);near(cfg.sortino,mean/down*math.sqrt(252))
  curve=[100000.]
  for v in r:curve.append(curve[-1]*(1+v))
  running=[];peak=curve[0]
  for v in curve:peak=max(peak,v);running.append(peak)
  dd=[1-v/p for v,p in zip(curve,running)];trough=max(range(len(dd)),key=dd.__getitem__);last_peak=max(k for k in range(trough+1) if curve[k]==running[trough]);recover=next((k for k in range(trough+1,len(curve)) if curve[k]>=running[trough]),None);finish=recover if recover is not None else len(curve)-1
  dates=[pd.Timestamp(d.date.iloc[0])-pd.Timedelta(days=1),*pd.to_datetime(d.date)];near(cfg.max_daily_close_drawdown_pct,max(dd)*100);near(cfg.worst_drawdown_duration_calendar_days,(dates[finish]-dates[last_peak]).days);assert cfg.worst_drawdown_recovered==(recover is not None)
  near(cfg.worst_day_pct,min(r)*100);assert cfg.worst_day==d.date.iloc[min(range(n),key=r.__getitem__)]
  for length,field in [(7,'month'),(4,'year')]:
   agg={}
   for date,v in zip(d.date,r):agg[date[:length]]=agg.get(date[:length],1.)*(1+v)
   worst=min(agg,key=agg.__getitem__);near(getattr(cfg,'worst_'+field+'_pct'),(agg[worst]-1)*100);assert str(getattr(cfg,'worst_'+field))==worst
 intervals=0
 for period in ['ALL','A','B']:
  u=json.loads((out/f'{period}_uncertainty.json').read_text());d=pd.read_csv(out/f'{period}_reference/daily.csv');x=d.return_net.to_numpy();n=len(x);rng=np.random.default_rng(u['seed']);cumulative=np.r_[0.,np.cumsum(np.r_[x,x])]
  for b in [5,20]:
   k=int(np.ceil(n/b));starts=rng.integers(0,n,size=(u['repetitions'],k));sums=np.zeros(u['repetitions'])
   for col in range(k):
    width=min(b,n-col*b);sums+=cumulative[starts[:,col]+width]-cumulative[starts[:,col]]
   want=np.quantile(sums/n,[.025,.975]);np.testing.assert_allclose(u['blocks'][str(b)]['conditional_daily_mean_ci95'],want,rtol=1e-10,atol=1e-15);intervals+=1
 a=pd.read_csv(out/'ALL_reference/trades.csv').sort_values('date').reset_index(drop=True);b=pd.concat([pd.read_csv(out/f'{p}_reference/trades.csv') for p in ['A','B']]).sort_values('date').reset_index(drop=True);assert a.date.tolist()==b.date.tolist()
 for col in ['signal_slot','entry_slot','exit_slot','entry_reference_qqq','entry_reference_spy','exit_reference_qqq','exit_reference_spy','stop_spread']:np.testing.assert_allclose(a[col],b[col],rtol=0,atol=1e-12)
 result=dict(status='passed',descriptive_numeric_checks=checks,scenarios=42,bootstrap_intervals=intervals,reference_pair_dates=len(a),scope='Independent scalar moments/drawdown duration/calendar extremes and prefix-sum circular bootstrap; no financial/statistics helper calls. Same exported returns and same seed; not a test of statistical assumptions.')
 (ROOT/'audit/STATISTICS_CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
