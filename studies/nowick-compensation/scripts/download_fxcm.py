"""Bounded, resumable GET-only public FXCM acquisition. Raw files remain local."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fx_data import decode_csv,combine_frames,save_prepared

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def one(item):
    pair,year,week=item
    url=f'https://candledata.fxcorporate.com/m1/{pair}/{year}/{week}.csv.gz'
    path=ROOT/'data/fxcm_raw'/pair/str(year)/f'{week}.csv.gz'
    record={'pair':pair,'year':year,'week':week,'url':url,'path':path.relative_to(ROOT).as_posix()}
    if path.exists():
        gzip.decompress(path.read_bytes())
        return record|{'status':200,'bytes':path.stat().st_size,'sha256':digest(path),'cached':True}
    for attempt in range(4):
        try:
            r=requests.get(url,timeout=(10,60))
            if r.status_code in [429,500,502,503,504]:
                delay=min(60,float(r.headers.get('Retry-After',3*(attempt+1))))
                time.sleep(delay)
                continue
            if r.status_code==404:
                return record|{'status':404,'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()}
            r.raise_for_status()
            raw=gzip.decompress(r.content)
            decode_csv(raw,pair) # Refuse corrupt/incompatible source before caching.
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.tmp')
            temp.write_bytes(r.content)
            temp.replace(path)
            return record|{'status':200,'bytes':len(r.content),'sha256':digest(path),'cached':False}
        except (requests.RequestException,OSError,ValueError) as exc:
            if attempt==3:
                return record|{'status':'error','error':str(exc)[:250]}
            time.sleep(2*(attempt+1))
    return record|{'status':'error','error':'Retries exhausted'}

def main():
    out=ROOT/'results/2026-10-24-python'
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/'source_manifest.json'
    previous=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
    if previous and previous.get('complete') and len(previous.get('prepared',{}))==3:
        # A reproduction must never rewrite the archived source evidence.
        cached=all((ROOT/r['path']).exists() and digest(ROOT/r['path'])==r['sha256']
                   for r in previous['archives'] if r['status']==200)
        cached &= all((ROOT/v['path']).exists() and digest(ROOT/v['path'])==v['sha256']
                      for v in previous['prepared'].values())
        if cached:
            print('Published acquisition and local cache verified; original manifest preserved.',flush=True)
            return
        manifest=ROOT/'data/prepared/acquisition_reproduction.json'
        manifest.parent.mkdir(parents=True,exist_ok=True)
    items=[(p,y,w) for p in ['GBPUSD','USDJPY','AUDUSD'] for y in range(2014,2026) for w in (range(48,54) if y==2014 else range(1,5) if y==2025 else range(1,54))]
    records=[]
    started=datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(one,i) for i in items]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records)%60==0:
                print(f'Acquisition {len(records)}/{len(items)} ; ok={sum(x["status"]==200 for x in records)} errors={sum(x["status"]=="error" for x in records)}',flush=True)
                manifest.write_text(json.dumps({'started_utc':started,'complete':False,'archives':records},indent=2)+'\n',encoding='utf-8',newline='\n')
    records.sort(key=lambda x:(x['pair'],x['year'],x['week']))
    payload={'provider':'FXCM','source_documentation':'https://github.com/fxcm/MarketData','started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),'complete':True,'archives':records,'prepared':{}}
    manifest.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8',newline='\n')
    errors=[x for x in records if x['status']=='error']
    if errors:
        raise SystemExit(f'Unresolved acquisition errors: {len(errors)}; see manifest')
    reproducing=previous and previous.get('complete') and len(previous.get('prepared',{}))==3
    if reproducing:
        key=lambda r:(r['pair'],r['year'],r['week'],r['status'])
        expected={key(r):r['sha256'] for r in previous['archives'] if r['status']==200}
        actual={key(r):r['sha256'] for r in records if r['status']==200}
        if expected!=actual:
            raise SystemExit('Provider archives differ from published fingerprints; original prepared files preserved.')
    for pair in ['GBPUSD','USDJPY','AUDUSD']:
        frames=[]
        for r in records:
            if r['pair']==pair and r['status']==200:
                frames.append(decode_csv(gzip.decompress((ROOT/r['path']).read_bytes()),pair))
        df,quality=combine_frames(frames)
        target=ROOT/'data/prepared'/f'{pair}_m1.npz'
        target.parent.mkdir(parents=True,exist_ok=True)
        staged=target.with_name(f'.{pair}_m1.reproduction.npz') if reproducing else target
        save_prepared(df,staged)
        if reproducing:
            if digest(staged)!=previous['prepared'][pair]['sha256']:
                raise SystemExit('Preparation differs from published fingerprint; original prepared file preserved.')
            staged.replace(target)
        payload['prepared'][pair]=quality|{'path':target.relative_to(ROOT).as_posix(),'sha256':digest(target)}
        print(pair,json.dumps(payload['prepared'][pair]),flush=True)
        del frames,df
    manifest.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8',newline='\n')
    if previous and previous.get('complete') and len(previous.get('prepared',{}))==3:
        key=lambda r:(r['pair'],r['year'],r['week'],r['status'])
        expected={key(r):r['sha256'] for r in previous['archives'] if r['status']==200}
        actual={key(r):r['sha256'] for r in records if r['status']==200}
        if expected!=actual or any(payload['prepared'][p]['sha256']!=v['sha256'] for p,v in previous['prepared'].items()):
            raise SystemExit('Provider/preparation differs from archived fingerprints; original manifest preserved. New source protocol required.')
    print('Acquisition and preparation complete.',flush=True)

if __name__=='__main__': main()
