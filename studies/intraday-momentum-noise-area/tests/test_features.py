from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from noise_area.features import compute_features, desired_position


def market_fixture(days=25):
    dates=pd.bdate_range('2024-01-02',periods=days)
    close=np.full((days,390),100.0)
    for i in range(days): close[i,:]=100+i*.1
    return SimpleNamespace(dates=dates,arrays=dict(open=np.full_like(close,100.),high=close+1,low=close-1,close=close,volume=np.ones_like(close)),valid=np.ones(days,dtype=bool),lengths=np.full(days,390),symbol='SPY')


def test_band_is_mean_of_previous_14_clocks_and_excludes_current_and_future():
    m=market_fixture(); f=compute_features(m,{})
    assert np.isnan(f['sigma'][13,29])
    assert f['sigma'][14,29]==pytest.approx(.0065)
    m.arrays['close'][14:,:]=500
    g=compute_features(m,{})
    np.testing.assert_allclose(f['sigma'][:15],g['sigma'][:15],equal_nan=True)
    np.testing.assert_allclose(f['volatility'][:15],g['volatility'][:15],equal_nan=True)


def test_volatility_includes_yesterday_but_not_todays_close():
    m=market_fixture(20)
    m.arrays['close'][:16,-1]=np.array([100,101,99,102,98,103,97,104,96,105,95,106,94,107,93,108])
    f=compute_features(m,{})
    prior=np.array([101/100-1,99/101-1,102/99-1,98/102-1,103/98-1,97/103-1,104/97-1,96/104-1,105/96-1,95/105-1,106/95-1,94/106-1,107/94-1,93/107-1])
    assert f['volatility'][15]==pytest.approx(prior.std(ddof=1))
    m.arrays['close'][15:,-1]=10000
    assert compute_features(m,{})['volatility'][15]==pytest.approx(f['volatility'][15])


def test_vwap_uses_only_finished_minutes_and_restarts_each_day():
    m=market_fixture();m.arrays['volume'][15,:2]=[1,3]
    m.arrays['high'][15,:2]=[105,111];m.arrays['low'][15,:2]=[99,105];m.arrays['close'][15,:2]=[102,108]
    f=compute_features(m,{})
    assert f['vwap'][15,1]==106.5
    m.arrays['high'][15,2:]=100000
    assert compute_features(m,{})['vwap'][15,1]==106.5


def test_dividend_changes_only_previous_close_reference_not_minute_prices():
    m=market_fixture();f=compute_features(m,{str(m.dates[15].date()):2.})
    assert f['previous_close_adjusted'][15]==pytest.approx(99.4)
    assert m.arrays['open'][15,0]==100
    assert f['upper'][15,29]==pytest.approx(100*(1+f['sigma'][15,29]))


def test_short_session_does_not_insert_zero_moves_after_1300():
    m=market_fixture();m.lengths[5]=210
    for values in m.arrays.values(): values[5,210:]=np.nan
    f=compute_features(m,{})
    assert np.isnan(f['sigma'][14,300])
    assert f['sigma'][15,300]==pytest.approx((sum(i*.001 for i in range(15))-.005)/14)


def test_excluded_day_does_not_enter_band_history():
    m=market_fixture();m.valid[5]=False;m.arrays['close'][5,:]=100000
    f=compute_features(m,{})
    assert np.isnan(f['sigma'][14,29])
    assert f['sigma'][15,29]==pytest.approx((.105-.005)/14)


@pytest.mark.parametrize('position,price,ub,lb,vwap,stop,want',[
    (0,105,104,98,106,'combined',0),
    (0,105,104,98,103,'combined',1),
    (0,97,104,98,99,'combined',-1),
    (1,104,104,98,103,'combined',1),
    (1,103.5,104,98,103,'combined',0),
    (-1,98,104,98,99,'combined',-1),
    (1,97,104,98,99,'combined',-1),
    (1,103.5,104,98,103,'vwap',1),
    (1,104.5,104,98,105,'band',1),
])
def test_strict_entry_filter_stop_equality_and_immediate_reversal(position,price,ub,lb,vwap,stop,want):
    assert desired_position(position,price,ub,lb,vwap,stop)==want
