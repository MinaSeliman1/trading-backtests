"""Declared daily paired contrasts; no strategy selection or retuning."""
import numpy as np

def holm(values):
 p=np.asarray(values,float);order=np.argsort(p);out=np.empty(len(p));out[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(p),0,-1)))
 return out

def bootstrap_indices(n,block,seed,repetitions=3000):
 if not n:return np.empty((repetitions,0),int)
 block=min(block,n);rng=np.random.default_rng(np.random.SeedSequence([20261031,2,int(seed),int(block)]))
 starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
 return ((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]

def contrast(values,block,seed):
 a=np.asarray(values,float)
 if not len(a):return dict(n=0,mean=None,ci_low=None,ci_high=None,p_centered=1.)
 if not np.isfinite(a).all():raise ValueError('unknown outcomes cannot be cash')
 mean=float(a.mean());means=a[bootstrap_indices(len(a),block,seed)].mean(axis=1)
 low,high=np.quantile(means,[.025,.975]);p=(1+int((means-mean>=mean-1e-12).sum()))/(len(means)+1)
 return dict(n=len(a),mean=mean,ci_low=float(low),ci_high=float(high),p_centered=p)

def portfolio(pnl,traded,risks=None,minutes=None):
 p=np.asarray(pnl,float);t=np.asarray(traded,bool);wins=p[t]>0;profits=p[t][p[t]>0].sum();losses=-p[t][p[t]<0].sum();curve=np.r_[0.,np.cumsum(p)]
 streak=longest=0
 for x in p[t]:
  streak=streak+1 if x<0 else 0;longest=max(longest,streak)
 n=int(t.sum());w=int(wins.sum());z=1.959963984540054
 if n:
  ph=w/n;den=1+z*z/n;center=(ph+z*z/(2*n))/den;half=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den;ci=[center-half,center+half]
 else:ci=[None,None]
 out=dict(sessions=len(p),trades=n,net_usd=float(p.sum()),mean_usd_day=float(p.mean()) if len(p) else None,win_rate=w/n if n else None,win_rate_wilson_low=ci[0],win_rate_wilson_high=ci[1],profit_factor=float(profits/losses) if losses else None,
  gross_wins_usd=float(profits),gross_losses_usd=float(losses),max_drawdown_closed_usd=float((np.maximum.accumulate(curve)-curve).max()),longest_loss_streak=longest,
  best_day=float(p.max()) if len(p) else None,worst_day=float(p.min()) if len(p) else None,top5_positive_usd=float(np.sort(p[p>0])[-5:].sum()))
 if risks is not None:
  risk=np.asarray(risks,float);valid=t&(risk>0);r=p[valid]/risk[valid];r_curve=np.r_[0.,np.cumsum(r)];out.update(net_r=float(r.sum()),mean_r_trade=float(r.mean()) if len(r) else None,zero_risk_trades=int((t&(risk==0)).sum()),max_drawdown_closed_r=float((np.maximum.accumulate(r_curve)-r_curve).max()),mean_risk_usd=float(risk[t].mean()) if n else None)
 if minutes is not None:out['exposure_minutes']=float(np.asarray(minutes,float).sum())
 return out
