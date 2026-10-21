from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from vwap_reversion.data import merge_page
from test_engine import market


def record(m,vw=103,seconds=0):
    from pandas import Timestamp,Timedelta
    t=Timestamp(m.quality.iloc[-1].session_open)+Timedelta(seconds=seconds)
    return dict(t=t.tz_convert('UTC').isoformat(),o=100,h=101,l=99,c=100,v=1000,vw=vw)


def state(m):return np.zeros((21,390),dtype=bool),np.full((21,390),np.nan)


def test_merge_source_vwap_including_value_outside_ohlc():
    m=market();seen,vw=state(m)
    merge_page(m,[record(m)],seen,vw)
    assert seen[-1,0] and vw[-1,0]==103


def test_duplicate_same_vwap_is_ok_but_conflicting_value_is_refused():
    m=market();seen,vw=state(m);merge_page(m,[record(m)],seen,vw);merge_page(m,[record(m)],seen,vw)
    with pytest.raises(ValueError,match='conflict'):merge_page(m,[record(m,vw=104)],seen,vw)


def test_raw_ohlcv_must_reconcile_with_prepared_arrays():
    m=market();seen,vw=state(m);r=record(m);r['c']=100.01
    with pytest.raises(ValueError,match='OHLCV'):merge_page(m,[r],seen,vw)


def test_off_grid_timestamp_inside_session_is_refused():
    m=market();seen,vw=state(m)
    with pytest.raises(ValueError,match='grid'):merge_page(m,[record(m,seconds=1)],seen,vw)
