from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from orb_shadow.ledger import Ledger
from orb_shadow.monitor import collect
from test_core import session,bars


def test_monitor_is_read_only_and_distinguishes_replay_from_prospective(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        with db.db:db.put('first_session',str(s.open.date()))
        for slot in (5,6,390):db.tick(s,f,s.open+pd.Timedelta(minutes=slot))
    status={'state':'closed','utc':str(s.close+pd.Timedelta(minutes=20))}
    (tmp_path/'status.json').write_text(json.dumps(status))
    before=(tmp_path/'state.sqlite').read_bytes()
    r=collect(tmp_path,s.close+pd.Timedelta(minutes=20))
    assert r['closed_trades']==1 and r['fully_observed_sessions']==0
    assert r['coverage_gaps']==[str(s.open.date())]
    assert r['balance']==pytest.approx(1009.1) and r['stage']=='waiting'
    assert (tmp_path/'state.sqlite').read_bytes()==before


def test_ordinary_intraday_position_is_not_a_failure(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        with db.db:db.put('first_session',str(s.open.date()))
        db.tick(s,f,s.open+pd.Timedelta(minutes=6))
    real=s.open+pd.Timedelta(minutes=22)
    (tmp_path/'status.json').write_text(json.dumps(dict(state='active',utc=str(real))))
    r=collect(tmp_path,real)
    assert r['open_day']==str(s.open.date()) and not r['alerts']
