from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from gap_reversal.engine import Config,prepare,simulate


def market():
    dates=pd.to_datetime(['2026-01-02','2026-01-05','2026-01-06'])
    a={k:np.full((3,390),100.) for k in ['open','high','low','close']}
    a['volume']=np.full((3,390),1000.)
    for k in ['open','high','low','close']:a[k][1,:]=102.01
    a['open'][1,1]=102.;a['low'][1,1]=101.9
    a['open'][1,30]=101.;a['low'][1,30]=101.
    return SimpleNamespace(dates=dates,arrays=a,lengths=np.full(3,390),valid=np.ones(3,dtype=bool),
        quality=pd.DataFrame(dict(date=dates.strftime('%Y-%m-%d'),reason=['','',''])),symbol='QQQ')


def opening(m,value):
    m.arrays['open'][1,0]=value
    m.arrays['low'][1,0]=min(m.arrays['low'][1,0],value)
    m.arrays['high'][1,0]=max(m.arrays['high'][1,0],value)


def one(m,cfg=None,div=None,profile='endpoints'):
    return simulate(m,prepare(m,div or {},profile),cfg or Config(),'2026-01-05','2026-01-05')


def test_short_fill_commission_and_borrow_reconcile_exactly():
    r=one(market());t=r.trades.iloc[0];q=980
    expected=q*(101.99-101.01)-2*q*.0035-q*101.99*.01/360
    assert t.sign==-1 and t.quantity==q and t.entry_price==101.99 and t.exit_price==101.01
    assert t.net_pnl==pytest.approx(expected) and r.daily.equity.iloc[-1]==pytest.approx(100000+expected)
    assert t.entry_time[11:16]=='09:31' and t.exit_time[11:16]=='10:00'


@pytest.mark.parametrize('opening',[98.,100.,102.])
def test_threshold_is_strict_including_float_ratio_boundary(opening):
    m=market();globals()['opening'](m,opening)
    assert one(m).trades.empty


def test_negative_gap_buys_and_minimum_fee_applies():
    m=market();opening(m,97.);m.arrays['open'][1,1]=97.;m.arrays['low'][1,1]=96.;m.arrays['high'][1,1]=103.
    r=one(m,Config(initial_capital=100));t=r.trades.iloc[0]
    assert t.sign==1 and t.quantity==1 and t.commission==.7 and t.borrow_fee==0


def test_dividend_removes_false_gap():
    m=market();opening(m,97.5)
    assert one(m,div={'2026-01-05':2.5}).trades.empty
    with pytest.raises(ValueError):one(m,div={'2026-01-05':-1})


@pytest.mark.parametrize('price',[128.52,123.48])
def test_exact_two_percent_after_decimal_dividend_is_not_an_event(price):
    m=market();m.arrays['close'][0,-1]=128.01;opening(m,price)
    assert one(m,div={'2026-01-05':2.01}).trades.empty


def test_missing_later_minutes_do_not_exclude_primary_trade():
    m=market()
    for a in m.arrays.values():a[1,100:114]=np.nan
    m.valid[1]=False;m.quality.loc[1,'reason']='missing_minutes'
    assert len(one(m).trades)==1 and one(m,profile='complete_days').trades.empty


def test_intermediate_halt_keeps_observed_endpoints_and_flags_missing_marks():
    m=market()
    for a in m.arrays.values():a[1,5:19]=np.nan
    m.valid[1]=False;m.quality.loc[1,'reason']='missing_minutes'
    t=one(m).trades.iloc[0]
    assert t.missing_holding_minutes==14 and np.isfinite(t.mae_observed_usd)


def test_missing_exit_has_explicit_exclusion_not_a_fabricated_fill():
    m=market();m.arrays['open'][1,30]=np.nan;r=one(m)
    assert r.trades.empty and r.daily.eligibility.iloc[0]=='missing_required_prices'


def test_previous_half_day_close_uses_its_actual_final_minute():
    m=market();m.lengths[0]=210;m.arrays['close'][0,209]=102.01
    assert one(m).trades.empty


def test_size_known_from_open_and_later_data_do_not_change_it():
    m=market();before=one(m).trades.iloc[0]
    for k in ['high','low','close']:m.arrays[k][1,31:]=9999.
    assert one(m).trades.iloc[0].net_pnl==before.net_pnl
    m.arrays['open'][1,1]=103.;m.arrays['high'][1,1]=104.
    assert one(m).trades.iloc[0].quantity==before.quantity


def test_momentum_control_uses_same_event_and_opposite_direction():
    m=market();r=one(m);c=one(m,Config(direction='momentum'))
    assert r.trades.date.tolist()==c.trades.date.tolist() and c.trades.sign.iloc[0]==1


def test_compounding_and_empty_result_are_supported():
    m=market();p=prepare(m,{})
    r=simulate(m,p,Config(),'2026-01-05','2026-01-06')
    assert r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())
    assert len(r.daily)==2
    m.arrays['open'][:,0]=100.
    r=one(m)
    assert r.trades.empty and r.daily.equity.iloc[-1]==100000
