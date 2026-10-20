from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters
from qqq_paper.runner import Executor,PendingOrder,paper_due
import pandas as pd
from test_ledger import filled
from qqq_paper.alpaca import OrderNotSent


class Broker:
    def __init__(self):self.orders={};self.calls=[];self.timeout=False;self.partial=False
    def get_order(self,cid):return self.orders.get(cid)
    def submit(self,cid,action,sign,qty):
        self.calls.append((action,sign,qty));snapshot=filled(cid,qty//2 if self.partial else qty,100,'partially_filled' if self.partial else 'filled')
        self.orders[cid]=snapshot
        if self.timeout:raise TimeoutError('ambiguous send')
        return snapshot
    def cancel(self,provider_id):self.orders[provider_id]['status']='canceled'


def setup(tmp_path):
    s=Store(tmp_path/'state.db',Parameters(),'paper','iex');b=Broker();e=Executor(s,b,wait_seconds=0,sleep=lambda _:None)
    return s,b,e


def test_timeout_after_acceptance_and_restart_do_not_resubmit(tmp_path):
    s,b,e=setup(tmp_path);b.timeout=True
    assert e.target(1,100,'2026-10-20','10:00')
    assert e.target(1,100,'2026-10-20','10:00')
    assert len(b.calls)==1 and s.position==100


def test_prepared_unknown_intent_is_never_blindly_resent(tmp_path):
    s,b,e=setup(tmp_path)
    cid=e.cid('2026-10-20','10:00','open',1)
    s.intent(cid,'2026-10-20','open',1,100,'10:00')
    with pytest.raises(PendingOrder):e.target(1,100,'2026-10-20','10:00')
    assert not b.calls and s.position==0


def test_reversal_requires_confirmed_close_before_second_order(tmp_path):
    s,b,e=setup(tmp_path);e.target(1,100,'2026-10-20','10:00')
    assert e.target(-1,100,'2026-10-20','10:30')
    assert [x[0] for x in b.calls]==['open','close','open'] and s.position==-100


def test_partial_close_canceled_and_no_reverse_open(tmp_path):
    s,b,e=setup(tmp_path);e.target(1,100,'2026-10-20','10:00');b.partial=True
    assert not e.target(-1,100,'2026-10-20','10:30')
    assert [x[0] for x in b.calls]==['open','close'] and s.position==50
    assert not s.pending()


def test_no_late_orders_on_old_bars_or_missed_decision():
    at=pd.Timestamp('2026-10-20 10:00',tz='America/New_York')
    assert paper_due(at+pd.Timedelta(seconds=5),at)
    assert not paper_due(at+pd.Timedelta(seconds=21),at)
    assert not paper_due(at-pd.Timedelta(seconds=1),at)


def test_local_no_post_refusal_leaves_no_unresolvable_prepared_intent(tmp_path):
    s,b,e=setup(tmp_path)
    def refuse(*args):raise OrderNotSent('expired decision')
    b.submit=refuse
    assert not e.target(1,100,'2026-10-20','10:00')
    assert not s.pending() and s.position==0


def test_failed_first_lookup_does_not_create_an_unsent_intent(tmp_path):
    s,b,e=setup(tmp_path)
    b.get_order=lambda cid:(_ for _ in ()).throw(ConnectionError('read unavailable'))
    with pytest.raises(ConnectionError):e.target(1,100,'2026-10-20','10:00')
    assert not s.pending() and not b.calls
