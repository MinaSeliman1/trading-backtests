"""Independent scalar OHLC aggregation and strictly trailing history."""
import math
def reconstruct(m):
    sessions=[];valid=[];history=[]
    for i,n in enumerate(m.lengths):
        good=[];high=[];low=[];close=[]
        for j in range(int(n)):
            op,hi,lo,cl=[float(m.arrays[k][i,j]) for k in ('open','high','low','close')]
            good.append(all(math.isfinite(x) and x>0 for x in (op,hi,lo,cl)) and hi>=max(op,cl,lo) and lo<=min(op,cl,hi));high.append(hi);low.append(lo);close.append(cl)
        valid.append(good)
        if all(good):
            h=max(high);l=min(low);c=close[-1];sessions.append(dict(width=h-l,ibs=.5 if h==l else (c-l)/(h-l),close=c))
        else:sessions.append(None)
        # Build the feature using sessions strictly before i, never selecting good rows across a gap.
        last=sessions[i-1] if i else None;prior=sessions[max(0,i-14):i];long=sessions[max(0,i-200):i]
        history.append(dict(ibs_previous=last['ibs'] if last else math.nan,previous_close=last['close'] if last else math.nan,
            adr=sum(x['width'] for x in prior)/14 if len(prior)==14 and all(x is not None for x in prior) else math.nan,
            sma200=sum(x['close'] for x in long)/200 if len(long)==200 and all(x is not None for x in long) else math.nan))
    return history,valid
