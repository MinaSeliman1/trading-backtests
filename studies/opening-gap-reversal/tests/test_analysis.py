from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from gap_reversal.analysis import annual_bootstrap,summarize
from gap_reversal.engine import Config,prepare,simulate
from test_engine import market


def test_annual_bootstrap_keeps_whole_years_and_zero_event_years():
    t=pd.DataFrame(dict(date=['2020-01-02','2020-01-03','2021-01-04'],net_bps=[100.,100.,-50.]))
    dates=['2020-01-02','2021-01-04','2022-01-03']
    x=annual_bootstrap(t,dates,repetitions=1000)
    assert x['years']==[2020,2021,2022] and x['events_by_year']==[2,1,0]
    assert x['mean_trade_bps_ci95'][0]>=-50 and x['mean_trade_bps_ci95'][1]<=100
    assert x==annual_bootstrap(t,dates,repetitions=1000)


def test_no_trade_summary_has_cash_return_and_no_false_win_rate():
    m=market();m.arrays['open'][1,0]=100.;m.arrays['low'][1,0]=100.
    r=simulate(m,prepare(m,{}),Config(),'2026-01-05','2026-01-06')
    x=summarize(r)
    assert x['trades']==0 and x['net_pnl']==0 and x['total_return_pct']==0 and x['win_rate_pct'] is None
    assert annual_bootstrap(r.trades,r.daily.date)['mean_trade_bps_ci95'] is None


def test_summary_reconciles_costs_and_observed_drawdown():
    m=market();r=simulate(m,prepare(m,{}),Config(),'2026-01-05','2026-01-06');x=summarize(r)
    assert x['net_pnl']==r.trades.net_pnl.sum()
    assert np.isclose(x['net_pnl'],x['price_move_pnl']-x['friction_cost']-x['commission']-x['borrow_fee'])
    assert x['observed_close_drawdown_pct']>=x['max_daily_close_drawdown_pct']


def test_exposure_uses_actual_regular_minutes_on_half_day():
    m=market();m.lengths[1]=210
    r=simulate(m,prepare(m,{}),Config(),'2026-01-05','2026-01-05')
    assert np.isclose(summarize(r)['regular_time_exposure_pct'],29/210*100)


def test_drawdown_duration_starts_at_last_plateau_before_loss():
    from gap_reversal.analysis import drawdown_duration
    dates=pd.date_range('2026-01-01',periods=4)
    x=drawdown_duration([0.,0.,-.1,0.],dates)
    assert x['worst_drawdown_duration_calendar_days']==2 and not x['worst_drawdown_recovered']
    assert drawdown_duration([0.,0.],dates[:2])['worst_drawdown_duration_calendar_days']==0
