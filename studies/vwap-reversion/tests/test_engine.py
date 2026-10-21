from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from vwap_reversion.engine import Config,UnresolvedExecution,prepare,trace,simulate


def market(short=False,half=False):
    dates=pd.bdate_range('2024-04-01',periods=21);dates=pd.DatetimeIndex([*dates[:-1],pd.Timestamp('2024-11-29')]) if half else dates
    a={k:np.full((21,390),x,dtype=float) for k,x in dict(open=100,high=101,low=99,close=100,volume=1000,vwap=100).items()}
    n=210 if half else 390
    # Previous 20 amplitudes are all2. Last first-hour close differs0.6 from actual source VWAP100.
    a['close'][-1,59]=100.6 if short else 99.4
    a['open'][-1,60]=100.6 if short else 99.4
    for k,x in dict(open=99.4,high=99.6,low=99.2,close=99.4,vwap=99.4).items():
        a[k][-1,60:n]=200-x if short else x
    if short:a['high'][-1,60:n],a['low'][-1,60:n]=a['low'][-1,60:n].copy(),a['high'][-1,60:n].copy()
    a['open'][-1,n-1]=100 if short else 100
    a['high'][-1,n-1]=101;a['low'][-1,n-1]=99;a['close'][-1,n-1]=100
    quality=pd.DataFrame([dict(session_open=str(pd.Timestamp(str(d.date())+' 09:30',tz='America/New_York')),session_close=str(pd.Timestamp(str(d.date())+(' 13:00' if half and i==20 else ' 16:00'),tz='America/New_York'))) for i,d in enumerate(dates)])
    return SimpleNamespace(symbol='QQQ',dates=dates,arrays=a,lengths=np.array([390]*20+[n]),valid=np.ones(21,dtype=bool),quality=quality)


def bar(m,j,o,h,l,c,vw=None):
    for k,x in zip(('open','high','low','close'),(o,h,l,c)):m.arrays[k][-1,j]=x
    if vw is not None:m.arrays['vwap'][-1,j]=vw


def run(m,**kwargs):
    date=str(m.dates[-1].date());return simulate(m,prepare(m),Config(initial_capital=1000,**kwargs),date,date)


def test_source_vwap_and_previous20_ranges_determine_contrarian_signal():
    f=prepare(market()).iloc[-1]
    assert f.adr20==2 and f.vwap_at_signal==100 and f.signal_sign==1 and f.sizing_price==99.4


def test_weighted_source_vwap_is_not_hlc3_or_unweighted_average():
    m=market();m.arrays['vwap'][-1,0]=102;m.arrays['volume'][-1,0]=3000
    f=prepare(m).iloc[-1]
    assert f.vwap_at_signal==pytest.approx((102*3000+100*59000)/62000)
    assert f.signal_sign==1


def test_threshold_is_strict_decimal():
    m=market();m.arrays['close'][-1,59]=99.5
    assert prepare(m).iloc[-1].signal_sign==0


def test_current_or_future_daily_extremes_cannot_change_prior_adr_or_signal():
    m=market();f=prepare(m).iloc[-1];m.arrays['high'][-1,100:]=999;m.arrays['low'][-1,100:]=1
    g=prepare(m).iloc[-1]
    assert f.adr20==g.adr20 and f.signal_sign==g.signal_sign


def test_invalid_prior_session_is_causal_abstention_without_skipping_to_older():
    m=market();m.valid[5]=False;r=run(m);d=r.daily.iloc[0]
    assert d.eligibility=='invalid_prior20' and not d.conditionally_excluded and d.observed_return==0
    assert r.trades.empty


def test_warmup_abstains_on_exact_first20_sessions():
    f=prepare(market())
    assert f.eligibility.iloc[:20].eq('warmup20').all() and f.iloc[20].eligibility=='eligible'


def test_missing_firsthour_price_or_positive_volume_vwap_excludes_unknown_signal():
    m=market();m.arrays['vwap'][-1,20]=np.nan
    r=run(m);assert r.trades.empty and r.daily.iloc[0].conditionally_excluded and pd.isna(r.daily.iloc[0].observed_return)


def test_zero_volume_has_no_weight_even_with_nan_vwap():
    m=market();m.arrays['volume'][-1,20]=0;m.arrays['vwap'][-1,20]=np.nan
    assert prepare(m).iloc[-1].vwap_at_signal==100


def test_vwap_outside_ohlc_is_not_automatically_rejected():
    m=market();m.arrays['vwap'][-1,:60]=102
    assert prepare(m).iloc[-1].eligibility=='eligible'


def test_long_eod_and_costs():
    t=run(market()).trades.iloc[0]
    # q=min(floor1000/99.4, floor10/2)=5. gross reference3, slip.1, commission.7.
    assert t.quantity==5 and t.exit_reason=='eod_open' and t.net_pnl==pytest.approx(2.2)
    assert t.stop_price==pytest.approx(97.4) and t.holding_minutes_upper==329


def test_short_borrow_and_symmetry():
    t=run(market(short=True)).trades.iloc[0]
    assert t.quantity==5 and t.net_pnl==pytest.approx(2.2-5*100.59*.01/360)


def test_quantity_uses_completed_price_and_known_risk_not_entry_open():
    m=market();bar(m,60,110,110.2,109.8,110,110)
    t=run(m).trades.iloc[0]
    assert t.quantity==5 and t.entry_reference==110 and t.stop_price==108


def test_reversion_at_close_exits_only_next_open():
    m=market();bar(m,65,99.4,100.7,99.2,100.5,100);bar(m,66,100.7,101,100.2,100.5,100.5)
    t=run(m).trades.iloc[0]
    assert t.exit_reason=='vwap_next_open' and t.exit_slot==66 and t.exit_reference==100.7


def test_intraminute_vwap_touch_without_close_reversion_does_not_exit():
    m=market();bar(m,65,99.4,100.7,99.2,99.4,100)
    assert run(m).trades.iloc[0].exit_reason=='eod_open'


@pytest.mark.parametrize('short,opening,reference,reason',[(False,96,96,'stop_gap'),(True,104,104,'stop_gap'),(False,99.4,97.4,'stop_intrabar'),(True,100.6,102.6,'stop_intrabar')])
def test_stop_gap_and_intrabar_directional_execution(short,opening,reference,reason):
    m=market(short=short);bar(m,65,opening,max(opening,103),min(opening,97),opening,opening)
    t=run(m).trades.iloc[0];assert t.exit_reason==reason and t.exit_reference==pytest.approx(reference)


def test_stop_is_active_in_entry_bar_and_ignores_its_later_close():
    m=market();bar(m,60,99.4,105,97,104,104)
    r=run(m);assert r.trades.iloc[0].exit_reason=='stop_intrabar' and r.trades.iloc[0].net_pnl==pytest.approx(-10.8)
    bar(m,60,99.4,999,1,2,2);c=run(m)
    assert c.observed_close_drawdown_pct==pytest.approx(r.observed_close_drawdown_pct)


def test_scheduled_nextopen_exit_resolves_even_with_invalid_rest_of_bar():
    m=market();bar(m,65,99.4,100.7,99.2,100.5,100);bar(m,66,100.7,np.nan,np.nan,np.nan,np.nan);m.valid[-1]=False
    t=run(m,quality='resolved_prefix').trades.iloc[0]
    assert t.exit_slot==66 and t.exit_reason=='vwap_next_open'


def test_no_vwap_exit_reference_keeps_same_stop_but_holds_until_eod():
    m=market();bar(m,65,99.4,100.7,99.2,100.5,100)
    assert run(m,exit_policy='eod_only').trades.iloc[0].exit_reason=='eod_open'


def test_eod_only_does_not_require_unused_vwap_after_signal():
    m=market();m.arrays['vwap'][-1,70]=np.nan
    assert run(m,exit_policy='eod_only').trades.iloc[0].exit_reason=='eod_open'


def test_missing_vwap_during_vwap_strategy_is_unknown_not_cash():
    m=market();m.arrays['vwap'][-1,70]=np.nan
    r=run(m,quality='resolved_prefix')
    assert r.trades.empty and r.unresolved.iloc[0].reason=='missing_active_vwap'


def test_stop_exit_does_not_require_vwap_of_its_exit_bar():
    m=market();bar(m,65,99.4,100,97,98,np.nan)
    assert run(m,quality='resolved_prefix').trades.iloc[0].exit_reason=='stop_intrabar'


def test_half_session_liquidates1259():
    t=run(market(half=True)).trades.iloc[0]
    assert pd.Timestamp(t.exit_time).strftime('%H:%M')=='12:59' and t.holding_minutes_upper==149


def test_unknown_active_minute_omits_entire_trade_without_imputing_observed_cash():
    m=market();m.arrays['open'][-1,70]=np.nan;m.valid[-1]=False
    r=run(m,quality='resolved_prefix');d=r.daily.iloc[0]
    assert d.equity==1000 and d.net_pnl==0 and d.commission==0 and pd.isna(d.observed_return)
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==.35


def test_missing_entry_open_is_not_shifted_to_later_minute():
    m=market();m.arrays['open'][-1,60]=np.nan
    r=run(m,quality='resolved_prefix')
    assert r.trades.empty and r.unresolved.iloc[0].reason=='missing_entry_open'


def test_postexit_changes_leave_trades_and_drawdown_identical():
    m=market();bar(m,65,99.4,100.7,99.2,100.5,100);first=run(m,quality='resolved_prefix')
    for a in m.arrays.values():a[-1,67:]=np.nan
    m.valid[-1]=False;second=run(m,quality='resolved_prefix')
    pd.testing.assert_frame_equal(first.trades,second.trades);pd.testing.assert_frame_equal(first.daily,second.daily)
    assert first.observed_close_drawdown_pct==second.observed_close_drawdown_pct


def test_complete_quality_filter_is_retrospective_and_disclosed():
    m=market();m.valid[-1]=False;r=run(m)
    assert r.daily.iloc[0].eligibility=='excluded_incomplete_day' and r.daily.iloc[0].conditionally_excluded


@pytest.mark.parametrize('mode,short',[('long_only',True),('short_only',False)])
def test_direction_filter_is_known_causal_no_entry(mode,short):
    r=run(market(short=short),mode=mode)
    assert r.trades.empty and r.daily.iloc[0].observed_return==0


@pytest.mark.parametrize('kwargs',[dict(slippage=-1),dict(quality='ignore_missing'),dict(exit_policy='future_best'),dict(mode='optimize'),dict(initial_capital=0)])
def test_invalid_config_refused(kwargs):
    with pytest.raises(ValueError):Config(**kwargs)
