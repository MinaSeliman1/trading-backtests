"""Causal 5-minute RSI reversion with minute execution and conditional accounts."""
from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
from orb.engine import valid_bars,UnresolvedExecution
D=lambda x:Decimal(str(x))

@dataclass(frozen=True)
class Config:
    mode:str='long_only'
    slippage:float=.01
    quality:str='complete_days'
    use_regime:bool=True
    entry_threshold:float=5.
    exit_threshold:float=70.
    stop_atr:float=2.
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.
    def __post_init__(self):
        if self.mode not in ('long_only','short_only','both'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('slippage')
        if not 0<self.entry_threshold<50 or not 50<self.exit_threshold<100:raise ValueError('threshold')
        if not all(math.isfinite(x) and x>0 for x in (self.stop_atr,self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk/ATR')

def wilder(values,length):
    values=np.asarray(values,dtype=float);out=np.full(len(values),np.nan)
    if len(values)<length or not np.isfinite(values[:length]).all():return out
    value=float(values[:length].mean());out[length-1]=value
    for i in range(length,len(values)):
        if not np.isfinite(values[i]):break
        value=(value*(length-1)+float(values[i]))/length;out[i]=value
    return out


def rsi(closes,length=2):
    closes=np.asarray(closes,dtype=float);delta=np.diff(closes);out=np.full(len(closes),np.nan)
    g=wilder(np.maximum(delta,0),length);l=wilder(np.maximum(-delta,0),length)
    for i,(gain,loss) in enumerate(zip(g,l),start=1):
        if not np.isfinite(gain+loss):continue
        out[i]=50. if gain==loss==0 else 100. if loss==0 else 100-100/(1+gain/loss)
    return out


def atr(bars,length=14):
    bars=np.asarray(bars,dtype=float)
    if len(bars)==0:return np.array([])
    previous=np.r_[bars[0,3],bars[:-1,3]]
    tr=np.maximum.reduce([bars[:,1]-bars[:,2],np.abs(bars[:,1]-previous),np.abs(bars[:,2]-previous)])
    tr[0]=bars[0,1]-bars[0,2]
    return wilder(tr,length)


def prepare(market,cash):
    a=market.arrays;features=[];daily_closes=[];cumulative=0.
    for i,day in enumerate(market.dates):
        date=str(day.date());n=int(market.lengths[i]);good=valid_bars(a,i,n)
        div=float(cash.get(date,0))
        if not math.isfinite(div) or div<0:raise ValueError('dividend')
        cumulative+=div
        history=np.asarray(daily_closes[max(0,i-200):i])
        why='warmup200' if i<200 else 'invalid_prior_close' if not np.isfinite(history).all() else 'eligible'
        previous=float(history[-1]) if len(history) else np.nan;average=float(history.mean()) if len(history)==200 else np.nan
        trend=int(np.sign(previous-average)) if why=='eligible' else 0
        bars=[];complete=[]
        for left in range(0,n,5):
            right=left+5;ok=right<=n and bool(good[left:right].all());complete.append(ok)
            bars.append([a['open'][i,left],max(a['high'][i,left:right]),min(a['low'][i,left:right]),a['close'][i,right-1]] if ok else [np.nan]*4)
        bars=np.asarray(bars);features.append(dict(index=i,date=date,n=n,regime_reason=why,trend=trend,prior_close=previous,prior_sma=average,
            bars=bars,good=np.asarray(complete),rsi=rsi(bars[:,3]),atr=atr(bars),complete_day=bool(market.valid[i])))
        last=float(a['close'][i,n-1])
        daily_closes.append(last+cumulative if math.isfinite(last) and last>0 else np.nan)
    return features


def signal(feature,cfg):
    f=feature;trend=f['trend']
    if cfg.use_regime and f['regime_reason']!='eligible':return dict(reason=f['regime_reason'])
    allowed=[]
    if cfg.mode in ('long_only','both') and (not cfg.use_regime or trend==1):allowed.append(1)
    if cfg.mode in ('short_only','both') and (not cfg.use_regime or trend==-1):allowed.append(-1)
    if not allowed:return dict(reason='regime_filtered')
    for b in range(len(f['bars'])):
        entry=(b+1)*5
        if entry>=min(330,f['n']-1):break
        if not f['good'][b]:return dict(reason='unknown_signal')
        if entry<30 or not np.isfinite(f['atr'][b]) or f['atr'][b]<=0:continue
        value=f['rsi'][b]
        side=1 if 1 in allowed and value<cfg.entry_threshold else -1 if -1 in allowed and value>100-cfg.entry_threshold else 0
        if not side:continue
        price=float(f['bars'][b,3]);stop=D(price)-side*D(cfg.stop_atr)*D(f['atr'][b])
        stop=stop.quantize(D('.01'),rounding=ROUND_FLOOR if side==1 else ROUND_CEILING)
        if stop<=0:return dict(reason='invalid_stop')
        return dict(reason='eligible',sign=side,signal_bar=b,signal_slot=entry-1,entry_slot=entry,sizing_price=price,stop_price=float(stop),signal_rsi=float(value),signal_atr=float(f['atr'][b]))
    return dict(reason='no_signal')


def trace(market,index,feature,setup,cfg):
    a=market.arrays;i=index;n=int(market.lengths[i]);side=setup['sign'];left=setup['entry_slot'];stop=setup['stop_price']
    entry=float(a['open'][i,left])
    if not math.isfinite(entry) or entry<=0:raise UnresolvedExecution('missing_entry_open',left)
    good=valid_bars(a,i,n);held=[];adverse=[entry];favorable=[entry];scheduled=None;exit_signal=None;resolution='bar_open'
    for j in range(left,n):
        opening=float(a['open'][i,j])
        if not math.isfinite(opening) or opening<=0:raise UnresolvedExecution('missing_active_open',j)
        if side*(opening-stop)<=0:ref=opening;reason='entry_marketable_stop' if j==left else 'stop_gap';break
        if scheduled==j:ref=opening;reason='indicator_next_open';break
        if j==n-1:ref=opening;reason='eod_open';break
        if not good[j]:raise UnresolvedExecution('invalid_active_bar',j)
        if a['low'][i,j]<=stop if side==1 else a['high'][i,j]>=stop:
            ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        held.append(float(a['close'][i,j]));adverse.append(float(a['low' if side==1 else 'high'][i,j]));favorable.append(float(a['high' if side==1 else 'low'][i,j]))
        if j%5==4:
            value=feature['rsi'][j//5]
            if not np.isfinite(value):raise UnresolvedExecution('unknown_exit_indicator',j)
            if value>cfg.exit_threshold if side==1 else value<100-cfg.exit_threshold:scheduled=j+1;exit_signal=j
    adverse.append(ref);favorable.append(ref);opening=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(entry_slot=left,exit_slot=j,entry_reference=entry,exit_reference=ref,stop_price=stop,sign=side,exit_reason=reason,exit_signal_slot=exit_signal,
        entry_time=str(opening+pd.Timedelta(minutes=left)),exit_time=str(opening+pd.Timedelta(minutes=j)),exit_resolution=resolution,
        holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=held,adverse=adverse,favorable=favorable)


TRADE_COLUMNS=['date','symbol','mode','quality','direction','sign','quantity','signal_slot','sizing_price','signal_rsi','signal_atr','prior_close','prior_sma',
    'entry_slot','exit_slot','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','stop_price','exit_reason','exit_signal_slot','exit_resolution',
    'holding_minutes_upper','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_risk_pct',
    'mae_observed_usd','mfe_observed_usd','half_session','ambiguous_bar']


def simulate(market,features,cfg,start,end):
    capital=cfg.initial_capital;peak=capital;dd=usd=0.;trades=[];daily=[];unresolved=[]
    for f in features:
        date=f['date'];i=f['index']
        if not start<=date<=end:continue
        s=signal(f,cfg);why=s['reason'];excluded=why=='unknown_signal';before=capital;net=fee=borrow=0.;q=upper=0;marks=[before]
        if why=='eligible' and cfg.quality=='complete_days' and not market.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible':
            side=s['sign'];risk=side*(D(s['sizing_price'])-D(s['stop_price']))
            quantity=int(min(D(capital)*D(cfg.leverage_cap)/D(s['sizing_price']),D(capital)*D(cfg.risk_budget)/risk).to_integral_value(rounding=ROUND_FLOOR))
            if quantity<=0:why='zero_quantity'
            else:
                try:p=trace(market,i,f,s,cfg)
                except UnresolvedExecution as e:
                    why='unresolved_execution';excluded=True;ref=market.arrays['open'][i,s['entry_slot']];known=math.isfinite(ref) and ref>0
                    unresolved.append(dict(date=date,symbol=market.symbol,sign=side,quantity=quantity,reason=e.reason,first_unknown_slot=e.minute,
                        entry_reference=ref if known else None,known_entry_commission=max(.35,quantity*.0035) if known else 0.,known_entry_friction=quantity*cfg.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    q=quantity;entry=p['entry_reference']+side*cfg.slippage;exit_price=p['exit_reference']-side*cfg.slippage
                    if min(entry,exit_price)<=0:raise ValueError('nonpositive modeled fill')
                    fee=2*max(.35,q*.0035);borrow=q*entry*.01/360 if side<0 else 0.;gross=q*side*(exit_price-entry);net=gross-fee-borrow;capital+=net;upper=p['holding_minutes_upper']
                    marks=[before,before-fee/2-q*cfg.slippage,*[before-fee/2+q*side*(c-entry) for c in p.pop('closes')],capital]
                    mae=min(0.,min(q*side*(x-entry) for x in p.pop('adverse')));mfe=max(0.,max(q*side*(x-entry) for x in p.pop('favorable')))
                    trades.append(dict(date=date,symbol=market.symbol,mode=cfg.mode,quality=cfg.quality,direction='LONG' if side==1 else 'SHORT',quantity=q,signal_slot=s['signal_slot'],
                        sizing_price=s['sizing_price'],signal_rsi=s['signal_rsi'],signal_atr=s['signal_atr'],prior_close=f['prior_close'],prior_sma=f['prior_sma'],**p,entry_price=entry,exit_price=exit_price,
                        price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),friction_cost=2*q*cfg.slippage,commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,
                        equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,entry_risk_pct=q*max(0.,side*(p['entry_reference']-s['stop_price']))/before*100,
                        mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210,ambiguous_bar=False))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));usd=max(usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,net_pnl=net,
            equity=capital,trades=int(q>0),quantity=q,signal_sign=s.get('sign',0),commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=cfg.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=usd)
