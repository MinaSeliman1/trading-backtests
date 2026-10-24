from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pytest
import pandas as pd
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters
from qqq_paper.runtime import write_status
from qqq_paper.monitor import collect_report,initialize


def fixture(tmp_path):
    folder=tmp_path/'shadow-sip';folder.mkdir()
    store=Store(folder/'state.sqlite',Parameters(),'shadow','sip')
    now=pd.Timestamp('2026-10-20T20:55:00Z')
    return store,now


def marker(store,day,prospective=True):
    with store.db:store.put('completed_session:'+day,json.dumps(dict(day=day,fully_prospective=prospective)))


def test_baseline_preserves_balance_and_excludes_installation_day(tmp_path):
    store,now=fixture(tmp_path)
    with store.db:
        account=store._account();account['balance']=99237.196;store._save_account(account)
    baseline=initialize(tmp_path,now)
    assert baseline['first_session']=='2026-10-21'
    assert baseline['initial_realized_equity']==99237.196
    marker(store,'2026-10-20');marker(store,'2026-10-21',False);marker(store,'2026-10-22')
    write_status(tmp_path/'shadow-sip',state='running',utc='2026-10-22T20:55:00Z')
    report=collect_report(tmp_path,pd.Timestamp('2026-10-22T20:55:00Z'))
    assert report['fully_prospective_sessions']==1 and report['completed_sessions']==2
    assert report['coverage_gaps']==['2026-10-21']
    assert report['stage']=='waiting_for_observations'
    with store.db:store._save_account(dict(balance=1,position=0,entry=0))
    assert initialize(tmp_path,now)==baseline


def test_stale_status_and_pause_are_alerts_without_account_id(tmp_path):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    store.pause('missing historical data')
    with store.db:store.put('paper_account_id','PRIVATE-ACCOUNT-NUMBER')
    write_status(tmp_path/'shadow-sip',state='running',utc=str(now-pd.Timedelta(minutes=10)))
    report=collect_report(tmp_path,now)
    assert 'engine_status_stale' in report['alerts'] and 'ledger_paused' in report['alerts']
    assert 'PRIVATE-ACCOUNT-NUMBER' not in json.dumps(report)


def test_only_prospective_closed_trades_and_costs_count_toward_bilan(tmp_path):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    for day,good in [('2026-10-20',True),('2026-10-21',False),('2026-10-22',True)]:
        marker(store,day,good)
        store.intent(day+'o',day,'open',1,10,'1000')
        store.apply(dict(client_order_id=day+'o',filled_qty='10',filled_avg_price='100',status='filled',filled_at=day+'T14:00:00+00:00'))
        store.intent(day+'c',day,'close',-1,10,'1030')
        store.apply(dict(client_order_id=day+'c',filled_qty='10',filled_avg_price='101',status='filled',filled_at=day+'T14:30:00+00:00'))
    write_status(tmp_path/'shadow-sip',state='running',utc='2026-10-22T20:55:00Z')
    report=collect_report(tmp_path,pd.Timestamp('2026-10-22T20:55:00Z'))
    assert report['prospective_closed_trades']==1
    assert abs(report['prospective_realized_pnl']-9.1)<1e-9
    assert abs(report['all_period_realized_pnl']-18.2)<1e-9
    assert report['pending_orders']==0


def test_incomplete_coverage_explains_late_decisions_without_changing_journal(tmp_path):
    from qqq_paper.strategy import decision_times
    from qqq_paper.runtime import session_for,finalize_shadow_session
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    session=session_for('2026-10-21')
    for at in decision_times(session):
        observed=at+pd.Timedelta(seconds=65)
        if '1100'<=at.strftime('%H%M')<='1430':
            observed=pd.Timestamp('2026-10-21T18:55:51Z')
        store.record(f'2026-10-21:{at:%H%M}',dict(status='processed',decision_time=str(at),observed_at=str(observed)))
    finalize_shadow_session(store,session,session.close)
    before=list(store.db.execute('SELECT key,data FROM decisions ORDER BY key'))
    write_status(tmp_path/'shadow-sip',state='running',utc='2026-10-21T21:00:00Z')
    report=collect_report(tmp_path,pd.Timestamp('2026-10-21T21:00:00Z'))
    detail=report['coverage_details'][0]
    assert detail['day']=='2026-10-21' and detail['on_time_decisions']==4
    assert detail['late_decisions']==8 and detail['first_late_decision']=='11:00'
    assert detail['last_late_decision']=='14:30'
    assert detail['largest_delay_seconds']==14151
    assert report['fully_prospective_sessions']==0
    assert before==list(store.db.execute('SELECT key,data FROM decisions ORDER BY key'))


def test_monitor_surfaces_failed_stale_and_battery_power_protection(tmp_path):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    now=pd.Timestamp('2026-10-21T15:00:00Z')
    write_status(tmp_path/'shadow-sip',state='running',utc=str(now))
    power=tmp_path/'windows/power_status.json'
    power.write_text(json.dumps(dict(state='error',utc=str(now),on_ac=True,system_required=False)))
    assert 'power_protection_error' in collect_report(tmp_path,now)['alerts']
    power.write_text(json.dumps(dict(state='protected',utc=str(now-pd.Timedelta(minutes=5)),on_ac=True,system_required=True)))
    assert 'power_protection_stale' in collect_report(tmp_path,now)['alerts']
    power.write_text(json.dumps(dict(state='on_battery',utc=str(now),on_ac=False,system_required=False)))
    assert 'power_on_battery_during_session' in collect_report(tmp_path,now)['alerts']


@pytest.mark.parametrize('payload', [None,[],{'state':'protected','utc':None,'system_required':True},
    {'state':'protected','utc':'NaT','system_required':True}])
def test_invalid_power_status_alerts_instead_of_crashing_or_appearing_healthy(tmp_path,payload):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    now=pd.Timestamp('2026-10-21T15:00:00Z')
    write_status(tmp_path/'shadow-sip',state='running',utc=str(now))
    (tmp_path/'windows/power_status.json').write_text(json.dumps(payload))
    report=collect_report(tmp_path,now)
    assert 'power_protection_unavailable' in report['alerts']


def test_missing_power_status_alerts_once_supervisor_declares_guard_installed(tmp_path):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    write_status(tmp_path/'shadow-sip',state='running',utc=str(now))
    write_status(tmp_path/'windows',state='supervising_shadow',power_guard=True,utc=str(now))
    assert 'power_protection_unavailable' in collect_report(tmp_path,now)['alerts']


@pytest.mark.parametrize('ac,required', [(False,True),(True,'false'),(None,True)])
def test_contradictory_power_status_is_never_accepted_as_protected(tmp_path,ac,required):
    store,now=fixture(tmp_path);initialize(tmp_path,now)
    now=pd.Timestamp('2026-10-21T15:00:00Z')
    write_status(tmp_path/'shadow-sip',state='running',utc=str(now))
    (tmp_path/'windows/power_status.json').write_text(json.dumps(dict(state='protected',utc=str(now),on_ac=ac,system_required=required)))
    alerts=collect_report(tmp_path,now)['alerts']
    assert 'power_protection_inactive' in alerts or 'power_on_battery_during_session' in alerts
