"""Descriptive conditional statistics, no model selection."""
from .data import source
from orb.analysis import uncertainty
from closing_momentum.analysis import return_statistics,drawdown_duration,ablation_return
def summarize(r):
    d,t=r.daily,r.trades
    s=return_statistics(d.return_net,d.date);s.update(drawdown_duration(d.return_net,d.date))
    pos=t.loc[t.net_pnl>0,'net_pnl'];neg=t.loc[t.net_pnl<0,'net_pnl']
    s.update(final_equity=float(d.equity.iloc[-1]),trades=len(t),win_rate_pct=len(pos)/len(t)*100 if len(t) else None,
      profit_factor=float(pos.sum()/-neg.sum()) if len(neg) else None,mean_trade_bps=float(t.net_bps.mean()) if len(t) else None,
      observed_close_drawdown_pct=r.observed_close_drawdown_pct,observed_close_drawdown_usd=r.observed_close_drawdown_usd,
      data_excluded_sessions=int(d.conditionally_excluded.sum()),unresolved_sessions=len(r.unresolved),
      regular_time_exposure_pct=float(d.holding_minutes.sum()/d.session_minutes.sum()*100),
      max_entry_fill_leverage=float(t.entry_fill_leverage.max()) if len(t) else None,
      return_without_top3_days_pct=ablation_return(d.return_net,d.net_pnl),
      top3_positive_profit_share_pct=float(pos.nlargest(3).sum()/pos.sum()*100) if len(pos) else None,
      worst_trade_usd=float(t.net_pnl.min()) if len(t) else None,worst_observed_mae_usd=float(t.mae_price_usd.min()) if len(t) else None,
      conditional_historical_performance=True,continuous_observed_portfolio=False)
    for k in ('net_pnl','price_move_pnl','friction_cost','commission','borrow_fee'):s[k]=float(t[k].sum())
    assert abs(s['final_equity']-r.initial_capital-s['net_pnl'])<1e-6
    assert abs(s['price_move_pnl']-s['friction_cost']-s['commission']-s['net_pnl'])<1e-6
    return s
