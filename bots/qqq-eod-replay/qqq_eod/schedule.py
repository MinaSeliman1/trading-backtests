"""Calendar deadlines, independent of execution platform."""
import pandas as pd
import exchange_calendars as xc
NY='America/New_York'

def utc(value):
 t=pd.Timestamp(value)
 if t.tz is None:raise ValueError('timezone required')
 return t.tz_convert('UTC')

def calendar(start,end):
 return xc.get_calendar('XNYS',start=pd.Timestamp(start)-pd.Timedelta(days=7),end=pd.Timestamp(end)+pd.Timedelta(days=30))

def due_sessions(first_day,now):
 now=utc(now);first=pd.Timestamp(first_day).normalize();last=now.tz_convert(NY).tz_localize(None).normalize()
 if last<first:return []
 c=calendar(first,last);s=c.schedule.loc[str(first.date()):str(last.date())]
 return [str(day.date()) for day,row in s.iterrows() if row['close']+pd.Timedelta(minutes=17)<=now]

def capture_kind(day,captured_at):
 at=utc(captured_at);c=calendar(day,day);d=pd.Timestamp(day)
 if not c.is_session(d):raise ValueError('closed session')
 if at<c.session_close(d)+pd.Timedelta(minutes=17):raise ValueError('capture before data deadline')
 following=c.next_session(d)
 return 'timely_eod' if at<c.session_open(following) else 'catchup'
