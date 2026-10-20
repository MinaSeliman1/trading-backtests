import numpy as np
import pandas as pd
import pytest
from noise_area.statistics import return_statistics, block_bootstrap, timed_benchmarks


def test_compounding_drawdown_and_zero_sharpe_have_hand_checked_values():
    returns=np.array([.1,-.1,.1,-.1])
    result=return_statistics(returns,['2024-01-02','2024-01-03','2024-01-04','2024-01-05'])
    assert result['total_return_pct']==pytest.approx(-1.99)
    assert result['sharpe']==pytest.approx(0)
    assert result['max_daily_close_drawdown_pct']==pytest.approx(10.9)


def test_constant_positive_daily_returns_bootstrap_cannot_create_loss():
    b=block_bootstrap(np.full(20,.001),np.zeros(20),repetitions=100,seed=2)
    assert b['daily_mean_ci95']==pytest.approx([.001,.001])
    assert b['block_length']==5 and b['repetitions']==100


def test_random_control_and_always_long_keep_times_and_charge_two_sided_costs():
    trades=pd.DataFrame([dict(date='2024-01-02',entry_reference=100.,exit_reference=101.,opening_price=100.,target_leverage=1.,quantity=1000)])
    daily=pd.DataFrame([dict(date='2024-01-02',return_net=.00993,equity=100993.)])
    result=timed_benchmarks(trades,daily,slippage=0,borrow_rate=0,repetitions=1000,seed=1)
    assert result['always_long']['final_equity']==pytest.approx(100993.)
    assert sorted(set(result['random_final_equity']))==pytest.approx([98993.,100993.])
    assert len(result['random_final_equity'])==1000


def test_control_with_no_affordable_share_pays_no_order_commission():
    trades=pd.DataFrame([dict(date='2024-01-02',entry_reference=200000.,exit_reference=201000.,opening_price=200000.,target_leverage=1.,quantity=1)])
    daily=pd.DataFrame([dict(date='2024-01-02',return_net=0.,equity=100000.)])
    result=timed_benchmarks(trades,daily,slippage=0,borrow_rate=0,repetitions=10,seed=1)
    assert result['always_long']['final_equity']==100000.
    assert result['random_final_equity']==[100000.]*10
