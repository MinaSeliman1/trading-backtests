"""Prix égaux au tick malgré une unité d'erreur de représentation binaire."""
import math
import pandas as pd
import pytest
from fvg_backtest.engine import exit_fill, INSTRUMENTS, Config


def test_real_20230817_short_stop_touch_is_not_delayed_six_minutes():
    bar=pd.Series(dict(open=440.63,high=440.71,low=440.4199,close=440.42))
    stop=44071*.01  # 440.71000000000004 in binary floating point
    result=exit_fill(bar,-1,stop,439.27,INSTRUMENTS['SPY'],Config())
    assert result is not None and result[1]=='stop'


@pytest.mark.parametrize('direction,level_kind',[(1,'stop'),(-1,'stop'),(1,'target'),(-1,'target')])
def test_tick_boundary_touch_for_both_directions(direction,level_kind):
    level=100.01
    if level_kind=='stop':
        stop=math.nextafter(level,-math.inf if direction==1 else math.inf)
        target=105. if direction==1 else 95.
        bar=pd.Series(dict(open=101. if direction==1 else 99.,high=102. if direction==1 else level,
                           low=level if direction==1 else 98.,close=101. if direction==1 else 99.))
    else:
        stop=95. if direction==1 else 105.
        target=math.nextafter(level,math.inf if direction==1 else -math.inf)
        bar=pd.Series(dict(open=99. if direction==1 else 101.,high=level if direction==1 else 102.,
                           low=98. if direction==1 else level,close=99. if direction==1 else 101.))
    result=exit_fill(bar,direction,stop,target,INSTRUMENTS['SPY'],Config())
    assert result is not None and result[1]==level_kind


def test_subcent_gap_before_stop_is_not_a_touch():
    bar=pd.Series(dict(open=100.,high=100.00999,low=99.5,close=99.9))
    assert exit_fill(bar,-1,100.01,99.,INSTRUMENTS['SPY'],Config()) is None
