"""42 preregistered pair-portfolio scenarios; verified local history only."""
from pathlib import Path
import sys,argparse,shutil,platform,time,importlib.metadata
from dataclasses import asdict,replace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from relative.data import source,load_sources
from relative.engine import Config,prepare,simulate
from relative.analysis import summarize,uncertainty
PERIODS=source.PERIODS
sha,write_json=source.sha,source.write_json

def specifications():
 c=Config()
 return [('reference',c)]+[(f'cost_{v:g}',replace(c,slippage=v)) for v in (.02,.03,.05)]+[
  ('z1.5',replace(c,entry_z=1.5)),('z2.5',replace(c,entry_z=2.5)),('window10',replace(c,lookback=10)),('window40',replace(c,lookback=40)),
  ('long_spread_only',replace(c,direction='long_spread_only')),('short_spread_only',replace(c,direction='short_spread_only')),
  ('delay2',replace(c,delay=2)),('cost_gate',replace(c,cost_gate=True)),('resolved_prefix',replace(c,quality='resolved_prefix')),('friction_zero',replace(c,slippage=0))]

def dependencies():
 files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
 for folder in ['previous-day-ibs/ibs','closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area']:
  files+=list((ROOT.parent/folder).glob('*.py'))
 return sorted(set(files))

def assemble(label,period,name,start,end,cfg,result):
 return {**dict(label=label,period=period,variant=name,start=start,end=end),**asdict(cfg),**summarize(result)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
 if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an execution')
 out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();markets,cash,profile=load_sources()
 code=[ROOT/'requirements-lock.txt',*ROOT.glob('relative/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('audit/*.py'),ROOT/'scripts/run_study.py'];deps=dependencies()
 frozen=dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,executions=42,portfolio='QQQ+SPY',specifications={n:asdict(c) for n,c in specifications()},source=profile,
  protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in [ROOT/'PROTOCOL_EXECUTION.md',ROOT/'RESEARCH.md']},
  code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},dependencies_sha256={p.relative_to(ROOT.parents[1]).as_posix():sha(p) for p in deps},
  python=platform.python_version(),versions={v:importlib.metadata.version(v) for v in ['numpy','pandas','exchange_calendars','matplotlib','pytest']},
  note='Financial code/tests/oracle frozen before PnL; reporting scripts can be authored after outputs, sealed in final manifest. One paired account, not two ETF accounts. Reused A/B, no blind OOS, conditional coverage.')
 write_json(out/'PRE_EXECUTION_PROTOCOL.json',frozen);write_json(out/'DATA_SOURCE_PROFILE.json',profile)
 for path in code:
  target=out/'code_snapshot'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
 for path in deps:
  target=out/'dependency_snapshot'/path.relative_to(ROOT.parents[1]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
 feature_sets={w:prepare(markets,Config(lookback=w)) for w in [10,20,40]}
 for symbol,m in markets.items():
  quality=m.quality.copy();quality['date']=[str(x.date()) for x in m.dates];quality.to_csv(out/f'{symbol}_session_quality.csv',index=False)
 for w,fs in feature_sets.items():
  pd.DataFrame([dict(date=f['date'],history_state=f['reason'],session_minutes=f['n'],min_same_clock_observations=int(f['count'].min()),max_same_clock_observations=int(f['count'].max())) for f in fs]).to_csv(out/f'window{w}_history_profile.csv',index=False)
 rows=[]
 for period,(start,end) in PERIODS.items():
  for name,cfg in specifications():
   label=f'{period}_{name}';folder=out/label;folder.mkdir();r=simulate(markets,feature_sets[cfg.lookback],cfg,start,end)
   for field in ['daily','trades','legs','unresolved']:getattr(r,field).to_csv(folder/f'{field}.csv',index=False)
   r.daily.assign(year=r.daily.date.str[:4]).groupby('year').agg(pairs=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:((1+x).prod()-1)*100)).to_csv(folder/'by_year.csv')
   stats=assemble(label,period,name,start,end,cfg,r);write_json(folder/'summary.json',stats);rows.append(stats)
   if name=='reference':write_json(out/f'{period}_uncertainty.json',uncertainty(r))
   print(f'{len(rows):02d}/42 {label}: {len(r.trades)} pairs; net={stats["net_pnl"]:.2f} USD',flush=True)
 pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
 write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),executions=len(rows),elapsed_seconds=time.perf_counter()-started))
if __name__=='__main__':main()
