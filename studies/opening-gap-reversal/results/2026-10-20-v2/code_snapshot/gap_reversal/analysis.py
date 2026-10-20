from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'intraday-momentum-noise-area'))
from noise_area.statistics import return_statistics


def annual_bootstrap(trades,dates,repetitions=5000,seed=20261020):
    years=sorted(pd.DatetimeIndex(dates).year.unique().tolist())
    groups=pd.DatetimeIndex(trades.date).year if len(trades) else np.array([],dtype=int)
    sums=np.array([trades.loc[groups==year,'net_bps'].sum() for year in years])
    counts=np.array([int(np.sum(groups==year)) for year in years])
    rng=np.random.default_rng(seed);indices=rng.integers(0,len(years),size=(repetitions,len(years)))
    denominators=counts[indices].sum(axis=1);valid=denominators>0
    means=sums[indices].sum(axis=1)[valid]/denominators[valid]
    return dict(method='Resample entire calendar years, ratio of total trade bps to total events; zero-event years retained',
        years=years,events_by_year=counts.tolist(),repetitions=repetitions,valid_repetitions=int(valid.sum()),seed=seed,
        mean_trade_bps_ci95=np.quantile(means,[.025,.975]).tolist() if len(means) else None,
        caveat='Descriptive and fragile with few year clusters, especially three partial/complete years in B; not proof of an edge.')


def summarize(result):
    d=result.daily;t=result.trades
    if d.empty:raise ValueError('empty period')
    stats=return_statistics(d.return_net,d.date)
    gains=t.loc[t.net_pnl>0,'net_pnl'];losses=t.loc[t.net_pnl<0,'net_pnl']
    r=d.return_net.to_numpy();top=d.nlargest(min(3,int(d.trades.sum())),'net_pnl').index
    stripped=r.copy();stripped[top]=0
    no2020=r.copy();no2020[d.date.str.startswith('2020').to_numpy()]=0
    stats.update(trades=len(t),net_pnl=float(t.net_pnl.sum()),win_rate_pct=float(len(gains)/len(t)*100) if len(t) else None,
        profit_factor=float(gains.sum()/-losses.sum()) if len(losses) else None,
        mean_trade_bps=float(t.net_bps.mean()) if len(t) else None,median_trade_bps=float(t.net_bps.median()) if len(t) else None,
        price_move_pnl=float(t.price_move_pnl.sum()),friction_cost=float(t.friction_cost.sum()),commission=float(t.commission.sum()),borrow_fee=float(t.borrow_fee.sum()),
        observed_close_drawdown_pct=result.observed_close_drawdown_pct,observed_close_drawdown_usd=result.observed_close_drawdown_usd,
        days_with_position_pct=float(d.trades.mean()*100),regular_time_exposure_pct=float(d.trades.sum()*29/d.session_minutes.sum()*100),
        mean_actual_entry_leverage=float(t.entry_leverage.mean()) if len(t) else None,max_actual_entry_leverage=float(t.entry_leverage.max()) if len(t) else None,
        incomplete_day_trades=int((~t.complete_day).sum()) if len(t) else 0,trades_with_missing_holding_minutes=int((t.missing_holding_minutes>0).sum()),
        return_without_top3_days_pct=float((np.prod(1+stripped)-1)*100),return_without_2020_pct=float((np.prod(1+no2020)-1)*100),
        top3_positive_profit_share_pct=float(gains.nlargest(3).sum()/gains.sum()*100) if len(gains) else None,
        worst_trade_usd=float(t.net_pnl.min()) if len(t) else None,worst_observed_mae_usd=float(t.mae_observed_usd.min()) if len(t) else None,
        excluded_sessions=int((d.eligibility!='eligible').sum()),cash_return_pct=0.)
    assert abs(stats['final_equity']-(100000+stats['net_pnl']))<1e-6
    return stats
