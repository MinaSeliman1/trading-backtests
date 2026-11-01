from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from qqq_eod import market,schedule
from qqq_eod.journal import Journal

@pytest.fixture(autouse=True)
def frozen(pinned_sources):return pinned_sources

class Data:
 def __init__(self,break_history=False):self.calls=[];self.break_history=break_history
 def bars(self,start,end,feed):
  self.calls.append((start,end,feed))
  if self.break_history and (end-start)>pd.Timedelta(days=1):raise ConnectionError('sensitive-provider-message')
  cal=schedule.calendar(start.date(),end.date());frames=[]
  for _,row in cal.schedule.iterrows():
   idx=pd.date_range(row['open'],row['close'],inclusive='left',freq='min');idx=idx[(idx>=start)&(idx<end)]
   if len(idx):frames.append(pd.DataFrame({'open':100.,'high':100.5,'low':99.,'close':100.,'volume':1000.},index=idx))
  return pd.concat(frames) if frames else pd.DataFrame(columns=['open','high','low','close','volume'],index=pd.DatetimeIndex([],tz='UTC'))
 def dividend(self,day):return 0.

def test_one_day_and_rerun_are_idempotent(tmp_path):
 data=Data()
 with Journal(tmp_path/'ledger.sqlite',{'fixture':True},'2024-04-30') as db:
  market.run_due(db,data,tmp_path/'inputs','2024-04-30')
  assert db.session('orb','2024-04-30')['status']=='complete' and db.session('noise','2024-04-30')['status']=='complete'
  calls=len(data.calls);assert db.attempt_count()==2
  market.run_due(db,data,tmp_path/'inputs','2024-04-30');assert len(data.calls)==calls and db.attempt_count()==2

def test_history_failure_does_not_stop_orb_and_no_secret_message(tmp_path):
 data=Data(break_history=True)
 with Journal(tmp_path/'ledger.sqlite',{'fixture':True},'2024-04-30') as db:
  market.run_due(db,data,tmp_path/'inputs','2024-04-30')
  assert db.session('noise','2024-04-30')['status']=='unresolved' and db.session('orb','2024-04-30')['status']=='complete'
  assert 'sensitive-provider-message' not in str(db.export())
