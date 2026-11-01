from pathlib import Path
import sys
import pandas as pd
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.data import ny_timestamps,roll_guard,price_valid,normalize_frame

def test_utc_to_new_york_observes_dst():
 result=ny_timestamps(['2026-03-06T14:32:00Z','2026-03-09T13:32:00Z'],'UTC')
 assert result.hour.tolist()==[9,9] and result.minute.tolist()==[32,32]

def test_roll_guard_is_calendar_based_without_future_volume():
 days=pd.bdate_range('2026-03-01','2026-04-02');mask=roll_guard(days)
 assert mask[days.get_loc('2026-03-20')] and mask[days.get_loc('2026-03-23')]
 assert not mask[days.get_loc('2026-03-24')]

def test_missing_or_offtick_prices_invalid_but_volume_unused():
 a={k:np.array([v],float) for k,v in dict(open=100.,high=101.,low=99.,close=100.).items()}
 assert price_valid(a).tolist()==[True]
 a['close'][0]=100.1;assert price_valid(a).tolist()==[False]


def frame(times):return pd.DataFrame(dict(datetime=times,open=100.,high=101.,low=99.,close=100.))

def test_naive_declared_new_york_clock_is_not_shifted():
 t=ny_timestamps(['2026-07-02 09:32:00'],'America/New_York');assert t[0].hour==9 and str(t.tz)=='America/New_York'

def test_nonexistent_dst_clock_is_rejected():
 with pytest.raises(Exception):ny_timestamps(['2026-03-08 02:30:00'],'America/New_York')

def test_exact_duplicate_deduplicated_but_conflict_rejected():
 f=frame(['2026-07-02 09:32:00']*2);d,n=normalize_frame(f,'America/New_York');assert len(d)==1 and n==1
 f.loc[1,'close']=100.25
 with pytest.raises(ValueError):normalize_frame(f,'America/New_York')

def test_off_minute_timestamp_rejected():
 with pytest.raises(ValueError):normalize_frame(frame(['2026-07-02 09:32:05']),'America/New_York')

def test_june_holiday_expiry_guard_is_still_conservative():
 days=pd.bdate_range('2026-06-01','2026-06-24');m=roll_guard(days)
 assert m[days.get_loc('2026-06-22')] and not m[days.get_loc('2026-06-23')]
