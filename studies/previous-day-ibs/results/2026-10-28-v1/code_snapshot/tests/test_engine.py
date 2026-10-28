from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import sys,copy
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ibs.engine import Config,prepare,signal,simulate

def market(n=390,days=18):
    dates=pd.bdate_range('2024-01-02',periods=days)
    a={k:np.full((days,390),v,dtype=float) for k,v in dict(open=100.,high=101.,low=99.,close=99.2,volume=1000.).items()}
    for k,v in dict(open=100.,high=100.3,low=99.8,close=100.1).items():a[k][-1,:]=v
    for k,v in dict(open=101.,high=101.2,low=100.8,close=101.).items():a[k][-1,n-1]=v
    return SimpleNamespace(arrays=a,dates=dates,lengths=np.full(days,n),valid=np.ones(days,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))
def fs(m):return prepare(m,{})
def sig(m,c=Config()):return signal(m,fs(m)[-1],c)
def run(m,c=Config()):
    f=fs(m)[-1];return simulate(m,[f],c,f['date'],f['date'])
def setbar(m,j,**kw):
    for k,v in kw.items():m.arrays[k][-1,j]=v

def test_previous_day_ibs_and_adr_not_current_day():
    m=market();f=fs(m)[-1];assert f['ibs_previous']==pytest.approx(.1);assert f['adr']==2.;assert sig(m)['sign']==1
def test_exact_low_threshold_included():
    m=market();m.arrays['close'][-2,-1]=99.4;assert sig(m)['reason']=='eligible'
def test_above_low_threshold_no_trade():
    m=market();m.arrays['close'][-2,-1]=99.5;assert sig(m)['reason']=='no_signal'
def test_short_and_both_high_threshold():
    m=market();m.arrays['close'][-2,-1]=100.8
    assert sig(m)['reason']=='no_signal';assert sig(m,Config(mode='both'))['sign']==-1
    assert sig(m,Config(mode='short_only'))['sign']==-1
def test_short_only_does_not_trade_low_ibs():assert sig(market(),Config(mode='short_only'))['reason']=='no_signal'
def test_always_long_ignores_ibs():
    m=market();m.arrays['close'][-2,-1]=100.;assert sig(m,Config(mode='always_long'))['sign']==1
def test_zero_range_ibs_is_neutral():
    m=market()
    for k in ('open','high','low','close'):m.arrays[k][-2,:]=100.
    assert fs(m)[-1]['ibs_previous']==.5;assert sig(m)['reason']=='no_signal'
def test_warmup_does_not_skip_a_missing_historical_session():
    m=market();m.arrays['low'][-4,50]=np.nan;assert sig(m)['reason']=='unknown_history'
    assert signal(m,fs(m)[13],Config())['reason']=='warmup'
def test_old_missing_session_outside_adr_not_required():
    m=market();m.arrays['low'][0,50]=np.nan;assert sig(m)['reason']=='eligible'
def test_future_prices_do_not_change_decision():
    m=market();s=sig(m);m.arrays['high'][-1,2:]=10000.;np.testing.assert_equal(sig(m),s)
def test_today_sizing_minute_required():
    m=market();setbar(m,0,close=np.nan);assert sig(m)['reason']=='unknown_sizing'
def test_unused_opening_minutes_in_delayed_entry():
    m=market();setbar(m,0,close=np.nan);assert sig(m,Config(entry_slot=5))['reason']=='eligible'
def test_sizing_before_fill_and_fixed_stop():
    m=market();s=sig(m);assert s['entry_slot']==1 and s['signal_slot']==0;assert s['stop_price']==98.1
    r=run(m);t=r.trades.iloc[0];assert t.quantity==500 and t.entry_risk_pct<1
    assert t.entry_reference==100 and t.exit_reference==101 and t.exit_slot==389
def test_future_gap_does_not_resize_quantity():
    m=market();setbar(m,1,open=105.,high=105.2,low=104.8,close=105.);assert run(m).trades.iloc[0].quantity==500
def test_stop_gap_uses_adverse_open():
    m=market();setbar(m,3,open=97.,high=97.2,low=96.8,close=97.);t=run(m).trades.iloc[0];assert t.exit_reason=='stop_gap' and t.exit_reference==97.
def test_stop_intrabar_before_eod():
    m=market();setbar(m,2,low=98.);t=run(m).trades.iloc[0];assert t.exit_reason=='stop_intrabar' and t.exit_reference==98.1
def test_entry_marketable_stop_pays_roundtrip():
    m=market();setbar(m,1,open=97.,high=97.2,low=96.8,close=97.);t=run(m).trades.iloc[0];assert t.entry_reference==t.exit_reference==97. and t.net_pnl<0
def test_commission_and_friction_once():
    t=run(market()).trades.iloc[0];assert t.friction_cost==10.;assert t.commission==3.5;assert t.net_pnl==pytest.approx(486.5)
def test_half_session_exit_last_open_before_its_wick():
    m=market(210);setbar(m,209,low=1.);t=run(m).trades.iloc[0];assert t.exit_slot==209 and t.exit_reason=='eod_open' and t.half_session
def test_incomplete_day_filter_and_prefix():
    m=market();m.valid[-1]=False;assert run(m).trades.empty
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1
def test_active_gap_is_unresolved_not_flat():
    m=market();setbar(m,5,low=np.nan);r=run(m,Config(quality='resolved_prefix'));assert r.trades.empty and len(r.unresolved)==1 and r.daily.conditionally_excluded.all()
def test_missing_after_stop_does_not_erase_fill():
    m=market();setbar(m,2,low=98.);setbar(m,5,low=np.nan);assert len(run(m,Config(quality='resolved_prefix')).trades)==1
def test_missing_entry_open_omits_unresolved_trade():
    m=market();setbar(m,1,open=np.nan);r=run(m);assert r.trades.empty and len(r.unresolved)==1
def test_short_borrow_and_symmetric_stop():
    m=market();m.arrays['close'][-2,-1]=100.8;t=run(m,Config(mode='short_only')).trades.iloc[0];assert t.stop_price==102.1 and t.borrow_fee>0
def test_trend_warmup_and_past_sma():
    m=market();assert sig(m,Config(trend_filter=True))['reason']=='warmup'
    m=market(days=205);assert sig(m,Config(trend_filter=True))['reason']=='trend_filtered'
    m.arrays['close'][-2,-1]=99.3;assert sig(m,Config(trend_filter=True))['reason']=='eligible'
@pytest.mark.parametrize('kw',[{'mode':'bad'},{'threshold':.6},{'slippage':-1},{'entry_slot':0},{'risk_budget':0},{'quality':'bad'}])
def test_invalid_config(kw):
    with pytest.raises(ValueError):Config(**kw)


def test_stop_ignores_subcent_floating_arithmetic_noise():
    m=market();f=fs(m)[-1];f['adr']=2.000000000000001
    assert signal(m,f,Config())['stop_price']==98.1

def test_minimum_commission_applies_on_both_sides():
    t=run(market(),Config(initial_capital=1000.)).trades.iloc[0]
    assert t.quantity==5 and t.commission==.7
    assert t.net_pnl==pytest.approx(4.2)
