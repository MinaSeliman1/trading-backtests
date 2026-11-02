import pandas as pd
import pytest

def test_within_day_order_and_previous_peak_are_distinct():
 from qqq_eod.risk_marks import path_summary,extend_peak
 early=path_summary([100,80,120]);late=path_summary([100,120,80])
 assert early['within_drawdown_fraction']==pytest.approx(.2)
 assert late['within_drawdown_fraction']==pytest.approx(1/3)
 assert extend_peak(150,early)['max_drawdown_fraction']==pytest.approx(1-80/150)
 assert extend_peak(90,early)['max_drawdown_fraction']==pytest.approx(.2)

def test_noise_telemetry_includes_fees_then_closed_minute_equity():
 from qqq_eod.risk_marks import noise_path
 idx=pd.date_range('2026-10-30 10:00',periods=2,freq='min',tz='America/New_York');bars=pd.DataFrame({'open':[100.,101.],'close':[110.,101.]},index=idx)
 fills=[dict(action='open',timestamp=str(idx[0]),qty=10,sign=1,actual=100.,modeled=100.01,commission=.35,borrow=0,realized=0),dict(action='close',timestamp=str(idx[1]),qty=10,sign=-1,actual=101.,modeled=100.99,commission=.35,borrow=0,realized=9.8)]
 out=noise_path(bars,fills,1000)
 assert out['maximum']==pytest.approx(1099.55) and out['minimum']==pytest.approx(999.55)
 assert out['ending']==pytest.approx(1009.1)
 assert out['within_drawdown_fraction']==pytest.approx((1099.55-1009.1)/1099.55)
