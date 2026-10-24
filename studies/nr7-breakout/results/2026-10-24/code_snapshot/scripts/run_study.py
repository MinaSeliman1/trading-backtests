"""48 frozen scenarios, verified local SIP archives only."""
from pathlib import Path
import sys,argparse,shutil,time,platform,importlib.metadata
from dataclasses import asdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from nr7.data import source,load_sources
from nr7.engine import Config,prepare,simulate
from orb.analysis import summarize,uncertainty
PERIODS=source.PERIODS
sha,write_json=source.sha,source.write_json


def specifications():
    return [Config(slippage=s) for s in (.01,.02,.03,.05)]+[Config(mode=m) for m in ('long_only','short_only')]+[Config(require_nr7=False),Config(quality='resolved_prefix')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24');a=p.parse_args();out=a.out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();markets,cash,profile=load_sources();features={s:prepare(m,cash[s]) for s,m in markets.items()}
    for s,f in features.items():f.to_csv(out/f'{s}_features_quality.csv',index=False)
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([*ROOT.glob('nr7/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py')])
    dependencies=[ROOT.parent/'closing-momentum/scripts/run_study.py',ROOT.parent/'closing-momentum/closing_momentum/analysis.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/statistics.py',ROOT.parent/'intraday-momentum-noise-area/noise_area/data.py',ROOT.parent/'opening-range-5m/orb/analysis.py',ROOT.parent/'opening-range-5m/orb/engine.py']
    versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','exchange_calendars','matplotlib','pytest')}
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,specifications=[asdict(c) for c in specifications()],executions=48,
        protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in (ROOT/'README.md',ROOT/'PROTOCOL_EXECUTION.md')},source=profile,
        code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},dependencies_sha256={p.relative_to(ROOT.parents[1]).as_posix():sha(p) for p in dependencies},python=platform.python_version(),versions=versions,
        note='Before first P&L loop. Reused B, not blind OOS. Conditional histories, no continuous portfolio on excluded days.'))
    for path in code:
        dest=out/'code_snapshot'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    rows=[]
    for symbol in ('SPY','QQQ'):
        for period,(start,end) in PERIODS.items():
            for cfg in specifications():
                label=f'{symbol}_{period}_{cfg.mode}_s{cfg.slippage:g}_{cfg.quality}_nr7{int(cfg.require_nr7)}';folder=out/label;folder.mkdir()
                r=simulate(markets[symbol],features[symbol],cfg,start,end)
                r.daily.to_csv(folder/'daily.csv',index=False);r.trades.to_csv(folder/'trades.csv',index=False);r.unresolved.to_csv(folder/'unresolved.csv',index=False)
                s=dict(label=label,symbol=symbol,period=period,start=start,end=end,**asdict(cfg),**summarize(r));write_json(folder/'summary.json',s);rows.append(s)
                if cfg==Config():write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(r,seed=20261024))
                print(f'{len(rows):02d}/48 {label}: {len(r.trades)} trades; net={s["net_pnl"]:.2f} USD',flush=True)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=len(rows),files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))


if __name__=='__main__':main()
