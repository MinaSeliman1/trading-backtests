import pytest
from qqq_eod import journal as j
V={'strategy_commit':'test','costs':'fixed','release':'test'}
def result(before=100000,net=-10,status='complete'):
 return dict(status=status,capital_before=before,capital_after=before+net if status=='complete' else None,net_pnl=net if status=='complete' else None,known_balance=before+net,open_position=0 if status=='complete' else 10,known_commission=.35,trades=[],decisions=[],operationally_observed=False)

def test_version_and_closed_results_are_immutable(tmp_path):
 p=tmp_path/'ledger.sqlite'
 with j.Journal(p,V,'2026-11-02') as db:
  assert db.record('noise','2026-11-02',result(),{'sha':'a'})
  assert not db.record('noise','2026-11-02',result(),{'sha':'a'})
  assert db.balance('noise')==99990 and db.attempt_count()==1
  with pytest.raises(ValueError):db.record('noise','2026-11-02',result(net=100),{'sha':'a'})
 with pytest.raises(ValueError):j.Journal(p,dict(V,costs='changed'),'2026-11-02')

def test_unknown_blocks_only_one_bot_and_preserves_fees(tmp_path):
 with j.Journal(tmp_path/'x.sqlite',V,'2026-11-02') as db:
  db.record('noise','2026-11-02',result(net=-.35,status='unresolved'),{'sha':'a'})
  assert db.balance('noise')==100000 and db.session('noise','2026-11-02')['result']['known_balance']==99999.65
  with pytest.raises(ValueError):db.record('noise','2026-11-03',result(),{'sha':'b'})
  db.record('orb','2026-11-02',result(net=25),{'sha':'a'})
  assert db.balance('orb')==100025
  db.record('noise','2026-11-02',result(net=-20),{'sha':'revised'})
  assert db.balance('noise')==99980 and db.attempt_count()==3

def test_no_skipping_and_no_dates_before_registration(tmp_path):
 with j.Journal(tmp_path/'x.sqlite',V,'2026-11-02') as db:
  with pytest.raises(ValueError):db.record('orb','2026-10-30',result(),{'sha':'a'})
  with pytest.raises(ValueError):db.record('orb','2026-11-03',result(),{'sha':'a'})
  db.record('orb','2026-11-02',result(),{'sha':'a'})
  with pytest.raises(ValueError):db.record('orb','2026-11-03',result(before=100000),{'sha':'b'})

def test_sqlite_backup_is_coherent(tmp_path):
 import sqlite3
 with j.Journal(tmp_path/'source.sqlite',V,'2026-11-02') as db:
  db.record('orb','2026-11-02',result(),{'sha':'a'});db.snapshot(tmp_path/'backup.sqlite')
 con=sqlite3.connect('file:'+str(tmp_path/'backup.sqlite')+'?mode=ro',uri=True)
 assert con.execute('select count(*) from sessions').fetchone()[0]==1;con.close()
