"""Statistiques descriptives du compte historique conditionnel."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'closing-momentum'))
from closing_momentum.analysis import return_statistics,drawdown_duration,ablation_return


def summarize(result):
    d=result.daily;t=result.trades
    if d.empty:raise ValueError('empty evaluation period')
    s=return_statistics(d.return_net,d.date);s.update(drawdown_duration(d.return_net,d.date))
    gains=t.loc[t.net_pnl>0,'net_pnl'];losses=t.loc[t.net_pnl<0,'net_pnl']
    s.update(final_equity=float(d.equity.iloc[-1]),net_pnl=float(t.net_pnl.sum()),trades=len(t),
        conditional_historical_performance=True,continuous_observed_portfolio=False,
        data_excluded_sessions=int(d.conditionally_excluded.sum()),unresolved_sessions=len(result.unresolved),
        win_rate_pct=float(len(gains)/len(t)*100) if len(t) else None,
        profit_factor=float(gains.sum()/-losses.sum()) if len(losses) else None,
        mean_trade_bps=float(t.net_bps.mean()) if len(t) else None,median_trade_bps=float(t.net_bps.median()) if len(t) else None,
        observed_close_drawdown_pct=result.observed_close_drawdown_pct,observed_close_drawdown_usd=result.observed_close_drawdown_usd,
        regular_time_exposure_upper_pct=float(d.holding_minutes_upper.sum()/d.session_minutes.sum()*100),
        holding_minutes_upper_mean=float(t.holding_minutes_upper.mean()) if len(t) else None,
        intrabar_exit_count=int((t.exit_resolution=='intrabar_minute_unknown').sum()),ambiguous_trades=int(t.ambiguous_bar.sum()),
        entry_marketable_stop_count=int((t.exit_reason=='entry_marketable_stop').sum()),
        stop_gap_count=int((t.exit_reason=='stop_gap').sum()),target_gap_count=int((t.exit_reason=='target_gap').sum()),
        half_session_trades=int(t.half_session.sum()),mean_actual_entry_leverage=float(t.entry_leverage.mean()) if len(t) else None,
        max_actual_entry_leverage=float(t.entry_leverage.max()) if len(t) else None,
        entry_risk_over_one_pct_count=int((t.entry_risk_pct>1+1e-10).sum()),max_entry_risk_pct=float(t.entry_risk_pct.max()) if len(t) else None,
        worst_trade_usd=float(t.net_pnl.min()) if len(t) else None,worst_observed_mae_usd=float(t.mae_observed_usd.min()) if len(t) else None,
        return_without_top3_days_pct=ablation_return(d.return_net,d.net_pnl),
        top3_positive_profit_share_pct=float(gains.nlargest(3).sum()/gains.sum()*100) if len(gains) else None,
        days_with_position_pct=float(d.trades.mean()*100),cash_return_pct=0.)
    for k in ('price_move_pnl','friction_cost','commission','borrow_fee'):s[k]=float(t[k].sum())
    assert abs(s['final_equity']-(result.initial_capital+s['net_pnl']))<1e-6
    assert abs(float(d.net_pnl.sum())-s['net_pnl'])<1e-6
    assert abs(s['price_move_pnl']-s['friction_cost']-s['commission']-s['borrow_fee']-s['net_pnl'])<1e-6
    return s


def uncertainty(result,repetitions=3000,seed=20261020):
    r=result.daily.return_net.to_numpy(dtype=float);n=len(r)
    if not n:raise ValueError('empty uncertainty sample')
    rng=np.random.default_rng(seed);blocks={}
    for block in (5,20):
        starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
        indices=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
        blocks[str(block)]=dict(conditional_daily_mean_ci95=np.quantile(r[indices].mean(axis=1),[.025,.975]).tolist())
    years=sorted(pd.DatetimeIndex(result.daily.date).year.unique().tolist());groups=pd.DatetimeIndex(result.trades.date).year
    sums=np.array([result.trades.loc[groups==y,'net_bps'].sum() for y in years]);counts=np.array([int(np.sum(groups==y)) for y in years])
    idx=rng.integers(0,len(years),size=(repetitions,len(years)));den=counts[idx].sum(axis=1);valid=den>0
    means=sums[idx].sum(axis=1)[valid]/den[valid]
    return dict(repetitions=repetitions,seed=seed,blocks=blocks,
        annual_cluster=dict(years=years,events_by_year=counts.tolist(),valid_repetitions=int(valid.sum()),mean_trade_bps_ci95=np.quantile(means,[.025,.975]).tolist() if len(means) else None),
        caveat='Descriptive conditional intervals; excluded sessions have zero bookkeeping return, not observed cash. Reused B, few annual clusters and no multiplicity correction.')
