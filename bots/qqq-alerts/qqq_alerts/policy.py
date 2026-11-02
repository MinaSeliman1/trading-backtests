"""Pure technical alert policy. No trading, network or journal writes."""
from functools import lru_cache
import pandas as pd
import exchange_calendars as xcals
NY='America/New_York'
@lru_cache(maxsize=32)
def schedule(day):
 d=pd.Timestamp(day);return xcals.get_calendar('XNYS',start=d-pd.Timedelta(days=7),end=d+pd.Timedelta(days=16)).schedule

def session(day):
 rows=schedule(day);d=pd.Timestamp(day)
 return rows.loc[d] if d in rows.index else None

def observation_window(now):
 now=pd.Timestamp(now).tz_convert('UTC');row=session(str(now.tz_convert(NY).date()))
 return bool(row is not None and row['open']-pd.Timedelta(minutes=20)<=now<=row['close']+pd.Timedelta(minutes=20))

def guard_deadline(now):
 now=pd.Timestamp(now).tz_convert('UTC');rows=schedule(str(now.tz_convert(NY).date()))
 if observation_window(now):return min(now+pd.Timedelta(minutes=12),session(str(now.tz_convert(NY).date()))['close']+pd.Timedelta(minutes=22))
 for _,row in rows.iterrows():
  at=row['open']-pd.Timedelta(minutes=10)
  if at>now:return at if at-now<pd.Timedelta(days=3)-pd.Timedelta(minutes=1) else None
 return None

def evaluate(s,now):
 now=pd.Timestamp(now).tz_convert('UTC');day=str(now.tz_convert(NY).date());row=session(day);result=set()
 if s.get('mode')!='shadow' or s.get('feed')!='sip':result.add('unexpected_configuration')
 if s.get('stop'):result.add('operator_stop')
 if s.get('paused'):result.add('ledger_paused')
 if s.get('pending'):result.add('pending_orders')
 if s.get('read_error'):result.add('journal_unavailable')
 if s.get('position'):
  position_day=s.get('open_day');position_session=session(position_day) if position_day else None
  if position_session is None or now>=position_session['close']+pd.Timedelta(minutes=18):result.add('position_unresolved')
 if s.get('phase')=='unresolved':result.add('position_unresolved')
 if s.get('stop'):return result
 if not s.get('alive'):result.add('process_stopped')
 try:
  age=(now-pd.Timestamp(s['stamp'])).total_seconds()
  if not pd.notna(age) or age>180 or age < -60:result.add('engine_stale')
 except (KeyError,ValueError,TypeError):result.add('engine_stale')
 if s.get('state') in ('error_no_new_entries','startup_failed','startup_retry','retrying_shadow_startup','stopped','ALERT_position_open'):
  result.add('engine_error')
 if result.intersection({'operator_stop','process_stopped','journal_unavailable'}):return result
 if not observation_window(now):return result
 logical=now-pd.Timedelta(minutes=16)
 if row is None:return result
 if s['bot']=='noise':
  entries={pd.Timestamp(d['decision_time']):d for d in s.get('decisions',[]) if d.get('decision_time')}
  for at in pd.date_range(row['open']+pd.Timedelta(minutes=30),row['close']-pd.Timedelta(minutes=1),freq='30min'):
   if logical<=at+pd.Timedelta(minutes=2):continue
   d=entries.get(at)
   if not d:result.add('decision_missing');continue
   if d.get('status')!='processed':result.add('data_delayed');continue
   try:late=(pd.Timestamp(d['observed_at'])-at).total_seconds();valid=0<=late<=120
   except (ValueError,TypeError,KeyError):valid=False
   if not valid:result.add('decision_late')
 else:
  if logical>row['open']+pd.Timedelta(minutes=7):
   if s.get('phase') not in ('active','closed','flat','unresolved'):result.add('orb_missed_entry')
   if set(s.get('notes',[])).intersection({'late_start','missed_entry','late_observation','process_restart'}):result.add('orb_observation_gap')
   if 'data_gap' in s.get('notes',[]):result.add('data_delayed')
  if s.get('phase')=='active' and s.get('last_bar'):
   if logical-pd.Timestamp(s['last_bar'])>pd.Timedelta(minutes=3):result.add('data_delayed')
 return result
