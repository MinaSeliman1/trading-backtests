"""Separate deque/NumPy historical reconstruction; no strategy imports."""
from collections import deque
import math
import numpy as np

def reconstruct(market,cash=None):
    a=market.arrays;history={k:deque(maxlen=20) for k in range(29,330,5)};days=[];valid=[]
    for i in range(len(market.dates)):
        n=int(market.lengths[i]);p=np.column_stack([a[key][i,:n] for key in ['open','high','low','close']])
        good=np.isfinite(p).all(axis=1)&(p>0).all(axis=1)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1));valid.append(good)
        bars=[]
        for end in range(29,min(n,330),5):
            prior=list(history[end]);count=len(prior)
            mu=float(np.mean(prior)) if count==20 and all(math.isfinite(v) for v in prior) else np.nan
            sd=float(np.std(prior,ddof=1)) if math.isfinite(mu) else np.nan
            state='warmup_initial' if count<20 else 'unknown_history' if not math.isfinite(sd) else 'zero_variance' if sd<=1e-12 else 'ready'
            window_valid=bool(good[end-29:end+1].all())
            raw=math.log(float(a['close'][i,end])/float(a['open'][i,end-29])) if window_valid else np.nan
            bars.append(dict(shock_end=end,valid=window_valid,state_reason=state,prior_count=count,
                shock_return=raw,history_mean=mu,history_std=sd,shock_z=(raw-mu)/sd if state=='ready' else np.nan,
                shock_close=float(a['close'][i,end]),shock_low=float(min(a['low'][i,end-29:end+1])),shock_high=float(max(a['high'][i,end-29:end+1])),
                confirmation_valid=end+6<=n and bool(good[end+1:end+6].all()),confirmation_open=float(a['open'][i,end+1]),confirmation_close=float(a['close'][i,end+5]),
                confirmation_low=float(min(a['low'][i,end+1:end+6])),confirmation_high=float(max(a['high'][i,end+1:end+6]))))
            history[end].append(raw)
        days.append(bars)
    return days,valid
