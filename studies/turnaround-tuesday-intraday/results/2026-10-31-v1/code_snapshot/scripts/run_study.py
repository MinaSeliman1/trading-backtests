"""84 fixed scenarios; local verified SIP history only, no broker/API access."""
from pathlib import Path
import sys,argparse,shutil,platform,time,importlib.metadata
from datetime import datetime,timezone
from dataclasses import asdict,replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from tuesday.data import source,load_sources
from tuesday.engine import Config,prepare,signal,simulate,valid_ohlc
from orb.analysis import summarize,uncertainty
sha,write_json=source.sha,source.write_json
PERIODS=source.PERIODS

def specifications():
    c=Config()
    return [('reference',c)]+[(f'cost_{x:g}',replace(c,slippage=x)) for x in (.02,.03,.05)]+[
      ('drop_0.005',replace(c,drop=.005)),('drop_0.01',replace(c,drop=.01)),
      ('all_tuesdays',replace(c,require_down=False,require_monday=False)),('all_down_days',replace(c,weekday=None,require_monday=False))]+[
      (f'weekday_{x}',replace(c,weekday=x,require_monday=False)) for x in (0,2,3,4)]+[
      ('entry_5',replace(c,entry_slot=5)),('resolved_prefix',replace(c,quality='resolved_prefix'))]

def dependencies():
    files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
    for folder in ['previous-day-ibs/ibs','closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area','opening-range-5m/orb']:
        files+=list((ROOT.parent/folder).glob('*.py'))
    return sorted(set(files))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    markets,cash,profile=load_sources();features={s:prepare(m,cash[s]) for s,m in markets.items()}
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([ROOT/'requirements-lock.txt',*ROOT.glob('tuesday/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('audit/*.py')]);deps=dependencies()
    frozen=dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,executions=84,symbols=['SPY','QQQ'],specifications={name:asdict(c) for name,c in specifications()},source=profile,
      protocols={f.name:dict(sha256=sha(f),text=f.read_text(encoding='utf-8')) for f in [ROOT/'PROTOCOL_EXECUTION.md',ROOT/'RESEARCH.md']},
      code_sha256={f.relative_to(ROOT).as_posix():sha(f) for f in code},dependencies_sha256={f.relative_to(ROOT.parents[1]).as_posix():sha(f) for f in deps},
      python=platform.python_version(),versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','exchange_calendars','matplotlib','pytest']},
      note='Frozen before first market PnL; conditional coverage, reused B, original intraday adaptation, no bot.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',frozen)
    for f in code:
        target=out/'code_snapshot'/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    for f in deps:
        target=out/'dependency_snapshot'/f.relative_to(ROOT.parents[1]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    for symbol,m in markets.items():
        fs=features[symbol];rows=[]
        for f in fs:
            row=dict(f)
            for name,c in specifications():row['signal_'+name]=signal(m,f,c)['reason']
            rows.append(row)
        pd.DataFrame(rows).to_csv(out/f'{symbol}_features.csv',index=False)
        quality=m.quality.copy();quality['date']=[str(x.date()) for x in m.dates];quality.to_csv(out/f'{symbol}_session_quality.csv',index=False)
        gaps=[]
        for i,date in enumerate(m.dates):
            good=valid_ohlc(m.arrays,i,int(m.lengths[i]))
            gaps.extend(dict(date=str(date.date()),slot=j,reason='missing_or_invalid_ohlc') for j,ok in enumerate(good) if not ok)
        pd.DataFrame(gaps,columns=['date','slot','reason']).to_csv(out/f'{symbol}_gaps.csv',index=False)
    rows=[]
    for symbol in ['SPY','QQQ']:
        for period,(start,end) in PERIODS.items():
            for name,cfg in specifications():
                label=f'{symbol}_{period}_{name}';folder=out/label;folder.mkdir()
                result=simulate(markets[symbol],features[symbol],cfg,start,end)
                result.daily.to_csv(folder/'daily.csv',index=False);result.trades.to_csv(folder/'trades.csv',index=False);result.unresolved.to_csv(folder/'unresolved.csv',index=False)
                stats=dict(label=label,symbol=symbol,period=period,variant=name,start=start,end=end,**asdict(cfg),**summarize(result))
                result.daily.assign(year=result.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:((1+x).prod()-1)*100)).to_csv(folder/'by_year.csv')
                for field in ['entry_fill_leverage','modeled_stop_net_risk_pct']:
                    stats['max_'+field]=float(result.trades[field].max()) if len(result.trades) else None
                write_json(folder/'summary.json',stats);rows.append(stats)
                if name=='reference':write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(result,seed=20261031))
                print(f'{len(rows):02d}/84 {label}: {len(result.trades)} trades; net={stats["net_pnl"]:.2f} USD',flush=True)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=len(rows)))
if __name__=='__main__':main()
