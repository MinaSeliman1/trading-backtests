from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from noise_area.engine import Config, simulate


def one_day(length=390):
    a={name:np.full((1,390),100.) for name in ['open','high','low','close']}
    a['volume']=np.full((1,390),1000.)
    a['close'][0,29]=105;a['open'][0,30]=106
    a['close'][0,59]=103;a['open'][0,60]=102
    m=SimpleNamespace(arrays=a,dates=pd.DatetimeIndex(['2024-01-02']),lengths=np.array([length]),valid=np.array([True]),symbol='SPY')
    f=dict(upper=np.full((1,390),104.),lower=np.full((1,390),98.),vwap=np.full((1,390),100.),volatility=np.array([.02]))
    return m,f


def test_close_and_next_open_prices_are_distinct_and_commissions_are_two_sides():
    m,f=one_day()
    a=simulate(m,f,Config(execution='close',slippage=.01,borrow_rate=0))
    b=simulate(m,f,Config(execution='next_open',slippage=.01,borrow_rate=0))
    assert len(a.trades)==len(b.trades)==1
    x=a.trades.iloc[0];y=b.trades.iloc[0]
    assert (x.quantity,y.quantity)==(1000,1000)
    assert x.entry_price==105.01 and x.exit_price==102.99
    assert y.entry_price==106.01 and y.exit_price==101.99
    assert x.commission==7
    assert x.net_pnl==pytest.approx(-2027)
    assert y.net_pnl==pytest.approx(-4027)
    assert x.entry_time.endswith('10:00:00-05:00')


def test_quantity_floor_uses_known_open_and_prior_equity_never_next_open():
    m,f=one_day();f['volatility'][0]=.03
    a=simulate(m,f,Config(slippage=0))
    m.arrays['open'][0,30]=10000
    b=simulate(m,f,Config(slippage=0))
    assert a.trades.iloc[0].quantity==b.trades.iloc[0].quantity==666


def test_reversal_closes_long_and_opens_short_with_four_sides():
    m,f=one_day();m.arrays['close'][0,59]=97;m.arrays['open'][0,60]=96
    result=simulate(m,f,Config(execution='next_open',slippage=0,borrow_rate=0))
    assert result.trades.direction.tolist()==['LONG','SHORT']
    assert result.trades.iloc[0].exit_time==result.trades.iloc[1].entry_time
    assert result.trades.commission.sum()==14
    assert result.trades.iloc[0].exit_reason=='reversal'


@pytest.mark.parametrize('length,lasttime',[(390,'15:59:00-05:00'),(210,'12:59:00-05:00')])
def test_flatten_at_last_open_and_never_overnight(length,lasttime):
    m,f=one_day(length);m.arrays['close'][0,30:]=105
    result=simulate(m,f,Config(slippage=0,borrow_rate=0))
    assert len(result.trades)==1
    assert result.trades.iloc[0].exit_time.endswith(lasttime)
    assert result.trades.iloc[0].exit_reason=='session_end'
    assert result.daily.iloc[0].equity==pytest.approx(93993)


def test_no_trade_on_excluded_or_unwarmed_day_and_no_intra_halfhour_decision():
    m,f=one_day();m.arrays['close'][0,15]=110
    m.valid[0]=False
    assert simulate(m,f,Config()).trades.empty
    m.valid[0]=True;f['volatility'][0]=np.nan
    assert simulate(m,f,Config()).trades.empty
    f['volatility'][0]=.02;m.arrays['close'][0,29]=100
    assert simulate(m,f,Config()).trades.empty


def test_borrow_minimum_one_day_and_cash_ledger_reconcile():
    m,f=one_day();m.arrays['close'][0,29]=97;m.arrays['open'][0,30]=96
    result=simulate(m,f,Config(slippage=0,borrow_rate=.01))
    trade=result.trades.iloc[0]
    assert trade.borrow_fee==pytest.approx(96*1000*.01/360)
    assert trade.net_pnl==pytest.approx(trade.gross_pnl-trade.commission-trade.borrow_fee)
    assert result.daily.equity.iloc[-1]==pytest.approx(100000+result.trades.net_pnl.sum())


def test_intraday_drawdown_sees_adverse_prices_before_recovery():
    m,f=one_day();m.arrays['close'][0,30:59]=80
    result=simulate(m,f,Config(slippage=0,borrow_rate=0))
    assert result.summary['max_drawdown_usd']>25000
    assert result.summary['max_drawdown_usd']>100000-result.daily.equity.iloc[-1]


def test_excluded_sessions_stay_flat_in_daily_calendar_and_risk_denominators():
    m,f=one_day()
    m.arrays={k:np.repeat(v,2,axis=0) for k,v in m.arrays.items()}
    m.dates=pd.DatetimeIndex(['2024-01-02','2024-01-03']);m.lengths=np.array([390,390]);m.valid=np.array([False,True])
    f={k:np.repeat(v,2,axis=0) for k,v in f.items()}
    r=simulate(m,f,Config())
    assert len(r.daily)==2
    assert r.daily.iloc[0].return_net==0
    assert r.daily.iloc[0].equity==100000
