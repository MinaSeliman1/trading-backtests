from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from orb.analysis import summarize,uncertainty
from test_engine import market,run,setbar


def test_summary_reconciles_costs_and_variable_holding_exposure():
    r=run(market());s=summarize(r)
    assert s['net_pnl']==pytest.approx(9.1) and s['final_equity']==pytest.approx(1009.1)
    assert s['regular_time_exposure_upper_pct']==pytest.approx(384/390*100)
    assert s['conditional_historical_performance'] and s['data_excluded_sessions']==0


def test_unresolved_day_is_disclosed_even_when_conditional_book_is_flat():
    m=market();m.arrays['close'][0,7]=np.nan;m.valid[0]=False
    s=summarize(run(m,quality='resolved_prefix'))
    assert s['data_excluded_sessions']==1 and s['unresolved_sessions']==1 and s['trades']==0
    assert s['net_pnl']==0 and not s['continuous_observed_portfolio']


def test_intrabarrier_exit_does_not_claim_exact_holding_minutes():
    m=market();setbar(m,10,100,100.2,98,100)
    s=summarize(run(m))
    assert s['holding_minutes_upper_mean']==6 and s['intrabar_exit_count']==1


def test_empty_period_cannot_be_reported_as_zero_profit():
    from orb.engine import simulate,Config
    r=simulate(market(),Config(),'2030-01-01','2030-01-02')
    with pytest.raises(ValueError,match='empty'):summarize(r)


def test_constant_returns_produce_degenerate_block_interval_but_no_trade_year_certainty():
    d=pd.DataFrame(dict(date=pd.bdate_range('2024-05-01',periods=25).strftime('%Y-%m-%d'),return_net=np.full(25,.001)))
    r=SimpleNamespace(daily=d,trades=pd.DataFrame(columns=['date','net_bps']))
    u=uncertainty(r,repetitions=100)
    assert u['blocks']['5']['conditional_daily_mean_ci95']==pytest.approx([.001,.001])
    assert u['annual_cluster']['mean_trade_bps_ci95'] is None
