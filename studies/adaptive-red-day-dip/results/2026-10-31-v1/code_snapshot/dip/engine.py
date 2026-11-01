"""Past red bodies including zero green days; confirmed dip, delayed long entry."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))
HISTORY=('average_drop','adr','previous_close','previous_red_count')
FIELDS=(*HISTORY,'opening_price','dip_level','stop_price','bar_index','decision_slot','signal_slot','entry_slot','sizing_price')
@dataclass(frozen=True)
class Config:
    window:int=21
    adr_days:int=14
    multiplier:float=1.
    bar_minutes:int=5
    start_minute:int=5
    end_minute:int=360
    red_filter:bool=False
    stop_enabled:bool=True
    quality:str='complete_days'
    slippage:float=.01
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if any(not isinstance(x,int) or x<1 for x in (self.window,self.adr_days)):raise ValueError('history length')
        if not math.isfinite(self.multiplier) or self.multiplier<=0:raise ValueError('multiplier')
        if self.bar_minutes not in (1,5,15):raise ValueError('bar size')
        if not 1<=self.start_minute<self.end_minute<=360:raise ValueError('window')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('friction')
        if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk')

class Unresolved(Exception):
    def __init__(self,reason,slot):self.reason=reason;self.slot=slot;super().__init__(reason)

def valid_bars(a,i,n):
    o,h,l,c,v=[a[k][i,:n] for k in ('open','high','low','close','volume')]
    return np.isfinite([o,h,l,c,v]).all(axis=0)&(o>0)&(l>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(v>=0)

def flag_valid(m,i):
    return set(str(m.quality.iloc[i].get('reason','')).split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'})

def history(m,c):
    daily=[];out=[]
    for i,n in enumerate(m.lengths):
        n=int(n);good=bool(m.valid[i]) and flag_valid(m,i) and bool(valid_bars(m.arrays,i,n).all())
        d=dict(open=float(m.arrays['open'][i,0]),high=float(m.arrays['high'][i,:n].max()),low=float(m.arrays['low'][i,:n].min()),close=float(m.arrays['close'][i,n-1])) if good else None
        daily.append(d);past=daily[max(0,i-c.window):i];ranges=daily[max(0,i-c.adr_days):i]
        avg=float(np.mean([max(x['open']-x['close'],0.) for x in past])) if len(past)==c.window and all(x is not None for x in past) else None
        adr=float(np.mean([x['high']-x['low'] for x in ranges])) if len(ranges)==c.adr_days and all(x is not None for x in ranges) else None
        red=0
        for prev in reversed(daily[max(0,i-2):i]):
            if prev is None:red=None;break
            if prev['close']>=prev['open']:break
            red+=1
        prev=daily[i-1] if i else None
        why='warmup' if i<max(c.window,c.adr_days) else 'unknown_history' if avg is None or adr is None or c.red_filter and red is None else 'ready'
        out.append(dict(average_drop=avg,adr=adr,previous_close=prev['close'] if prev else None,previous_red_count=red,history_reason=why))
    return out

def select(m,i,c,h=None):
    h=h or history(m,c)[i]
    x=dict(index=i,date=str(m.dates[i].date()),session_minutes=int(m.lengths[i]),**{k:None for k in FIELDS});x.update({k:h[k] for k in HISTORY})
    if m.lengths[i]!=390:return dict(x,reason='half_session')
    if not flag_valid(m,i):return dict(x,reason='unknown_source')
    if h['history_reason']!='ready':return dict(x,reason=h['history_reason'])
    if h['average_drop']<=0:return dict(x,reason='zero_average_drop')
    if h['adr']<=0:return dict(x,reason='zero_adr')
    op=float(m.arrays['open'][i,0])
    if not math.isfinite(op) or op<=0:return dict(x,reason='unknown_scan')
    drop=D(h['average_drop']).quantize(D('.00000001'));adr=D(h['adr']).quantize(D('.00000001'))
    level=float((D(op)-D(c.multiplier)*drop).quantize(D('.01'),rounding=ROUND_FLOOR))
    stop=float((D(level)-adr).quantize(D('.01'),rounding=ROUND_FLOOR));x.update(opening_price=op,dip_level=level,stop_price=stop)
    if min(level,stop)<=0:return dict(x,reason='invalid_level')
    if c.red_filter and h['previous_red_count']<2:return dict(x,reason='red_filtered')
    bad=np.cumsum(~valid_bars(m.arrays,i,390));b=c.bar_minutes
    for end in range(b,391,b):
        if end<c.start_minute:continue
        if end>c.end_minute:break
        if bad[end-1]:return dict(x,reason='unknown_scan')
        price=float(m.arrays['close'][i,end-1])
        if price<level-1e-10:
            return dict(x,reason='eligible' if price>stop else 'invalid_geometry',bar_index=end//b-1,decision_slot=end,signal_slot=end-1,entry_slot=end+1,sizing_price=price)
    return dict(x,reason='no_signal')

def prepare(m,c):
    hs=history(m,c);return [select(m,i,c,h) for i,h in enumerate(hs)]

def trace(m,f,c):
    i=f['index'];a=m.arrays;left=f['entry_slot'];stop=f['stop_price'];n=int(m.lengths[i])
    entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise Unresolved('missing_entry_open',left)
    good=valid_bars(a,i,n);held=[];lows=[];highs=[];resolution='bar_open'
    for j in range(left,n):
        op=float(a['open'][i,j])
        if not math.isfinite(op) or op<=0:raise Unresolved('missing_active_open',j)
        if c.stop_enabled and op<=stop:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==n-1:ref=op;why='eod_open';break
        if not good[j]:raise Unresolved('invalid_active_bar',j)
        if c.stop_enabled and a['low'][i,j]<=stop:ref=stop;why='stop_intrabar';resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]));lows.append(float(a['low'][i,j]));highs.append(float(a['high'][i,j]))
    opened=pd.Timestamp(m.quality.iloc[i].session_open)
    return dict(exit_slot=j,entry_reference=entry,exit_reference=float(ref),entry_time=str(opened+pd.Timedelta(minutes=left)),
       exit_time=str(opened+pd.Timedelta(minutes=j)),exit_reason=why,exit_resolution=resolution,ambiguous_bar=False,
       holding_minutes=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,lows=lows,highs=highs)

TRADE_COLUMNS=['date','symbol','quality','direction','quantity',*FIELDS,'exit_slot','entry_reference','exit_reference','entry_time','exit_time','exit_reason','exit_resolution','ambiguous_bar',
 'holding_minutes','entry_price','exit_price','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after',
 'entry_leverage','entry_fill_leverage','entry_risk_pct','modeled_stop_net_risk_pct','mae_price_usd','mfe_price_usd']
UNKNOWN_COLUMNS=['date','symbol','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']
def simulate(m,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unknown=[]
    for f in features:
        if not start<=f['date']<=end:continue
        i=f['index'];date=f['date'];why=f['reason'];excluded=why.startswith('unknown_')
        before=capital;net=fee=friction=0.;qty=minutes=0;marks=[capital]
        if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            risk=D(f['sizing_price'])-D(f['stop_price'])
            q=int(min(D(capital)*D(cfg.leverage_cap)/D(f['sizing_price']),D(capital)*D(cfg.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))
            if q<=0:why='zero_quantity'
            else:
                try:p=trace(m,f,cfg)
                except Unresolved as e:
                    why='unresolved_execution';excluded=True;ref=float(m.arrays['open'][i,f['entry_slot']]);known=math.isfinite(ref) and ref>0
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,reason=e.reason,first_unknown_slot=e.slot,entry_reference=ref if known else None,
                        known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=p['holding_minutes'];entry=p['entry_reference']+cfg.slippage;exit_price=p['exit_reference']-cfg.slippage
                    if min(entry,exit_price)<=0:raise ValueError('nonpositive fill')
                    fee=2*max(.35,q*.0035);friction=2*q*cfg.slippage;gross=q*(exit_price-entry);net=gross-fee;capital+=net
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*(x-entry) for x in p.pop('closes')],capital]
                    mae=q*(min([entry,exit_price,*p.pop('lows')])-entry);mfe=q*(max([entry,exit_price,*p.pop('highs')])-entry)
                    trades.append(dict(date=date,symbol=m.symbol,quality=cfg.quality,direction='LONG',quantity=q,**{k:f[k] for k in FIELDS},**p,
                       entry_price=entry,exit_price=exit_price,price_move_pnl=q*(p['exit_reference']-p['entry_reference']),friction_cost=friction,commission=fee,borrow_fee=0.,
                       gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,
                       entry_fill_leverage=q*entry/before,entry_risk_pct=q*max(0,p['entry_reference']-f['stop_price'])/before*100,
                       modeled_stop_net_risk_pct=(q*max(0,entry-(min(f['stop_price'],p['entry_reference'])-cfg.slippage))+fee)/before*100,mae_price_usd=mae,mfe_price_usd=mfe))
        vals=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,vals])[1:];dd=max(dd,float(np.max((peaks-vals)/peaks)));usd=max(usd,float(np.max(peaks-vals)));peak=max(peak,float(vals.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,
            return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,holding_minutes=minutes,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unknown,columns=UNKNOWN_COLUMNS),
      initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
