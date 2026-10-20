from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters


def filled(cid,qty,price,status='filled'):
    return dict(id=cid,client_order_id=cid,filled_qty=str(qty),filled_avg_price=str(price),status=status,filled_at='2026-10-20T14:00:01Z')


def test_costs_long_roundtrip_and_repeated_snapshot_idempotent(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip')
    s.intent('a','2026-10-20','open',1,100,'10:00')
    s.apply(filled('a',100,100));s.apply(filled('a',100,100))
    assert s.position==100 and s.balance==pytest.approx(99999.65)
    s.intent('b','2026-10-20','close',-1,100,'10:30');s.apply(filled('b',100,101))
    assert s.position==0 and s.balance==pytest.approx(100097.3)
    assert len(s.fills())==2


def test_partial_fill_charges_one_minimum_per_order_and_cumulative_average(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'paper','sip');s.intent('a','2026-10-20','open',1,1000,'10:00')
    s.apply(filled('a',10,100,'partially_filled'));s.apply(filled('a',1000,101))
    assert s.balance==pytest.approx(99996.5)
    assert s.entry==pytest.approx(101.01)
    assert sum(x['commission'] for x in s.fills())==pytest.approx(3.5)


def test_short_borrow_and_restart_preserve_position_and_net_equity(tmp_path):
    path=tmp_path/'s.db';s=Store(path,Parameters(),'paper','sip')
    s.intent('a','2026-10-20','open',-1,100,'10:00');s.apply(filled('a',100,100));s.close()
    s=Store(path,Parameters(),'paper','sip')
    assert s.position==-100
    s.intent('b','2026-10-20','close',1,100,'10:30');s.apply(filled('b',100,99))
    assert s.balance==pytest.approx(100097.3-100*99.99*.01/360)
    with pytest.raises(ValueError,match='configuration'):Store(path,Parameters(),'paper','iex')


def test_intent_collision_and_overfill_fail_without_corrupting_ledger(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'paper','sip');s.intent('a','2026-10-20','open',1,100,'10:00')
    with pytest.raises(ValueError):s.intent('a','2026-10-20','open',-1,100,'10:00')
    with pytest.raises(ValueError):s.apply(filled('a',101,100))
    assert s.position==0 and s.balance==100000


def test_incomplete_filled_status_and_price_corrections_are_rejected(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'paper','iex');s.intent('a','2026-10-20','open',1,100,'10:00')
    with pytest.raises(ValueError):s.apply(filled('a',50,100,'filled'))
    s.apply(filled('a',50,100,'partially_filled'))
    with pytest.raises(ValueError):s.apply(filled('a',50,101,'partially_filled'))
    assert s.position==50


def test_unintended_multiday_short_charges_elapsed_calendar_days(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'paper','iex');s.intent('a','2026-10-16','open',-1,100,'10:00')
    x=filled('a',100,100);x['filled_at']='2026-10-16T14:00:00Z';s.apply(x)
    s.intent('b','2026-10-19','close',1,100,'10:00');y=filled('b',100,99);y['filled_at']='2026-10-19T14:00:00Z';s.apply(y)
    assert s.fills()[-1]['borrow']==pytest.approx(3*100*99.99*.01/360)
