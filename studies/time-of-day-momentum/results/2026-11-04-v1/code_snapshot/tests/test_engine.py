from pathlib import Path
import sys,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from seasonal.engine import Config,training,prepare,simulate,trace,Unresolved,CLOCKS


def market(n=70,negative=False):
    dates=pd.bdate_range('2023-01-02',periods=n);a={k:np.full((n,390),100.,dtype=float) for k in ('open','high','low','close','volume')}
    quality=[]
    for i,date in enumerate(dates):
        returns=np.array([(-.002 if negative else .002)+(.001 if i%2 else -.001)]+[(.0005 if (i+j)%2 else -.0005) for j in range(10)])
        anchors=np.r_[100.,100.*np.cumprod(1+returns)];slots=np.r_[31,CLOCKS+31]
        p=np.interp(np.arange(390),slots,anchors)
        for k in ('open','close'):a[k][i]=p
        a['high'][i]=p+.01;a['low'][i]=p-.01;a['volume'][i]=1000.
        opened=pd.Timestamp(str(date.date())+' 09:30',tz='America/New_York')
        quality.append(dict(session_open=str(opened),session_close=str(opened+pd.Timedelta(minutes=390)),reason=''))
    return SimpleNamespace(dates=dates,arrays=a,lengths=np.full(n,390),valid=np.ones(n,dtype=bool),quality=pd.DataFrame(quality),symbol='TEST')


def one(m,c=None):
    c=c or Config();f=prepare(m,c);d=str(m.dates[-1].date());return simulate(m,f,c,d,d)


def test_first_known_clock_and_next_minute_entry():
    m=market();f=prepare(m,Config())[-1]
    assert f['reason']=='eligible' and f['historical_slot']==30 and f['decision_slot']==30
    assert f['entry_slot']==31 and f['scheduled_exit_slot']==61 and f['sign']==1
    assert f['sizing_price']==m.arrays['close'][-1,29] and f['stop_price']<f['sizing_price']


def test_40_prior_sessions_exclude_current_and_future():
    m=market(73);c=Config();before=prepare(m,c)[69]
    for v in m.arrays.values():v[69:,100:]*=2
    after=prepare(m,c)[69]
    assert before==after
    for v in m.arrays.values():v[70:]*=2
    assert prepare(m,c)[69]==before


def test_current_future_hole_does_not_change_candidate_but_complete_filter_excludes():
    m=market();c=Config();before=prepare(m,c)[-1]
    m.arrays['close'][-1,200]=np.nan;m.valid[-1]=False
    assert prepare(m,c)[-1]==before
    r=one(m,c);assert r.trades.empty and r.daily.iloc[0].eligibility=='excluded_incomplete_day'
    r=one(m,Config(quality='resolved_prefix'));assert len(r.trades)==1


def test_missing_earlier_history_cannot_promote_later_clock():
    m=market();m.arrays['open'][-2,40]=np.nan
    f=prepare(m,Config())[-1]
    assert f['reason']=='unknown_history' and f['historical_slot'] is None


def test_no_skipping_missing_scheduled_history():
    m=market(90);m.arrays['open'][-20,40]=np.nan
    assert prepare(m,Config())[-1]['reason']=='unknown_history'


def test_warmup_does_not_trade():
    m=market(40);assert all(f['reason']=='warmup' for f in prepare(m,Config()))


def test_zero_variance_never_becomes_infinite_t_signal():
    m=market();
    for k in ('open','close'):m.arrays[k][:]=100.
    m.arrays['high'][:]=100.1;m.arrays['low'][:]=99.9
    assert prepare(m,Config())[-1]['reason']=='no_signal'


def test_unknown_current_prefix_abstains_without_delaying_entry():
    m=market();m.arrays['low'][-1,20]=np.nan
    assert prepare(m,Config())[-1]['reason']=='unknown_current_context'


def test_long_only_consumes_negative_candidate():
    m=market(negative=True);assert prepare(m,Config(mode='long_only'))[-1]['reason']=='direction_filtered'


@pytest.mark.parametrize('mode',['inverse','control_same_clock_long','control_fixed_clock','control_random_clock'])
def test_controls_and_inverse_are_deterministic_and_causal(mode):
    m=market(negative=True);c=Config(mode=mode);before=prepare(m,c)[-1]
    assert before['reason']=='eligible'
    assert before['decision_slot'] in CLOCKS
    if mode=='control_fixed_clock':assert before['decision_slot']==30
    if mode in ('inverse','control_same_clock_long'):assert before['sign']==1
    for v in m.arrays.values():v[-1,370:]*=2
    assert prepare(m,c)[-1]==before


def test_half_session_never_schedules_after_close():
    m=market();m.lengths[-1]=210;m.quality.loc[len(m.dates)-1,'session_close']=str(pd.Timestamp(m.quality.iloc[-1].session_open)+pd.Timedelta(minutes=210))
    f=prepare(m,Config(mode='control_random_clock'))[-1]
    assert f['scheduled_exit_slot']<=209


def test_training_windows_follow_local_clock_across_dst():
    m=market();m.quality.loc[0,'session_open']='2023-03-10 09:30:00-05:00';m.quality.loc[1,'session_open']='2023-03-13 09:30:00-04:00'
    t=training(m,40);assert t['returns'].shape==(70,11)
    assert np.isfinite(t['returns'][:,0]).all()


def test_long_costs_and_compounding_reconcile():
    m=market();r=one(m,Config(initial_capital=1000));t=r.trades.iloc[0]
    assert t.quantity==10 and t.commission==pytest.approx(.7) and t.friction_cost==pytest.approx(.2)
    assert t.net_pnl==pytest.approx(t.price_move_pnl-t.commission-t.friction_cost)
    assert r.daily.iloc[-1].equity==pytest.approx(1000+t.net_pnl)


def test_short_costs_include_one_day_borrow():
    m=market(negative=True);r=one(m,Config(initial_capital=1000));t=r.trades.iloc[0]
    assert t.sign==-1 and t.borrow_fee==pytest.approx(t.quantity*t.entry_price*.01/360)
    assert t.net_pnl==pytest.approx(t.price_move_pnl-t.commission-t.friction_cost-t.borrow_fee)


@pytest.mark.parametrize('negative,opening',[(False,98.),(True,102.)])
def test_entry_beyond_stop_is_immediate_costed_roundtrip(negative,opening):
    m=market(negative=negative)
    for k in ('open','close'):m.arrays[k][-1,31]=opening
    m.arrays['high'][-1,31]=opening+.1;m.arrays['low'][-1,31]=opening-.1
    r=one(m);t=r.trades.iloc[0]
    assert t.exit_slot==31 and t.exit_reason=='entry_marketable_stop'
    assert t.net_pnl<0 and t.entry_reference==t.exit_reference


@pytest.mark.parametrize('negative',[False,True])
def test_intrabar_stop_uses_level_and_excludes_terminal_wicks(negative):
    m=market(negative=negative);f=prepare(m,Config())[-1];stop=f['stop_price']
    m.arrays['high' if negative else 'low'][-1,33]=stop
    p=trace(m,f,Config());assert p['exit_slot']==33 and p['exit_reference']==stop and p['exit_reason']=='stop_intrabar'
    assert len(p['closes'])==2


def test_scheduled_exit_ignores_future_terminal_wicks():
    m=market();f=prepare(m,Config())[-1];m.arrays['low'][-1,61]=1.
    p=trace(m,f,Config());assert p['exit_slot']==61 and p['exit_reason']=='scheduled_open'


def test_open_gap_stop_gets_adverse_open_not_level():
    m=market();f=prepare(m,Config())[-1];m.arrays['open'][-1,33]=98.
    p=trace(m,f,Config());assert p['exit_reference']==98 and p['exit_reason']=='stop_gap'


def test_missing_held_minute_is_unresolved_and_preserves_known_costs():
    m=market();m.arrays['open'][-1,34]=np.nan;m.valid[-1]=False
    r=one(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and len(r.unresolved)==1
    assert r.unresolved.iloc[0].known_entry_commission>0 and r.daily.iloc[0].conditionally_excluded
    assert np.isnan(r.daily.iloc[0].observed_return)


def test_missing_delay_bar_outside_holding_does_not_hide_resolved_trade():
    m=market();m.arrays['open'][-1,30]=np.nan;m.valid[-1]=False
    assert len(one(m,Config(quality='resolved_prefix')).trades)==1


def test_quantity_does_not_resize_from_future_open():
    m=market();before=one(m).trades.iloc[0]
    for k in ('open','close'):m.arrays[k][-1,31]=101.
    m.arrays['high'][-1,31]=101.1;m.arrays['low'][-1,31]=100.9
    after=one(m).trades.iloc[0]
    assert after.quantity==before.quantity and after.entry_fill_leverage>before.entry_fill_leverage


def test_config_rejects_invalid_parameters():
    for args in (dict(lookback=1),dict(threshold=0),dict(stop_multiple=0),dict(slippage=-1),dict(mode='oracle'),dict(quality='future')):
        with pytest.raises(ValueError):Config(**args)


def test_immediate_roundtrip_mae_includes_modeled_exit_friction():
    m=market()
    for k in ('open','close'):m.arrays[k][-1,31]=98.
    m.arrays['high'][-1,31]=98.1;m.arrays['low'][-1,31]=97.9
    t=one(m).trades.iloc[0]
    assert t.mae_observed_usd==pytest.approx(-t.friction_cost)
