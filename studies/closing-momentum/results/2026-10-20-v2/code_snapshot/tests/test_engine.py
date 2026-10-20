from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from closing_momentum.engine import Config,prepare,simulate


def market(half=False):
    dates=pd.DatetimeIndex(['2024-11-27','2024-11-29'] if half else ['2024-04-29','2024-04-30'])
    lengths=np.array([390,210 if half else 390])
    arrays={k:np.full((2,390),v,dtype=float) for k,v in dict(open=100,high=102,low=98,close=100,volume=1000).items()}
    arrays['close'][1,:30]=101
    arrays['open'][1,lengths[1]-1]=101
    quality=pd.DataFrame([dict(reason='',session_open=str(pd.Timestamp(str(d.date())+' 09:30',tz='America/New_York')),
        session_close=str(pd.Timestamp(str(d.date())+(' 13:00' if i==1 and half else ' 16:00'),tz='America/New_York'))) for i,d in enumerate(dates)])
    return SimpleNamespace(dates=dates,arrays=arrays,lengths=lengths,valid=np.array([True,True]),quality=quality,symbol='QQQ')


def run(m,**kwargs):
    return simulate(m,prepare(m,{}),Config(initial_capital=1000,**kwargs),str(m.dates[1].date()),str(m.dates[1].date()))


def test_morning_signal_includes_overnight_even_when_open_to_morning_is_flat():
    m=market();m.arrays['open'][1,:30]=101
    row=prepare(m,{}).iloc[1]
    assert row.signal_sign==1 and row.morning_return==pytest.approx(.01)


def test_exact_ex_dividend_cancellation_produces_no_trade():
    m=market();m.arrays['close'][1,:30]=99.8
    p=prepare(m,{'2024-04-30':.2});assert p.iloc[1].signal_sign==0
    r=simulate(m,p,Config(initial_capital=1000),'2024-04-30','2024-04-30')
    assert r.trades.empty and r.daily.iloc[0].net_pnl==0


def test_missing_morning_bar_blocks_entry_but_missing_midday_bar_does_not():
    m=market();m.arrays['close'][1,150]=np.nan;m.valid[1]=False
    assert prepare(m,{}).iloc[1].eligibility=='eligible'
    m.arrays['close'][1,12]=np.nan
    assert prepare(m,{}).iloc[1].eligibility=='invalid_morning_window'


def test_missing_immediate_previous_close_is_never_replaced():
    m=market();m.arrays['close'][0,389]=np.nan
    assert prepare(m,{}).iloc[1].eligibility=='invalid_previous_close'


def test_future_mutation_cannot_change_signal_or_entry_eligibility():
    m=market();before=prepare(m,{}).iloc[1]
    m.arrays['close'][1,380:]=np.nan;m.valid[1]=False
    after=prepare(m,{}).iloc[1]
    assert after.signal_sign==before.signal_sign and after.morning_return==before.morning_return
    assert after.eligibility==before.eligibility=='eligible'


def test_sizing_uses_finished_pre_entry_minute_not_entry_or_future_close():
    m=market();m.arrays['close'][1,359]=125;m.arrays['high'][1,359]=126
    r=run(m);t=r.trades.iloc[0]
    assert t.quantity==8 and t.entry_reference==100 and t.exit_reference==101
    assert t.net_pnl==pytest.approx(7.14)


def test_long_roundtrip_costs_are_charged_once_per_side():
    t=run(market()).trades.iloc[0]
    assert t.quantity==10 and t.entry_price==100.01 and t.exit_price==100.99
    assert t.friction_cost==pytest.approx(.2) and t.commission==.7 and t.borrow_fee==0
    assert t.net_pnl==pytest.approx(9.1) and t.equity_after==pytest.approx(1009.1)


def test_short_roundtrip_has_adverse_fills_and_one_day_borrow():
    m=market();m.arrays['close'][1,:30]=99;m.arrays['open'][1,389]=99
    t=run(m).trades.iloc[0]
    assert t.sign==-1 and t.entry_price==99.99 and t.exit_price==99.01
    assert t.borrow_fee==pytest.approx(.027775) and t.net_pnl==pytest.approx(9.072225)


def test_half_session_uses_1230_to_1259_in_correct_timezone():
    t=run(market(half=True)).trades.iloc[0]
    assert pd.Timestamp(t.entry_time)==pd.Timestamp('2024-11-29 12:30',tz='America/New_York')
    assert pd.Timestamp(t.exit_time)==pd.Timestamp('2024-11-29 12:59',tz='America/New_York')


def test_missing_exit_raises_instead_of_inventing_flat_performance():
    m=market();m.arrays['open'][1,389]=np.nan
    with pytest.raises(ValueError,match='unresolved exit'):run(m)


def test_holding_gap_keeps_trade_but_flags_incomplete_minute_drawdown():
    m=market();m.arrays['close'][1,370]=np.nan
    r=run(m)
    assert len(r.trades)==1 and r.trades.iloc[0].missing_holding_minutes==1


def test_intraday_loss_recovery_still_has_observed_drawdown():
    m=market();m.arrays['close'][1,370]=90;m.arrays['low'][1,370]=89
    r=run(m)
    assert r.daily.iloc[0].net_pnl>0 and r.observed_close_drawdown_pct>10


def test_long_only_skips_negative_signal_without_costs():
    m=market();m.arrays['close'][1,:30]=99
    r=run(m,mode='long_only')
    assert r.trades.empty and r.daily.iloc[0].commission==0


def test_reference_inherits_exact_quantity_instead_of_own_equity_sizing():
    m=market();p=prepare(m,{})
    r=simulate(m,p,Config(initial_capital=1000,mode='always_long'),'2024-04-30','2024-04-30',fixed_quantities={'2024-04-30':7})
    assert r.trades.iloc[0].quantity==7 and r.trades.iloc[0].net_pnl==pytest.approx(6.16)


def test_ambiguous_source_is_not_silently_resolved():
    m=market();m.quality.loc[1,'reason']='conflicting_duplicates'
    with pytest.raises(ValueError,match='ambiguous'):prepare(m,{})


@pytest.mark.parametrize('kwargs',[{'slippage':float('nan')},{'initial_capital':float('inf')},{'borrow_rate':-.01},{'mode':'best_after_inspection'}])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):Config(**kwargs)
