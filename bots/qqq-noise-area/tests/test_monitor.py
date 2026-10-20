from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
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
