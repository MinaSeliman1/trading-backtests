"""Scalar, independent history reconstruction; no strategy imports."""
import math

def reconstruct(m):
    sessions=[];valid=[];history=[]
    for i,n in enumerate(m.lengths):
        good=[];high=[];low=[];close=[]
        for j in range(int(n)):
            op,hi,lo,cl=[float(m.arrays[k][i,j]) for k in ('open','high','low','close')]
            good.append(all(math.isfinite(x) and x>0 for x in (op,hi,lo,cl)) and hi>=max(op,cl,lo) and lo<=min(op,cl,hi));high.append(hi);low.append(lo);close.append(cl)
        valid.append(good)
        sessions.append(dict(width=max(high)-min(low),close=close[-1]) if m.valid[i] and all(good) else None)
        last=sessions[i-1] if i else None;previous=sessions[i-2] if i>=2 else None;prior=sessions[max(0,i-14):i]
        history.append(dict(weekday=m.dates[i].weekday(),previous_weekday=m.dates[i-1].weekday() if i else -1,
            previous_close=last['close'] if last else math.nan,before_previous_close=previous['close'] if previous else math.nan,
            previous_return=last['close']/previous['close']-1 if last and previous else math.nan,
            adr=sum(x['width'] for x in prior)/14 if len(prior)==14 and all(x is not None for x in prior) else math.nan))
    return history,valid
