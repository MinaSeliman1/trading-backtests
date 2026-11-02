import sqlite3,json,hashlib
import pytest
from qqq_eod import live

def test_noise_reader_is_readonly_and_omits_private_meta(tmp_path):
 path=tmp_path/'live.sqlite';c=sqlite3.connect(path)
 c.executescript('CREATE TABLE meta(key TEXT,value TEXT);CREATE TABLE days(day TEXT,quantity INTEGER,balance REAL);CREATE TABLE orders(cid TEXT,day TEXT,action TEXT);CREATE TABLE fills(qty INTEGER,sign INTEGER,actual REAL,modeled REAL,commission REAL,borrow REAL,realized REAL,timestamp TEXT,cid TEXT);CREATE TABLE decisions(key TEXT,data TEXT);')
 c.execute('INSERT INTO meta VALUES(?,?)',('paper_account_id','DO-NOT-EXPORT'))
 c.execute('INSERT INTO meta VALUES(?,?)',('completed_session:2026-10-30',json.dumps({'fully_prospective':True})))
 c.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-30',10,1000))
 for cid,action in [('open','open'),('close','close')]:c.execute('INSERT INTO orders VALUES(?,?,?)',(cid,'2026-10-30',action))
 c.execute('INSERT INTO fills VALUES(?,?,?,?,?,?,?,?,?)',(10,1,100,100.01,.35,0,0,'2026-10-30T10:00:00-04:00','open'))
 c.execute('INSERT INTO fills VALUES(?,?,?,?,?,?,?,?,?)',(10,-1,101,100.99,.35,0,9.8,'2026-10-30T15:59:00-04:00','close'))

 import pandas as pd
 for t in pd.date_range('2026-10-30 10:00','2026-10-30 15:30',freq='30min',tz='America/New_York'):
  c.execute('INSERT INTO decisions VALUES(?,?)',('2026-10-30:'+t.strftime('%H%M'),json.dumps({'status':'processed','target':1,'quantity':10,'decision_time':str(t),'observed_at':str(t+pd.Timedelta(minutes=1)),'private_value':'DO-NOT-EXPORT'})))
 c.commit();c.close();before=hashlib.sha256(path.read_bytes()).hexdigest();x=live.read_noise(path,'2026-10-30')
 assert x['qualified'] and x['net_pnl']==pytest.approx(9.1) and x['capital_before']==1000
 assert 'DO-NOT-EXPORT' not in json.dumps(x) and before==hashlib.sha256(path.read_bytes()).hexdigest()
 c=sqlite3.connect(path);key,payload=c.execute('SELECT key,data FROM decisions LIMIT 1').fetchone();d=json.loads(payload);d['observed_at']=str(pd.Timestamp(d['decision_time'])+pd.Timedelta(minutes=3));c.execute('UPDATE decisions SET data=? WHERE key=?',(json.dumps(d),key));c.commit();c.close()
 assert not live.read_noise(path,'2026-10-30')['qualified']

def test_op_journal_does_not_promote_old_qualification(tmp_path):
 with live.OperationalJournal(tmp_path/'op.sqlite') as db:
  a={'bot':'noise','day':'2026-10-30','qualified':True,'net_pnl':10}
  assert db.record(a) and not db.record(a)
  assert len(db.latest(qualified_only=True))==1
  db.record(dict(a,qualified=False));assert db.latest(qualified_only=True)==[] and len(db.latest())==1

def test_capital_and_coverage_differences_are_context_not_proven_bugs():
 stat={'capital_before':100000,'net_pnl':10,'decisions':[{'target':1}]}
 op={'capital_before':98000,'net_pnl':9.8,'qualified':False,'decisions':[{'target':1}]}
 x=live.compare(stat,op);assert x['classification']=='needs_investigation' and 'different_initial_capital' in x['context'] and 'unqualified_live' in x['context']
 assert not x['proven_engine_bug']

def test_actual_orb_trade_direction_is_categorical():
 stat={'capital_before':100000,'net_pnl':10,'trades':[{'direction':'LONG','quantity':10,'entry_price':100.,'exit_price':101.}],'decisions':[]}
 op=dict(stat,qualified=True)
 assert live.compare(stat,op)['differences']==[]
 op=dict(op,trades=[dict(op['trades'][0],direction='SHORT')])
 assert live.compare(stat,op)['differences'][0]['field']=='trades.direction'

def test_equal_prices_at_different_minutes_are_a_discrepancy():
 stat={'capital_before':100000,'net_pnl':10,'trades':[{'entry_time':'2026-10-30T09:35:00-04:00','exit_time':'2026-10-30T15:59:00-04:00','exit_reason':'eod_open'}]}
 op=dict(stat,qualified=True,trades=[dict(stat['trades'][0],entry_time='2026-10-30T13:36:00Z')])
 assert live.compare(stat,op)['differences'][0]['field']=='trades.entry_time'
 op['trades'][0]['entry_time']='2026-10-30T13:35:00Z';assert not live.compare(stat,op)['differences']
