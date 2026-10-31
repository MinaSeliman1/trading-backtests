"""84 predefined local-history accounts. No API or broker order."""
from pathlib import Path
from dataclasses import asdict,replace
from datetime import datetime,timezone
import sys,argparse,shutil,time,platform,importlib.metadata
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from variation.data import source,load_sources
from variation.engine import Config,prepare,simulate,valid_bars
from variation.analysis import summarize,uncertainty
sha,write_json=source.sha,source.write_json
PERIODS=source.PERIODS
def specifications():
    c=Config()
    return [('reference',c)]+[(f'cost_{x:g}',replace(c,slippage=x)) for x in (.02,.03,.05)]+[
      ('quantile_0.8',replace(c,quantile=.8)),('quantile_0.95',replace(c,quantile=.95)),
      ('sampling_1',replace(c,sampling_minutes=1)),('sampling_5',replace(c,sampling_minutes=5)),
      ('raw_momentum',replace(c,metric='return')),('always_long',replace(c,metric='always')),
      ('noon',replace(c,observation_minutes=150)),('exit_close',replace(c,exit_kind='close')),
      ('resolved_prefix',replace(c,quality='resolved_prefix')),('rolling252',replace(c,history_mode='rolling'))]
def dependencies():
    files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
    for folder in ('previous-day-ibs/ibs','closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area','opening-range-5m/orb'):
        files+=list((ROOT.parent/folder).glob('*.py'))
    return sorted(set(files))
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an execution')
    out.mkdir(parents=True,exist_ok=True);tick=time.perf_counter();markets,_,profile=load_sources()
    code=sorted([ROOT/'requirements-lock.txt',*ROOT.glob('variation/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('audit/*.py')]);deps=dependencies()
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,executions=84,specifications={n:asdict(c) for n,c in specifications()},source=profile,
       protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in (ROOT/'PROTOCOL_EXECUTION.md',ROOT/'RESEARCH.md')},
       code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},dependencies_sha256={p.relative_to(ROOT.parents[1]).as_posix():sha(p) for p in deps},
       python=platform.python_version(),versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','exchange_calendars','matplotlib','pytest')},
       note='Frozen before first market PnL. Reused B, conditional coverage, independent ETF accounts, no bot.'))
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    for group,files,base in [('code_snapshot',code,ROOT),('dependency_snapshot',deps,ROOT.parents[1])]:
        for p in files:
            target=out/group/p.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    rows=[]
    for symbol,m in markets.items():
        quality=m.quality.copy();quality['date']=[str(x.date()) for x in m.dates];quality.to_csv(out/f'{symbol}_session_quality.csv',index=False)
        gaps=[dict(date=str(date.date()),slot=int(j)) for i,date in enumerate(m.dates) for j in (~valid_bars(m.arrays,i,int(m.lengths[i]))).nonzero()[0]]
        pd.DataFrame(gaps,columns=['date','slot']).to_csv(out/f'{symbol}_gaps.csv',index=False)
        for name,c in specifications():
            features=prepare(m,c);pd.DataFrame(features).to_csv(out/f'{symbol}_{name}_features.csv',index=False)
            for period,(start,end) in PERIODS.items():
                label=f'{symbol}_{period}_{name}';folder=out/label;folder.mkdir()
                r=simulate(m,features,c,start,end)
                for key in ('daily','trades','unresolved'):getattr(r,key).to_csv(folder/f'{key}.csv',index=False)
                r.daily.assign(year=r.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:((1+x).prod()-1)*100)).to_csv(folder/'by_year.csv')
                stats=dict(label=label,symbol=symbol,period=period,variant=name,start=start,end=end,**asdict(c),**summarize(r));write_json(folder/'summary.json',stats);rows.append(stats)
                if name=='reference':write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(r,seed=20261031))
                print(f'{len(rows)}/84 {label}: {stats["trades"]} trades net={stats["net_pnl"]:.2f}',flush=True)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),executions=len(rows),elapsed_seconds=time.perf_counter()-tick))
if __name__=='__main__':main()
