from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sqlite3
import pytest
from orb_shadow.ledger import Ledger


def test_restart_active_position_is_marked_non_prospective(tmp_path):
    from test_core import session,bars
    import pandas as pd
    s=session();f=bars(s)
    with Ledger(tmp_path/'restart.sqlite',1000) as db:
        db.tick(s,f,s.open+pd.Timedelta(minutes=6))
    with Ledger(tmp_path/'restart.sqlite',1000) as db:
        before=db.get_account()
        db.record_restart()
        d=db.day(str(s.open.date()))
        assert not d['prospective'] and 'process_restart' in d['notes']
        assert db.get_account()==before
from test_core import session,bars


def test_persistence_keeps_entry_fee_and_resume_does_not_duplicate(tmp_path):
    path=tmp_path/'state.sqlite';s=session();f=bars(s)
    with Ledger(path,1000) as db:
        db.tick(s,f,s.open.replace(minute=35));db.tick(s,f,s.open.replace(minute=36))
        assert db.get_account()['balance']==pytest.approx(999.65)
    with Ledger(path,1000) as db:
        db.tick(s,f,s.open.replace(minute=36))
        assert db.get_account()['balance']==pytest.approx(999.65)
        db.tick(s,f,s.close)
        assert db.get_account()['balance']==pytest.approx(1009.1)
        db.tick(s,f,s.close)
        assert db.db.execute('select count(*) from trades').fetchone()[0]==1
        assert db.db.execute("select count(*) from events where kind='entry'").fetchone()[0]==1


def test_other_database_is_not_overwritten(tmp_path):
    path=tmp_path/'other.sqlite'
    con=sqlite3.connect(path);con.execute('create table important(value)');con.commit();con.close()
    with pytest.raises(ValueError,match='database'):Ledger(path)
    con=sqlite3.connect(path);assert con.execute("select name from sqlite_master where name='important'").fetchone();con.close()


def test_initial_capital_is_not_changed_on_restart(tmp_path):
    path=tmp_path/'state.sqlite'
    with Ledger(path,1000):pass
    with pytest.raises(ValueError,match='configuration'):Ledger(path,100000)
