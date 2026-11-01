"""Causal daily levels, declared sample and date-keyed control draws."""
import numpy as np
import pandas as pd
SEED=20261031

def random_controls(dates,seed=SEED,repetitions=1000):
 sides=[];minutes=[]
 for d in dates:
  key=int(pd.Timestamp(d).strftime('%Y%m%d'))
  sides.append(int(np.random.default_rng(np.random.SeedSequence([seed,0,key])).choice([-1,1])))
  minutes.append(np.random.default_rng(np.random.SeedSequence([seed,1,key])).integers(332,421,size=repetitions))
 return np.array(sides,dtype=int),np.array(minutes,dtype=int).T

def day_context(ds,i):
 reasons=[];levels=[]
 if i==0:reasons.append('no_previous_session')
 else:
  for name,idx,start,end in [('London',i,0,180),('Premarket',i,180,330),('Previous',i-1,330,ds.close_slots[i-1])]:
   lev={'name':name}
   for symbol in ('ES','NQ'):
    good=bool(ds.valid[symbol][idx,start:end].all())
    if not good:reasons.append('unknown_'+name+'_'+symbol)
    a=ds.arrays[symbol]
    lev[symbol]={'high':float(np.max(a['high'][idx,start:end])) if good else None,'low':float(np.min(a['low'][idx,start:end])) if good else None}
   levels.append(lev)
 if ds.roll[i] or (i>0 and ds.roll[i-1]):reasons.append('roll_current_or_previous')
 complete=bool(ds.valid['ES'][i,:420].all() and ds.valid['NQ'][i,:450].all() and np.isfinite(ds.arrays['NQ']['open'][i,450]) and ds.arrays['NQ']['open'][i,450]>0 and abs(ds.arrays['NQ']['open'][i,450]/.25-round(ds.arrays['NQ']['open'][i,450]/.25))<1e-7)
 if not complete:reasons.append('incomplete_paired_window')
 a_reasons=list(reasons);daily=ds.daily_nq
 if i<20 or not daily.iloc[max(0,i-20):i]['known'].all():a_reasons.append('unknown_bias_A_history')
 if ds.roll[max(0,i-20):i].any():a_reasons.append('roll_bias_A_history')
 bias_a=bias_b=0
 if i>=20 and daily.iloc[i-20:i]['known'].all():bias_a=int(np.sign(float(daily.iloc[i-1]['close'])-float(daily.iloc[i-20:i]['close'].mean())))
 if i>0 and daily.iloc[i-1]['known']:bias_b=int(np.sign(float(daily.iloc[i-1]['close'])-float(daily.iloc[i-1]['open'])))
 return dict(levels=levels,eligible={'A':not a_reasons,'B':not reasons,'C':not reasons},reasons={'A':a_reasons,'B':list(reasons),'C':list(reasons)},bias={'A':bias_a,'B':bias_b,'C':None},complete=complete)

def period(day):return 'A' if str(day)[:10]<='2026-02-27' else 'B'
