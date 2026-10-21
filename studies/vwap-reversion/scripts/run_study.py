"""48 specifications figees avant calcul; uniquement archives locales."""
from pathlib import Path
import sys,argparse,shutil,time,platform,importlib.metadata
from dataclasses import asdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from vwap_reversion.data import source,load_sources
from vwap_reversion.engine import Config,prepare,simulate
from vwap_reversion.analysis import summarize,uncertainty
PERIODS=source.PERIODS
sha,write_json=source.sha,source.write_json


def specifications():
    return [Config(slippage=s) for s in (.01,.02,.03,.05)]+[Config(mode=m) for m in ('long_only','short_only')]+[Config(exit_policy='eod_only'),Config(quality='resolved_prefix')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');a=p.parse_args();out=a.out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();markets,_,profile=load_sources();features={s:prepare(m) for s,m in markets.items()}
    for s,f in features.items():f.to_csv(out/f'{s}_features_quality.csv',index=False)
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([*ROOT.glob('vwap_reversion/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py')])
    dependencies=[ROOT.parent/'closing-momentum/scripts/run_study.py',ROOT.parent/'closing-momentum/closing_momentum/analysis.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/statistics.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/data.py',ROOT.parent/'opening-range-5m/orb/analysis.py']
    versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','exchange_calendars','matplotlib','pytest')}
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,specifications=[asdict(c) for c in specifications()],executions=48,
        protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in (ROOT/'README.md',ROOT/'PROTOCOL_EXECUTION.md')},source=profile,
        code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},dependencies_sha256={p.relative_to(ROOT.parents[1]).as_posix():sha(p) for p in dependencies},
        python=platform.python_version(),packages=versions,note='Frozen before first financial loop. Conditional current data coverage; B reused, not blind OOS. Source per-minute VWAP, no HLC3 proxy.'))
    for path in code:
        target=out/'code_snapshot'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    rows=[]
    for symbol in ('SPY','QQQ'):
        for period,(start,end) in PERIODS.items():
            for cfg in specifications():
                label=f'{symbol}_{period}_{cfg.mode}_{cfg.quality}_{cfg.exit_policy}_s{cfg.slippage:g}';folder=out/label;folder.mkdir()
                r=simulate(markets[symbol],features[symbol],cfg,start,end);s=summarize(r);s.update(label=label,symbol=symbol,period=period,mode=cfg.mode,quality=cfg.quality,exit_policy=cfg.exit_policy,slippage=cfg.slippage)
                for name in ('trades','daily','unresolved'):getattr(r,name).to_csv(folder/f'{name}.csv',index=False)
                r.daily.assign(year=r.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:(np.prod(1+x)-1)*100),data_excluded=('conditionally_excluded','sum')).to_csv(folder/'by_year.csv')
                for group in ('direction','half_session','exit_reason'):
                    r.trades.groupby(group).agg(trades=('net_pnl','size'),net_pnl=('net_pnl','sum'),mean_net_bps=('net_bps','mean')).to_csv(folder/f'by_{group}.csv')
                r.daily.groupby('eligibility').agg(sessions=('date','size'),net_pnl=('net_pnl','sum')).to_csv(folder/'by_eligibility.csv')
                write_json(folder/'summary.json',s);rows.append(s)
                if cfg==Config():write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(r))
                print(f'{len(rows):02d}/48 {label}: {len(r.trades)} trades; net={s["net_pnl"]:.2f} USD',flush=True)
    assert len(rows)==48
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=48,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    print('COMPLETE',flush=True)


if __name__=='__main__':main()
