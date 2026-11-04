"""Separate scalar implementation; no import from the strategy engine."""
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from datetime import timedelta
import hashlib,math

D=lambda x:Decimal(str(x))
CLOCKS=tuple(range(30,331,30))


def good(a,i,j):
    o,h,l,c,v=(float(a[k][i,j]) for k in ('open','high','low','close','volume'))
    return all(math.isfinite(x) for x in (o,h,l,c,v)) and min(o,l,c)>0 and h>=max(o,c) and l<=min(o,c) and v>=0


def source_ok(m,i):return set(str(m.quality.iloc[i].get('reason','')).split('|'))<={'','nan','missing_minutes','invalid_ohlcv'}


class History(list):pass


def historical_returns(m):
    rows=History();rows.bad=[];rows.flags=[]
    for i in range(len(m.dates)):
        bad=[0]
        for j in range(int(m.lengths[i])):bad.append(bad[-1]+int(not good(m.arrays,i,j)))
        rows.bad.append(bad);ok=source_ok(m,i);rows.flags.append(ok);row=[]
        for k in CLOCKS:
            value=None
            if ok and k+31<int(m.lengths[i]) and bad[k+32]==bad[k+1]:
                value=float(m.arrays['open'][i,k+31])/float(m.arrays['open'][i,k+1])-1
            row.append(value)
        rows.append(row)
    return rows


def feature(m,i,c,history):
    available=[k for k in CLOCKS if k+31<int(m.lengths[i])]
    f=dict(index=i,date=str(m.dates[i].date()),reason='warmup',historical_slot=None,reference_sign=0,sign=0)
    n=c['lookback']
    if i<n:return f
    if not history.flags[i]:return dict(f,reason='unknown_source')
    moments={}
    for k in available:
        col=k//30-1;x=[history[j][col] for j in range(i-n,i)]
        if any(v is None for v in x):moments[k]=None
        else:
            mean=math.fsum(x)/n;std=math.sqrt(max(0.,math.fsum((v-mean)**2 for v in x)/(n-1)))
            if std<=1e-12:std=0.
            moments[k]=(mean,std,mean*math.sqrt(n)/std if std else None)
    selected=None
    for k in available:
        if moments[k] is None:return dict(f,reason='unknown_history')
        mu,sd,t=moments[k]
        if sd and abs(t)>=c['threshold']:selected=k;break
    if selected is None:return dict(f,reason='no_signal')
    mu,sd,t=moments[selected];side=1 if mu>0 else -1;f.update(historical_slot=selected,reference_sign=side,historical_t=t)
    mode=c['mode']
    if mode=='long_only' and side<0:return dict(f,reason='direction_filtered')
    k=selected
    if mode=='inverse':side=-side
    if mode=='control_same_clock_long':side=1
    if mode=='control_fixed_clock':k=30
    if mode=='control_random_clock':
        code=hashlib.sha256(f"{c['seed']}|{m.symbol}|{f['date']}".encode()).hexdigest();k=available[int(code,16)%len(available)]
    f.update(decision_slot=k,entry_slot=k+1,scheduled_exit_slot=k+31,sign=side)
    if moments[k] is None:return dict(f,reason='unknown_control_history')
    if history.bad[i][k]:return dict(f,reason='unknown_current_context')
    mu,sd,t=moments[k];price=float(m.arrays['close'][i,k-1]);width=max(D('.02'),D(c['stop_multiple'])*D(sd)*D(price))
    stop=float((D(price)-side*width).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING))
    return dict(f,reason='eligible' if stop>0 else 'invalid_stop',sizing_price=price,stop_price=stop,history_sigma=sd,history_mean=mu,history_t=t)


def trade(m,f,c,capital):
    q=int(min(D(capital)*D(c['leverage_cap'])/D(f['sizing_price']),D(capital)*D(c['risk_budget'])/(f['sign']*(D(f['sizing_price'])-D(f['stop_price'])))).to_integral_value(rounding=ROUND_FLOOR))
    if q<=0:return dict(reason='zero_quantity')
    i=f['index'];a=m.arrays;side=f['sign'];left=f['entry_slot'];end=f['scheduled_exit_slot'];stop=f['stop_price'];entry_ref=float(a['open'][i,left])
    if not math.isfinite(entry_ref) or entry_ref<=0:return dict(reason='unresolved_execution',unknown='missing_entry_open',slot=left)
    reason='scheduled_open';resolution='bar_open';held=[]
    for j in range(left,end+1):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:return dict(reason='unresolved_execution',unknown='missing_active_open',slot=j)
        if side*(op-stop)<=0:exit_ref=op;reason='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==end:exit_ref=op;break
        if not good(a,i,j):return dict(reason='unresolved_execution',unknown='invalid_active_bar',slot=j)
        hit=float(a['low'][i,j])<=stop if side>0 else float(a['high'][i,j])>=stop
        if hit:exit_ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]))
    entry=entry_ref+side*c['slippage'];exit_price=exit_ref-side*c['slippage'];commission=2*max(.35,q*.0035);borrow=q*entry*.01/360 if side<0 else 0.
    net=q*side*(exit_price-entry)-commission-borrow
    return dict(reason='eligible',quantity=q,entry_reference=entry_ref,exit_reference=exit_ref,entry_price=entry,exit_price=exit_price,exit_slot=j,exit_reason=reason,exit_resolution=resolution,commission=commission,borrow_fee=borrow,friction_cost=2*q*c['slippage'],net_pnl=net,
                marks=[capital,capital-commission/2-q*c['slippage'],*[capital-commission/2+q*side*(x-entry) for x in held],capital+net])
