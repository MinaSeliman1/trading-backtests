from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from seasonal.analysis import bootstrap_mean,paired_tests,holm,random_clock_panel
from seasonal.engine import Config,prepare
from test_engine import market


def test_holm_is_step_down_and_preserves_names():
    assert holm({'QQQ':.01,'SPY':.04})=={'QQQ':.02,'SPY':.04}
    assert holm({'QQQ':.03,'SPY':.04})=={'QQQ':.06,'SPY':.06}


def test_bootstrap_centers_null_and_negative_edge_cannot_pass():
    positive=bootstrap_mean(np.full(30,.001),100,42);negative=bootstrap_mean(np.full(30,-.001),100,42)
    assert positive['blocks']['20']['mean_ci95'][0]>0 and positive['blocks']['20']['p_one_sided']<.05
    assert negative['blocks']['20']['p_one_sided']==1


def test_paired_comparison_excludes_either_unknown_day():
    a=SimpleNamespace(daily=pd.DataFrame(dict(date=['2020-01-02','2020-01-03','2020-01-06'],return_net=[.01,.02,.03],conditionally_excluded=[False,True,False])))
    b=SimpleNamespace(daily=pd.DataFrame(dict(date=['2020-01-02','2020-01-03','2020-01-06'],return_net=[0.,0.,0.],conditionally_excluded=[False,False,True])))
    v=paired_tests(a,{'control':b},100,42)['control']
    assert v['paired_sessions']==1 and v['mean_difference_bps']==pytest.approx(100.)


def test_random_clock_diagnostic_is_seeded_and_normalized():
    m=market(45);c=Config();f=prepare(m,c)
    a=random_clock_panel(m,f,c,repetitions=50);b=random_clock_panel(m,f,c,repetitions=50)
    assert a['summary']==b['summary'] and a['summary']['paired_signal_dates']==5
    assert len(a['draws'])==50 and a['summary']['capital_policy']=='constant 100000 USD each day; not compounded accounts'


def test_missing_calendar_days_are_not_bootstrapped_as_cash():
    from seasonal.analysis import observed_bootstrap
    u=observed_bootstrap([.01,np.nan,np.nan],100,42)
    assert u['observed_sessions']==1 and u['calendar_sessions']==3
    assert u['mean']==pytest.approx(.01)
    assert u['blocks']['20']['mean_ci95'][0]==pytest.approx(.01)


def test_all_unknown_calendar_sample_cannot_claim_positive_interval():
    from seasonal.analysis import observed_bootstrap
    u=observed_bootstrap([np.nan,np.nan],100,42)
    assert u['observed_sessions']==0 and not u['blocks'] and u['mean'] is None
