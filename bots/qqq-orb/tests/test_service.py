from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from orb_shadow.ledger import Ledger
from orb_shadow.service import cycle
from test_core import session,bars


def test_entry_deadline_uses_clock_after_slow_data_request(tmp_path):
    s=session();f=bars(s);moments=iter([s.open+pd.Timedelta(minutes=22),s.open+pd.Timedelta(minutes=24)])
    class Data:
        def bars(self,start,end,feed):assert feed=='sip';return f.iloc[:6]
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        result=cycle(db,Data(),lambda:next(moments))
        assert result['state']=='skipped' and db.get_account()['balance']==1000


def test_completed_session_does_not_keep_fetching_or_reprice_trade(tmp_path):
    s=session();f=bars(s)
    class Data:
        def bars(self,*args):raise AssertionError('no more source data needed')
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        for minute in (5,6,390):db.tick(s,f,s.open+pd.Timedelta(minutes=minute))
        result=cycle(db,Data(),lambda:s.close+pd.Timedelta(minutes=20))
        assert result['state']=='closed' and db.get_account()['balance']>1000


def test_restart_next_day_reconciles_existing_trade_without_new_entry(tmp_path):
    s=session();f=bars(s)
    class Data:
        def bars(self,start,end,feed):
            assert start==s.open and end==s.close and feed=='sip'
            return f
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        db.tick(s,f,s.open+pd.Timedelta(minutes=6))
        assert db.get_account()['open_day']==str(s.open.date())
        result=cycle(db,Data(),lambda:s.open+pd.Timedelta(days=1,hours=2))
        assert result['state']=='closed' and db.get_account()['open_day'] is None
        assert db.get_account()['balance']==pytest.approx(1009.1)
        assert not db.day(str(s.open.date()))['fully_observed']
        assert db.db.execute('SELECT COUNT(*) FROM trades').fetchone()[0]==1


def test_startup_retries_network_failure_then_recovers_without_reset_or_secret_log(tmp_path,monkeypatch):
    import json
    import orb_shadow.service as svc
    from contextlib import nullcontext
    from qqq_paper.alpaca import DataConnectionError
    snapshots=[];attempts=[];cleared=[]
    monkeypatch.setattr(svc,'PowerGuard',lambda root:nullcontext())
    monkeypatch.setattr(svc.WindowsVault,'load',lambda self:('FAKE-KEY-DO-NOT-LOG','FAKE-SECRET-DO-NOT-LOG'))
    class Transport:
        def __init__(self,*args):pass
        def clear(self):cleared.append(True)
    monkeypatch.setattr(svc,'ReadOnlyTransport',Transport)
    def probe(data):
        attempts.append(True)
        if len(attempts)==1:raise DataConnectionError('dns')
        return dict(state='read_only_sip_connected',broker_orders=False)
    monkeypatch.setattr(svc,'probe',probe)
    monkeypatch.setattr(svc,'cycle',lambda *a,**k:dict(state='waiting_opening'))
    monkeypatch.setattr(svc,'write_status',lambda root,**fields:snapshots.append(fields))
    monkeypatch.setattr(svc,'utcnow',lambda:pd.Timestamp('2026-10-28T12:00Z'))
    pauses=[]
    def pause(stop,seconds):
        pauses.append(seconds)
        if len(pauses)==2:stop.touch()
    monkeypatch.setattr(svc,'pause',pause)
    with Ledger(tmp_path/'state.sqlite') as db:
        with db.db:db.put('first_session','2026-10-26')
    assert svc.main(['--runtime',str(tmp_path)])==0
    assert len(attempts)==2 and len(cleared)==2 and pauses==[60,5]
    retries=[v for v in snapshots if v['state']=='startup_retry']
    assert len(retries)==1 and retries[0]['network_reason']=='dns'
    assert any(v['state']=='checking_connection' for v in snapshots)
    assert any(v['state']=='waiting_opening' for v in snapshots)
    with Ledger(tmp_path/'state.sqlite') as db:
        assert db.get_account()['balance']==100000 and db.get('first_session')=='2026-10-26'
        assert db.db.execute('SELECT COUNT(*) FROM trades').fetchone()[0]==0
    assert 'DO-NOT-LOG' not in json.dumps(snapshots)+(tmp_path/'background.log').read_text(encoding='utf-8')
