"""Conditional portfolio statistics; paired legs are not independent accounts."""
import numpy as np
import pandas as pd
from .data import source
from closing_momentum.analysis import return_statistics,drawdown_duration,ablation_return

def summarize(r):
 d,t,l=r.daily,r.trades,r.legs;s=return_statistics(d.return_net,d.date);s.update(drawdown_duration(d.return_net,d.date));g=t.loc[t.net_pnl>0,'net_pnl'];loss=t.loc[t.net_pnl<0,'net_pnl']
 s.update(initial_capital=r.initial_capital,final_equity=float(d.equity.iloc[-1]),net_pnl=float(t.net_pnl.sum()),pairs=len(t),leg_trades=len(l),win_rate_pct=float((t.net_pnl>0).mean()*100) if len(t) else None,
  profit_factor=float(g.sum()/-loss.sum()) if len(loss) else None,mean_pair_usd=float(t.net_pnl.mean()) if len(t) else None,
  observed_drawdown_pct=r.observed_drawdown_pct,observed_drawdown_usd=r.observed_drawdown_usd,data_excluded_sessions=int(d.conditionally_excluded.sum()),unresolved_sessions=len(r.unresolved),
  return_without_top3_days_pct=ablation_return(d.return_net,d.net_pnl),top3_positive_profit_share_pct=float(g.nlargest(3).sum()/g.sum()*100) if len(g) else None,
  simulated_rth_time_exposure_pct=float(d.holding_minutes.sum()/d.session_minutes.sum()*100),worst_pair_usd=float(t.net_pnl.min()) if len(t) else None,
  max_entry_leverage=float(t.entry_leverage.max()) if len(t) else None,max_entry_fill_leverage=float(t.entry_fill_leverage.max()) if len(t) else None,max_proxy_risk_pct=float(t.proxy_risk_pct.max()) if len(t) else None,
  conditional_historical_performance=True,blind_oos=False,independent_etf_accounts=False)
 for field in ['price_move_pnl','friction_cost','commission','borrow_fee']:s[field]=float(t[field].sum())
 for symbol in ['QQQ','SPY']:
  sl=l[l.symbol==symbol];s[symbol+'_net_contribution_usd']=float(sl.net_pnl.sum());s[symbol+'_net_contribution_initial_capital_pct']=float(sl.net_pnl.sum()/r.initial_capital*100)
 assert len(l)==2*len(t)
 assert abs(s['net_pnl']-l.net_pnl.sum())<1e-6 and abs(s['net_pnl']-d.net_pnl.sum())<1e-6
 assert abs(s['final_equity']-r.initial_capital-s['net_pnl'])<1e-6
 assert abs(s['price_move_pnl']-s['friction_cost']-s['commission']-s['borrow_fee']-s['net_pnl'])<1e-6
 return s

def uncertainty(r,repetitions=3000,seed=20261031):
 x=r.daily.return_net.to_numpy();n=len(x);rng=np.random.default_rng(seed);blocks={}
 for b in [5,20]:
  starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/b))));indices=((starts[:,:,None]+np.arange(b))%n).reshape(repetitions,-1)[:,:n]
  blocks[str(b)]=dict(conditional_daily_mean_ci95=np.quantile(x[indices].mean(axis=1),[.025,.975]).tolist())
 return dict(repetitions=repetitions,seed=seed,blocks=blocks,caveat='Conditional bookkeeping returns, unknown days at zero; reused history, no correction across prior hypotheses. Not a guaranteed edge.')
