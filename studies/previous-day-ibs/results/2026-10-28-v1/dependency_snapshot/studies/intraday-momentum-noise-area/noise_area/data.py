"""OHLCV bruts : calendrier NYSE et exclusion des séances incomplètes."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import exchange_calendars as xcals


@dataclass
class Market:
    dates: pd.DatetimeIndex
    arrays: dict
    lengths: np.ndarray
    valid: np.ndarray
    quality: pd.DataFrame
    manifests: list
    symbol: str


def read_market(paths,symbol):
    frames=[]; manifests=[]
    required=['timestamp','open','high','low','close','volume']
    for path in paths:
        path=Path(path)
        raw=pd.read_csv(path,usecols=required,float_precision='round_trip')
        raw['timestamp']=pd.to_datetime(raw['timestamp'],utc=True,format='mixed')
        count=len(raw);raw=raw.drop_duplicates()
        manifests.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              rows=count,identical_duplicates_removed=count-len(raw)))
        frames.append(raw)
    frame=pd.concat(frames,ignore_index=True).drop_duplicates().set_index('timestamp').sort_index()
    frame.index=frame.index.tz_convert('America/New_York')
    del frames
    if frame.empty: raise ValueError('empty dataset')
    first=str(frame.index[0].date());last=str(frame.index[-1].date())
    cal=xcals.get_calendar('XNYS',start=pd.Timestamp(first)-pd.Timedelta(days=7),end=pd.Timestamp(last)+pd.Timedelta(days=7))
    schedule=cal.schedule.loc[first:last]
    dates=pd.DatetimeIndex(schedule.index).tz_localize(None)
    arrays={name:np.full((len(dates),390),np.nan) for name in required[1:]}
    valid=[];lengths=[];reports=[]
    for i,(_,session) in enumerate(schedule.iterrows()):
        opening=pd.Timestamp(session['open']).tz_convert('America/New_York')
        closing=pd.Timestamp(session['close']).tz_convert('America/New_York')
        expected=pd.date_range(opening,closing,inclusive='left',freq='min')
        raw=frame.loc[opening:closing-pd.Timedelta(nanoseconds=1)]
        missing=expected.difference(raw.index)
        conflicts=int(raw.index.duplicated(keep=False).sum())
        off_grid=int((~raw.index.isin(expected)).sum())
        price=raw[['open','high','low','close']]
        bad=(~np.isfinite(price).all(axis=1))|(price.min(axis=1)<=0)|(~np.isfinite(raw.volume))|(raw.volume<0)
        bad|=(raw.high<price.max(axis=1))|(raw.low>price.min(axis=1))
        reasons=[]
        if len(missing): reasons.append('missing_minutes')
        if conflicts: reasons.append('conflicting_duplicates')
        if off_grid: reasons.append('off_minute_timestamps')
        if bad.any(): reasons.append('invalid_ohlcv')
        ok=not reasons
        cleaned=raw[~raw.index.duplicated(keep='first')].reindex(expected)
        for name in arrays: arrays[name][i,:len(expected)]=cleaned[name].to_numpy()
        valid.append(ok);lengths.append(len(expected))
        reports.append(dict(date=str(dates[i].date()),status='accepted' if ok else 'excluded',reason='|'.join(reasons),
                            expected_minutes=len(expected),observed_minutes=len(raw),missing_minutes=len(missing),
                            conflicting_rows=conflicts,invalid_ohlcv=int(bad.sum()),off_grid_rows=off_grid,
                            missing_decision_minutes=sum((x.hour*60+x.minute-570+1)%30==0 for x in missing),
                            session_open=str(opening),session_close=str(closing)))
    return Market(dates,arrays,np.array(lengths),np.array(valid),pd.DataFrame(reports),manifests,symbol)
