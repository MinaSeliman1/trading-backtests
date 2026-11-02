import numpy as np
import pandas as pd
import pytest
from qqq_eod.schedule import calendar

def dates():return calendar('2026-01-05','2026-02-13').sessions_in_range('2026-01-05','2026-02-13')

def test_blocks_never_bridge_an_exclusion_or_missing_session():
 from qqq_eod.calibration import valid_blocks
 d=dates();good=np.ones(len(d),dtype=bool);good[5]=False;b=valid_blocks(d,good,5)
 assert not any(5 in row for row in b) and any(np.array_equal(row,[6,7,8,9,10]) for row in b)
 removed=d.delete(8);b=valid_blocks(removed,np.ones(len(removed),dtype=bool),5)
 assert not any(7 in row and 8 in row for row in b)

def test_constant_returns_have_exact_compounded_bands_and_keep_no_trade_days():
 from qqq_eod.calibration import bootstrap_bands
 d=dates();r=np.full(len(d),.01);out=bootstrap_bands(d,r,np.ones(len(d),bool),replications=100,seed=1)
 for horizon in (20,60):
  expected=100000*(1.01**horizon-1)
  for value in out['bands'][str(horizon)].values():assert value==pytest.approx(expected)
 zero=bootstrap_bands(d,np.zeros(len(d)),np.ones(len(d),bool),replications=100,seed=1)
 assert zero['bands']['20']['p05']==0 and zero['eligible_sessions']==len(d)

def test_seed_reproduces_the_same_distribution_without_global_rng():
 from qqq_eod.calibration import bootstrap_bands
 d=dates();r=np.linspace(-.02,.025,len(d));kwargs=dict(replications=200,seed=20261101)
 a=bootstrap_bands(d,r,np.ones(len(d),bool),**kwargs);np.random.seed(123);b=bootstrap_bands(d,r,np.ones(len(d),bool),**kwargs)
 assert a==b and a['bands']['20']['p05']<a['bands']['20']['p95']

def test_bad_eligible_return_and_insufficient_blocks_are_refused():
 from qqq_eod.calibration import bootstrap_bands
 d=dates();r=np.zeros(len(d));r[3]=np.nan
 with pytest.raises(ValueError):bootstrap_bands(d,r,np.ones(len(d),bool))
 with pytest.raises(ValueError):bootstrap_bands(d,np.zeros(len(d)),np.zeros(len(d),bool))
