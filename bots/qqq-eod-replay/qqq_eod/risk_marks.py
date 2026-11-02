"""Risk telemetry only; never changes a frozen signal, fill or cost."""
import numpy as np
import pandas as pd

def path_summary(marks):
 a=np.asarray(marks,dtype=float)
 if not len(a) or not np.isfinite(a).all() or a[0]<=0:raise ValueError('finite ordered marks with positive start required')
 peaks=np.maximum.accumulate(a)
 return dict(minimum=float(a.min()),maximum=float(a.max()),ending=float(a[-1]),within_drawdown_fraction=float(np.max((peaks-a)/peaks)),metric='ordered_minute_close_and_fill_marks')

def extend_peak(previous_peak,day):
 if previous_peak<=0:raise ValueError('positive peak required')
 return dict(peak=max(previous_peak,day['maximum']),max_drawdown_fraction=max(day['within_drawdown_fraction'],(previous_peak-day['minimum'])/previous_peak))

def noise_path(bars,fills,capital):
 events={};position=0;entry=0.;balance=float(capital);marks=[balance]
 for fill in fills:
  at=pd.Timestamp(fill['timestamp'])
  if at.tz is None or at not in bars.index:raise ValueError('unmatched risk fill time')
  events.setdefault(at,[]).append(fill)
 for at,row in bars.iterrows():
  for f in events.get(at,[]):
   if f['action']=='open':entry=(entry*abs(position)+f['modeled']*f['qty'])/(abs(position)+f['qty'])
   position+=f['qty']*f['sign'];balance+=f['realized']-f['commission']-f['borrow']
   if not position:entry=0.
   marks.append(balance+position*(f['actual']-entry))
  marks.append(balance+position*(float(row['close'])-entry))
 if position:raise ValueError('risk path not closed')
 return path_summary(marks)
