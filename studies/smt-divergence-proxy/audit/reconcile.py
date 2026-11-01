"""Reconstruct all random portfolios and declared inference from CSV, independently."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(a,b,label):
 a=np.asarray(a,float);b=np.asarray(b,float)
 assert np.allclose(a,b,rtol=1e-9,atol=1e-7,equal_nan=True),str(label)
 return a.size

def main():
 daily=pd.read_csv(O/'daily_comparisons.csv');published=pd.read_csv(O/'random_portfolios.csv');draws=pd.read_csv(O/'control_draws.csv').set_index('date');contrasts=pd.read_csv(O/'contrasts.csv');gates=json.loads((O/'gates.json').read_text(encoding='utf-8'));checks=0;inference=0;expected_p=[]
 dates=sorted(draws.index);di={d:i for i,d in enumerate(dates)}
 for friction in (1,2):
  net=np.zeros((len(dates),2,2,89));risk=net.copy();minutes=net.copy();traded=np.zeros_like(net,dtype=bool)
  grid=pd.read_csv(O/f'candidate_grid_{friction}.csv',usecols=['date','model','side','entry_slot','net_pnl','risk_usd','holding_minutes','status'])
  for row in grid.itertuples(index=False):
   idx=(di[row.date],0 if row.model=='H1' else 1,0 if row.side==-1 else 1,row.entry_slot-332)
   net[idx]=row.net_pnl;risk[idx]=row.risk_usd;minutes[idx]=row.holding_minutes;traded[idx]=row.status=='filled'
  for vi,(model,bias) in enumerate((m,b) for m in ('H1','H2') for b in ('A','B','C')):
   d=daily[(daily.friction==friction)&(daily.model==model)&(daily.bias==bias)].sort_values('date');m=0 if model=='H1' else 1
   bins=[];risks=[];times=[];trades=[]
   for row in d.itertuples(index=False):
    dd=draws.loc[row.date].filter(like='rep_').to_numpy(int)-332
    if row.control_side:
     idx=(di[row.date],m,0 if row.control_side==-1 else 1)
     bins.append(net[idx][dd]);risks.append(risk[idx][dd]);times.append(minutes[idx][dd]);trades.append(traded[idx][dd])
    else:bins.append(np.zeros(1000));risks.append(np.zeros(1000));times.append(np.zeros(1000));trades.append(np.zeros(1000,bool))
   bins=np.array(bins).T;risks=np.array(risks).T;times=np.array(times).T;trades=np.array(trades).T
   checks+=check(bins.mean(axis=0),d.random_mean_net,'daily random mean')
   checks+=check(trades.mean(axis=0),d.random_trade_fraction,'daily random count')
   for part in ('A','B','ALL'):
    mask=np.ones(len(d),bool) if part=='ALL' else d.period.to_numpy()==part
    z=published[(published.friction==friction)&(published.model==model)&(published.bias==bias)&(published.period==part)].sort_values('rep')
    values=bins[:,mask];r=risks[:,mask];t=trades[:,mask];counts=t.sum(axis=1);defined=(t&(r>0)).sum(axis=1);rs=np.divide(values,r,out=np.zeros_like(values),where=r>0).sum(axis=1)
    for value,key in [(values.sum(axis=1),'net_usd'),(counts,'trades'),(r.sum(axis=1),'risk_usd_sum'),(times[:,mask].sum(axis=1),'exposure_minutes'),(rs,'net_r'),(defined,'defined_r_trades'),((t&(r==0)).sum(axis=1),'zero_risk_trades'),(counts*2.5,'commission'),(counts*friction,'friction_cost')]:checks+=check(value,z[key],key)
    means=np.divide(rs,defined,out=np.full(1000,np.nan),where=defined>0);checks+=check(means,z.mean_r_trade,'meanR')
    total_smt=d.smt_net.to_numpy()[mask].sum();rank=(1+np.sum(values.sum(axis=1)>=total_smt-1e-10))/1001
    for block in (5,20):
     n=int(mask.sum());b=min(n,block);seed=vi*10+(0 if part=='A' else 1 if part=='B' else 2);rng=np.random.default_rng(np.random.SeedSequence([20261031,2,seed,block]));starts=rng.integers(0,n,size=(3000,int(np.ceil(n/b))));idx=((starts[:,:,None]+np.arange(b))%n).reshape(3000,-1)[:,:n]
     for cmp in ('bias','random'):
      difference=d.smt_net.to_numpy()-(d.bias_net.to_numpy() if cmp=='bias' else bins.mean(axis=0));a=difference[mask];mu=a.mean();boot=a[idx].mean(axis=1);lo,hi=np.quantile(boot,[.025,.975]);p=(1+np.sum(boot-mu>=mu-1e-12))/3001
      row=contrasts[(contrasts.friction==friction)&(contrasts.model==model)&(contrasts.bias==bias)&(contrasts.period==part)&(contrasts.block==block)&(contrasts.comparator==cmp)].iloc[0]
      for value,key in [(mu,'mean'),(lo,'ci_low'),(hi,'ci_high'),(p,'p_centered'),(rank,'random_rank_p')]:inference+=check(value,row[key],key)
   print('Reconciled',friction,model,bias,flush=True)
 for gate in gates:
  z=contrasts[(contrasts.friction==1)&(contrasts.model==gate['model'])&(contrasts.bias==gate['bias'])&(contrasts.period=='B')&(contrasts.block==20)];expected_p.append(max(z.p_centered.max(),z.random_rank_p.iloc[0]))
 order=np.argsort(expected_p);adjusted=np.zeros(6);last=0.
 for rank,i in enumerate(order):last=max(last,min(1.,expected_p[i]*(6-rank)));adjusted[i]=last
 for i,g in enumerate(gates):checks+=check(expected_p[i],g['B_joint_p'],'jointp');checks+=check(adjusted[i],g['B_holm_p'],'Holmp');assert g['passes_proxy_phase2']==all(g['checks'].values())
 receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),random_portfolios=len(published),numeric_checks=checks,inference_checks=inference,engine_imported=False,stats_imported=False,oracle_sha256=sha(__file__),run_receipt_sha256=sha(O/'run_receipt.json'))
 (R/'audit/reconciliation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
