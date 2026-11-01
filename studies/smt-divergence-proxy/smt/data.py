"""Read-only ES/NQ proxy ingestion; NY clock, price validation and roll masks."""
from dataclasses import dataclass
from pathlib import Path
from datetime import date,timedelta
import hashlib,json,gzip,re
import numpy as np
import pandas as pd
import exchange_calendars as xc
ROOT=Path(__file__).resolve().parents[1]
FIELDS=('open','high','low','close')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def ny_timestamps(values,source_tz):
 t=pd.DatetimeIndex(pd.to_datetime(values))
 if t.tz is None:t=t.tz_localize(source_tz,ambiguous='raise',nonexistent='raise')
 return t.tz_convert('America/New_York')

def price_valid(a):
 o,h,l,c=[a[k] for k in FIELDS];xs=np.stack([o,h,l,c])
 return np.isfinite(xs).all(axis=0)&(xs>0).all(axis=0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(np.abs(xs/.25-np.round(xs/.25))<1e-7).all(axis=0)

def roll_guard(dates):
 days=pd.DatetimeIndex(dates);lo=days.min()-pd.Timedelta(days=40);hi=days.max()+pd.Timedelta(days=50)
 cal=xc.get_calendar('XNYS',start=str(lo.date()),end=str(hi.date()));sessions=cal.sessions
 result=np.zeros(len(days),bool)
 for year in range(days.min().year,days.max().year+1):
  for month in (3,6,9,12):
   first=date(year,month,1);third=first+timedelta(days=(4-first.weekday())%7+14)
   later=sessions[sessions>pd.Timestamp(third)]
   if not len(later):continue
   end=later[0];result|=(days>=pd.Timestamp(first))&(days<=end)
 return result

def normalize_frame(df,timezone):
 t=ny_timestamps(df['datetime'],timezone)
 if not (t==t.floor('min')).all():raise ValueError('off-minute timestamps')
 out=df[list(FIELDS)].copy();out.index=t.tz_convert('UTC')
 duplicates=int(out.index.duplicated().sum())
 if duplicates:
  for _,group in out.loc[out.index.duplicated(keep=False)].groupby(level=0):
   if (group.nunique(dropna=False)>1).any():raise ValueError('conflicting duplicate prices')
  out=out[~out.index.duplicated(keep='first')]
 return out.sort_index(),duplicates

@dataclass
class Dataset:
 dates:pd.DatetimeIndex
 close_slots:np.ndarray
 arrays:dict
 valid:dict
 roll:np.ndarray
 evaluation:np.ndarray
 daily_nq:pd.DataFrame
 profile:dict

def news_calendar():
 rows=[];path=ROOT/'sources/bls_calendar_rows.json';source=json.loads(path.read_text(encoding='utf-8'))
 months={m:i for i,m in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'),1)}
 for item in source['rows']:
  m=re.fullmatch(r'(\w+) (\d+), (\d{4})',item['date_text']);day=date(int(m[3]),months[m[1]],int(m[2]))
  kind='CPI' if item['release'].startswith('Consumer Price Index for ') else 'NFP'
  rows.append(dict(date=day.isoformat(),kind=kind,time_ny='08:30',source=item['source_url'],detail=item['release']))
 fed=(ROOT/'sources/fed_calendar.html').read_text(encoding='utf-8')
 for ymd in sorted(set(re.findall(r'/newsevents/pressreleases/monetary(20(?:25|26)\d{4})a\.htm',fed))):
  rows.append(dict(date=f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}',kind='FOMC',time_ny='14:00',source='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',detail='scheduled policy statement; after forced11:30 exit'))
 return pd.DataFrame(rows).drop_duplicates(['date','kind']).sort_values(['date','kind']).reset_index(drop=True)

def load_sources(raw_root=None):
 raw_root=Path(raw_root) if raw_root is not None else ROOT.parents[2]/'data/free_sources/BARS'
 frames={};profiles={}
 for symbol in ('ES','NQ'):
  path=raw_root/f'{symbol}_1m_raw.csv.gz';provenance=path.with_name(path.name+'.provenance.json');prov=json.loads(provenance.read_text(encoding='utf-8'))
  assert sha(path)==prov['sha256'],'raw acquisition hash mismatch'
  with gzip.open(path,'rt',encoding='utf-8') as f:header=f.readline().strip()
  if f'symbol={symbol}' not in header or 'tz=America/New_York' not in header:raise ValueError('unexpected raw source/timezone')
  original=pd.read_csv(path,comment='#');frame,dups=normalize_frame(original,'America/New_York');frames[symbol]=frame
  ny=frame.index.tz_convert('America/New_York');mins=ny.hour*60+ny.minute
  profiles[symbol]=dict(file=path.name,sha256=sha(path),acquisition_provenance_sha256=sha(provenance),url=prov['url'],header=header,rows=len(original),duplicates_removed=dups,
   start=str(ny.min()),end=str(ny.max()),source_timezone='America/New_York',storage_timezone='UTC',offset_counts=pd.Series(ny.strftime('%z')).value_counts().to_dict(),
   london_bars=int(((mins>=240)&(mins<420)).sum()),premarket_bars=int(((mins>=420)&(mins<570)).sum()),price_invalid_rows=int((~price_valid({k:frame[k].to_numpy() for k in FIELDS})).sum()),
   instrument_type='unadjusted front-month continuous proxy; per-minute expiry unavailable',volume_used_for_signal=False)
 first=min(f.index.tz_convert('America/New_York').min().date() for f in frames.values());last=min(f.index.tz_convert('America/New_York').max().date() for f in frames.values())
 cal=xc.get_calendar('XNYS',start=str(first-pd.Timedelta(days=5)),end=str(last+pd.Timedelta(days=5)));dates=cal.sessions_in_range(str(first),str(last));dates=pd.DatetimeIndex(dates)
 closes=cal.schedule.loc[dates,'close'].dt.tz_convert('America/New_York');close_slots=(closes.dt.hour*60+closes.dt.minute-240).to_numpy(dtype=int)
 arrays={};valid={}
 for symbol,frame in frames.items():
  ny=frame.index.tz_convert('America/New_York');idx=dates.get_indexer(ny.tz_localize(None).normalize());slot=ny.hour*60+ny.minute-240;keep=(idx>=0)&(slot>=0)&(slot<720)
  arrays[symbol]={k:np.full((len(dates),720),np.nan) for k in FIELDS}
  for k in FIELDS:arrays[symbol][k][idx[keep],slot[keep]]=frame[k].to_numpy()[keep]
  valid[symbol]=price_valid(arrays[symbol])
 roll=roll_guard(dates);start=max(f.index.tz_convert('America/New_York').min().date() for f in frames.values());evaluation=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(last))
 daily=[];a=arrays['NQ']
 for i,end in enumerate(close_slots):
  good=bool(valid['NQ'][i,330:end].all());daily.append(dict(date=str(dates[i].date()),known=good,open=float(a['open'][i,330]) if good else None,close=float(a['close'][i,end-1]) if good else None))
 profile=dict(inputs=profiles,calendar='XNYS cash-session anchor; closed days excluded, half-day previous RTH ends13:00',evaluation_start=str(start),evaluation_end=str(last),
   sessions=int(evaluation.sum()),calendar_eligible_dates=len(dates),roll_policy='calendar precaution: quartermonth day1 through firstNYSEsession after thirdFriday; exact changes unknown',
   actual_roll_dates_identified=None,roll_guard_sessions=int((roll&evaluation).sum()),source_readme_sha256=sha(raw_root/'README.md'),source_catalog_sha256=sha(raw_root/'catalog.json'),
   proxy_authorized=True,actual_micro_data=False,limitations=['ES/NQ prints not guaranteed equal to MES/MNQ','No per-minute contract identity or verified roll ledger','Calendar guard is conditional protection, not certification','No volume signal/selection or broker calls'])
 return Dataset(dates,close_slots,arrays,valid,roll,np.asarray(evaluation),pd.DataFrame(daily),profile)
