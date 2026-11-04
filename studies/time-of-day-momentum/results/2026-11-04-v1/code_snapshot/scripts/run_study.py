"""Frozen 96-account study. Local data only, no credentials or bot mutation."""
from pathlib import Path
from dataclasses import asdict,replace
from datetime import datetime,timezone
import argparse,hashlib,importlib.metadata,json,platform,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from seasonal.data import source,load_sources
from seasonal.engine import Config,training,prepare,simulate,valid_bars
from seasonal.analysis import summarize,uncertainty,paired_tests,holm,random_clock_panel
sha,write_json=source.sha,source.write_json
PERIODS=source.PERIODS
CONTROLS=('control_same_clock_long','control_fixed_clock','control_random_clock')


def specifications():
    c=Config()
    return [('reference',c)]+[(f'cost_{s:g}',replace(c,slippage=s)) for s in (.02,.03,.05)]+[
        ('lookback_20',replace(c,lookback=20)),('lookback_60',replace(c,lookback=60)),('threshold_1',replace(c,threshold=1.)),('threshold_2',replace(c,threshold=2.)),
        ('stop_1',replace(c,stop_multiple=1.)),('stop_3',replace(c,stop_multiple=3.)),('long_only',replace(c,mode='long_only')),('inverse',replace(c,mode='inverse')),
        *[(name,replace(c,mode=name)) for name in CONTROLS],('resolved_prefix',replace(c,quality='resolved_prefix'))]


def dependencies():
    repo=ROOT.parents[1];files=[ROOT.parent/'closing-momentum/scripts/run_study.py']
    for folder in ('previous-day-ibs/ibs','closing-momentum/closing_momentum','intraday-momentum-noise-area/noise_area','opening-range-5m/orb'):
        files+=list((ROOT.parent/folder).glob('*.py'))
    return sorted(set(files))


def screen(comparison,uncertainties,contrasts):
    maxp={s:max(contrasts[(s,'ALL')][n]['p_one_sided'] for n in CONTROLS) for s in ('SPY','QQQ')};adjusted=holm(maxp);out={}
    for symbol in ('SPY','QQQ'):
        refs={p:comparison.loc[(comparison.symbol==symbol)&(comparison.period==p)&(comparison.variant=='reference')].iloc[0] for p in PERIODS}
        stress=comparison.loc[(comparison.symbol==symbol)&(comparison.period=='A')&(comparison.variant=='cost_0.02')].iloc[0]
        pairs=contrasts[(symbol,'ALL')]
        pair_ok=all(v['paired_signal_dates']>=100 and v['uncertainty']['blocks'].get('20',{}).get('mean_ci95',[-np.inf])[0]>0 for v in pairs.values())
        criteria=dict(at_least_100_trades_all=int(refs['ALL'].trades)>=100,positive_A_B_ALL=all(v.net_pnl>0 for v in refs.values()),positive_without_top3=refs['ALL'].return_without_top3_days_pct>0,
                      positive_A_double_friction=stress.net_pnl>0,positive_daily_ci20=uncertainties[(symbol,'ALL')]['observed_calendar_blocks']['blocks'].get('20',{}).get('mean_ci95',[-np.inf])[0]>0,
                      beats_all_three_controls_with_100_paired_trade_dates=pair_ok,holm_p_below_005=adjusted[symbol]<.05)
        out[symbol]=dict(criteria={k:bool(v) for k,v in criteria.items()},passes_all=all(criteria.values()),intersection_raw_p=maxp[symbol],holm_p=adjusted[symbol])
    return dict(results=out,multiplicity='Intersection max-p over three controls within ETF, Holm over the two ETF; does not correct earlier studies or the choice of this hypothesis.',not_blind_oos=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-11-04-v1');args=p.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('execution must stay inside study directory')
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();code=sorted([ROOT/'requirements-lock.txt',*ROOT.glob('seasonal/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('audit/*.py')]);deps=dependencies()
    markets,_,profile=load_sources()
    frozen=dict(utc=datetime.now(timezone.utc).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),periods=PERIODS,executions=96,specifications={n:asdict(c) for n,c in specifications()},source=profile,
                protocols={f.name:dict(sha256=sha(f),text=f.read_text(encoding='utf-8')) for f in (ROOT/'PROTOCOL_EXECUTION.md',ROOT/'RESEARCH.md')},code_sha256={f.relative_to(ROOT).as_posix():sha(f) for f in code},
                dependencies_sha256={f.relative_to(ROOT.parents[1]).as_posix():sha(f) for f in deps},python=platform.python_version(),versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','exchange_calendars','matplotlib','pytest')},note='Frozen before first MARKET PnL; reused A/B, no live bot changes.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',frozen);write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    for group,files,base in [('code_snapshot',code,ROOT),('dependency_snapshot',deps,ROOT.parents[1])]:
        for f in files:
            target=out/group/f.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    rows=[];uncertainties={};contrasts={}
    for symbol,m in markets.items():
        quality=m.quality.copy();quality['date']=[str(x.date()) for x in m.dates];quality.to_csv(out/f'{symbol}_session_quality.csv',index=False)
        gaps=[dict(date=str(date.date()),slot=int(j)) for i,date in enumerate(m.dates) for j in (~valid_bars(m.arrays,i,int(m.lengths[i]))).nonzero()[0]]
        pd.DataFrame(gaps,columns=['date','slot']).to_csv(out/f'{symbol}_gaps.csv',index=False)
        histories={n:training(m,n) for n in (20,40,60)};results={};features_by_name={}
        for name,c in specifications():
            features=prepare(m,c,histories[c.lookback]);features_by_name[name]=features;pd.DataFrame(features).to_csv(out/f'{symbol}_{name}_features.csv',index=False)
            for period,(start,end) in PERIODS.items():
                label=f'{symbol}_{period}_{name}';folder=out/label;folder.mkdir();r=simulate(m,features,c,start,end);results[(name,period)]=r
                for key in ('daily','trades','unresolved'):getattr(r,key).to_csv(folder/f'{key}.csv',index=False)
                r.daily.assign(year=r.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:((1+x).prod()-1)*100)).to_csv(folder/'by_year.csv')
                stats=dict(label=label,symbol=symbol,period=period,variant=name,start=start,end=end,**asdict(c),**summarize(r));stats['max_modeled_stop_net_risk_pct']=float(r.trades.modeled_stop_net_risk_pct.max()) if len(r.trades) else None
                write_json(folder/'summary.json',stats);rows.append(stats)
                if name=='reference':
                    u=uncertainty(r,seed=20261104);uncertainties[(symbol,period)]=u;write_json(out/f'{symbol}_{period}_uncertainty.json',u)
                print(f'{len(rows)}/96 {label}: {len(r.trades)} trades, net={stats["net_pnl"]:.2f}',flush=True)
        for period in PERIODS:
            pairs=paired_tests(results[('reference',period)],{n:results[(n,period)] for n in CONTROLS});contrasts[(symbol,period)]=pairs;write_json(out/f'{symbol}_{period}_controls.json',pairs)
        panel=random_clock_panel(m,features_by_name['reference'],Config());write_json(out/f'{symbol}_random_clock_panel.json',panel['summary'])
        for key in ('draws','daily','excluded'):panel[key].to_csv(out/f'{symbol}_random_clock_{key}.csv',index=False)
    comparison=pd.DataFrame(rows);comparison.to_csv(out/'comparison_all.csv',index=False);write_json(out/'SCREENING.json',screen(comparison,uncertainties,contrasts))
    write_json(out/'RUN_COMPLETE.json',dict(utc=datetime.now(timezone.utc).isoformat(),executions=len(rows),elapsed_seconds=time.perf_counter()-started));print('COMPLETE',flush=True)
if __name__=='__main__':main()
