"""Check 16 selected sessions against original CSV acquisitions; publish small excerpts."""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from nr7.data import load_sources,source


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24');out=p.parse_args().out
    markets,_,profile=load_sources();sample_rows=[];checks=[]
    for symbol,m in markets.items():
        trades=pd.read_csv(out/f'{symbol}_ALL_both_s0.01_complete_days_nr71/trades.csv')
        dates=[trades.date.iloc[0],trades.date.iloc[-1],trades.loc[trades.net_pnl.idxmin(),'date'],trades.loc[trades.net_pnl.idxmax(),'date']]
        if symbol=='QQQ':dates.append('2020-03-09')
        rng=np.random.default_rng(20261024)
        for x in rng.permutation(trades.date):
            if x not in dates:dates.append(x)
            if len(set(dates))>=8:break
        dates=list(dict.fromkeys(dates))[:8];frames=[]
        for item in profile['raw_acquisitions']:
            path=ROOT.parents[2]/item['path']
            if path.name!=symbol+'_1m.csv':continue
            for chunk in pd.read_csv(path,chunksize=200000):
                keep=chunk.timestamp.str[:10].isin(dates)
                if keep.any():frames.append(chunk.loc[keep])
        raw=pd.concat(frames,ignore_index=True);raw['timestamp']=pd.to_datetime(raw.timestamp,utc=True,format='mixed')
        cols=['open','high','low','close','volume']
        for _,g in raw.groupby('timestamp'):
            if len(g)>1:assert (g[cols].nunique(dropna=False)<=1).all(),'conflicting raw duplicate'
        raw=raw.drop_duplicates('timestamp').set_index('timestamp').sort_index()
        for date in dates:
            i=m.dates.get_loc(pd.Timestamp(date));n=int(m.lengths[i]);opening=pd.Timestamp(m.quality.iloc[i].session_open);idx=pd.date_range(opening,periods=n,freq='min').tz_convert('UTC')
            actual=raw.reindex(idx)[cols];expected=np.column_stack([m.arrays[k][i,:n] for k in cols])
            assert np.isclose(actual.to_numpy(),expected,atol=1e-9,rtol=1e-12,equal_nan=True).all(),(symbol,date)
            selected={0,n-1};t=trades[trades.date==date]
            if len(t):
                z=t.iloc[0];selected.update([int(z.signal_slot),int(z.entry_slot),int(z.exit_slot)])
                selected.update(range(max(0,int(z.signal_slot)-2),min(n,int(z.entry_slot)+3)))
            else:selected.update(range(3,9))
            for j in sorted(selected):sample_rows.append(dict(symbol=symbol,date=date,minute=j,timestamp=str(idx[j]),**actual.iloc[j].to_dict()))
            checks.append(dict(symbol=symbol,date=date,grid_minutes=n,present_minutes=int(actual.open.notna().sum()),fields_compared=n*5,cache_matches_original=True))
    pd.DataFrame(sample_rows).to_csv(out/'RAW_SOURCE_EXCERPTS.csv',index=False)
    source.write_json(out/'AUDIT_RAW_SAMPLES.json',dict(status='passed',selected_sessions=len(checks),fields_compared=sum(x['fields_compared'] for x in checks),sample_excerpts=len(sample_rows),sessions=checks,
        selection='First,last,worst,best,seeded additional principal trade dates; includes unresolved QQQ2020-03-09. Whole selected grids checked, only small excerpts published.',
        caveat='Sample verification supplements source-wide SHA reconciliation; not an independent re-download from the provider.'))
    print(dict(sessions=len(checks),fields=sum(x['fields_compared'] for x in checks),excerpts=len(sample_rows)))


if __name__=='__main__':main()
