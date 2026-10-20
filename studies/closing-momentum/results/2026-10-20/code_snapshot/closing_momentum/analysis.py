"""Statistiques descriptives ; aucun choix de modele apres observation."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'intraday-momentum-noise-area'))
from noise_area.statistics import return_statistics


def ablation_return(returns,pnl,count=3):
    r=np.asarray(returns,dtype=float).copy();p=np.asarray(pnl,dtype=float)
    positive=np.flatnonzero(p>0);top=positive[np.argsort(p[positive])[-count:]]
    r[top]=0
    return float((np.prod(1+r)-1)*100)


def summarize(result):
    d=result.daily;t=result.trades
    if d.empty:raise ValueError('empty evaluation period')
    stats=return_statistics(d.return_net,d.date)
    stats['final_equity']=float(d.equity.iloc[-1])
    gains=t.loc[t.net_pnl>0,'net_pnl'];losses=t.loc[t.net_pnl<0,'net_pnl']
    stats.update(net_pnl=float(t.net_pnl.sum()),trades=len(t),win_rate_pct=float(len(gains)/len(t)*100) if len(t) else None,
        profit_factor=float(gains.sum()/-losses.sum()) if len(losses) else None,
        mean_trade_bps=float(t.net_bps.mean()) if len(t) else None,median_trade_bps=float(t.net_bps.median()) if len(t) else None,
        price_move_pnl=float(t.price_move_pnl.sum()),friction_cost=float(t.friction_cost.sum()),commission=float(t.commission.sum()),borrow_fee=float(t.borrow_fee.sum()),
        observed_close_drawdown_pct=result.observed_close_drawdown_pct,observed_close_drawdown_usd=result.observed_close_drawdown_usd,
        days_with_position_pct=float(d.trades.mean()*100),regular_time_exposure_pct=float(d.trades.sum()*29/d.session_minutes.sum()*100),
        mean_actual_entry_leverage=float(t.entry_leverage.mean()) if len(t) else None,max_actual_entry_leverage=float(t.entry_leverage.max()) if len(t) else None,
        trades_with_missing_holding_minutes=int((t.missing_holding_minutes>0).sum()),half_session_trades=int(t.half_session.sum()),
        return_without_top3_days_pct=ablation_return(d.return_net,d.net_pnl),
        top3_positive_profit_share_pct=float(gains.nlargest(3).sum()/gains.sum()*100) if len(gains) else None,
        worst_trade_usd=float(t.net_pnl.min()) if len(t) else None,worst_observed_mae_usd=float(t.mae_observed_usd.min()) if len(t) else None,
        excluded_sessions=int((d.eligibility!='eligible').sum()),cash_return_pct=0.)
    assert abs(stats['final_equity']-(result.initial_capital+stats['net_pnl']))<1e-6
    assert abs(float(d.net_pnl.sum())-stats['net_pnl'])<1e-6
    return stats


def uncertainty(result,benchmark,repetitions=3000,seed=20261020):
    if result.daily.date.tolist()!=benchmark.daily.date.tolist():raise ValueError('benchmark dates not aligned')
    r=result.daily.return_net.to_numpy(dtype=float);b=benchmark.daily.return_net.to_numpy(dtype=float);n=len(r)
    if not n:raise ValueError('empty uncertainty sample')
    rng=np.random.default_rng(seed);blocks={}
    for block in (5,20):
        starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
        indices=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
        means=r[indices].mean(axis=1);deltas=(r-b)[indices].mean(axis=1)
        blocks[str(block)]=dict(daily_mean_ci95=np.quantile(means,[.025,.975]).tolist(),mean_minus_long_ci95=np.quantile(deltas,[.025,.975]).tolist())
    years=sorted(pd.DatetimeIndex(result.daily.date).year.unique().tolist())
    groups=pd.DatetimeIndex(result.trades.date).year
    sums=np.array([result.trades.loc[groups==year,'net_bps'].sum() for year in years]);counts=np.array([int(np.sum(groups==year)) for year in years])
    indices=rng.integers(0,len(years),size=(repetitions,len(years)));denominators=counts[indices].sum(axis=1);valid=denominators>0
    means=sums[indices].sum(axis=1)[valid]/denominators[valid]
    return dict(repetitions=repetitions,seed=seed,paired_blocks=blocks,block_method='Circular blocks of complete aligned sessions; daily returns and long reference paired by date',
        annual_cluster=dict(years=years,events_by_year=counts.tolist(),valid_repetitions=int(valid.sum()),mean_trade_bps_ci95=np.quantile(means,[.025,.975]).tolist() if len(means) else None),
        caveat='Descriptive intervals, no multiplicity correction; few calendar-year clusters and reused B limit evidence. Fixed-quantity benchmark equity differs from a separately resized 1x strategy.')
