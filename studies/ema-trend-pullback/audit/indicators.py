"""Separate EWM reconstruction in an additive dividend-neutral coordinate."""
import math
import numpy as np
import pandas as pd

def reconstruct(market,cash):
    a=market.arrays;rows=[];valid=[];cumcash=0.;segment=0;ever=False;origin='warmup_initial'
    for i,date in enumerate(market.dates):
        cumcash+=float(cash.get(str(date.date()),0));n=int(market.lengths[i]);ok=[]
        for j in range(n):
            o,h,l,c=[float(a[k][i,j]) for k in ('open','high','low','close')]
            ok.append(all(math.isfinite(x) and x>0 for x in (o,h,l,c)) and h>=max(o,l,c) and l<=min(o,h,c))
        valid.append(np.asarray(ok))
        for left in range(0,n,5):
            good=all(ok[left:left+5]);end=left+5
            row=dict(index=i,left=left,entry_slot=end,valid=good,cumcash=cumcash,segment=segment,
                origin=origin,open=float(a['open'][i,left]),high=float(max(a['high'][i,left:end])),
                low=float(min(a['low'][i,left:end])),close=float(a['close'][i,end-1]))
            rows.append(row)
            if good:ever=True
            else:
                segment+=1
                if ever:origin='unknown_indicator_history'
    frame=pd.DataFrame(rows);known=frame[frame.valid].copy();known['neutral']=known.close+known.cumcash
    groups=known.groupby('segment',sort=False)
    for period,key in [(9,'ema_fast'),(20,'ema_slow')]:
        e=groups.neutral.transform(lambda s:s.ewm(span=period,adjust=False).mean())
        prior=e.groupby(known.segment).shift(1);past=e.groupby(known.segment).shift(4)
        for lag in range(1,5):
            assert not ((e.groupby(known.segment).shift(lag)-known.cumcash).dropna()<=0).any(),'nonpositive retained cash state needs explicit segmented cash reset'
        known[key]=prior-known.cumcash;known['slope_fast' if period==9 else 'slope_slow']=prior-past
    known['previous_close']=groups.neutral.shift(1)-known.cumcash
    known['count']=groups.cumcount()
    known['state_reason']=np.where(known['count']>=60,'ready',known.origin)
    # Such a cash-scale exception requires an explicit audit extension rather than
    # silently accepting an unsupported segment. It does not occur in these ETF sources.
    for key in ['ema_fast','ema_slow','previous_close']:
        assert not (known[key].dropna()<=0).any(),'nonpositive adjusted state needs explicit segmented cash reset'
    fields=['ema_fast','ema_slow','slope_fast','slope_slow','previous_close','state_reason']
    frame=frame.join(known[fields]);frame.loc[~frame.valid,'state_reason']='invalid_bar'
    return {int(i):g.to_dict('records') for i,g in frame.groupby('index',sort=False)},valid
