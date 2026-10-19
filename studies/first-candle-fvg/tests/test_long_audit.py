import pandas as pd
import pytest
from scripts.audit_long_history import local_timestamp


@pytest.mark.parametrize('day,offset',[('2023-01-04','-05:00'),('2023-07-05','-04:00')])
def test_csv_offset_and_named_calendar_zone_slice_same_minutes(day,offset):
    index=pd.date_range(day+' 09:30',periods=10,freq='min',tz='America/New_York')
    bars=pd.Series(range(10),index=index)
    start=local_timestamp(day+' 09:30:00'+offset)
    end=pd.Timestamp(day+' 09:35',tz='America/New_York')
    assert bars.loc[start:end].tolist()==[0,1,2,3,4,5]
