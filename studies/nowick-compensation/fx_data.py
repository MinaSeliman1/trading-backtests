"""Read-only decoding and quality checks for public FXCM minute archives."""
from io import BytesIO
import numpy as np
import pandas as pd

RAW_COLUMNS=['BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']
PRICE_COLUMNS=['bo','bh','bl','bc','ao','ah','al','ac']

def scale_for(pair):
    return 1000 if pair=='USDJPY' else 100000

def decode_csv(blob,pair):
    df=pd.read_csv(BytesIO(blob),skip_blank_lines=True)
    if list(df.columns)!=['DateTime']+RAW_COLUMNS:
        raise ValueError('Unexpected FXCM columns')
    times=pd.DatetimeIndex(pd.to_datetime(df['DateTime'],format='%m/%d/%Y %H:%M:%S.%f',utc=True)).as_unit('ns')
    if times.isna().any() or (times.astype('int64')%60000000000!=0).any():
        raise ValueError('Non-minute timestamp')
    values=df[RAW_COLUMNS].to_numpy(dtype=float)
    scaled=values*scale_for(pair)
    finite=np.isfinite(scaled)
    if np.any(finite & (np.abs(scaled-np.rint(scaled))>1e-5)):
        raise ValueError('Sub-tick price precision')
    valid=np.isfinite(values).all(axis=1) & (values>0).all(axis=1)
    safe=np.where(finite,scaled,0)
    if np.any(np.abs(safe)>np.iinfo(np.int32).max):
        raise ValueError('Price integer overflow')
    out=pd.DataFrame(np.rint(safe).astype(np.int32),index=pd.DatetimeIndex(times),columns=PRICE_COLUMNS)
    b=values[:,:4]; a=values[:,4:]
    out['valid_bid']=np.isfinite(b).all(axis=1)&(b>0).all(axis=1)&(b[:,1]>=np.maximum(b[:,0],b[:,3]))&(b[:,2]<=np.minimum(b[:,0],b[:,3]))
    out['valid_ask']=np.isfinite(a).all(axis=1)&(a>0).all(axis=1)&(a[:,1]>=np.maximum(a[:,0],a[:,3]))&(a[:,2]<=np.minimum(a[:,0],a[:,3]))
    out.index.name='time'
    return out

def combine_frames(frames):
    if not frames:
        raise ValueError('No source archives')
    df=pd.concat(frames).sort_index(kind='stable')
    duplicates=df[df.index.duplicated(keep=False)]
    if len(duplicates) and (duplicates.groupby(level=0).nunique(dropna=False)>1).any().any():
        raise ValueError('Conflicting duplicate timestamps')
    count=int(df.index.duplicated().sum())
    df=df[~df.index.duplicated(keep='first')]
    seconds=df.index.astype('int64').to_numpy()//1000000000
    gaps=np.diff(seconds)//60-1
    report={'rows':len(df),'first_utc':df.index[0].isoformat(),'last_utc':df.index[-1].isoformat(),
            'identical_duplicate_rows':count,'invalid_bid_rows':int((~df.valid_bid).sum()),
            'invalid_ask_rows':int((~df.valid_ask).sum()),'crossed_close_quotes':int((df.ac<df.bc).sum()),
            'minute_gaps':int((gaps>0).sum()),'missing_clock_minutes_including_weekends':int(gaps[gaps>0].sum()),
            'longest_clock_gap_minutes':int(gaps.max()) if len(gaps) else 0}
    return df,report

def save_prepared(df,path):
    np.savez_compressed(path,t=df.index.astype('int64').to_numpy()//1000000000,
                        bid=df[['bo','bh','bl','bc']].to_numpy(np.int32),
                        ask=df[['ao','ah','al','ac']].to_numpy(np.int32),
                        valid_bid=df.valid_bid.to_numpy(bool),valid_ask=df.valid_ask.to_numpy(bool))

def load_prepared(path):
    with np.load(path,allow_pickle=False) as d:
        return {k:d[k] for k in d.files}
