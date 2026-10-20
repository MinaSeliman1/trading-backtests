from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from orb.engine import Config,UnresolvedExecution,opening_features,trade_path,simulate


def market(short=False,half=False):
    date='2024-11-29' if half else '2024-04-30';n=210 if half else 390
    a={k:np.full((1,390),v,dtype=float) for k,v in dict(open=100,high=100.2,low=99.8,close=100,volume=1000).items()}
    a['open'][0,:5]=100.5 if short else 99.5;a['high'][0,:5]=101 if short else 100.5;a['low'][0,:5]=99.5 if short else 99
    a['open'][0,n-1]=99 if short else 101
    a['high'][0,n-1]=100 if short else 102;a['low'][0,n-1]=98 if short else 100;a['close'][0,n-1]=99 if short else 101
    return SimpleNamespace(dates=pd.DatetimeIndex([date]),arrays=a,lengths=np.array([n]),valid=np.array([True]),symbol='QQQ',
        quality=pd.DataFrame([dict(reason='',session_open=str(pd.Timestamp(date+' 09:30',tz='America/New_York')),session_close=str(pd.Timestamp(date+(' 13:00' if half else ' 16:00'),tz='America/New_York')))]))


def run(m,**kwargs):return simulate(m,Config(initial_capital=1000,**kwargs),str(m.dates[0].date()),str(m.dates[-1].date()))


def setbar(m,j,o,h,l,c):
    for k,v in zip(('open','high','low','close'),(o,h,l,c)):m.arrays[k][0,j]=v


def test_signal_and_levels_use_only_first_five_finished_bars():
    m=market();f=opening_features(m).iloc[0]
    assert f.signal_sign==1 and f.sizing_price==100 and f.range_low==99 and f.range_high==100.5
    m.arrays['close'][0,9:]=np.nan
    g=opening_features(m).iloc[0]
    assert g.signal_sign==f.signal_sign and g.range_high==f.range_high and g.range_low==f.range_low


def test_flat_first_candle_does_not_generate_a_rounding_signal():
    m=market();m.arrays['close'][0,4]=99.5
    r=run(m);assert r.trades.empty and r.daily.iloc[0].net_pnl==0


def test_missing_opening_minute_blocks_trade():
    m=market();m.arrays['close'][0,2]=np.nan
    r=run(m);assert r.trades.empty and r.daily.iloc[0].eligibility=='invalid_opening_window'


def test_long_costs_and_last_minute_open_liquidation():
    r=run(market());t=r.trades.iloc[0]
    assert t.quantity==10 and t.entry_reference==100 and t.exit_reference==101
    assert t.commission==.7 and t.friction_cost==pytest.approx(.2) and t.borrow_fee==0
    assert t.net_pnl==pytest.approx(9.1) and t.exit_reason=='eod_open'
    assert pd.Timestamp(t.entry_time).strftime('%H:%M')=='09:35' and pd.Timestamp(t.exit_time).strftime('%H:%M')=='15:59'


def test_short_costs_include_one_day_borrow():
    t=run(market(short=True)).trades.iloc[0]
    assert t.sign==-1 and t.borrow_fee==pytest.approx(.027775) and t.net_pnl==pytest.approx(9.072225)


def test_quantity_uses_known_close_not_future_entry_open():
    m=market();setbar(m,5,102,102.2,101.8,102)
    t=run(m).trades.iloc[0]
    assert t.quantity==10 and t.entry_leverage==pytest.approx(1.02)
    assert t.entry_risk_pct==pytest.approx(3.) and t.target_price==132


def test_risk_budget_can_reduce_quantity_below_one_times_capital():
    m=market();m.arrays['low'][0,:5]=90
    assert run(m).trades.iloc[0].quantity==1


def test_entry_through_stop_is_costed_immediate_exit_not_removed():
    m=market();setbar(m,5,98,98.2,97.8,98)
    t=run(m).trades.iloc[0]
    assert t.exit_reason=='entry_marketable_stop' and t.entry_reference==t.exit_reference==98
    assert t.net_pnl==pytest.approx(-.9) and t.holding_minutes_upper==0


def test_gap_through_stop_fills_at_worse_observed_open():
    m=market();setbar(m,10,98,100,97,98)
    t=run(m).trades.iloc[0]
    assert t.exit_reference==98 and t.exit_reason=='stop_gap' and t.net_pnl==pytest.approx(-20.9)


def test_favorable_target_gap_gets_no_unobserved_price_improvement():
    m=market();setbar(m,10,112,113,111,112)
    t=run(m).trades.iloc[0]
    assert t.target_price==110 and t.exit_reference==110 and t.exit_reason=='target_gap'
    assert t.net_pnl==pytest.approx(99.1)


def test_same_bar_stop_target_defaults_to_stop_and_is_flagged():
    m=market();setbar(m,10,100,111,98,100)
    t=run(m).trades.iloc[0]
    assert t.ambiguous_bar and t.exit_reference==99 and t.net_pnl==pytest.approx(-10.9)


def test_target_priority_is_separate_execution_sensitivity():
    m=market();setbar(m,10,100,111,98,100)
    t=run(m,priority='target_first').trades.iloc[0]
    assert t.ambiguous_bar and t.exit_reference==110 and t.net_pnl==pytest.approx(99.1)


def test_open_is_ordered_before_intraminute_extremes():
    m=market();setbar(m,10,111,112,98,100)
    t=run(m).trades.iloc[0]
    assert t.exit_reference==110 and t.exit_reason=='target_gap' and not t.ambiguous_bar


def test_exit_bar_close_and_post_stop_extreme_do_not_create_drawdown():
    m=market();setbar(m,10,100,100.2,98,98)
    original=run(m);setbar(m,10,100,100.2,1,2)
    changed=run(m)
    assert changed.trades.iloc[0].net_pnl==pytest.approx(original.trades.iloc[0].net_pnl)
    assert changed.observed_close_drawdown_pct==pytest.approx(original.observed_close_drawdown_pct)


def test_half_day_exits_at_1259():
    t=run(market(half=True)).trades.iloc[0]
    assert pd.Timestamp(t.exit_time)==pd.Timestamp('2024-11-29 12:59',tz='America/New_York')


def test_complete_day_filter_is_explicitly_retrospective():
    m=market();m.valid[0]=False
    r=run(m)
    assert r.trades.empty and r.daily.iloc[0].eligibility=='excluded_incomplete_day'
    assert r.daily.iloc[0].conditionally_excluded and pd.isna(r.daily.iloc[0].observed_return)


def test_resolved_prefix_keeps_exit_before_later_missing_data():
    m=market();setbar(m,7,100,100.2,98,100);m.arrays['close'][0,100]=np.nan;m.valid[0]=False
    r=run(m,quality='resolved_prefix')
    assert len(r.trades)==1 and not r.daily.iloc[0].conditionally_excluded


def test_missing_active_bar_is_unresolved_not_an_observed_cash_return():
    m=market();m.arrays['close'][0,7]=np.nan;m.valid[0]=False
    r=run(m,quality='resolved_prefix')
    assert r.trades.empty and len(r.unresolved)==1
    assert r.daily.iloc[0].eligibility=='unresolved_execution' and pd.isna(r.daily.iloc[0].observed_return)


def test_missing_entry_open_is_never_shifted_to_a_later_fill():
    m=market();m.arrays['open'][0,5]=np.nan
    with pytest.raises(UnresolvedExecution):trade_path(m,0,1,10,Config())


def test_eod_fill_does_not_require_prices_after_eod_open():
    m=market();m.arrays['close'][0,389]=np.nan
    r=run(m,quality='resolved_prefix')
    assert r.trades.iloc[0].exit_reference==101


def test_all_data_after_resolved_exit_can_change_without_affecting_accounting():
    m=market();setbar(m,7,100,100.2,98,100)
    original=run(m,quality='resolved_prefix')
    for a in m.arrays.values():a[0,8:]=np.nan
    m.valid[0]=False
    changed=run(m,quality='resolved_prefix')
    pd.testing.assert_frame_equal(original.trades,changed.trades)
    pd.testing.assert_frame_equal(original.daily,changed.daily)
    assert changed.observed_close_drawdown_pct==original.observed_close_drawdown_pct


def test_unknown_whole_trade_omission_leaves_conditional_book_unchanged():
    m=market();m.arrays['close'][0,7]=np.nan;m.valid[0]=False
    r=run(m,quality='resolved_prefix');d=r.daily.iloc[0]
    assert d.equity==1000 and d.commission==0 and d.borrow_fee==0 and d.net_pnl==0
    assert r.unresolved.iloc[0].known_entry_commission==.35
    assert pd.isna(d.observed_return) and d.return_net==0


def test_observed_stop_at_open_resolves_without_later_fields_of_that_bar():
    m=market();setbar(m,10,98,np.nan,np.nan,np.nan);m.valid[0]=False
    t=run(m,quality='resolved_prefix').trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==98 and t.net_pnl==pytest.approx(-20.9)


@pytest.mark.parametrize('bar,priority,reference,net',[
    ((102,103,101.5,102),'stop_first',102,-20.927775),
    ((88,89,87,88),'stop_first',90,99.072225),
    ((100,102,89,100),'stop_first',101,-10.927775),
    ((100,102,89,100),'target_first',90,99.072225)])
def test_short_barrier_and_gap_symmetry_includes_borrow(bar,priority,reference,net):
    m=market(short=True);setbar(m,10,*bar)
    t=run(m,priority=priority).trades.iloc[0]
    assert t.exit_reference==reference and t.net_pnl==pytest.approx(net)


def test_short_entry_through_stop_still_pays_roundtrip_and_borrow():
    m=market(short=True);setbar(m,5,102,103,101.5,102)
    t=run(m).trades.iloc[0]
    assert t.exit_reason=='entry_marketable_stop' and t.net_pnl==pytest.approx(-.9283305555556)


def test_unreachable_nonpositive_short_target_never_fabricates_a_fill():
    m=market(short=True);m.arrays['high'][0,:5]=111
    r=simulate(m,Config(),'2024-04-30','2024-04-30');t=r.trades.iloc[0]
    assert t.target_price==-10 and t.exit_reason=='eod_open' and t.quantity==90


@pytest.mark.parametrize('mode,short,expected',[('long_only',True,0),('short_only',False,0),('inverse',False,-1)])
def test_direction_diagnostics_are_predefined(mode,short,expected):
    r=run(market(short=short),mode=mode)
    assert (int(r.trades.iloc[0].sign) if len(r.trades) else 0)==expected


@pytest.mark.parametrize('kwargs',[{'slippage':float('nan')},{'initial_capital':0},{'risk_budget':-1},{'priority':'best_after_fact'},{'quality':'pretend_complete'}])
def test_invalid_configuration_refused(kwargs):
    with pytest.raises(ValueError):Config(**kwargs)
