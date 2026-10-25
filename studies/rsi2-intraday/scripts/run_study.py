"""72 preregistered RSI scenarios, only verified local SIP history."""
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
from rsi2.data import source,load_sources
from rsi2.engine import Config,prepare,signal,simulate
from orb.analysis import summarize,uncertainty
PERIODS=source.PERIODS
sha,write_json=source.sha,source.write_json


def specifications():
    base=Config()
    return [('reference' if s==.01 else f'cost_{s:g}',replace(base,slippage=s)) for s in (.01,.02,.03,.05)]+[
        ('both',replace(base,mode='both')),('short_only',replace(base,mode='short_only')),
        ('no_regime',replace(base,use_regime=False)),('entry_10',replace(base,entry_threshold=10)),
        ('stop_1atr',replace(base,stop_atr=1)),('stop_3atr',replace(base,stop_atr=3)),
        ('exit_80',replace(base,exit_threshold=80)),('resolved_prefix',replace(base,quality='resolved_prefix'))]


def dependencies():
    files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
    for folder in ['closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area','opening-range-5m/orb']:
        files+=list((ROOT.parent/folder).glob('*.py'))
    return sorted(set(files))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24-v1');out=p.parse_args().out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    markets,cash,profile=load_sources();features={s:prepare(m,cash[s]) for s,m in markets.items()}
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    for s,fs in features.items():
        data=[]
        for f in fs:
            row={k:v for k,v in f.items() if k not in ('bars','good','rsi','atr')}
            selected=signal(f,Config());row.update({f'principal_{k}':v for k,v in selected.items()})
            data.append(row)
        pd.DataFrame(data).to_csv(out/f'{s}_features_quality.csv',index=False)
    code=sorted([*ROOT.glob('rsi2/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py')]);deps=dependencies()
    frozen=dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,executions=72,specifications={name:asdict(cfg) for name,cfg in specifications()},source=profile,
        protocols={path.name:dict(sha256=sha(path),text=path.read_text(encoding='utf-8')) for path in [ROOT/'PROTOCOL_EXECUTION.md']},
        code_sha256={path.relative_to(ROOT).as_posix():sha(path) for path in code},dependencies_sha256={path.relative_to(ROOT.parents[1]).as_posix():sha(path) for path in deps},
        python=platform.python_version(),versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','exchange_calendars','matplotlib','pytest']},
        note='Frozen before first PnL loop; reused B and conditional histories, no blind OOS or new bot.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',frozen)
    for path in code:
        target=out/'code_snapshot'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    for path in deps:
        target=out/'dependency_snapshot'/path.relative_to(ROOT.parents[1]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    rows=[]
    for symbol in ['SPY','QQQ']:
        for period,(start,end) in PERIODS.items():
            for name,cfg in specifications():
                label=f'{symbol}_{period}_{name}';folder=out/label;folder.mkdir()
                result=simulate(markets[symbol],features[symbol],cfg,start,end)
                result.daily.to_csv(folder/'daily.csv',index=False);result.trades.to_csv(folder/'trades.csv',index=False);result.unresolved.to_csv(folder/'unresolved.csv',index=False)
                stats=dict(label=label,symbol=symbol,period=period,variant=name,start=start,end=end,**asdict(cfg),**summarize(result))
                write_json(folder/'summary.json',stats);rows.append(stats)
                if name=='reference':write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(result,seed=20261024))
                print(f'{len(rows):02d}/72 {label}: {len(result.trades)} trades; net={stats["net_pnl"]:.2f} USD',flush=True)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=len(rows)))


if __name__=='__main__':main()
