"""Separate statistical ledger: atomic, version-bound, no unknown cash days."""
from pathlib import Path
import sqlite3,json,hashlib,math
import pandas as pd
from .schedule import calendar

def dump(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def economic(result):return {k:v for k,v in result.items() if k!='evaluated_utc'}

class Journal:
 def __init__(self,path,version,first_day):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.first_day=str(first_day)
  self.db=sqlite3.connect(self.path,timeout=10);self.db.row_factory=sqlite3.Row
  try:
   self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
   self.db.executescript('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS accounts(bot TEXT PRIMARY KEY,balance REAL NOT NULL); CREATE TABLE IF NOT EXISTS sessions(bot TEXT NOT NULL,day TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(bot,day)); CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,bot TEXT NOT NULL,day TEXT NOT NULL,fingerprint TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(bot,day,fingerprint));')
   config=dump(dict(version=version,first_day=self.first_day,initial_capital=100000))
   row=self.db.execute('SELECT value FROM meta WHERE key=?',('configuration',)).fetchone()
   if row and row[0]!=config:raise ValueError('journal version changed; reset refused')
   with self.db:
    self.db.execute('INSERT OR IGNORE INTO meta VALUES(?,?)',('configuration',config))
    for bot in ('noise','orb'):self.db.execute('INSERT OR IGNORE INTO accounts VALUES(?,?)',(bot,100000.))
  except Exception:self.db.close();raise
 def balance(self,bot):
  row=self.db.execute('SELECT balance FROM accounts WHERE bot=?',(bot,)).fetchone()
  if row is None:raise ValueError('unknown bot')
  return float(row[0])
 def session(self,bot,day):
  row=self.db.execute('SELECT payload FROM sessions WHERE bot=? AND day=?',(bot,day)).fetchone()
  return json.loads(row[0]) if row else None
 def attempt_count(self):return self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
 def next_due(self,bot,through):
  if str(through)<self.first_day:return None
  days=calendar(self.first_day,through).sessions_in_range(self.first_day,str(through))
  for day in days:
   name=str(day.date());row=self.session(bot,name)
   if not row or row['status']!='complete':return name
  return None
 def record(self,bot,day,result,inputs):
  self.balance(bot)
  if result['status'] not in ('complete','unresolved'):raise ValueError('unknown result status')
  if str(day)<self.first_day:raise ValueError('date precedes registration')
  value=dict(status=result['status'],result=result,inputs=inputs)
  signature=hashlib.sha256(dump(dict(result=economic(result),inputs=inputs)).encode()).hexdigest()
  with self.db:
   self.db.execute('BEGIN IMMEDIATE');old=self.session(bot,day)
   if old and old['status']=='complete':
    if economic(old['result'])!=economic(result) or old['inputs']!=inputs:raise ValueError('closed session mutation refused')
    return False
   if self.next_due(bot,day)!=day:raise ValueError('earlier unresolved or missing session')
   before=self.balance(bot)
   if not math.isfinite(result['capital_before']) or abs(result['capital_before']-before)>1e-6:raise ValueError('incorrect starting capital')
   duplicate=self.db.execute('SELECT 1 FROM attempts WHERE bot=? AND day=? AND fingerprint=?',(bot,day,signature)).fetchone()
   if duplicate:return False
   if result['status']=='complete':
    after=result['capital_after'];net=result['net_pnl']
    if not all(math.isfinite(v) for v in (after,net)) or abs(after-before-net)>1e-6 or result.get('open_position')!=0:raise ValueError('inconsistent closed result')
    self.db.execute('UPDATE accounts SET balance=? WHERE bot=?',(after,bot))
   elif result.get('net_pnl') is not None or result.get('capital_after') is not None:raise ValueError('unresolved cannot be closed cash')
   payload=dump(value);self.db.execute('INSERT INTO attempts(bot,day,fingerprint,payload) VALUES(?,?,?,?)',(bot,day,signature,payload))
   self.db.execute('INSERT INTO sessions VALUES(?,?,?,?) ON CONFLICT(bot,day) DO UPDATE SET status=excluded.status,payload=excluded.payload',(bot,day,result['status'],payload))
  return True
 def snapshot(self,target):
  target=Path(target)
  if target.exists():raise ValueError('snapshot overwrite refused')
  target.parent.mkdir(parents=True,exist_ok=True)
  backup=sqlite3.connect(target)
  try:self.db.backup(backup)
  finally:backup.close()
 def export(self):
  return dict(accounts={b:self.balance(b) for b in ('noise','orb')},sessions=[dict(bot=r['bot'],day=r['day'],**json.loads(r['payload'])) for r in self.db.execute('SELECT * FROM sessions ORDER BY day,bot')],attempts=self.attempt_count(),first_day=self.first_day)
 def close(self):
  self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
