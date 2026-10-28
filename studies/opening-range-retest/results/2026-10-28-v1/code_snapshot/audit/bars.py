"""Separate minute loop aggregation; no production strategy imports."""
import math
def reconstruct(market):
    sessions=[];valid=[]
    for i,n in enumerate(market.lengths):
        good=[];bars=[]
        for j in range(int(n)):
            op,hi,lo,cl=[float(market.arrays[k][i,j]) for k in ('open','high','low','close')]
            good.append(all(math.isfinite(p) and p>0 for p in (op,hi,lo,cl)) and hi>=max(op,hi,lo,cl) and lo<=min(op,hi,lo,cl))
        for j in range(0,int(n),5):
            bars.append(dict(left=j,entry_slot=j+5,valid=all(good[j:j+5]),open=float(market.arrays['open'][i,j]),
                high=max(float(v) for v in market.arrays['high'][i,j:j+5]),low=min(float(v) for v in market.arrays['low'][i,j:j+5]),close=float(market.arrays['close'][i,j+4])))
        sessions.append(bars);valid.append(good)
    return sessions,valid
