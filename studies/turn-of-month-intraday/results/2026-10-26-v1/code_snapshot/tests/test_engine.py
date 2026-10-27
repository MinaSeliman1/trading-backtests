import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tom.engine import Config,make_calendar,prepare,signal,trace,simulate
from tom.statistics import monthly_contrast

def fixture(n=390):
    dates=pd.DatetimeIndex(['2024-01-02','2024-01-08','2024-01-31'])
    a={k:np.full((3,390),v,dtype=float) for k,v in dict(open=100.25,high=100.3,low=100.2,close=100.25,volume=1000).items()}
    return SimpleNamespace(arrays=a,dates=dates,lengths=np.full(3,n),valid=np.ones(3,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))

def fs(m):return prepare(m,{})
def run(m,cfg=Config(),index=0):
    f=fs(m)[index];return simulate(m,[f],cfg,f['date'],f['date'])

def test_calendar_holidays_true_ordinal_and_last_day():
    c=make_calendar(pd.DatetimeIndex(['2024-01-02','2024-01-31'])).set_index('date')
    assert c.loc['2024-01-02','month_ordinal']==1
    assert c.loc['2024-01-04','month_ordinal']==3
    assert c.loc['2024-01-08','month_ordinal']==5
    assert c.loc['2024-01-31','sessions_to_end']==0
    assert '2024-01-01' not in c.index and '2024-01-15' not in c.index

@pytest.mark.parametrize('dates,first,last',[
    (['2015-12-31','2026-10-16'],'2015-11-02','2026-11-30'),
    (['2024-01-02','2024-02-12'],'2023-12-01','2024-03-28'),
])
def test_calendar_month_boundaries_can_be_non_sessions(dates,first,last):
    c=make_calendar(pd.DatetimeIndex(dates))
    assert c.date.iloc[0]==first and c.date.iloc[-1]==last
    assert c.month_ordinal.iloc[0]==1 and c.sessions_to_end.iloc[-1]==0

def test_truncated_source_and_period_are_not_month_end():
    m=fixture();m.dates=pd.DatetimeIndex(['2024-01-02','2024-01-08','2024-01-16'])
    f=fs(m)[-1]
    assert f['sessions_to_end']>0 and signal(m,f,Config())['reason']=='calendar_filtered'

def test_known_calendar_does_not_depend_on_prices_or_volume():
    m=fixture();before=fs(m);m.arrays['high'][:]=999;m.arrays['volume'][:]=np.nan
    assert fs(m)==before

def test_reference_and_calendar_controls():
    m=fixture();f=fs(m)
    assert [signal(m,x,Config())['reason'] for x in f]==['eligible','calendar_filtered','eligible']
    assert signal(m,f[0],Config(mode='last1'))['reason']=='calendar_filtered'
    assert signal(m,f[2],Config(mode='first1'))['reason']=='calendar_filtered'
    assert signal(m,f[1],Config(mode='first5_last1'))['reason']=='eligible'
    assert signal(m,f[1],Config(mode='other_days'))['reason']=='eligible'
    assert signal(m,f[0],Config(mode='other_days'))['reason']=='calendar_filtered'
    assert signal(m,f[1],Config(mode='all_days'))['reason']=='eligible'

def test_signal_close_0934_then_open_0935_and_outward_stop():
    m=fixture();s=signal(m,fs(m)[0],Config())
    assert s['signal_slot']==4 and s['entry_slot']==5 and s['sizing_price']==100.25
    assert s['stop_price']==99.24 and s['sign']==1

def test_missing_unneeded_early_minutes_does_not_change_signal():
    m=fixture();m.arrays['close'][0,0]=np.nan
    assert signal(m,fs(m)[0],Config())['reason']=='eligible'

def test_missing_sizing_bar_unknown_only_on_eligible_calendar_day():
    m=fixture();m.arrays['close'][:,4]=np.nan
    assert signal(m,fs(m)[0],Config())['reason']=='unknown_sizing_bar'
    assert signal(m,fs(m)[1],Config())['reason']=='calendar_filtered'

def test_no_future_price_or_entry_open_in_sizing():
    m=fixture();s=signal(m,fs(m)[0],Config());q=run(m).trades.iloc[0].quantity
    m.arrays['open'][0,5]=98;m.arrays['high'][0,200]=1000
    assert signal(m,fs(m)[0],Config())==s and run(m).trades.iloc[0].quantity==q

def test_gap_beyond_stop_not_cancelled_and_minimum_fees():
    m=fixture();m.arrays['open'][0,5]=98;t=run(m,Config(initial_capital=1000)).trades.iloc[0]
    assert t.quantity==9 and t.exit_reason=='entry_marketable_stop' and t.net_pnl==pytest.approx(-.88)
    assert t.commission==.7 and t.friction_cost==.18 and t.borrow_fee==0

def test_stop_gap_and_stop_intrabar_are_conservative():
    m=fixture();m.arrays['open'][0,6]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==98
    m=fixture();m.arrays['low'][0,6]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_intrabar' and t.exit_reference==99.24
    assert t.mae_observed_usd==pytest.approx(t.quantity*(99.24-100.26))

def test_no_take_profit_even_for_large_gain():
    m=fixture();m.arrays['high'][0,6]=1000;t=run(m).trades.iloc[0]
    assert t.exit_reason=='eod_open' and pd.isna(t.target_price)

def test_no_stop_retains_virtual_sizing_but_allows_larger_loss():
    m=fixture();m.arrays['low'][0,6]=90;m.arrays['open'][0,389]=95
    base=run(m).trades.iloc[0];nostop=run(m,Config(stop_enabled=False)).trades.iloc[0]
    assert base.quantity==nostop.quantity and not nostop.stop_enabled
    assert nostop.exit_reason=='eod_open' and nostop.net_pnl<base.net_pnl

@pytest.mark.parametrize('n',[210,390])
def test_last_open_exit_before_last_wick(n):
    m=fixture(n);m.arrays['low'][0,n-1]=1;t=run(m).trades.iloc[0]
    assert t.exit_slot==n-1 and t.exit_reason=='eod_open'
    assert t.mae_observed_usd>-100

def test_missing_entry_open_and_active_hole_are_unresolved():
    m=fixture();m.arrays['open'][0,5]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==0
    m=fixture();m.arrays['close'][0,6]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission>0
    assert np.isnan(r.daily.iloc[0].observed_return)

def test_future_complete_filter_and_prefix_resolved_exit():
    m=fixture();m.valid[0]=False;m.arrays['close'][0,300]=np.nan
    assert run(m).trades.empty
    m.arrays['low'][0,6]=98
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_multiday_compounding_and_cost_identity():
    m=fixture();f=fs(m);r=simulate(m,f,Config(),f[0]['date'],f[-1]['date'])
    assert len(r.trades)==2 and r.trades.iloc[1].equity_before==pytest.approx(r.trades.iloc[0].equity_after)
    assert r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())
    assert (r.trades.price_move_pnl-r.trades.friction_cost-r.trades.commission-r.trades.borrow_fee).sum()==pytest.approx(r.trades.net_pnl.sum())

def test_month_cluster_contrast_known_difference_and_missing_group():
    t=pd.DataFrame(dict(date=['2024-01-02','2024-01-10','2024-02-01','2024-02-12','2024-03-01'],net_bps=[10,0,-10,-20,99],month_ordinal=[1,7,1,8,1],sessions_to_end=[20,14,19,12,19],month_sessions=[21,21,20,20,20]))
    result=monthly_contrast(t)
    assert result['qualifying_months']==2 and result['months_without_both_groups']==1
    assert result['mean_difference_bps']==pytest.approx(10)
    assert result['ci95_bps']==pytest.approx([10,10])

def test_half_session_can_be_last_session_and_historical_exception_closed():
    c=make_calendar(pd.DatetimeIndex(['2024-11-29','2025-01-10'])).set_index('date')
    assert c.loc['2024-11-29','sessions_to_end']==0 and c.loc['2024-11-29','is_tom']
    assert '2025-01-09' not in c.index

def test_missing_last_close_not_needed_after_eod_open():
    m=fixture();m.valid[0]=False;m.arrays['close'][0,389]=np.nan
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_risk_budget_binds_before_cap_and_gap_can_exceed_it():
    m=fixture();m.arrays['open'][0,5]=110;m.arrays['high'][0,5]=110
    t=run(m,Config(stop_pct=.02)).trades.iloc[0]
    assert t.quantity==497 and t.entry_risk_pct>1

def test_zero_quantity_has_no_costs_or_invented_fill():
    r=run(fixture(),Config(initial_capital=1))
    assert r.trades.empty and r.daily.iloc[0].eligibility=='zero_quantity' and r.daily.iloc[0].equity==1

def test_empty_month_contrast_has_no_fabricated_estimate():
    t=pd.DataFrame(columns=['date','net_bps','month_ordinal','sessions_to_end','month_sessions'])
    r=monthly_contrast(t)
    assert r['qualifying_months']==0 and r['mean_difference_bps'] is None and r['ci95_bps'] is None

@pytest.mark.parametrize('kw',[dict(mode='bad'),dict(stop_pct=0),dict(stop_pct=1),dict(slippage=-1),dict(quality='bad')])
def test_config_rejects_bad_values(kw):
    with pytest.raises(ValueError):Config(**kw)
