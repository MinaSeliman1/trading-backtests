import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pdr.engine import Config,prepare,signal,trace,simulate

def fixture(n=390):
    arrays={k:np.full((3,390),v,dtype=float) for k,v in dict(open=100,high=101,low=99,close=100,volume=1000).items()}
    dates=pd.bdate_range('2024-01-02',periods=3)
    m=SimpleNamespace(arrays=arrays,lengths=np.full(3,n),dates=dates,valid=np.ones(3,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))
    arrays['high'][-1,:]=100.1;arrays['low'][-1,:]=99.9
    arrays['low'][-1,12]=98.99
    return m

def fs(m,cash=None,w=5):return prepare(m,cash or {},w)[-1]
def run(m,cfg=Config()):
    f=fs(m,w=cfg.bar_minutes)
    return simulate(m,[f],cfg,f['date'],f['date'])

def test_prior_range_uses_full_immediate_previous_session():
    m=fixture();m.arrays['high'][-2,300]=102
    assert fs(m)['prior_high']==102
    m.arrays['high'][-2,300]=np.nan
    assert signal(m,fs(m),Config())['reason']=='unknown_prior_range'

def test_range_does_not_depend_on_volume():
    m=fixture();m.arrays['volume'][-2,:]=np.nan
    assert signal(m,fs(m),Config())['reason']=='eligible'

def test_warmup_and_half_day_previous_range():
    m=fixture();m.lengths[-2]=210;m.arrays['high'][-2,211]=999
    assert fs(m)['prior_high']==101
    assert signal(m,prepare(m,{},5)[0],Config())['reason']=='warmup_previous_session'

def test_signal_complete_five_minutes_then_next_open():
    m=fixture();s=signal(m,fs(m),Config())
    assert s['sign']==1 and s['signal_slot']==14 and s['entry_slot']==15
    assert s['stop_price']==98.98 and s['sizing_price']==100

def test_exact_cent_sweep_counts_but_touch_and_boundary_close_do_not():
    m=fixture();m.arrays['low'][-1,12]=99
    assert signal(m,fs(m),Config())['reason']=='no_rejection'
    m.arrays['low'][-1,12]=98.99;m.arrays['close'][-1,14]=99;m.arrays['low'][-1,14]=99
    assert signal(m,fs(m),Config())['reason']=='no_rejection'

def test_both_extremes_same_signal_is_ambiguous_no_later_trade():
    m=fixture();m.arrays['high'][-1,13]=101.01;m.arrays['low'][-1,22]=98
    assert signal(m,fs(m),Config())['reason']=='ambiguous_two_sided_signal'

def test_short_direction_filter_does_not_search_later():
    m=fixture();m.arrays['low'][-1,12]=99.9;m.arrays['high'][-1,12]=101.01;m.arrays['low'][-1,22]=98
    s=signal(m,fs(m),Config());assert s['sign']==-1 and s['stop_price']==101.02
    assert signal(m,fs(m),Config(mode='long_only'))['reason']=='direction_filtered'

def test_open_must_be_inside_range_but_gap_variant_allows_it():
    m=fixture();m.arrays['open'][-1,0]=102
    assert signal(m,fs(m),Config())['reason']=='opening_outside_range'
    assert signal(m,fs(m),Config(allow_opening_gap=True))['reason']=='eligible'

def test_open_only_known_value_not_future_first_bar_ohlc():
    m=fixture();m.arrays['close'][-1,0]=np.nan
    assert signal(m,fs(m),Config())['reason']=='eligible'

def test_cash_dividend_subtracted_only_on_current_ex_date():
    m=fixture();f=fs(m,{str(m.dates[-1].date()):.5,'2030-01-01':10})
    assert f['cash_dividend']==.5 and f['prior_high']==100.5 and f['prior_low']==98.5
    assert signal(m,f,Config())['reason']=='no_rejection'
    assert signal(m,f,Config(cash_adjust=False))['reason']=='eligible'

def test_unknown_candidate_before_signal_blocks_but_pre_window_gap_does_not():
    m=fixture();m.arrays['close'][-1,11]=np.nan
    assert signal(m,fs(m),Config())['reason']=='unknown_signal'
    m=fixture();m.arrays['close'][-1,8]=np.nan
    assert signal(m,fs(m),Config())['reason']=='eligible'

def test_no_future_data_in_signal_or_quantity():
    m=fixture();s=signal(m,fs(m),Config());q=run(m).trades.iloc[0].quantity
    m.arrays['high'][-1,15:]=500;m.arrays['open'][-1,15]=110
    assert signal(m,fs(m),Config())==s and run(m).trades.iloc[0].quantity==q

def test_cutoff_and_last_allowed_entry():
    m=fixture();m.arrays['low'][-1,12]=99.9;m.arrays['low'][-1,267]=98
    assert signal(m,fs(m),Config())['reason']=='no_rejection'
    m.arrays['low'][-1,262]=98
    assert signal(m,fs(m),Config())['entry_slot']==265

def test_fifteen_minute_signal_includes_first_bar():
    m=fixture();m.arrays['low'][-1,12]=99.9;m.arrays['low'][-1,1]=98.99
    s=signal(m,fs(m,w=15),Config(bar_minutes=15));assert s['entry_slot']==15

def test_stop_rounds_outward_target_rounds_adverse():
    m=fixture();m.arrays['low'][-1,12]=98.985;s=signal(m,fs(m),Config())
    assert s['stop_price']==98.97
    m.arrays['open'][-1,15]=100.003;m.arrays['high'][-1,15]=100.1
    assert trace(m,fs(m),s,Config(target_r=1.5))['target_price']==101.55

def test_gap_past_stop_not_cancelled_and_minimum_fees():
    m=fixture();m.arrays['open'][-1,15]=98
    t=run(m,Config(initial_capital=1000)).trades.iloc[0]
    assert t.quantity==9 and t.exit_reason=='entry_marketable_stop'
    assert t.net_pnl==pytest.approx(-.88)

def test_stop_first_when_both_hit_and_no_exit_bar_wick_mae():
    m=fixture();m.arrays['low'][-1,16]=90;m.arrays['high'][-1,16]=110
    t=run(m).trades.iloc[0]
    assert t.ambiguous_bar and t.exit_reason=='stop_intrabar'
    assert t.mae_observed_usd==pytest.approx(t.quantity*(98.98-100.01))

def test_short_borrow_minimum_one_day():
    m=fixture();m.arrays['low'][-1,12]=99.9;m.arrays['high'][-1,12]=101.01
    t=run(m).trades.iloc[0]
    assert t.borrow_fee==pytest.approx(t.quantity*99.99*.01/360)

@pytest.mark.parametrize('n',[210,390])
def test_eod_open_ignores_last_wick(n):
    m=fixture(n);m.arrays['high'][-1,n-1]=1000;t=run(m).trades.iloc[0]
    assert t.exit_slot==n-1 and t.exit_reason=='eod_open' and t.mfe_observed_usd<100

def test_target_gap_no_improvement_and_stop_gap_adverse():
    m=fixture();m.arrays['open'][-1,16]=110;t=run(m).trades.iloc[0]
    assert t.exit_reason=='target_gap' and t.exit_reference==102.04
    m.arrays['open'][-1,16]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==98

def test_missing_entry_and_active_hole_are_unresolved():
    m=fixture();m.arrays['open'][-1,15]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==0
    m=fixture();m.arrays['close'][-1,16]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission>0 and np.isnan(r.daily.iloc[0].observed_return)

def test_complete_day_filter_is_distinct_from_prefix():
    m=fixture();m.valid[-1]=False;m.arrays['close'][-1,300]=np.nan
    assert run(m).trades.empty
    m.arrays['low'][-1,16]=98
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_multiday_compounding_and_cost_mark_drawdown():
    m=fixture();m.arrays['low'][1,12]=98.99;m.arrays['low'][1,16]=98;m.arrays['low'][-1,12]=97.99
    features=prepare(m,{},5)[1:]
    r=simulate(m,features,Config(),features[0]['date'],features[-1]['date'])
    assert len(r.trades)==2
    assert r.trades.iloc[1].equity_before==pytest.approx(r.trades.iloc[0].equity_after)
    assert r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())
    assert r.observed_close_drawdown_usd>=r.trades.commission.iloc[0]/2

def test_current_volume_unused_by_signal_and_resolved_trace():
    m=fixture();m.arrays['volume'][-1,:]=np.nan
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_signal_bar_may_open_outside_range():
    m=fixture();m.arrays['open'][-1,10]=98.995;m.arrays['low'][-1,10]=98.995
    assert signal(m,fs(m),Config())['reason']=='eligible'

def test_exact_boundary_open_is_filtered():
    m=fixture();m.arrays['open'][-1,0]=99
    assert signal(m,fs(m),Config())['reason']=='opening_outside_range'

@pytest.mark.parametrize('kw',[dict(bar_minutes=1),dict(mode='bad'),dict(slippage=-1),dict(target_r=0),dict(quality='bad')])
def test_config_rejects_bad_values(kw):
    with pytest.raises(ValueError):Config(**kw)
