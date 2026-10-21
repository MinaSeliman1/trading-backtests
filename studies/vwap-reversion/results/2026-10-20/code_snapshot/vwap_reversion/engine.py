from dataclasses import dataclass
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
import math
import numpy as np
import pandas as pd
D=lambda x:Decimal(str(x))

@dataclass(frozen=True)
class Config:
    mode:str='both'
    slippage:float=.01
    quality:str='complete_days'
    exit_policy:str='vwap'
    initial_capital:float=100000.
    risk_budget:float=.01
    leverage_cap:float=1.

    def __post_init__(self):
        if self.mode not in ('both','long_only','short_only'):raise ValueError('mode')
        if self.quality not in ('complete_days','resolved_prefix'):raise ValueError('quality')
        if self.exit_policy not in ('vwap','eod_only'):raise ValueError('exit_policy')
        if not all(math.isfinite(v) and v>0 for v in (self.initial_capital,self.risk_budget,self.leverage_cap)):raise ValueError('capital/risk')
        if not math.isfinite(self.slippage) or self.slippage<0:raise ValueError('slippage')

class UnresolvedExecution(Exception):
    def __init__(self,reason,minute):self.reason=reason;self.minute=minute;super().__init__(reason)


def valid_bars(a,i,n):
    p=np.column_stack([a[k][i,:n] for k in ('open','high','low','close')]);v=a['volume'][i,:n]
    return np.isfinite(p).all(axis=1)&np.isfinite(v)&(p.min(axis=1)>0)&(v>=0)&(p[:,1]>=p.max(axis=1))&(p[:,2]<=p.min(axis=1))


def prepare(market):
    m=market;a=m.arrays;rows=[];ranges=[]
    for i,day in enumerate(m.dates):
        n=int(m.lengths[i]);good=bool(m.valid[i] and valid_bars(a,i,n).all())
        ranges.append(D(a['high'][i,:n].max())-D(a['low'][i,:n].min()) if good else None)
        f=dict(index=i,date=str(day.date()),eligibility='eligible',data_excluded=False,adr20=np.nan,adr_decimal=None,vwap_at_signal=np.nan,
            pv_decimal=None,volume_decimal=None,sizing_price=float(a['close'][i,59]),signal_sign=0,stretch_adr=np.nan)
        if i<20:f['eligibility']='warmup20'
        elif any(x is None for x in ranges[i-20:i]):f['eligibility']='invalid_prior20'
        else:
            adr=sum(ranges[i-20:i],D(0))/20;f.update(adr20=float(adr),adr_decimal=str(adr))
            if adr<=0:f['eligibility']='zero_adr'
            else:
                v=a['volume'][i,:60];vw=a['vwap'][i,:60];positive=v>0
                if not valid_bars(a,i,60).all() or not (np.isfinite(vw[positive])&(vw[positive]>0)).all() or not positive.any():f.update(eligibility='invalid_firsthour',data_excluded=True)
                else:
                    pv=sum((D(vw[j])*D(v[j]) for j in range(60) if v[j]>0),D(0));volume=sum((D(x) for x in v),D(0));mean=pv/volume;delta=D(f['sizing_price'])-mean
                    sign=-1 if delta>adr*D('.25') else 1 if delta<-adr*D('.25') else 0
                    f.update(vwap_at_signal=float(mean),pv_decimal=str(pv),volume_decimal=str(volume),signal_sign=sign,stretch_adr=float(delta/adr))
        rows.append(f)
    return pd.DataFrame(rows)


def trace(market,index,feature,exit_policy='vwap'):
    a=market.arrays;i=index;f=feature;side=int(f['signal_sign']);n=int(market.lengths[i]);adr=D(f['adr_decimal'])
    entry=D(a['open'][i,60])
    if not entry.is_finite() or entry<=0:raise UnresolvedExecution('missing_entry_open',60)
    stop=entry-side*adr;pv=D(f['pv_decimal']);volume=D(f['volume_decimal']);pending=False;closes=[];adverse=[float(entry)];favorable=[float(entry)];valid=valid_bars(a,i,n);resolution='bar_open';signal_slot=None
    for j in range(60,n):
        o=D(a['open'][i,j])
        if not o.is_finite() or o<=0:raise UnresolvedExecution('missing_active_open',j)
        if side*(o-stop)<=0:exit_ref=o;reason='stop_gap';break
        if pending:exit_ref=o;reason='vwap_next_open';break
        if j==n-1:exit_ref=o;reason='eod_open';break
        if not valid[j]:raise UnresolvedExecution('invalid_active_bar',j)
        if (side>0 and D(a['low'][i,j])<=stop) or (side<0 and D(a['high'][i,j])>=stop):
            exit_ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        close=D(a['close'][i,j]);closes.append(float(close));adverse.append(float(a['low' if side>0 else 'high'][i,j]));favorable.append(float(a['high' if side>0 else 'low'][i,j]))
        if exit_policy=='vwap':
            v=D(a['volume'][i,j]);vw=D(a['vwap'][i,j])
            if v>0:
                if not vw.is_finite() or vw<=0:raise UnresolvedExecution('missing_active_vwap',j)
                pv+=v*vw;volume+=v
            if side*(close-pv/volume)>=0:pending=True;signal_slot=j
    else:raise UnresolvedExecution('no_exit',n-1)
    adverse.append(float(exit_ref));favorable.append(float(exit_ref));opening=pd.Timestamp(market.quality.iloc[i].session_open)
    return dict(entry_reference=float(entry),exit_reference=float(exit_ref),stop_price=float(stop),exit_slot=j,exit_reason=reason,exit_resolution=resolution,
        exit_signal_slot=signal_slot,entry_time=str(opening+pd.Timedelta(minutes=60)),exit_time=str(opening+pd.Timedelta(minutes=j)),
        holding_minutes_upper=j-60+int(resolution=='intrabar_minute_unknown'),closes=closes,adverse=adverse,favorable=favorable)


TRADE_COLUMNS=['date','symbol','mode','quality','exit_policy','direction','sign','quantity','adr20','sizing_price','vwap_at_signal','stretch_adr','entry_time','exit_time','entry_reference','exit_reference','entry_price','exit_price','stop_price','exit_slot','exit_reason','exit_resolution','exit_signal_slot','holding_minutes_upper','price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl','net_bps','equity_before','equity_after','entry_leverage','entry_risk_pct','mae_observed_usd','mfe_observed_usd','half_session']


def simulate(market,features,config,start,end):
    capital=config.initial_capital;peak=capital;dd=dd_usd=0.;trades=[];daily=[];unresolved=[]
    for f in features.to_dict('records'):
        date=f['date'];i=f['index']
        if not start<=date<=end:continue
        why=f['eligibility'];excluded=f['data_excluded'];side=f['signal_sign'];before=capital;net=fee=borrow=0.;q=0;upper=0;marks=[before]
        filtered=(config.mode=='long_only' and side<0) or (config.mode=='short_only' and side>0)
        if filtered:why='direction_filtered'
        elif why=='eligible' and config.quality=='complete_days' and not market.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        if why=='eligible' and side:
            adr=D(f['adr_decimal']);target=min(D(capital)*D(config.leverage_cap)/D(f['sizing_price']),D(capital)*D(config.risk_budget)/adr);quantity=int(target.to_integral_value(rounding=ROUND_FLOOR))
            if quantity<=0:why='zero_quantity'
            else:
                try:p=trace(market,i,f,config.exit_policy)
                except UnresolvedExecution as e:
                    why='unresolved_execution';excluded=True;ref=market.arrays['open'][i,60];known=math.isfinite(ref) and ref>0
                    unresolved.append(dict(date=date,symbol=market.symbol,sign=side,quantity=quantity,reason=e.reason,first_unknown_slot=e.minute,entry_reference=ref if known else None,
                        known_entry_commission=max(.35,quantity*.0035) if known else 0.,known_entry_friction=quantity*config.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    q=quantity;entry=p['entry_reference']+side*config.slippage;exit_price=p['exit_reference']-side*config.slippage
                    if min(entry,exit_price)<=0:raise ValueError('nonpositive modeled fill')
                    fee=2*max(.35,q*.0035);borrow=q*entry*.01/360 if side<0 else 0.;gross=q*side*(exit_price-entry);net=gross-fee-borrow;capital+=net
                    marks=[before,before-fee/2-q*config.slippage,*[before-fee/2+q*side*(x-entry) for x in p['closes']],capital];upper=p['holding_minutes_upper']
                    mae=min(0.,min(q*side*(x-entry) for x in p.pop('adverse')));mfe=max(0.,max(q*side*(x-entry) for x in p.pop('favorable')));p.pop('closes')
                    trades.append(dict(date=date,symbol=market.symbol,mode=config.mode,quality=config.quality,exit_policy=config.exit_policy,direction='LONG' if side>0 else 'SHORT',sign=side,quantity=q,
                        **{k:f[k] for k in ('adr20','sizing_price','vwap_at_signal','stretch_adr')},**p,entry_price=entry,exit_price=exit_price,price_move_pnl=q*side*(p['exit_reference']-p['entry_reference']),friction_cost=2*q*config.slippage,
                        commission=fee,borrow_fee=borrow,gross_pnl=gross,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before,equity_after=capital,entry_leverage=q*p['entry_reference']/before,
                        entry_risk_pct=float(q*adr/D(before)*100),mae_observed_usd=mae,mfe_observed_usd=mfe,half_session=int(market.lengths[i])==210))
        values=np.asarray(marks);peaks=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max((peaks-values)/peaks)));dd_usd=max(dd_usd,float(np.max(peaks-values)));peak=max(peak,float(values.max()))
        ret=net/before if before>0 else 0.
        daily.append(dict(date=date,session_minutes=int(market.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=np.nan if excluded else ret,return_net=ret,
            net_pnl=net,equity=capital,trades=int(q>0),quantity=q,signal_sign=f['signal_sign'],commission=fee,borrow_fee=borrow,holding_minutes_upper=upper,observed_close_drawdown_pct_so_far=dd*100))
    return SimpleNamespace(daily=pd.DataFrame(daily),trades=pd.DataFrame(trades,columns=TRADE_COLUMNS),unresolved=pd.DataFrame(unresolved,columns=['date','symbol','sign','quantity','reason','first_unknown_slot','entry_reference','known_entry_commission','known_entry_friction','omitted_entire_trade']),
        initial_capital=config.initial_capital,observed_close_drawdown_pct=dd*100,observed_close_drawdown_usd=dd_usd)
