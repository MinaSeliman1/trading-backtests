from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from closing_momentum.engine import Config,prepare,simulate
from closing_momentum.analysis import summarize,ablation_return,uncertainty,drawdown_duration
from test_engine import market,run


def test_metrics_reconcile_real_capital_and_costed_trade():
    s=summarize(run(market()))
    assert s['final_equity']==pytest.approx(1009.1) and s['total_return_pct']==pytest.approx(.91)
    assert s['net_pnl']==pytest.approx(9.1) and s['friction_cost']==pytest.approx(.2)
    assert s['regular_time_exposure_pct']==pytest.approx(29/390*100)


def test_no_trade_is_zero_performance_and_missing_win_rate():
    m=market();m.arrays['close'][1,:30]=99
    s=summarize(run(m,mode='long_only'))
    assert s['net_pnl']==0 and s['win_rate_pct'] is None and s['trades']==0


def test_empty_period_fails_instead_of_showing_zero_results():
    m=market();r=simulate(m,prepare(m,{}),Config(),'2030-01-01','2030-12-31')
    with pytest.raises(ValueError,match='empty'):summarize(r)


def test_top_three_ablation_removes_positive_days_without_changing_other_returns():
    assert ablation_return([.1,.2,-.1,.05],[10,20,-10,5])==pytest.approx(-10)


def test_recovered_intraday_drawdown_does_not_become_daily_drawdown():
    m=market();m.arrays['close'][1,370]=90;m.arrays['low'][1,370]=89
    s=summarize(run(m))
    assert s['max_daily_close_drawdown_pct']==0 and s['observed_close_drawdown_pct']>10


def test_paired_blocks_keep_identical_benchmark_difference_zero():
    dates=pd.bdate_range('2024-05-01',periods=45).strftime('%Y-%m-%d')
    daily=pd.DataFrame(dict(date=dates,return_net=np.full(45,.001)))
    trades=pd.DataFrame(dict(date=dates,net_bps=np.full(45,10.)))
    r=SimpleNamespace(daily=daily,trades=trades)
    u=uncertainty(r,r,repetitions=100)
    for block in ['5','20']:
        assert u['paired_blocks'][block]['daily_mean_ci95']==pytest.approx([.001,.001])
        assert u['paired_blocks'][block]['mean_minus_long_ci95']==pytest.approx([0,0])


def test_annual_uncertainty_retains_years_without_trades_and_does_not_fake_confidence():
    daily=pd.DataFrame(dict(date=['2024-12-31','2025-01-02'],return_net=[0.,0.]))
    r=SimpleNamespace(daily=daily,trades=pd.DataFrame(columns=['date','net_bps']))
    u=uncertainty(r,r,repetitions=100)
    assert u['annual_cluster']['years']==[2024,2025]
    assert u['annual_cluster']['mean_trade_bps_ci95'] is None


@pytest.mark.parametrize('returns,dates,want,recovered',[
    ([0,0,0],['2024-01-02','2024-01-03','2024-01-04'],0,True),
    ([.1,0,-.1,0,.2],['2024-01-02','2024-01-03','2024-01-04','2024-01-05','2024-01-08'],5,True),
    ([.1,0,-.1,0],['2024-01-02','2024-01-03','2024-01-04','2024-01-05'],2,False)])
def test_duration_starts_at_latest_repeated_peak_or_is_zero_when_no_loss(returns,dates,want,recovered):
    result=drawdown_duration(returns,dates)
    assert result['worst_drawdown_duration_calendar_days']==want
    assert result['worst_drawdown_recovered']==recovered
