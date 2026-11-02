"""Read-only live snapshots and a distinct operational observation journal."""
from pathlib import Path
from datetime import datetime,timezone,date
import sqlite3,json,hashlib,math
import pandas as pd
from .schedule import calendar
from .source import rows_sha
FIELDS=('status','decision_time','observed_at','target','quantity','price','upper','lower','vwap','sigma','volatility','opening','previous_close_adjusted')
def dump(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def connect_readonly(path):
 p=Path(path).resolve()
 if not p.is_file():raise FileNotFoundError('live journal unavailable')
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2);c.row_factory=sqlite3.Row;c.execute('BEGIN');return c

def read_noise(path,day):
 date.fromisoformat(day);c=connect_readonly(path)
 try:
  row=c.execute('SELECT quantity,balance FROM days WHERE day=?',(day,)).fetchone();before=float(row['balance']) if row else None
  m=c.execute('SELECT value FROM meta WHERE key=?',('completed_session:'+day,)).fetchone();marker=json.loads(m[0]) if m else {}
  decisions=[]
  for v in c.execute('SELECT data FROM decisions WHERE key LIKE ? ORDER BY key',(day+':%',)):
   d=json.loads(v[0]);decisions.append({k:d[k] for k in FIELDS if k in d})
  fills=[dict(r) for r in c.execute('SELECT f.qty,f.sign,f.actual,f.modeled,f.commission,f.borrow,f.realized,f.timestamp,o.action FROM fills f JOIN orders o ON f.cid=o.cid WHERE o.day=? ORDER BY f.rowid',(day,))]
  prior=c.execute('SELECT coalesce(sum(f.qty*f.sign),0) FROM fills f JOIN orders o ON f.cid=o.cid WHERE o.day<?',(day,)).fetchone()[0]
  position=int(prior+sum(f['qty']*f['sign'] for f in fills));known_net=sum(f['realized']-f['commission']-f['borrow'] for f in fills)
  schedule=calendar(day,day).schedule.loc[pd.Timestamp(day)];expected=len(pd.date_range(schedule['open']+pd.Timedelta(minutes=30),schedule['close']-pd.Timedelta(minutes=1),freq='30min'))
  def on_time(d):
   try:
    at=pd.Timestamp(d['decision_time']);seen=pd.Timestamp(d['observed_at'])
    return at.tz is not None and seen.tz is not None and 0<=(seen-at).total_seconds()<=120
   except (KeyError,ValueError,TypeError):return False
  qualified=bool(marker.get('fully_prospective') and len(decisions)==expected and all(d.get('status')=='processed' and on_time(d) for d in decisions) and position==0 and prior==0)
  net=known_net if before is not None and position==0 and prior==0 else None
  result=dict(bot='noise',day=day,qualified=qualified,capital_before=before,capital_after=before+net if net is not None else None,net_pnl=net,known_net=known_net,position_before=int(prior),position_after=position,decisions=decisions,fills=fills,model_version_recorded=False,observations_kind='live_shadow',commission=sum(f['commission'] for f in fills),borrow_fee=sum(f['borrow'] for f in fills))
  result['observation_clock']='wall_clock_minus_16_minutes';result['delay_minutes']=16
 finally:c.close()
 return result

def read_orb(path,day):
 date.fromisoformat(day);c=connect_readonly(path)
 try:
  row=c.execute('SELECT data FROM days WHERE day=?',(day,)).fetchone()
  if not row:return dict(bot='orb',day=day,qualified=False,net_pnl=None,capital_before=None,decisions=[],missing_live=True)
  d=json.loads(row[0]);trade=d.get('trade');closed=d['phase'] in ('closed','flat');before=d.get('capital_before');intent={k:v for k,v in (d.get('intent') or {}).items() if k in ('sign','quantity','stop','sizing_price','observed_at')}
  model=c.execute("SELECT json_extract(value,'$.model_sha256') FROM meta WHERE key='configuration'").fetchone()
  result=dict(bot='orb',day=day,qualified=bool(closed and d.get('fully_observed')),capital_before=before,capital_after=trade['capital_after'] if trade else before if closed else None,net_pnl=trade['net_pnl'] if trade else 0. if closed else None,decisions=[intent] if intent else [],trades=[trade] if trade else [],model_sha256=model[0] if model else None,phase=d['phase'],notes=[v for v in d.get('notes',[]) if v in ('late_start','process_restart','source_revision','data_gap','late_observation','missed_entry','invalid_opening')],observations_kind='live_shadow')
  result['price_prefix_sha256']=rows_sha(d.get('bars',{}));result['observation_clock']='wall_clock_minus_16_minutes';result['delay_minutes']=16
 finally:c.close()
 return result

def compare(statistical,operational,tolerance=1e-6):
 context=[];differences=[]
 if not operational.get('qualified'):context.append('unqualified_live')
 a=statistical.get('capital_before');b=operational.get('capital_before')
 if a is None or b is None:context.append('unknown_initial_capital')
 elif abs(a-b)>tolerance:context.append('different_initial_capital')
 x=statistical.get('net_pnl');y=operational.get('net_pnl')
 if x is None or y is None:context.append('unknown_result')
 elif abs(x-y)>tolerance:differences.append(dict(field='net_pnl',statistical=x,operational=y,delta=x-y))
 sd=statistical.get('decisions',[]);od=operational.get('decisions',[])
 if len(sd)!=len(od):differences.append(dict(field='decision_count',statistical=len(sd),operational=len(od)))
 else:
  for i,(u,v) in enumerate(zip(sd,od)):
   us=u.get('target',u.get('sign'));vs=v.get('target',v.get('sign'))
   if us!=vs:differences.append(dict(field='direction',index=i,statistical=us,operational=vs))
  for i,(u,v) in enumerate(zip(sd,od)):
   for field in ('quantity','price','upper','lower','vwap','sigma','volatility','opening','previous_close_adjusted','stop','sizing_price'):
    if field in u and field in v and abs(u[field]-v[field])>tolerance:differences.append(dict(field=field,index=i,statistical=u[field],operational=v[field]))
 for group,fields in [('trades',('direction','quantity','entry_price','exit_price','stop_price','target_price','entry_time','exit_time','exit_reason','commission','borrow_fee','net_pnl')),('fills',('qty','sign','actual','modeled','timestamp','commission','borrow','realized'))]:
  left=statistical.get(group,[]);right=operational.get(group,[])
  if left and right:
   if len(left)!=len(right):differences.append(dict(field=group+'_count',statistical=len(left),operational=len(right)))
   for i,(u,v) in enumerate(zip(left,right)):
    for field in fields:
     if field in u and field in v:
      if field in ('timestamp','entry_time','exit_time'):changed=pd.Timestamp(u[field])!=pd.Timestamp(v[field])
      else:changed=(u[field]!=v[field]) if isinstance(u[field],str) or isinstance(v[field],str) else abs(u[field]-v[field])>tolerance
      if changed:differences.append(dict(field=group+'.'+field,index=i,statistical=u[field],operational=v[field]))
 if statistical.get('price_prefix_sha256') and operational.get('price_prefix_sha256') and statistical['price_prefix_sha256']!=operational['price_prefix_sha256']:context.append('different_archived_price_prefix')
 if not operational.get('input_sha'):context.append('live_full_input_version_unverified')
 confirmed=operational.get('input_sha') is not None and operational.get('input_sha')==statistical.get('input_sha') and not context
 return dict(classification='needs_investigation' if differences else 'comparison_limited' if context else 'observed_agreement',context=context,differences=differences,proven_engine_bug=bool(confirmed and differences),parity_confirmed=bool(confirmed and not differences))

class OperationalJournal:
 def __init__(self,path,first_day=None):
  p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(p)
  self.db.execute('CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,bot TEXT,day TEXT,snapshot_sha TEXT,payload TEXT,captured_utc TEXT,UNIQUE(bot,day,snapshot_sha))');self.db.commit()
  self.db.execute('CREATE TABLE IF NOT EXISTS ledger_config(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
  self.db.execute('CREATE TABLE IF NOT EXISTS observation_heads(bot TEXT,day TEXT,observation_id INTEGER,last_seen_utc TEXT,PRIMARY KEY(bot,day))')
  try:
   with self.db:
    self.db.execute('BEGIN IMMEDIATE');old=self.db.execute("SELECT value FROM ledger_config WHERE key='first_session'").fetchone()
    self.db.execute('INSERT OR IGNORE INTO observation_heads SELECT bot,day,max(id),max(captured_utc) FROM observations GROUP BY bot,day')
    if first_day is not None:
     date.fromisoformat(first_day)
     if old and old[0]!=first_day:raise ValueError('operational cohort date changed')
     self.db.execute('INSERT OR IGNORE INTO ledger_config VALUES(?,?)',('first_session',first_day))
    self.db.execute('DROP VIEW IF EXISTS qualified_sessions')
    self.db.execute("CREATE VIEW qualified_sessions AS SELECT o.* FROM observations o JOIN observation_heads x ON o.id=x.observation_id WHERE json_extract(o.payload,'$.qualified')=1 AND o.day>=coalesce((SELECT value FROM ledger_config WHERE key='first_session'),'0001-01-01')")
  except Exception:self.db.close();raise
 def record(self,record):
  payload=dump(record);h=hashlib.sha256(payload.encode()).hexdigest()
  with self.db:
   cursor=self.db.execute('INSERT OR IGNORE INTO observations(bot,day,snapshot_sha,payload,captured_utc) VALUES(?,?,?,?,?)',(record['bot'],record['day'],h,payload,datetime.now(timezone.utc).isoformat()))
   changed=cursor.rowcount==1;row=self.db.execute('SELECT id FROM observations WHERE bot=? AND day=? AND snapshot_sha=?',(record['bot'],record['day'],h)).fetchone()
   self.db.execute('INSERT INTO observation_heads VALUES(?,?,?,?) ON CONFLICT(bot,day) DO UPDATE SET observation_id=excluded.observation_id,last_seen_utc=excluded.last_seen_utc',(record['bot'],record['day'],row[0],datetime.now(timezone.utc).isoformat()))
  return changed
 def latest(self,qualified_only=False):
  sql='SELECT payload FROM qualified_sessions ORDER BY day,bot' if qualified_only else 'SELECT o.payload FROM observations o JOIN observation_heads x ON o.id=x.observation_id ORDER BY o.day,o.bot'
  return [json.loads(r[0]) for r in self.db.execute(sql)]
 def close(self):self.db.close()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
