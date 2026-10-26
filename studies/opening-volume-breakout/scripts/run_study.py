"""72 preregistered scenarios; verified local history, no broker transport."""
from pathlib import Path
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import importlib.metadata
import platform
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from ovb.data import source,load_sources
from ovb.engine import Config,prepare,signal,simulate,valid_bars
from orb.analysis import summarize,uncertainty
PERIODS=source.PERIODS
sha,write_json=source.sha,source.write_json

def specifications():
    c=Config()
    return [('reference' if s==.01 else f'cost_{s:g}',replace(c,slippage=s)) for s in (.01,.02,.03,.05)]+[
        ('no_volume',replace(c,volume_threshold=0)),('volume_1.5',replace(c,volume_threshold=1.5)),('volume_2',replace(c,volume_threshold=2)),
        ('range15',replace(c,window=15)),('cutoff60',replace(c,cutoff=60)),('long_only',replace(c,mode='long_only')),
        ('short_only',replace(c,mode='short_only')),('resolved_prefix',replace(c,quality='resolved_prefix'))]

def dependencies():
    files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
    for folder in ['closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area','opening-range-5m/orb']:
        files+=list((ROOT.parent/folder).glob('*.py'))
    return sorted(set(files))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24-v1');out=p.parse_args().out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    markets,cash,profile=load_sources();features={(s,w):prepare(m,w) for s,m in markets.items() for w in (5,15)}
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([*ROOT.glob('ovb/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('audit/*.py')]);deps=dependencies()
    frozen=dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,executions=72,specifications={name:asdict(c) for name,c in specifications()},source=profile,
        protocols={path.name:dict(sha256=sha(path),text=path.read_text(encoding='utf-8')) for path in [ROOT/'PROTOCOL_EXECUTION.md',ROOT/'RESEARCH.md']},
        code_sha256={path.relative_to(ROOT).as_posix():sha(path) for path in code},dependencies_sha256={path.relative_to(ROOT.parents[1]).as_posix():sha(path) for path in deps},
        python=platform.python_version(),versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','exchange_calendars','matplotlib','pytest']},
        note='Frozen before first market PnL; conditional coverage; reused B; no bot or claim of blind OOS.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',frozen)
    for path in code:
        target=out/'code_snapshot'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    for path in deps:
        target=out/'dependency_snapshot'/path.relative_to(ROOT.parents[1]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    for (s,w),fs in features.items():
        pd.DataFrame([{**f,**{f'principal_{k}':v for k,v in signal(markets[s],f,replace(Config(),window=w)).items()}} for f in fs]).to_csv(out/f'{s}_range{w}_features.csv',index=False)
    for symbol,m in markets.items():
        quality=m.quality.copy();quality['date']=[str(x.date()) for x in m.dates];quality.to_csv(out/f'{symbol}_session_quality.csv',index=False)
        gaps=[]
        for i,date in enumerate(m.dates):
            good=valid_bars(m.arrays,i,int(m.lengths[i]))
            gaps.extend(dict(date=str(date.date()),slot=j,reason='missing_or_invalid_ohlcv') for j,ok in enumerate(good) if not ok)
        pd.DataFrame(gaps,columns=['date','slot','reason']).to_csv(out/f'{symbol}_gaps.csv',index=False)
    rows=[]
    for symbol in ['SPY','QQQ']:
        for period,(start,end) in PERIODS.items():
            for name,cfg in specifications():
                label=f'{symbol}_{period}_{name}';folder=out/label;folder.mkdir()
                result=simulate(markets[symbol],features[(symbol,cfg.window)],cfg,start,end)
                result.daily.to_csv(folder/'daily.csv',index=False);result.trades.to_csv(folder/'trades.csv',index=False);result.unresolved.to_csv(folder/'unresolved.csv',index=False)
                stats=dict(label=label,symbol=symbol,period=period,variant=name,start=start,end=end,**asdict(cfg),**summarize(result))
                write_json(folder/'summary.json',stats);rows.append(stats)
                if name=='reference':write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(result,seed=20261024))
                print(f'{len(rows):02d}/72 {label}: {len(result.trades)} trades; net={stats["net_pnl"]:.2f} USD',flush=True)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=len(rows)))

if __name__=='__main__':main()
