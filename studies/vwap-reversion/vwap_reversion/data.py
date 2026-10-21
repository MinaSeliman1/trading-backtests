"""Champ VWAP original : pages gzip hachees, rapprochement OHLCV de toutes barres RTH."""
from pathlib import Path
import importlib.util,json,gzip
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vwap_verified_sources',ROOT.parent/'closing-momentum/scripts/run_study.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)


def merge_page(market,records,seen,vwap):
    if not records:return 0
    times=pd.DatetimeIndex(pd.to_datetime([r['t'] for r in records],utc=True,format='mixed')).as_unit('ns').asi8
    opens=pd.DatetimeIndex(pd.to_datetime(market.quality.session_open,utc=True,format='mixed')).as_unit('ns').asi8
    closes=opens+market.lengths.astype('int64')*60000000000
    ix=np.searchsorted(opens,times,side='right')-1;safe=np.maximum(ix,0);mask=(ix>=0)&(times<closes[safe]);positions=np.flatnonzero(mask)
    if not len(positions):return 0
    ix=ix[mask];delta=times[mask]-opens[ix]
    if np.any(delta%60000000000):raise ValueError('timestamp off grid')
    slot=delta//60000000000
    for key,raw in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]:
        values=np.array([records[j][raw] for j in positions],dtype=float)
        if not np.allclose(values,market.arrays[key][ix,slot],rtol=0,atol=1e-10,equal_nan=True):raise ValueError('raw/prepared OHLCV mismatch: '+key)
    values=np.array([records[j].get('vw',np.nan) for j in positions],dtype=float)
    # Distinct source records at one minute are accepted only if VWAP agrees too.
    frame=pd.DataFrame(dict(i=ix,j=slot,vw=values))
    for _,group in frame[frame.duplicated(['i','j'],keep=False)].groupby(['i','j']):
        if not np.allclose(group.vw,group.vw.iloc[0],rtol=0,atol=1e-10,equal_nan=True):raise ValueError('VWAP duplicate conflict')
    old=seen[ix,slot]
    if not np.allclose(vwap[ix[old],slot[old]],values[old],rtol=0,atol=1e-10,equal_nan=True):raise ValueError('VWAP conflict')
    vwap[ix,slot]=values;seen[ix,slot]=True
    return len(positions)


def load_sources():
    markets,cash,profile=source.load_sources();trade_root=ROOT.parents[2];validation=json.loads((ROOT.parent/'intraday-momentum-noise-area/data/prepared/DATA_VALIDATION.json').read_text(encoding='utf-8'))
    pages=[];manifests={}
    for a in validation['acquisitions']:
        manifest=Path(a['manifest']);manifests[manifest.relative_to(trade_root).as_posix()]=source.sha(manifest)
        symbol=Path(a['path']).name.split('_')[0];data=json.loads(manifest.read_text(encoding='utf-8'))
        for p in data['pages']:
            path=Path(p['path']);path=path if path.is_absolute() else trade_root/path
            if source.sha(path)!=p['sha256']:raise ValueError('raw page SHA mismatch')
            pages.append(dict(symbol=symbol,path=path.relative_to(trade_root).as_posix(),sha256=p['sha256'],rows=p['rows']))
    cache=ROOT/'data/prepared';meta=cache/'VWAP_SOURCE.json';basis=dict(manifests=manifests,pages=pages,prepared=profile['prepared_files_sha256'])
    if meta.exists():
        extra=json.loads(meta.read_text(encoding='utf-8'))
        if extra['basis']!=basis:raise ValueError('VWAP cache source basis changed; use a new extraction')
        for s,m in markets.items():
            path=cache/f'{s}_vwap.npy'
            if source.sha(path)!=extra['vwap_files_sha256'][path.name]:raise ValueError('VWAP cache SHA mismatch')
            vw=np.load(path,allow_pickle=False)
            if vw.shape!=m.arrays['open'].shape or vw.dtype!=np.float64:raise ValueError('VWAP cache shape/precision')
            m.arrays['vwap']=vw
    else:
        cache.mkdir(parents=True,exist_ok=True);coverage=[];hashes={}
        for s,m in markets.items():
            vw=np.full(m.arrays['open'].shape,np.nan);seen=np.zeros(vw.shape,dtype=bool);records=0
            for p in pages:
                if p['symbol']!=s:continue
                with gzip.open(trade_root/p['path'],'rt',encoding='utf-8') as stream:body=json.load(stream)
                bars=body['bars'];bars=bars[s] if isinstance(bars,dict) else bars
                if len(bars)!=p['rows']:raise ValueError('raw page row count')
                records+=merge_page(m,bars,seen,vw)
            expected=np.isfinite(m.arrays['open'])
            if not np.array_equal(seen,expected):raise ValueError('RTH coverage differs from prepared OHLCV')
            volume=m.arrays['volume'];positive=expected&(volume>0);invalid=positive&(~np.isfinite(vw)|(vw<=0));outside=positive&np.isfinite(vw)&((vw<m.arrays['low'])|(vw>m.arrays['high']))
            m.arrays['vwap']=vw;path=cache/f'{s}_vwap.npy';np.save(path,vw,allow_pickle=False);hashes[path.name]=source.sha(path)
            coverage.append(dict(symbol=s,rth_rows=int(expected.sum()),rth_records_including_overlaps=records,invalid_positive_volume_vwap=int(invalid.sum()),vwap_outside_ohlc=int(outside.sum()),zero_volume_bars=int((expected&(volume==0)).sum())))
        extra=dict(basis=basis,vwap_files_sha256=hashes,coverage=coverage,method='Original SIP per-minute vw weighted by corresponding volume; all RTH OHLCV reconciled, no HLC3 proxy or gap interpolation.')
        source.write_json(meta,extra)
    profile['vwap_source']=extra;profile['vwap_source_metadata_sha256']=source.sha(meta)
    return markets,cash,profile
