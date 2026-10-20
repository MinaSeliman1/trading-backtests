from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest
from qqq_paper.strategy import Parameters,Session,signal,day_size,decision_times,completed_prefix


def fixture():
    from types import SimpleNamespace
    dates=pd.bdate_range('2026-01-01',periods=20)
    a={k:np.full((20,390),100.) for k in ['open','high','low','close']}
    a['volume']=np.full((20,390),1000.)
    for i in range(20):a['close'][i]=100*(1+.001*(i%3))
    m=SimpleNamespace(dates=dates,arrays=a,valid=np.ones(20,dtype=bool),lengths=np.full(20,390))
    s=Session(pd.Timestamp('2026-10-20 09:30',tz='America/New_York'),pd.Timestamp('2026-10-20 16:00',tz='America/New_York'))
    idx=pd.date_range(s.open,s.close,inclusive='left',freq='min')
    f=pd.DataFrame({k:105. if k!='volume' else 1000. for k in ['open','high','low','close','volume']},index=idx)
    f.loc[idx[0],'open']=100.;f.loc[idx[0],'low']=100.
    return m,s,f


def test_default_parameters_frozen_and_realistic_overlay():
    p=Parameters()
    assert (p.symbol,p.lookback,p.volatility_window,p.frequency,p.target_vol,p.leverage_cap)==('QQQ',14,14,30,.02,4.)
    assert (p.commission,p.minimum_commission,p.slippage,p.borrow_rate)==(.0035,.35,.01,.01)


def test_signal_uses_only_completed_prefix_and_prior_days():
    m,s,f=fixture();at=s.open+pd.Timedelta(minutes=30)
    x=signal(m,f,s,at,0)
    assert x.target==1 and x.price==105 and x.upper==pytest.approx(100.1*(1+.013/14))
    f.loc[f.index>=at,['high','low','close']]=9999
    y=signal(m,f,s,at,0)
    assert (x.target,x.upper,x.vwap,x.volatility)==(y.target,y.upper,y.vwap,y.volatility)
    assert x.vwap==pytest.approx((103.33333333333333+29*105)/30)


def test_dividend_changes_reference_only_and_intraday_prices_remain_raw():
    m,s,f=fixture();m.arrays['close'][-1,:]=110
    x=signal(m,f,s,s.open+pd.Timedelta(minutes=30),0,dividend=2)
    y=signal(m,f,s,s.open+pd.Timedelta(minutes=30),0,dividend=0)
    assert x.upper==pytest.approx(y.upper*108/110)
    assert f.close.iloc[0]==105


def test_volatility_is_last_fourteen_returns_with_yesterday_included():
    m,s,f=fixture();x=signal(m,f,s,s.open+pd.Timedelta(minutes=30),0)
    closes=m.arrays['close'][-15:,-1]
    assert x.volatility==pytest.approx(np.std(closes[1:]/closes[:-1]-1,ddof=1))
    m.valid[-3]=False
    with pytest.raises(ValueError,match='consecutive'):signal(m,f,s,s.open+pd.Timedelta(minutes=30),0)


def test_missing_or_unfinished_bar_never_becomes_a_signal():
    m,s,f=fixture();at=s.open+pd.Timedelta(minutes=30)
    with pytest.raises(ValueError,match='missing'):signal(m,f.drop(f.index[4]),s,at,0)
    with pytest.raises(ValueError,match='decision'):signal(m,f,s,at+pd.Timedelta(seconds=1),0)


def test_provider_utc_bars_equal_same_new_york_instants():
    m,s,f=fixture();at=s.open+pd.Timedelta(minutes=30)
    local=signal(m,f,s,at,0)
    provider=signal(m,f.tz_convert('UTC'),s,at,0)
    assert vars(provider)==vars(local)


def test_half_day_schedule_and_quantity_known_before_execution():
    m,s,f=fixture();short=Session(s.open,s.open+pd.Timedelta(minutes=210))
    times=decision_times(short)
    assert times[0].strftime('%H:%M')=='10:00' and times[-1].strftime('%H:%M')=='12:30'
    assert short.flatten.strftime('%H:%M')=='12:59'
    assert day_size(100000,100,.03)==666
    assert day_size(100000,100,0)==4000
    with pytest.raises(ValueError):day_size(-10,100,.01)


def test_bad_ohlcv_rejected_and_identical_duplicates_are_safe():
    _,s,f=fixture();at=s.open+pd.Timedelta(minutes=30)
    assert len(completed_prefix(pd.concat([f,f.iloc[:1]]),s,at))==30
    bad=f.copy();bad.iloc[0,bad.columns.get_loc('high')]=1
    with pytest.raises(ValueError,match='OHLCV'):completed_prefix(bad,s,at)
