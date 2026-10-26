import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ovb.engine import Config,prepare,signal,trace,simulate

def fixture(n=390):
    count=16
    arrays={k:np.full((count,390),v,dtype=float) for k,v in dict(open=100,high=100.5,low=99.5,close=100,volume=1000).items()}
    dates=pd.bdate_range('2024-01-02',periods=count)
    m=SimpleNamespace(arrays=arrays,lengths=np.full(count,n),dates=dates,valid=np.ones(count,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))
    arrays['close'][-1,4]=100.2
    arrays['low'][-1,5:]=99.9;arrays['high'][-1,5:]=100.1
    arrays['close'][-1,6]=100.6;arrays['high'][-1,6]=100.7
    return m

def test_prior_only_volume_and_no_future_window():
    m=fixture();f=prepare(m,5)[-1]
    assert f['rvol']==1 and f['volume_history_reason']=='eligible'
    m.arrays['volume'][-1,5:]=1e9
    assert prepare(m,5)[-1]['rvol']==1
    m.arrays['volume'][-2,:5]*=2
    assert prepare(m,5)[-1]['rvol']==pytest.approx(14/15)

def test_warmup_and_missing_prior_window_no_replacement():
    m=fixture();fs=prepare(m,5)
    assert fs[13]['volume_history_reason']=='warmup14'
    m.arrays['volume'][1,0]=np.nan
    assert prepare(m,5)[-1]['volume_history_reason']=='invalid_prior_opening_volume'
    assert signal(m,prepare(m,5)[-1],Config())['reason']=='unknown_volume_history'
    assert signal(m,prepare(m,5)[-1],Config(volume_threshold=0))['reason']=='eligible'

def test_confirmation_is_completed_close_then_next_open():
    m=fixture();f=prepare(m,5)[-1];s=signal(m,f,Config())
    assert s['signal_slot']==6 and s['entry_slot']==7 and s['sign']==1
    assert s['stop_price']==99.5 and s['sizing_price']==100.6
    m.arrays['high'][-1,5]=999
    assert signal(m,f,Config())==s

def test_volume_filter_and_doji():
    m=fixture();f=prepare(m,5)[-1];f['rvol']=.99
    assert signal(m,f,Config())['reason']=='volume_filtered'
    assert signal(m,f,Config(volume_threshold=0))['reason']=='eligible'
    m.arrays['close'][-1,4]=100
    assert signal(m,prepare(m,5)[-1],Config())['reason']=='doji'

def test_missing_prefix_before_breakout_cannot_skip_forward():
    m=fixture();m.arrays['close'][-1,5]=np.nan
    assert signal(m,prepare(m,5)[-1],Config())['reason']=='unknown_signal'

def test_cutoff_excludes_entry_at_1130():
    m=fixture();m.arrays['close'][-1,6]=100;m.arrays['close'][-1,119]=100.6;m.arrays['high'][-1,119]=100.7
    assert signal(m,prepare(m,5)[-1],Config())['reason']=='no_breakout'

def test_short_and_direction_filter():
    m=fixture();m.arrays['close'][-1,4]=99.8;m.arrays['close'][-1,6]=99.4;m.arrays['low'][-1,6]=99.3
    f=prepare(m,5)[-1];s=signal(m,f,Config())
    assert s['sign']==-1 and s['stop_price']==100.5
    assert signal(m,f,Config(mode='long_only'))['reason']=='direction_filtered'

def test_gap_entry_not_resized_or_cancelled_and_costs():
    m=fixture();m.arrays['open'][-1,7]=99
    f=prepare(m,5)[-1];r=simulate(m,[f],Config(initial_capital=1000),f['date'],f['date']);t=r.trades.iloc[0]
    assert t.quantity==9 and t.exit_reason=='entry_marketable_stop'
    assert t.net_pnl==pytest.approx(-.88) and t.commission==.7 and t.friction_cost==.18

def test_gap_stop_and_tp_stop_first():
    m=fixture();f=prepare(m,5)[-1];s=signal(m,f,Config())
    m.arrays['low'][-1,8]=99;m.arrays['high'][-1,8]=106
    p=trace(m,f,s,Config());assert p['exit_reason']=='stop_intrabar' and p['ambiguous_bar']

def test_half_session_eod_ignores_last_wick():
    m=fixture(210);f=prepare(m,5)[-1];s=signal(m,f,Config());m.arrays['high'][-1,209]=999
    p=trace(m,f,s,Config());assert p['exit_slot']==209 and p['exit_reason']=='eod_open'
    assert p['exit_time'].endswith('12:59:00-05:00') and max(p['favorable'])<999

def test_target_fill_and_gap_no_price_improvement():
    m=fixture();f=prepare(m,5)[-1];s=signal(m,f,Config());m.arrays['open'][-1,8]=106
    p=trace(m,f,s,Config());assert p['exit_reason']=='target_gap' and p['exit_reference']==105

def test_signal_sizing_does_not_use_future_entry_open():
    m=fixture();m.arrays['open'][-1,7]=102;m.arrays['high'][-1,7]=102.1
    f=prepare(m,5)[-1];r=simulate(m,[f],Config(initial_capital=1000),f['date'],f['date'])
    assert r.trades.iloc[0].quantity==9

def test_short_borrow_charged_minimum_day():
    m=fixture();m.arrays['close'][-1,4]=99.8;m.arrays['close'][-1,6]=99.4;m.arrays['low'][-1,6]=99.3
    f=prepare(m,5)[-1];r=simulate(m,[f],Config(initial_capital=1000),f['date'],f['date']);t=r.trades.iloc[0]
    assert t.borrow_fee==pytest.approx(t.quantity*99.99*.01/360)

def test_range15_uses_own_volume_and_waits_until_after_range():
    m=fixture();m.arrays['close'][-1,14]=100.2;m.arrays['high'][-1,14]=100.3;m.arrays['close'][-1,16]=100.8;m.arrays['high'][-1,16]=100.9
    f=prepare(m,15)[-1];s=signal(m,f,Config(window=15))
    assert s['entry_slot']==17 and f['opening_volume']==15000

def test_invalid_current_opening_and_zero_volume_are_unknown():
    m=fixture();m.arrays['volume'][-1,:5]=0
    assert signal(m,prepare(m,5)[-1],Config())['reason']=='unknown_opening'

def test_missing_entry_open_is_unresolved_without_invented_costs():
    m=fixture();m.arrays['open'][-1,7]=np.nan;f=prepare(m,5)[-1]
    r=simulate(m,[f],Config(quality='resolved_prefix'),f['date'],f['date'])
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==0

def test_last_allowed_entry_and_exact_boundary_close():
    m=fixture();m.arrays['close'][-1,6]=100.5;m.arrays['close'][-1,118]=100.6;m.arrays['high'][-1,118]=100.7
    s=signal(m,prepare(m,5)[-1],Config());assert s['signal_slot']==118 and s['entry_slot']==119

def test_risk_budget_binds_and_commission_exceeds_minimum():
    m=fixture();m.arrays['low'][-1,:5]=95;f=prepare(m,5)[-1]
    r=simulate(m,[f],Config(),f['date'],f['date']);t=r.trades.iloc[0]
    assert t.quantity==178 and t.commission==pytest.approx(2*178*.0035)

def test_adverse_stop_gap_uses_open():
    m=fixture();m.arrays['open'][-1,8]=99;f=prepare(m,5)[-1]
    p=trace(m,f,signal(m,f,Config()),Config());assert p['exit_reason']=='stop_gap' and p['exit_reference']==99

@pytest.mark.parametrize('entry_gap',[False,True])
def test_short_ambiguous_stop_and_marketable_gap(entry_gap):
    m=fixture();m.arrays['close'][-1,4]=99.8;m.arrays['close'][-1,6]=99.4;m.arrays['low'][-1,6]=99.3
    f=prepare(m,5)[-1];s=signal(m,f,Config())
    if entry_gap:m.arrays['open'][-1,7]=101
    else:m.arrays['high'][-1,8]=101;m.arrays['low'][-1,8]=94
    p=trace(m,f,s,Config())
    assert p['exit_reason']==('entry_marketable_stop' if entry_gap else 'stop_intrabar')
    assert p['exit_reference']==(101 if entry_gap else 100.5)

def test_multiday_capital_and_mark_drawdown():
    m=fixture();m.arrays['close'][-2,4]=100.2;m.arrays['close'][-2,6]=100.6;m.arrays['high'][-2,6]=100.7;m.arrays['low'][-2,5:]=99.9
    m.arrays['low'][-1,8]=99;fs=prepare(m,5)[-2:]
    r=simulate(m,fs,Config(initial_capital=1000),fs[0]['date'],fs[1]['date'])
    assert len(r.trades)==2 and r.trades.iloc[1].equity_before==pytest.approx(r.trades.iloc[0].equity_after)
    assert r.daily.equity.iloc[-1]==pytest.approx(1000+r.trades.net_pnl.sum())
    assert r.observed_close_drawdown_usd>=1000-r.daily.equity.iloc[-1]

def test_unresolved_active_gap_exports_known_entry_costs():
    m=fixture();m.valid[-1]=False;m.arrays['close'][-1,8]=np.nan;f=prepare(m,5)[-1]
    c=Config(initial_capital=1000,quality='resolved_prefix');r=simulate(m,[f],c,f['date'],f['date'])
    assert len(r.unresolved)==1 and r.trades.empty
    assert r.unresolved.iloc[0].known_entry_commission==.35
    assert np.isnan(r.daily.iloc[0].observed_return)

def test_future_incomplete_day_is_only_conditional_filter():
    m=fixture();m.valid[-1]=False;m.arrays['close'][-1,300]=np.nan;f=prepare(m,5)[-1]
    primary=simulate(m,[f],Config(),f['date'],f['date'])
    assert primary.trades.empty and primary.daily.iloc[0].conditionally_excluded
    m.arrays['low'][-1,8]=99
    prefix=simulate(m,[f],Config(quality='resolved_prefix'),f['date'],f['date'])
    assert len(prefix.trades)==1

@pytest.mark.parametrize('kw',[dict(volume_threshold=-1),dict(window=0),dict(cutoff=5),dict(mode='bad'),dict(slippage=-1)])
def test_config_rejects_invalid(kw):
    with pytest.raises(ValueError):Config(**kw)
