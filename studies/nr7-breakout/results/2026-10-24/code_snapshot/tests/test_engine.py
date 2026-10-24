from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from nr7.engine import Config,prepare,simulate


def market(short=False,half=False):
    dates=pd.bdate_range('2024-04-19',periods=8);n=210 if half else 390
    a={k:np.full((8,390),100.,dtype=float) for k in ('open','high','low','close')};a['volume']=np.full((8,390),1000.)
    for i,width in enumerate((8,7,6,5,4,3,2)):
        a['high'][i]=100+width/2;a['low'][i]=100-width/2
    a['high'][7]=100.5;a['low'][7]=99.5
    sign=-1 if short else 1
    for k in ('open','high','low','close'):a[k][7,11:]=100+sign*1.6
    a['close'][7,10]=100+sign*1.5;a['high' if sign>0 else 'low'][7,10]=100+sign*1.6
    for k in ('open','high','low','close'):a[k][7,n-1]=100+sign*2
    q=pd.DataFrame({'session_open':[str(d.tz_localize('America/New_York')+pd.Timedelta(hours=9,minutes=30)) for d in dates]})
    return SimpleNamespace(dates=dates,arrays=a,lengths=np.array([390]*7+[n]),valid=np.ones(8,dtype=bool),quality=q,symbol='QQQ')


def run(m,cfg=None,cash=None):
    return simulate(m,prepare(m,cash or {}),cfg or Config(initial_capital=1000),str(m.dates[-1].date()),str(m.dates[-1].date()))


def test_long_next_open_sizing_and_costs():
    r=run(market());t=r.trades.iloc[0]
    assert t.signal_slot==10 and t.entry_slot==11 and t.quantity==4
    assert t.entry_reference==101.6 and t.exit_reference==102
    assert t.net_pnl==pytest.approx(.82) and t.commission==.7 and t.friction_cost==.08


def test_short_borrow():
    t=run(market(True)).trades.iloc[0]
    assert t.borrow_fee==pytest.approx(4*98.39*.01/360)
    assert t.net_pnl==pytest.approx(.82-t.borrow_fee)


def test_equal_range_is_not_nr7_and_reference_still_trades():
    m=market();m.arrays['high'][6]=101.5;m.arrays['low'][6]=98.5
    assert run(m).trades.empty
    assert len(run(m,Config(initial_capital=1000,require_nr7=False)).trades)==1


def test_invalid_previous_session_is_not_replaced():
    m=market();m.valid[2]=False
    r=run(m);assert r.trades.empty and r.daily.iloc[0].eligibility=='invalid_prior7'


def test_touch_without_close_does_not_signal():
    m=market();m.arrays['high'][7,:10]=105
    assert run(m).trades.iloc[0].signal_slot==10


def test_current_ex_dividend_translates_both_limits():
    m=market();f=prepare(m,{str(m.dates[-1].date()):.5}).iloc[-1]
    assert f.prior_high==100.5 and f.prior_low==98.5


@pytest.mark.parametrize('opening,low,reason,ref',[(98,97,'entry_marketable_stop',98),(100,98,'stop_intrabar',99)])
def test_entry_gap_or_stop_never_omits_cost(opening,low,reason,ref):
    m=market();a=m.arrays
    for k,v in dict(open=opening,high=102,low=low,close=100).items():a[k][7,11]=v
    t=run(m).trades.iloc[0]
    assert t.quantity==4 and t.exit_reason==reason and t.exit_reference==ref
    assert t.net_pnl==pytest.approx(4*(ref-opening)-.78)
    assert t.entry_risk_pct>=0


def test_future_after_exit_cannot_change_resolved_trade():
    m=market();m.arrays['low'][7,11]=98
    t=run(m,Config(initial_capital=1000,quality='resolved_prefix')).trades.iloc[0]
    for k in m.arrays:m.arrays[k][7,12:]=np.nan
    m.valid[7]=False
    z=run(m,Config(initial_capital=1000,quality='resolved_prefix')).trades.iloc[0]
    assert z.net_pnl==t.net_pnl and z.quantity==t.quantity
    assert run(m).trades.empty


def test_missing_before_signal_is_unknown_not_observed_cash():
    m=market();m.arrays['close'][7,1]=np.nan;m.valid[7]=False
    r=run(m,Config(initial_capital=1000,quality='resolved_prefix'))
    assert r.trades.empty and np.isnan(r.daily.iloc[0].observed_return)


def test_missing_active_price_records_unresolved_intent_and_known_fee():
    m=market();m.arrays['open'][7,20]=np.nan;m.valid[7]=False
    r=run(m,Config(initial_capital=1000,quality='resolved_prefix'))
    assert r.trades.empty and len(r.unresolved)==1
    assert r.unresolved.iloc[0].known_entry_commission==.35
    assert np.isnan(r.daily.iloc[0].observed_return)


def test_half_day_and_no_final_minute_entry():
    m=market(half=True);t=run(m).trades.iloc[0]
    assert t.exit_slot==209 and t.exit_time.endswith('12:59:00-04:00')
    for k,v in dict(open=100,high=100.5,low=99.5,close=100).items():m.arrays[k][7,:]=v
    m.arrays['close'][7,208]=102;m.arrays['high'][7,208]=102
    assert run(m).trades.empty


@pytest.mark.parametrize('slip',[.01,.02,.03,.05])
def test_friction_stress_is_applied_to_both_sides(slip):
    t=run(market(),Config(initial_capital=1000,slippage=slip)).trades.iloc[0]
    assert t.net_pnl==pytest.approx(4*.4-8*slip-.7)
