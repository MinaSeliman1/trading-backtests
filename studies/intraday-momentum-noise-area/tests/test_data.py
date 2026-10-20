import pandas as pd
import numpy as np
from noise_area.data import read_market


def csv_for(tmp_path,days):
    frames=[]
    for day,length in days:
        index=pd.date_range(day+' 09:30',periods=length,freq='min',tz='America/New_York')
        frame=pd.DataFrame(dict(timestamp=index.astype(str),open=100.,high=101.,low=99.,close=100.,volume=100),index=range(length))
        frames.append(frame)
    frame=pd.concat(frames,ignore_index=True)
    path=tmp_path/'bars.csv';frame.to_csv(path,index=False)
    return path,frame


def test_dst_and_early_close_follow_nyse_calendar(tmp_path):
    path,_=csv_for(tmp_path,[('2023-07-03',210),('2023-07-05',390)])
    m=read_market([path],'SPY')
    assert m.lengths.tolist()==[210,390]
    assert m.valid.tolist()==[True,True]
    assert np.isnan(m.arrays['close'][0,210])
    path,_=csv_for(tmp_path,[('2024-03-08',390),('2024-03-11',390)])
    m=read_market([path],'SPY')
    assert m.valid.all()
    assert len(m.dates)==2


def test_missing_minute_and_conflicting_duplicate_exclude_whole_day(tmp_path):
    path,frame=csv_for(tmp_path,[('2024-01-02',390),('2024-01-03',390)])
    frame=frame.drop(index=29)
    duplicate=frame.iloc[[400]].copy();duplicate['close']=100.5
    pd.concat([frame,duplicate]).to_csv(path,index=False)
    m=read_market([path],'SPY')
    assert m.valid.tolist()==[False,False]
    assert m.quality.missing_minutes.tolist()==[1,0]
    assert m.quality.conflicting_rows.iloc[1]==2


def test_identical_duplicates_removed_and_afterhours_cannot_change_close(tmp_path):
    path,frame=csv_for(tmp_path,[('2024-01-02',390)])
    extra=frame.iloc[[0]].copy();extra['timestamp']='2024-01-02 16:00:00-05:00';extra['close']=999
    pd.concat([frame,frame.iloc[[0]],extra]).to_csv(path,index=False)
    m=read_market([path],'SPY')
    assert m.valid.tolist()==[True]
    assert m.arrays['close'][0,389]==100
    assert m.manifests[0]['identical_duplicates_removed']==1


def test_inconsistent_ohlc_or_negative_volume_is_rejected(tmp_path):
    path,frame=csv_for(tmp_path,[('2024-01-02',390)])
    frame.loc[100,'low']=102;frame.loc[200,'volume']=-1;frame.to_csv(path,index=False)
    m=read_market([path],'SPY')
    assert not m.valid.any()
    assert m.quality.invalid_ohlcv.iloc[0]==2
