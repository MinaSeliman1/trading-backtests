from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import copy,sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tuesday.engine import Config,prepare,signal,simulate

def market(n=390,days=26,end='2024-02-06'):
    dates=pd.bdate_range(end=end,periods=days)
    a={k:np.full((days,390),v,dtype=float) for k,v in dict(open=100.,high=101.,low=99.,close=100.,volume=1000.).items()}
    a['close'][-2,n-1]=99.
    for k,v in dict(open=100.,high=100.3,low=99.8,close=100.1).items():a[k][-1,:]=v
    for k,v in dict(open=101.,high=101.2,low=100.8,close=101.).items():a[k][-1,n-1]=v
    return SimpleNamespace(arrays=a,dates=dates,lengths=np.full(days,n),valid=np.ones(days,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))

def bar(m,j,**values):
    for k,v in values.items():m.arrays[k][-1,j]=v

def feature(m):return prepare(m,{})[-1]

def sig(m,c=None):return signal(m,feature(m),c or Config())

def run(m,c=None):
    f=feature(m);return simulate(m,[f],c or Config(),f['date'],f['date'])

def test_monday_negative_triggers_tuesday_from_past_only():
    m=market();f=feature(m);assert f['weekday']==1 and f['previous_weekday']==0
    assert f['previous_return']==pytest.approx(-.01);assert f['adr']==2.;assert sig(m)['reason']=='eligible'

def test_flat_or_positive_monday_does_not_trigger():
    for close in [100.,100.5]:
        m=market();m.arrays['close'][-2,-1]=close;assert sig(m)['reason']=='no_signal'

def test_other_weekday_does_not_trade_without_explicit_control():
    m=market(end='2024-02-07');assert sig(m)['reason']=='no_signal'
    assert sig(m,Config(weekday=2,require_monday=False))['reason']=='eligible'

def test_monday_holiday_is_not_silently_replaced_by_friday():
    m=market();m.dates=m.dates[:-2].append(m.dates[-1:])
    for k in m.arrays:m.arrays[k]=np.delete(m.arrays[k],-2,axis=0)
    m.lengths=m.lengths[:-1];m.valid=m.valid[:-1];m.quality=m.quality.drop(index=len(m.quality)-2).reset_index(drop=True)
    m.arrays['close'][-2,-1]=99.
    assert feature(m)['previous_weekday']==4 and sig(m)['reason']=='no_signal'
    assert sig(m,Config(require_down=False,require_monday=False))['reason']=='eligible'

def test_last_actual_close_used_if_friday_was_closed():
    m=market();remove=len(m.dates)-3;m.dates=m.dates.delete(remove)
    for k in m.arrays:m.arrays[k]=np.delete(m.arrays[k],remove,axis=0)
    m.lengths=np.delete(m.lengths,remove);m.valid=np.delete(m.valid,remove);m.quality=m.quality.drop(index=remove).reset_index(drop=True)
    assert feature(m)['before_previous_close']==100. and sig(m)['reason']=='eligible'

def test_thresholds_are_inclusive_and_zero_is_strict():
    m=market();m.arrays['close'][-2,-1]=99.5
    assert sig(m,Config(drop=.005))['reason']=='eligible'
    assert sig(m,Config(drop=.01))['reason']=='no_signal'
    m.arrays['close'][-2,-1]=100.;assert sig(m)['reason']=='no_signal'

def test_all_tuesdays_and_all_down_days_are_distinct_controls():
    m=market();m.arrays['close'][-2,-1]=100.5
    assert sig(m,Config(require_down=False,require_monday=False))['reason']=='eligible'
    m=market(end='2024-02-08');assert sig(m,Config(weekday=None,require_monday=False))['reason']=='eligible'

def test_history_gap_not_skipped_in_adr():
    m=market();m.arrays['low'][-4,40]=np.nan;assert sig(m)['reason']=='unknown_history'
    assert signal(m,prepare(m,{})[13],Config())['reason']=='warmup'

def test_older_history_outside_fourteen_days_is_not_required():
    m=market();m.arrays['low'][0,50]=np.nan;assert sig(m)['reason']=='eligible'

def test_future_bars_do_not_change_order_or_size():
    m=market();s=sig(m);m.arrays['high'][-1,2:]=10000.;np.testing.assert_equal(sig(m),s)

def test_signal_bar_is_required_but_earlier_unused_bars_are_not():
    m=market();bar(m,0,close=np.nan);assert sig(m)['reason']=='unknown_sizing'
    assert sig(m,Config(entry_slot=5))['reason']=='eligible'

def test_causal_size_and_next_open_fill():
    t=run(market()).trades.iloc[0]
    assert t.signal_slot==0 and t.entry_slot==1 and t.quantity==500 and t.stop_price==98.1
    assert t.entry_reference==100. and t.exit_reference==101. and t.exit_slot==389

def test_entry_gap_does_not_resize_using_future_open():
    m=market();bar(m,1,open=105.,high=105.2,low=104.8,close=105.)
    t=run(m).trades.iloc[0];assert t.quantity==500 and t.entry_risk_pct>1

def test_gap_stop_uses_actual_adverse_open():
    m=market();bar(m,3,open=97.,high=97.2,low=96.8,close=97.)
    t=run(m).trades.iloc[0];assert t.exit_reason=='stop_gap' and t.exit_reference==97.

def test_intrabar_stop_uses_stop_price():
    m=market();bar(m,2,low=98.);t=run(m).trades.iloc[0];assert t.exit_reason=='stop_intrabar' and t.exit_reference==98.1

def test_entry_beyond_stop_pays_roundtrip():
    m=market();bar(m,1,open=97.,high=97.2,low=96.8,close=97.)
    t=run(m).trades.iloc[0];assert t.entry_reference==t.exit_reference==97. and t.net_pnl<0

def test_commission_and_friction_charged_once_per_side():
    t=run(market()).trades.iloc[0];assert t.commission==3.5 and t.friction_cost==10. and t.borrow_fee==0.
    assert t.net_pnl==pytest.approx(486.5)

def test_small_account_pays_minimum_commission():
    t=run(market(),Config(initial_capital=1000.)).trades.iloc[0]
    assert t.quantity==5 and t.commission==.7 and t.net_pnl==pytest.approx(4.2)

def test_half_session_exits_before_last_minute_wick():
    m=market(n=210);bar(m,209,low=1.);t=run(m).trades.iloc[0]
    assert t.exit_slot==209 and t.exit_reason=='eod_open' and t.half_session

def test_complete_day_filter_and_prefix_are_distinct():
    m=market();m.valid[-1]=False
    assert run(m).trades.empty and len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_unknown_active_bar_is_not_reported_as_observed_cash():
    m=market();bar(m,5,low=np.nan);r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and len(r.unresolved)==1 and r.daily.conditionally_excluded.all() and r.daily.observed_return.isna().all()
    assert r.unresolved.iloc[0].known_entry_commission==1.75

def test_gap_after_resolved_stop_does_not_erase_trade():
    m=market();bar(m,2,low=98.);bar(m,5,low=np.nan)
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_unknown_entry_open_exports_unresolved_not_trade():
    m=market();bar(m,1,open=np.nan);r=run(m)
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==0 and r.trades.empty

def test_decimal_stop_ignores_floating_point_noise():
    m=market();f=feature(m);f['adr']=2.000000000000001
    assert signal(m,f,Config())['stop_price']==98.1

@pytest.mark.parametrize('kw',[{'weekday':7},{'drop':-.1},{'slippage':-1},{'entry_slot':0},{'risk_budget':0},{'quality':'bad'},{'leverage_cap':0}])
def test_invalid_config_rejected(kw):
    with pytest.raises(ValueError):Config(**kw)


def test_reference_risk_and_modeled_net_stop_risk_are_distinct():
    t=run(market()).trades.iloc[0]
    assert t.entry_risk_pct==pytest.approx(.95)
    assert t.entry_leverage==pytest.approx(.5) and t.entry_fill_leverage==pytest.approx(.50005)
    assert t.modeled_stop_net_risk_pct==pytest.approx(.9635)


def test_invalid_historical_session_not_accepted_from_cleaned_ohlc():
    m=market();m.valid[-4]=False
    assert sig(m)['reason']=='unknown_history'
    assert sig(m,Config(quality='resolved_prefix'))['reason']=='unknown_history'


def test_immediate_stop_excursion_includes_both_fill_frictions():
    m=market();bar(m,1,open=97.,high=97.2,low=96.8,close=97.)
    t=run(m).trades.iloc[0]
    assert t.mae_observed_usd==pytest.approx(-10.) and t.mfe_observed_usd==0.

def test_eod_excursion_does_not_include_unheld_reference_open():
    t=run(market()).trades.iloc[0]
    assert t.mfe_observed_usd==pytest.approx(490.)
