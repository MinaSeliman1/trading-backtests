from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
import numpy as np
import pytest
from types import SimpleNamespace
from orb_shadow.core import account,advance


def session(half=False):
    day='2024-11-29' if half else '2024-04-30'
    return SimpleNamespace(open=pd.Timestamp(day+' 09:30',tz='America/New_York'),close=pd.Timestamp(day+(' 13:00' if half else ' 16:00'),tz='America/New_York'))


def bars(s,short=False):
    idx=pd.date_range(s.open,s.close-pd.Timedelta(minutes=1),freq='min');n=len(idx)
    f=pd.DataFrame(dict(open=np.full(n,100.),high=np.full(n,100.2),low=np.full(n,99.8),close=np.full(n,100.),volume=np.full(n,1000.)),index=idx)
    f.iloc[:5,f.columns.get_loc('open')]=100.5 if short else 99.5
    f.iloc[:5,f.columns.get_loc('high')]=101 if short else 100.5;f.iloc[:5,f.columns.get_loc('low')]=99.5 if short else 99
    f.iloc[-1,:4]=[99,100,98,99] if short else [101,102,100,101]
    return f


def apply(a,d,f,s,slot):return advance(a,d,f,s,s.open+pd.Timedelta(minutes=slot))


def timely(f,s):
    a=account(1000);d=None
    for slot in range(5,len(f)+1):a,d=apply(a,d,f.iloc[:5] if slot==5 else f.iloc[[slot-1]],s,slot)
    return a,d


def test_no_future_entry_before_first_five_bars_and_entry_bar_closed():
    s=session();f=bars(s);a=account(1000)
    a,d=apply(a,None,f,s,4);assert a['balance']==1000 and not d.get('entry_done')
    a,d=apply(a,d,f,s,5);assert d['phase']=='pending_entry' and d['intent']['quantity']==10 and a['balance']==1000
    a,d=apply(a,d,f,s,6);assert d['entry_done'] and a['balance']==pytest.approx(999.65)


def test_long_matches_frozen_backtest_costs_and_eod():
    s=session();a,d=timely(bars(s),s)
    assert d['trade']['net_pnl']==pytest.approx(9.1) and a['balance']==pytest.approx(1009.1)
    assert d['trade']['exit_reason']=='eod_open' and a['open_day'] is None and d['fully_observed']


def test_short_matches_borrow():
    s=session();a,d=timely(bars(s,True),s)
    assert d['trade']['net_pnl']==pytest.approx(9.072225)


def test_late_launch_skips_day_and_preserves_capital():
    s=session();a,d=apply(account(1000),None,bars(s),s,20)
    assert d['phase']=='skipped' and d['reason']=='late_start' and a['balance']==1000 and not d['fully_observed']


def test_doji_is_known_no_trade():
    s=session();f=bars(s);f.iloc[4,f.columns.get_loc('close')]=99.5
    a,d=apply(account(1000),None,f,s,5)
    assert d['phase']=='flat' and d['fully_observed'] and a['balance']==1000


def test_entry_beyond_stop_costed_roundtrip():
    s=session();f=bars(s);f.iloc[5,:4]=[98,98.2,97.8,98]
    a,d=timely(f,s);assert d['trade']['exit_reason']=='entry_marketable_stop' and a['balance']==pytest.approx(999.1)


@pytest.mark.parametrize('values,reason,reference',[
    ([98,100,97,98],'stop_gap',98),
    ([112,113,111,112],'target_gap',110),
    ([100,111,98,100],'stop_intrabar',99)])
def test_frozen_barriers_and_stop_priority(values,reason,reference):
    s=session();f=bars(s);f.iloc[10,:4]=values
    a,d=timely(f,s)
    assert d['trade']['exit_reason']==reason and d['trade']['exit_reference']==reference


def test_half_day_liquidation():
    s=session(True);a,d=timely(bars(s),s)
    assert pd.Timestamp(d['trade']['exit_time']).strftime('%H:%M')=='12:59'


def test_repeat_poll_and_restart_roundtrip_are_idempotent():
    s=session();f=bars(s);a,d=timely(f,s);before=json.dumps([a,d],sort_keys=True)
    a,d=apply(json.loads(json.dumps(a)),json.loads(json.dumps(d)),f,s,len(f)+10)
    assert json.dumps([a,d],sort_keys=True)==before


def test_active_restart_catches_up_but_does_not_claim_prospective_session():
    s=session();f=bars(s);a,d=apply(account(1000),None,f,s,5);a,d=apply(a,d,f,s,6)
    a,d=apply(a,d,f,s,len(f))
    assert a['balance']==pytest.approx(1009.1) and not d['fully_observed'] and 'late_observation' in d['notes']


def test_missing_active_minute_keeps_known_entry_fee_and_position():
    s=session();f=bars(s);a,d=apply(account(1000),None,f,s,5);a,d=apply(a,d,f,s,6)
    bad=f.drop(f.index[7]);a,d=apply(a,d,bad,s,11)
    assert d['phase']=='unresolved' and a['open_day'] is not None and a['balance']==pytest.approx(999.65)
    assert not d['fully_observed'] and 'data_gap' in d['notes']


def test_missing_entry_not_shifted_or_replayed_later():
    s=session();f=bars(s);a,d=apply(account(1000),None,f,s,5)
    a,d=apply(a,d,f.drop(f.index[5]),s,8)
    assert d['phase']=='skipped' and a['balance']==1000 and not d.get('entry_done')


def test_bad_current_bar_cannot_retroactively_change_a_closed_trade():
    s=session();f=bars(s);f.iloc[7,:4]=[100,100.2,98,100]
    a,d=timely(f,s);original=d['trade'].copy();f.iloc[50:,:4]=np.nan
    a,d=apply(a,d,f,s,len(f));assert d['trade']==original


def test_new_day_cannot_hide_an_unresolved_old_position():
    s=session();a=account(1000);a['open_day']='2024-04-29'
    with pytest.raises(RuntimeError,match='unresolved'):apply(a,None,bars(s),s,5)


def test_duplicate_timestamps_refused_before_any_mutation():
    s=session();f=bars(s);a=account(1000)
    with pytest.raises(ValueError,match='duplicate'):apply(a,None,pd.concat([f,f.iloc[:1]]),s,6)
    assert a['balance']==1000


def test_unresolved_entry_bar_preserves_known_entry_reference_for_reconciliation():
    s=session();f=bars(s);f.iloc[5,f.columns.get_loc('close')]=np.nan
    a,d=apply(account(1000),None,f,s,5);a,d=apply(a,d,f,s,6)
    assert d['phase']=='unresolved' and d['entry_reference']==100 and d['entry_price']==100.01


def test_first_five_revision_is_flagged_and_original_quantity_retained():
    s=session();f=bars(s);a,d=apply(account(1000),None,f,s,5)
    f.iloc[4,f.columns.get_loc('close')]=99.6
    a,d=apply(a,d,f,s,6)
    assert d['intent']['quantity']==10 and 'source_revision' in d['notes'] and not d['prospective']
