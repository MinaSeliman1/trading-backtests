"""Statistiques conditionnelles; helpers precedents reutilises sans modification."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'opening-range-5m'))
from orb.analysis import uncertainty,return_statistics,drawdown_duration,ablation_return


def summarize(result):
    d=result.daily;t=result.trades
    if d.empty:raise ValueError('empty evaluation period')
    s=return_statistics(d.return_net,d.date);s.update(drawdown_duration(d.return_net,d.date))
    gains=t.loc[t.net_pnl>0,'net_pnl'];losses=t.loc[t.net_pnl<0,'net_pnl'];stripped=d.return_net.to_numpy().copy();stripped[d.date.str.startswith('2020').to_numpy()]=0
    s.update(final_equity=float(d.equity.iloc[-1]),net_pnl=float(t.net_pnl.sum()),trades=len(t),conditional_historical_performance=True,continuous_observed_portfolio=False,
        data_excluded_sessions=int(d.conditionally_excluded.sum()),unresolved_sessions=len(result.unresolved),
        causal_history_abstention_sessions=int(d.eligibility.isin(['warmup20','invalid_prior20','zero_adr']).sum()),direction_filtered_sessions=int(d.eligibility.eq('direction_filtered').sum()),
        no_signal_sessions=int(((d.eligibility=='eligible')&(d.signal_sign==0)).sum()),
        win_rate_pct=float(len(gains)/len(t)*100) if len(t) else None,profit_factor=float(gains.sum()/-losses.sum()) if len(losses) else None,
        mean_gain_usd=float(gains.mean()) if len(gains) else None,mean_loss_usd=float(losses.mean()) if len(losses) else None,
        mean_trade_bps=float(t.net_bps.mean()) if len(t) else None,median_trade_bps=float(t.net_bps.median()) if len(t) else None,
        observed_close_drawdown_pct=result.observed_close_drawdown_pct,observed_close_drawdown_usd=result.observed_close_drawdown_usd,
        regular_time_exposure_upper_pct=float(d.holding_minutes_upper.sum()/d.session_minutes.sum()*100),holding_minutes_upper_mean=float(t.holding_minutes_upper.mean()) if len(t) else None,
        intrabar_exit_count=int(t.exit_resolution.eq('intrabar_minute_unknown').sum()),vwap_exit_count=int(t.exit_reason.eq('vwap_next_open').sum()),stop_gap_count=int(t.exit_reason.eq('stop_gap').sum()),
        half_session_trades=int(t.half_session.sum()),mean_actual_entry_leverage=float(t.entry_leverage.mean()) if len(t) else None,max_actual_entry_leverage=float(t.entry_leverage.max()) if len(t) else None,
        max_entry_risk_pct=float(t.entry_risk_pct.max()) if len(t) else None,entry_risk_over_one_pct_count=int((t.entry_risk_pct>1+1e-10).sum()),
        worst_trade_usd=float(t.net_pnl.min()) if len(t) else None,worst_observed_mae_usd=float(t.mae_observed_usd.min()) if len(t) else None,
        return_without_top3_days_pct=ablation_return(d.return_net,d.return_net),return_without_2020_daily_returns_pct=float((np.prod(1+stripped)-1)*100),
        top3_positive_profit_share_pct=float(gains.nlargest(3).sum()/gains.sum()*100) if len(gains) else None,days_with_position_pct=float(d.trades.mean()*100),cash_return_pct=0.)
    for k in ('price_move_pnl','friction_cost','commission','borrow_fee'):s[k]=float(t[k].sum())
    assert abs(s['final_equity']-(result.initial_capital+s['net_pnl']))<1e-6
    assert abs(d.net_pnl.sum()-s['net_pnl'])<1e-6
    assert abs(s['price_move_pnl']-s['friction_cost']-s['commission']-s['borrow_fee']-s['net_pnl'])<1e-6
    return s
