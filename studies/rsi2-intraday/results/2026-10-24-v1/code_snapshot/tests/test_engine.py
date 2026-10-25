import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rsi2.engine import Config,rsi,atr,prepare,signal,trace,simulate


def fixture(n=390):
    arrays={k:np.full((1,390),v,dtype=float) for k,v in dict(open=100,high=100.1,low=99.9,close=100,volume=1000).items()}
    day=pd.Timestamp('2024-01-03')
    m=SimpleNamespace(arrays=arrays,lengths=np.array([n]),dates=pd.DatetimeIndex([day]),valid=np.array([True]),symbol='SPY',quality=pd.DataFrame([{'session_open':'2024-01-03 09:30:00-05:00'}]))
    f=dict(index=0,date='2024-01-03',n=n,regime_reason='eligible',trend=1,prior_close=101,prior_sma=100,rsi=np.full(n//5,50.),atr=np.full(n//5,1.),good=np.ones(n//5,bool),bars=np.tile([100.,100.1,99.9,100.],(n//5,1)))
    f['rsi'][13]=2;f['rsi'][14]=75
    return m,f


def test_rsi_wilder_seed_and_recurrence():
    x=rsi(np.array([100.,99,98,99,100]))
    assert np.isnan(x[:2]).all()
    assert x[2:]==pytest.approx([0,50,75])


@pytest.mark.parametrize('prices,value',[(np.ones(6)*100,50),(np.arange(100,106),100),(np.arange(106,100,-1),0)])
def test_rsi_flat_and_one_direction(prices,value):
    assert rsi(prices)[-1]==value


def test_indicator_gap_is_not_forward_filled():
    assert np.isnan(rsi(np.array([100.,99,98,np.nan,100,99]))[3:]).all()
    bars=np.tile([100,101,99,100.],(20,1));bars[15]=np.nan
    assert np.isnan(atr(bars)[15:]).all()


def test_atr_initial_range_and_wilder_update():
    bars=np.tile([100.,101,99,100],(15,1));bars[14]=[100,102,98,100]
    a=atr(bars)
    assert np.isnan(a[:13]).all()
    assert a[13:]==pytest.approx([2,30/14])


def test_signal_after_completed_five_minute_bar():
    m,f=fixture();s=signal(f,Config())
    assert s['signal_slot']==69 and s['entry_slot']==70 and s['sign']==1
    assert s['stop_price']==98
    f['bars'][60:,3]=10000
    assert signal(f,Config())==s


def test_entry_window_and_missing_signal_prefix():
    _,f=fixture();f['rsi'][:]=2;f['atr'][:13]=np.nan
    assert signal(f,Config())['entry_slot']==70
    f['good'][5]=False
    assert signal(f,Config())['reason']=='unknown_signal'
    _,f=fixture();f['rsi'][:]=50;f['rsi'][65]=2
    assert signal(f,Config())['reason']=='no_signal'


def test_short_regime_and_no_regime_variant():
    _,f=fixture();f['trend']=-1;f['rsi'][13]=98
    assert signal(f,Config())['reason']=='regime_filtered'
    assert signal(f,Config(mode='both'))['sign']==-1
    f['rsi'][13]=2
    assert signal(f,Config(use_regime=False))['sign']==1


def test_exit_is_next_open_not_signal_close():
    m,f=fixture();m.arrays['open'][0,75]=100.4
    p=trace(m,0,f,signal(f,Config()),Config())
    assert p['entry_slot']==70 and p['exit_slot']==75
    assert p['exit_signal_slot']==74 and p['exit_reason']=='indicator_next_open'
    assert p['exit_reference']==100.4


def test_stop_precedes_later_indicator_exit():
    m,f=fixture();m.arrays['low'][0,74]=97
    p=trace(m,0,f,signal(f,Config()),Config())
    assert p['exit_slot']==74 and p['exit_reference']==98
    assert p['exit_reason']=='stop_intrabar'


def test_gap_through_frozen_stop_is_not_cancelled():
    m,f=fixture();m.arrays['open'][0,70]=97
    p=trace(m,0,f,signal(f,Config()),Config())
    assert p['entry_slot']==p['exit_slot']==70
    assert p['exit_reason']=='entry_marketable_stop'
    assert p['exit_reference']==97


def test_short_stop_and_exit_symmetry():
    m,f=fixture();f['trend']=-1;f['rsi'][13:15]=[98,20]
    p=trace(m,0,f,signal(f,Config(mode='short_only')),Config(mode='short_only'))
    assert p['stop_price']==102 and p['exit_slot']==75 and p['sign']==-1


def test_half_session_eod_open_without_later_prices():
    m,f=fixture(210);f['rsi'][14:]=50;m.arrays['open'][0,209]=100.4;m.arrays['high'][0,209]=500
    p=trace(m,0,f,signal(f,Config()),Config())
    assert p['exit_slot']==209 and p['exit_reason']=='eod_open'
    assert p['exit_time'].endswith('12:59:00-05:00')
    assert max(p['favorable'])<500


def test_causal_sizing_fees_marks_and_one_trade_per_day():
    m,f=fixture();m.arrays['open'][0,70]=101;m.arrays['high'][0,70]=101.1;m.arrays['open'][0,75]=101.4
    r=simulate(m,[f],Config(initial_capital=1000),'2024-01-03','2024-01-03')
    t=r.trades.iloc[0]
    assert len(r.trades)==1 and t.quantity==5
    assert t.commission==.7 and t.friction_cost==.1
    assert t.entry_leverage>0.5
    assert t.net_pnl==pytest.approx(5*.4-.1-.7)
    assert r.daily.iloc[0].equity==pytest.approx(1001.2)


def test_current_day_future_gap_does_not_change_known_entry():
    m,f=fixture();m.valid[0]=False;m.arrays['close'][0,200]=np.nan
    primary=simulate(m,[f],Config(),'2024-01-03','2024-01-03')
    prefix=simulate(m,[f],Config(quality='resolved_prefix'),'2024-01-03','2024-01-03')
    assert primary.trades.empty and primary.daily.iloc[0].conditionally_excluded
    assert len(prefix.trades)==1 and prefix.trades.iloc[0].entry_slot==70


def test_active_hole_is_unresolved_and_entry_costs_kept():
    m,f=fixture();m.valid[0]=False;m.arrays['close'][0,72]=np.nan
    r=simulate(m,[f],Config(quality='resolved_prefix',initial_capital=1000),'2024-01-03','2024-01-03')
    assert r.trades.empty and len(r.unresolved)==1
    assert r.unresolved.iloc[0].known_entry_commission==.35
    assert np.isnan(r.daily.iloc[0].observed_return)


def test_daily_regime_uses_prior_closes_and_only_known_dividends():
    m,_=fixture();n=202;m.dates=pd.bdate_range('2023-01-02',periods=n);m.lengths=np.full(n,390);m.valid=np.ones(n,bool)
    m.arrays={k:np.repeat(v,n,axis=0) for k,v in m.arrays.items()}
    for i in range(n):
        for k in ['open','high','low','close']:m.arrays[k][i]+=i
    f=prepare(m,{str(m.dates[100].date()):1.})
    assert f[199]['regime_reason']=='warmup200' and f[200]['trend']==1
    before=f[200]['prior_sma'];m.arrays['close'][200:]=np.nan
    assert prepare(m,{str(m.dates[100].date()):1.,'2099-01-01':1000})[200]['prior_sma']==before


def test_invalid_prior_last_close_is_not_replaced_by_an_older_day():
    m,_=fixture();n=202;m.dates=pd.bdate_range('2023-01-02',periods=n);m.lengths=np.full(n,390);m.valid=np.ones(n,bool)
    m.arrays={k:np.repeat(v,n,axis=0) for k,v in m.arrays.items()};m.arrays['close'][1,389]=np.nan
    assert prepare(m,{})[200]['regime_reason']=='invalid_prior_close'


def test_daily_close_regime_does_not_require_unrelated_ohlcv_fields():
    m,_=fixture();n=201;m.dates=pd.bdate_range('2023-01-02',periods=n);m.lengths=np.full(n,390);m.valid=np.ones(n,bool)
    m.arrays={k:np.repeat(v,n,axis=0) for k,v in m.arrays.items()}
    m.arrays['volume'][1,389]=np.nan;m.arrays['high'][2,389]=np.nan;m.arrays['close'][3,20]=np.nan
    assert prepare(m,{})[200]['regime_reason']=='eligible'


@pytest.mark.parametrize('kwargs',[{'slippage':-1},{'mode':'bad'},{'entry_threshold':0},{'stop_atr':0},{'quality':'bad'}])
def test_invalid_configuration_fails(kwargs):
    with pytest.raises(ValueError):Config(**kwargs)
