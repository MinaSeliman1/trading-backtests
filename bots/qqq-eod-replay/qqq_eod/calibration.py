"""Fixed pre-registered moving-block bootstrap; no model selection."""
import numpy as np
import pandas as pd
from .schedule import calendar

def valid_blocks(dates,eligible,length=5):
 d=pd.DatetimeIndex(dates);good=np.asarray(eligible,dtype=bool)
 if len(d)!=len(good) or not len(d) or length<1 or d.has_duplicates or not d.is_monotonic_increasing or d.tz is not None or not d.equals(d.normalize()):raise ValueError('ordered unique session dates and mask required')
 c=calendar(str(d[0].date()),str(d[-1].date()));positions=c.sessions.get_indexer(d)
 if (positions<0).any():raise ValueError('non-XNYS date')
 blocks=[np.arange(i,i+length) for i in range(len(d)-length+1) if good[i:i+length].all() and np.all(np.diff(positions[i:i+length])==1)]
 return np.asarray(blocks,dtype=int).reshape(-1,length)

def bootstrap_bands(dates,returns,eligible,replications=50000,seed=20261101,length=5,horizons=(20,60),initial=100000.):
 r=np.asarray(returns,dtype=float);good=np.asarray(eligible,dtype=bool)
 if len(r)!=len(good) or replications<1 or initial<=0 or not all(h>0 for h in horizons):raise ValueError('invalid bootstrap configuration')
 if not np.isfinite(r[good]).all() or np.any(r[good]<=-1):raise ValueError('invalid eligible return')
 blocks=valid_blocks(dates,good,length)
 if not len(blocks):raise ValueError('no complete eligible blocks')
 longest=max(horizons);rng=np.random.Generator(np.random.PCG64(seed));draw=rng.integers(0,len(blocks),size=(replications,(longest+length-1)//length))
 indices=blocks[draw].reshape(replications,-1)[:,:longest];equity=initial*np.cumprod(1+r[indices],axis=1);bands={}
 for h in horizons:
  values=np.quantile(equity[:,h-1]-initial,[.025,.05,.5,.95,.975],method='linear')
  bands[str(h)]=dict(zip(('p025','p05','p50','p95','p975'),map(float,values)))
 crossed=np.zeros(replications,dtype=bool)
 for h in horizons:crossed|=(equity[:,h-1]-initial)<bands[str(h)]['p05']
 return dict(bands=bands,eligible_sessions=int(good.sum()),valid_blocks=len(blocks),replications=replications,seed=seed,block_sessions=length,either_checkpoint_p5_rate=float(crossed.mean()))
