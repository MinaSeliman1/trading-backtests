from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest
from test_engine import market,run,bar
from vwap_reversion.engine import simulate,prepare,Config
from vwap_reversion.analysis import summarize


def test_net_costs_capital_and_exposure_reconcile():
    s=summarize(run(market()))
    assert s['net_pnl']==pytest.approx(2.2) and s['final_equity']==pytest.approx(1002.2)
    assert s['regular_time_exposure_upper_pct']==pytest.approx(329/390*100)
    assert s['conditional_historical_performance'] and not s['continuous_observed_portfolio']


def test_history_abstention_is_distinguished_from_unknown_current_day():
    m=market();r=simulate(m,prepare(m),Config(initial_capital=1000),str(m.dates[0].date()),str(m.dates[-1].date()));s=summarize(r)
    assert s['causal_history_abstention_sessions']==20 and s['data_excluded_sessions']==0 and s['trades']==1


def test_unresolved_trade_has_disclosed_omission_even_when_balance_flat():
    m=market();m.arrays['open'][-1,70]=np.nan;m.valid[-1]=False;s=summarize(run(m,quality='resolved_prefix'))
    assert s['unresolved_sessions']==1 and s['data_excluded_sessions']==1 and s['net_pnl']==0


def test_nextopen_exit_count_and_holding_mean_are_actual():
    m=market();bar(m,65,99.4,100.7,99.2,100.5,100);s=summarize(run(m))
    assert s['vwap_exit_count']==1 and s['holding_minutes_upper_mean']==6


def test_empty_period_is_not_reported_as_zero_performance():
    m=market();r=simulate(m,prepare(m),Config(),'2030-01-01','2030-01-02')
    with pytest.raises(ValueError,match='empty'):summarize(r)


def test_ablation_ranks_daily_returns_not_later_larger_dollar_pnl():
    r=run(market());rates=np.array([.10,.09,.08,.079]);equity=1000*np.cumprod(1+rates);pnl=equity-np.r_[1000,equity[:-1]]
    r.daily=pd.concat([r.daily]*4,ignore_index=True);r.trades=pd.concat([r.trades]*4,ignore_index=True)
    dates=pd.date_range('2024-05-01',periods=4).strftime('%Y-%m-%d')
    r.daily=r.daily.assign(date=dates,return_net=rates,net_pnl=pnl,equity=equity)
    r.trades=r.trades.assign(date=dates,net_pnl=pnl,price_move_pnl=pnl+r.trades.friction_cost+r.trades.commission+r.trades.borrow_fee)
    assert summarize(r)['return_without_top3_days_pct']==pytest.approx(7.9)
