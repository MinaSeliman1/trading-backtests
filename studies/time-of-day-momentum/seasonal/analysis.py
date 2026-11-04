"""Conditional account statistics and preregistered causal timing controls."""
from dataclasses import replace
import numpy as np
import pandas as pd
from .data import source
from orb.analysis import summarize,uncertainty as bookkeeping_uncertainty
from .engine import training,feature_at,trace,quantity,priced_path,Unresolved,CLOCKS


def bootstrap_mean(values,repetitions=3000,seed=20261104):
    x=np.asarray(values,dtype=float)
    if not np.isfinite(x).all():raise ValueError('nonfinite bootstrap input')
    n=len(x);out=dict(sessions=n,repetitions=repetitions,seed=seed,mean=float(x.mean()) if n else None,blocks={})
    if not n:return dict(out,insufficient=True)
    rng=np.random.default_rng(seed);centered=x-x.mean()
    for block in (5,20):
        starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
        idx=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
        samples=x[idx].mean(axis=1);null=centered[idx].mean(axis=1)
        p=(1+int(np.sum(null>=x.mean())))/(repetitions+1)
        out['blocks'][str(block)]=dict(mean_ci95=np.quantile(samples,[.025,.975]).tolist(),p_one_sided=float(p))
    return out



def observed_bootstrap(values,repetitions=3000,seed=20261104):
    x=np.asarray(values,dtype=float)
    if np.isinf(x).any():raise ValueError('infinite observation')
    known=np.isfinite(x);n=len(x);nknown=int(known.sum());mean=float(x[known].mean()) if nknown else None
    out=dict(calendar_sessions=n,observed_sessions=nknown,repetitions=repetitions,seed=seed,mean=mean,blocks={})
    if not nknown:return out
    rng=np.random.default_rng(seed);filled=np.where(known,x,0.);centered=np.where(known,x-mean,0.)
    for block in (5,20):
        starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
        idx=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
        counts=known[idx].sum(axis=1);valid=counts>0
        estimates=filled[idx].sum(axis=1)[valid]/counts[valid];null=centered[idx].sum(axis=1)[valid]/counts[valid]
        p=(1+int(np.sum(null>=mean)))/(len(null)+1)
        out['blocks'][str(block)]=dict(mean_ci95=np.quantile(estimates,[.025,.975]).tolist(),p_one_sided=float(p),valid_repetitions=int(valid.sum()))
    return out


def uncertainty(result,repetitions=3000,seed=20261104):
    out=bookkeeping_uncertainty(result,repetitions,seed)
    out['observed_calendar_blocks']=observed_bootstrap(result.daily.observed_return.to_numpy(dtype=float),repetitions,seed)
    out['economic_gate']='observed_calendar_blocks only; excluded dates stay missing while calendar blocks are preserved'
    out['caveat']='Conditional observed sample. Legacy blocks include bookkeeping zeros for excluded sessions and are descriptive only. Reused B and earlier research selection remain uncorrected.'
    return out


def paired_tests(primary,controls,repetitions=3000,seed=20261104):
    out={}
    for j,(name,control) in enumerate(controls.items()):
        a=primary.daily.copy();b=control.daily.copy()
        if a.date.duplicated().any() or b.date.duplicated().any():raise ValueError('duplicate daily key')
        if 'trades' not in a:a['trades']=(a.return_net!=0).astype(int)
        if 'trades' not in b:b['trades']=(b.return_net!=0).astype(int)
        cols=['date','return_net','conditionally_excluded','trades'];p=a[cols].merge(b[cols],on='date',suffixes=('_strategy','_control'),validate='one_to_one')
        keep=~p.conditionally_excluded_strategy&~p.conditionally_excluded_control
        calendar_delta=(p.return_net_strategy-p.return_net_control).where(keep,np.nan).to_numpy();stats=observed_bootstrap(calendar_delta,repetitions,seed+j);p=p.loc[keep]
        delta=p.return_net_strategy.to_numpy()-p.return_net_control.to_numpy()
        out[name]=dict(paired_sessions=len(p),paired_signal_dates=int(((p.trades_strategy>0)&(p.trades_control>0)).sum()),either_account_trade_dates=int(((p.trades_strategy>0)|(p.trades_control>0)).sum()),mean_difference_bps=float(delta.mean()*10000) if len(delta) else None,
                       strategy_mean_bps=float(p.return_net_strategy.mean()*10000) if len(p) else None,control_mean_bps=float(p.return_net_control.mean()*10000) if len(p) else None,
                       paired_dates=p.date.tolist(),uncertainty=stats,p_one_sided=stats['blocks'].get('20',{}).get('p_one_sided',1.))
    return out


def holm(values):
    ordered=sorted(values,key=lambda k:values[k]);previous=0.;out={};n=len(values)
    for rank,key in enumerate(ordered):
        value=min(1.,max(previous,(n-rank)*values[key]));out[key]=value;previous=value
    return out


def random_clock_panel(m,features,c,repetitions=1000,seed=20261104):
    h=training(m,c.lookback);cfg=replace(c,initial_capital=100000.,mode='both');capital=100000.;rng=np.random.default_rng(seed)
    totals=np.zeros(repetitions);ref_total=0.;rows=[];excluded=[]
    for f in features:
        if f['reason']!='eligible':continue
        i=f['index'];available=[int(k) for k in CLOCKS if k+31<int(m.lengths[i])]
        if not m.valid[i]:excluded.append(dict(date=f['date'],reason='incomplete_current_day'));continue
        values=[];unknown=None
        for k in available:
            other=feature_at(m,i,cfg,h,f,k,f['reference_sign'])
            if other['reason']!='eligible':unknown=other['reason'];break
            q=quantity(capital,other['sizing_price'],other['stop_price'],other['sign'],cfg)
            if q<=0:unknown='zero_quantity';break
            try:p=trace(m,other,cfg)
            except Unresolved:unknown='unresolved_path';break
            values.append(priced_path(p,other,q,cfg)['net_pnl'])
        if unknown:excluded.append(dict(date=f['date'],reason=unknown));continue
        chosen=available.index(f['historical_slot']);reference=values[chosen];draw=rng.integers(0,len(available),size=repetitions)
        totals+=np.asarray(values)[draw];ref_total+=reference
        rows.append(dict(date=f['date'],reference_clock=f['historical_slot'],reference_net_usd=reference,available_clocks=len(available),**{f'clock_{k}_net_usd':v for k,v in zip(available,values)}))
    n=len(rows);summary=dict(repetitions=repetitions,seed=seed,paired_signal_dates=n,excluded_signal_dates=len(excluded),capital_policy='constant 100000 USD each day; not compounded accounts',
        normalized_reference_total_usd=ref_total,random_total_usd_ci95=np.quantile(totals,[.025,.975]).tolist(),random_total_usd_median=float(np.median(totals)),
        reference_percentile_rank_pct=float(np.mean(totals<=ref_total)*100),random_upper_tail_probability=float((1+np.sum(totals>=ref_total))/(repetitions+1)),
        normalized_reference_mean_bps=ref_total/capital/n*10000 if n else None,conditional_common_coverage=True,selection='Every eligible reference candidate, only dates where all calendar-compatible clocks have resolved history and paths')
    return dict(summary=summary,draws=pd.DataFrame(dict(draw=np.arange(repetitions),normalized_net_usd=totals)),daily=pd.DataFrame(rows),excluded=pd.DataFrame(excluded,columns=['date','reason']))
