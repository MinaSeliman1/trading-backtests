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
