"""Execute the frozen FX study; refuse to overwrite a prior run."""
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fx_data import load_prepared,scale_for
from fx_engine import Config,prepare_market,simulate
from fx_metrics import summarize

def stamp(s): return int(pd.Timestamp(s).timestamp())
PERIODS={'ALL':(stamp('2015-01-01T00:00Z'),stamp('2025-01-01T00:00Z')),'A':(stamp('2015-01-01T00:00Z'),stamp('2020-01-01T00:00Z')),'B':(stamp('2020-01-01T00:00Z'),stamp('2025-01-01T00:00Z'))}
BASE=Config()
CONFIGS={'reference':BASE,'fill_first':replace(BASE,front_run='fill_first'),'observed_gap':replace(BASE,gap_policy='observed'),
         'swing_on':replace(BASE,swing=True),'sr_on':replace(BASE,sr=True),'double_on':replace(BASE,double=True),
         'filters_all':replace(BASE,swing=True,sr=True,double=True),'ema_1h':replace(BASE,trend='ema'),
         'mid_body':replace(BASE,midpoint=True),'rr_1_5':replace(BASE,rr=1.5),'rr_2':replace(BASE,rr=2),
         'front_run_off':replace(BASE,front_run='off'),'cost_2pips':replace(BASE,cost_pips=2),'cost_3pips':replace(BASE,cost_pips=3)}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(path,value): path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n')

def coverage(raw,market):
    start,end=PERIODS['ALL']
    expected=pd.date_range(pd.Timestamp(start,unit='s',tz='UTC'),pd.Timestamp(end,unit='s',tz='UTC'),freq='min',inclusive='left')
    local=expected.tz_convert('America/New_York')
    mask=(local.dayofweek<5)&(local.hour>=2)&(local.hour<8)
    et=expected[mask].as_unit('ns').asi8//1000000000
    existing=raw['t'][raw['valid_bid']]
    present=np.isin(et,existing,assume_unique=True)
    days=pd.DataFrame({'date':local[mask].strftime('%Y-%m-%d'),'present':present}).groupby('date').present.agg(['sum','count'])
    days['missing']=days['count']-days['sum']
    d=np.diff(existing)
    gaps=np.flatnonzero(d>60)
    top=sorted(gaps,key=lambda k:int(d[k]),reverse=True)[:20]
    relevant=market.features[(market.features.t>=start)&(market.features.t<end)&(market.features.current_minute>=120)&(market.features.current_minute<480)]
    report={'expected_weekday_0200_0800_minutes':len(et),'present_weekday_0200_0800_minutes':int(present.sum()),
            'weekday_window_coverage_pct':100*float(present.mean()),'weekday_days':len(days),'complete_360minute_days':int((days.missing==0).sum()),
            'missing_weekday_window_minutes':int((~present).sum()),'zero_quote_weekdays':int((days['sum']==0).sum()),
            'observed_target_15m_bars':len(relevant),'complete_target_15m_bars':int(relevant.complete.sum()),
            'longest_gaps':[{'last_utc':pd.Timestamp(int(existing[k]),unit='s',tz='UTC').isoformat(),'next_utc':pd.Timestamp(int(existing[k+1]),unit='s',tz='UTC').isoformat(),'missing_clock_minutes':int(d[k]//60-1)} for k in top],
            'definition':'Expected weekday envelope includes holidays; not a certification that every missing minute was a tradable quote. No forward fill.'}
    return report,days.reset_index()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',default='2026-10-24-python-v1'); parser.add_argument('--references-only',action='store_true')
    args=parser.parse_args()
    out=ROOT/'results'/args.run_id
    if out.exists(): raise SystemExit('Refusing to overwrite existing run')
    out.mkdir(parents=True)
    snapshot=out/'code_snapshot'; snapshot.mkdir()
    files=[ROOT/'fx_data.py',ROOT/'fx_engine.py',ROOT/'fx_metrics.py',Path(__file__),ROOT/'PYTHON_PROTOCOL.md']+sorted((ROOT/'tests').glob('*.py'))
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files}
    for p in files:
        target=snapshot/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,target)
    source=ROOT/'results/2026-10-24-python/source_manifest.json'
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'engine':'Python Nowick minute model, not TradingView','source_manifest_sha256':sha(source),'code_sha256':hashes,
              'configs':{k:asdict(v) for k,v in CONFIGS.items()},'periods':{k:[pd.Timestamp(a,unit='s',tz='UTC').isoformat(),pd.Timestamp(b,unit='s',tz='UTC').isoformat()] for k,(a,b) in PERIODS.items()},'python':sys.version,'complete':False}
    write_json(out/'RUN_MANIFEST.json',manifest)
    rows=[]; quality={}
    selected={'reference':BASE} if args.references_only else CONFIGS
    for pair in ['GBPUSD','USDJPY','AUDUSD']:
        rawpath=ROOT/'data/prepared'/f'{pair}_m1.npz'
        src=json.loads(source.read_text(encoding='utf-8'))['prepared'][pair]
        if sha(rawpath)!=src['sha256']: raise ValueError('Source fingerprint mismatch')
        raw=load_prepared(rawpath)
        market=prepare_market(raw,pair)
        fq=ROOT/'data/prepared'/f'{pair}_features.csv.gz'
        market.features.to_csv(fq,index=False,compression='gzip')
        quality[pair],days=coverage(raw,market)
        quality[pair]['features_sha256']=sha(fq)
        days.to_csv(out/f'{pair}_daily_coverage.csv',index=False)
        for name,cfg in selected.items():
            for period,(start,end) in PERIODS.items():
                result=simulate(market,cfg,start,end)
                summary={'pair':pair,'period':period,'variant':name,**summarize(result,start,end)}
                target=out/pair/period/name; target.mkdir(parents=True)
                trades=pd.DataFrame(result['trades']); setups=pd.DataFrame(result['setups'])
                if len(trades):
                    for col in ['signal_time','entry_time','exit_time']:
                        trades[col+'_utc']=pd.to_datetime(trades[col],unit='s',utc=True)
                    trades['entry_price']=trades.entry_ticks/scale_for(pair); trades['exit_price']=trades.exit_ticks/scale_for(pair)
                trades.to_csv(target/'trades.csv',index=False,float_format='%.15g')
                setups.to_csv(target/'setups.csv',index=False,float_format='%.15g')
                marks=pd.DataFrame(result['marks'],columns=['time','equity'])
                marks['date']=pd.to_datetime(marks.time,unit='s',utc=True).dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
                marks.groupby('date',sort=True).tail(1).to_csv(target/'daily_equity.csv',index=False,float_format='%.15g')
                write_json(target/'summary.json',summary)
                write_json(target/'end_state.json',{'open_position':result['open_position'],'pending':result['pending']})
                rows.append(summary)
                print(f'{pair} {period} {name}: trades={summary["closed_trades"]} resolved={summary["resolved_closed_trades"]}',flush=True)
                del result,marks
        del raw,market
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False,float_format='%.15g')
    write_json(out/'data_quality.json',quality)
    manifest['complete']=True; manifest['finished_utc']=datetime.now(timezone.utc).isoformat()
    write_json(out/'RUN_MANIFEST.json',manifest)
    base=[x for x in rows if x['period']=='ALL' and x['variant']=='reference']
    write_json(out/'MINIMUM_100.json',{'definition':'Reference ALL closed trades with no coverage penalty and no unresolved gap; not pooled variants/halves.','all_three_pass':all(x['minimum_100_resolved'] for x in base),'pairs':{x['pair']:{k:x[k] for k in ['closed_trades','resolved_closed_trades','minimum_100_resolved']} for x in base}})
    print('Study complete; '+str(len(rows))+' runs. Minimum100: '+str(all(x['minimum_100_resolved'] for x in base)),flush=True)

if __name__=='__main__': main()
