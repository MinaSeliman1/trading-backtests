import numpy as np
import pandas as pd
from fvg_backtest.report import metrics, bootstrap_sessions, split_sessions, export_run
from fvg_backtest.engine import Config, INSTRUMENTS, run
from tests.test_engine import session


def test_metrics_include_initial_capital_and_net_losses():
    t=pd.DataFrame({"net_pnl":[-100.,200.,-50.],"result_r":[-1.,2.,-.5],
                    "initial_risk_usd":[100.,100.,100.],"risk_fraction":[.001]*3,
                    "planned_loss_usd":[105.]*3,"exposure_usd":[10000.]*3,
                    "duration_minutes":[1.,2.,3.],"fees":[1.,1.,1.]})
    e=pd.DataFrame({"equity":[99900.,100100.,100050.]})
    m=metrics(t,e,Config(),10)
    assert m["net_pnl"]==50.
    assert m["max_drawdown_usd"]==100.
    assert m["profit_factor"]==200/150
    assert m["expectancy_r"]==.5/3
    assert m["win_rate"]==1/3


def test_empty_no_fake_profit_factor_and_degenerate_bootstrap():
    m=metrics(pd.DataFrame(),pd.DataFrame(),Config(),0)
    assert m["trades"]==0 and m["profit_factor"] is None
    assert bootstrap_sessions(pd.DataFrame(),["2025-01-02"])["status"]=="insufficient"


def test_chronological_split_and_short_history():
    sessions=[session("2025-03-10") for _ in range(300)]
    assert list(split_sessions(sessions,span_days=400))==["IS","OOS"]
    assert len(split_sessions(sessions,span_days=400)["IS"])==210
    assert list(split_sessions(sessions[:6],span_days=8))==["exploratoire"]


def test_export_artifacts_on_controlled_fixture(tmp_path):
    s=session(); t,e,r=run([s],INSTRUMENTS["SPY"],Config())
    summary=export_run(tmp_path,t,e,r,[s],Config(),"fixture_artificielle",bootstrap_reps=20)
    assert (tmp_path/"trades.csv").exists()
    assert (tmp_path/"diagnostics.png").exists()
    assert summary["trades"]==1


def test_bootstrap_reproducible_grouped_sessions():
    dates=pd.date_range("2025-01-01",periods=80).strftime("%Y-%m-%d").tolist()
    t=pd.DataFrame({"date":dates[::2],"result_r":[1.]*40})
    a=bootstrap_sessions(t,dates,reps=100,block=5)
    b=bootstrap_sessions(t,dates,reps=100,block=5)
    assert a==b and a["expectancy_r_ci95"]==[1.,1.]
