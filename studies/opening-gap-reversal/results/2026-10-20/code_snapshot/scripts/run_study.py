"""54 scénarios fixés, acquisitions SIP locales ; aucun ordre ou téléchargement."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'intraday-momentum-noise-area'))
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,pickle,platform,time
import numpy as np
import pandas as pd
from gap_reversal.engine import Config,prepare,simulate
from gap_reversal.analysis import summarize,annual_bootstrap


def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [clean(v) for v in x]
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    return x


def write_json(path,obj):path.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20')
    args=parser.parse_args();out=args.out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite previous execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    previous=ROOT.parent/'intraday-momentum-noise-area';prepared=previous/'data/prepared'
    validation=json.loads((prepared/'DATA_VALIDATION.json').read_text(encoding='utf-8'))
    for name,expected in validation['prepared_files_sha256'].items():
        if sha(prepared/name)!=expected:raise ValueError('source hash mismatch: '+name)
    markets={};dividends={};features={}
    for symbol in ['SPY','QQQ']:
        with (prepared/f'{symbol}_market.pkl').open('rb') as stream:markets[symbol]=pickle.load(stream)
        dividends[symbol]=json.loads((prepared/f'{symbol}_dividends.json').read_text(encoding='utf-8'))
        for profile in ['endpoints','complete_days']:
            features[symbol,profile]=prepare(markets[symbol],dividends[symbol],profile)
            features[symbol,profile].to_csv(out/f'{symbol}_quality_{profile}.csv',index=False)
        f=features[symbol,'complete_days'];counts={}
        for period,start in [('ALL','2016-01-04'),('B','2024-05-01')]:
            counts[period]=int(((f.date>=start)&(f.date<='2026-10-16')&(f.eligibility=='eligible')&f.event).sum())
        expected={'SPY':dict(ALL=42,B=11),'QQQ':dict(ALL=77,B=18)}[symbol]
        assert counts==expected,(symbol,counts,expected)
    code=[*ROOT.glob('gap_reversal/*.py'),*ROOT.glob('tests/*.py'),Path(__file__)]
    protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in [ROOT/'README.md',ROOT/'PROTOCOL_EXECUTION.md']}
    periods=dict(ALL=('2016-01-04','2026-10-16'),A=('2016-01-04','2024-04-30'),B=('2024-05-01','2026-10-16'))
    freeze=dict(utc=datetime.now(timezone.utc).isoformat(),periods=periods,config=asdict(Config()),threshold=.02,
        quantity='floor(current capital / observed 09:30 open)',entry='09:31 open',exit='10:00 open',
        scenario_count=54,protocols=protocols,source_sha256=validation['prepared_files_sha256'],
        data_validation_sha256=sha(prepared/'DATA_VALIDATION.json'),source_code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},
        original_statistics_sha256=sha(previous/'noise_area/statistics.py'),python=platform.python_version(),
        note='Written before first P&L simulation. Period B is exploratory reused history, not blind OOS. No optimization.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',freeze)
    rows=[];primaries={}
    for symbol in ['SPY','QQQ']:
        for period,(start,end) in periods.items():
            scenarios=[(profile,direction,slip) for profile in ['endpoints'] for direction in ['reversal','momentum'] for slip in [.01,.02,.03,.05]]
            scenarios.append(('complete_days','reversal',.01))
            for profile,direction,slip in scenarios:
                label=f'{symbol}_{period}_{direction}_{profile}_s{slip:g}';folder=out/label;folder.mkdir()
                result=simulate(markets[symbol],features[symbol,profile],Config(slippage=slip,direction=direction),start,end)
                stats=summarize(result);stats.update(symbol=symbol,period=period,profile=profile,strategy=direction,slippage=slip,label=label)
                result.trades.to_csv(folder/'trades.csv',index=False);result.daily.to_csv(folder/'daily.csv',index=False)
                if len(result.trades):
                    t=result.trades.assign(year=result.trades.date.str[:4])
                    for group in ['year','direction']:
                        t.groupby(group).agg(trades=('net_pnl','size'),net_pnl=('net_pnl','sum'),mean_net_bps=('net_bps','mean')).to_csv(folder/f'by_{group}.csv')
                if profile=='endpoints' and direction=='reversal' and slip==.01:
                    stats['annual_cluster_bootstrap']=annual_bootstrap(result.trades,result.daily.date)
                    primaries[symbol,period]=result
                write_json(folder/'summary.json',stats)
                rows.append({k:v for k,v in stats.items() if not isinstance(v,(dict,list))})
                print(f'{len(rows):02d}/54 {label}: {len(result.trades)} trades ; net {stats["net_pnl"]:.2f} USD',flush=True)
    assert len(rows)==54
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    correlations=[]
    for symbol in ['SPY','QQQ']:
        gap=primaries[symbol,'B'].daily[['date','return_net']].rename(columns={'return_net':'gap_return'})
        path=previous/f'results/2026-10-19/{symbol}/B_next_open_L1_s0.01_principal/daily.csv'
        noise=pd.read_csv(path,usecols=['date','return_net']).rename(columns={'return_net':'noise_return'})
        pair=gap.merge(noise,on='date',how='inner',validate='one_to_one');assert len(pair)==618
        pair.to_csv(out/f'{symbol}_B_noise_comparison.csv',index=False)
        correlations.append(dict(symbol=symbol,sessions=len(pair),correlation_daily=float(pair.gap_return.corr(pair.noise_return)),noise_daily_sha256=sha(path),
            note='Descriptive correlation only; both target 1x, 0.01 friction. No optimized combination.'))
    write_json(out/'noise_correlation.json',correlations)
    quality=[]
    official=['2020-03-09','2020-03-12','2020-03-16','2020-03-18']
    for symbol in ['SPY','QQQ']:
        f=features[symbol,'endpoints'];s=f[(f.date>='2016-01-04')&(~f.complete_day|~f.previous_complete_day|(f.eligibility!='eligible')|f.date.isin(official))].copy()
        s.insert(0,'symbol',symbol);s['official_mwcb_date']=s.date.isin(official);quality.append(s)
    pd.concat(quality,ignore_index=True).to_csv(out/'quality_exceptions.csv',index=False)
    write_json(out/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,scenarios=54,
        sources='Validated local Alpaca SIP raw cache, no acquisition performed in this run',source_validation='intraday-momentum-noise-area/data/prepared/DATA_VALIDATION.json',
        halt_context_source='https://www.nyse.com/article/assessing-nyse-model-performance',files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    print('COMPLETE',out,flush=True)


if __name__=='__main__':main()
