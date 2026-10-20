"""54 specifications figees avant premier P&L; aucune requete reseau."""
from pathlib import Path
import sys,importlib.util
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('orb_verified_sources',ROOT.parent/'closing-momentum/scripts/run_study.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
sha,write_json,load_sources=source.sha,source.write_json,source.load_sources
from orb.engine import Config,opening_features,simulate
from orb.analysis import summarize,uncertainty
from dataclasses import asdict
from datetime import datetime,timezone
import argparse,shutil,platform,time
import numpy as np
import pandas as pd
PERIODS=source.PERIODS


def specifications():
    return [Config(slippage=s) for s in (.01,.02,.03,.05)]+[Config(mode=m) for m in ('long_only','short_only','inverse')]+[Config(priority='target_first'),Config(quality='resolved_prefix')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');args=p.parse_args();out=args.out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();markets,_,profile=load_sources()
    for symbol,m in markets.items():
        f=opening_features(m);f['complete_session']=m.valid;f.to_csv(out/f'{symbol}_quality.csv',index=False)
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([*ROOT.glob('orb/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py')])
    dependencies=[ROOT.parent/'closing-momentum/scripts/run_study.py',ROOT.parent/'closing-momentum/closing_momentum/analysis.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/statistics.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/data.py']
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,specifications=[asdict(c) for c in specifications()],executions=54,
        protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in (ROOT/'README.md',ROOT/'PROTOCOL_EXECUTION.md')},source=profile,
        code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},dependencies_sha256={p.relative_to(ROOT.parents[1]).as_posix():sha(p) for p in dependencies},
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,note='Frozen before first financial loop. All returns conditional on historical source coverage; B reused, not blind OOS.'))
    for path in code:
        dest=out/'code_snapshot'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    rows=[]
    for symbol in ('SPY','QQQ'):
        for period,(start,end) in PERIODS.items():
            for cfg in specifications():
                label=f'{symbol}_{period}_{cfg.mode}_{cfg.quality}_{cfg.priority}_s{cfg.slippage:g}';folder=out/label;folder.mkdir()
                r=simulate(markets[symbol],cfg,start,end);s=summarize(r)
                s.update(label=label,symbol=symbol,period=period,mode=cfg.mode,quality=cfg.quality,priority=cfg.priority,slippage=cfg.slippage)
                for name in ('trades','daily','unresolved'):getattr(r,name).to_csv(folder/f'{name}.csv',index=False)
                r.daily.assign(year=r.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:(np.prod(1+x)-1)*100),data_excluded=('conditionally_excluded','sum')).to_csv(folder/'by_year.csv')
                for group in ('direction','half_session','exit_reason'):
                    r.trades.groupby(group).agg(trades=('net_pnl','size'),net_pnl=('net_pnl','sum'),mean_net_bps=('net_bps','mean')).to_csv(folder/f'by_{group}.csv')
                write_json(folder/'summary.json',s);rows.append(s)
                if cfg==Config():write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(r))
                print(f'{len(rows):02d}/54 {label}: {len(r.trades)} trades; net={s["net_pnl"]:.2f} USD',flush=True)
    assert len(rows)==54
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=54,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    print('COMPLETE',flush=True)


if __name__=='__main__':main()
