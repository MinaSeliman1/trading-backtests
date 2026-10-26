"""42 executions predefinies, aucune requete reseau ou mutation du bot."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'intraday-momentum-noise-area'))
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,pickle,platform,time,shutil
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from closing_momentum.engine import Config,prepare,simulate
from closing_momentum.analysis import summarize,uncertainty

PERIODS=dict(ALL=('2016-01-04','2026-10-16'),A=('2016-01-04','2024-04-30'),B=('2024-05-01','2026-10-16'))


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer):return int(value)
    if isinstance(value,np.bool_):return bool(value)
    return value


def write_json(path,value):Path(path).write_text(json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def verify_hashes(folder,expected):
    for name,want in expected.items():
        if sha(Path(folder)/name)!=want:raise ValueError('source hash mismatch: '+name)


def validate_market(market):
    if not market.dates.is_unique or not market.dates.is_monotonic_increasing:raise ValueError('session keys')
    cal=xcals.get_calendar('XNYS',start=market.dates[0],end=market.dates[-1]);schedule=cal.schedule
    if not market.dates.equals(pd.DatetimeIndex(schedule.index).tz_localize(None)):raise ValueError('calendar continuity')
    lengths=((schedule['close']-schedule['open']).dt.total_seconds()/60).to_numpy(dtype=int)
    if not np.array_equal(market.lengths,lengths):raise ValueError('calendar session lengths')
    for k in ('open','high','low','close','volume'):
        if market.arrays[k].shape!=(len(market.dates),390) or market.arrays[k].dtype!=np.float64:raise ValueError('array shape or precision')
    for i,row in market.quality.iterrows():
        if pd.Timestamp(row.session_open)!=pd.Timestamp(schedule.iloc[i]['open']) or pd.Timestamp(row.session_close)!=pd.Timestamp(schedule.iloc[i]['close']):raise ValueError('source session timezone')
    return dict(symbol=market.symbol,first=str(market.dates[0].date()),last=str(market.dates[-1].date()),calendar_sessions=len(market.dates),complete_sessions=int(market.valid.sum()),
        incomplete_sessions=int((~market.valid).sum()),dtypes={k:str(v.dtype) for k,v in market.arrays.items()},quality_reasons=market.quality.reason.fillna('').value_counts().to_dict(),
        calendar_continuous=True,duplicate_dates=0)


def load_sources():
    prepared=ROOT.parent/'intraday-momentum-noise-area/data/prepared';validation=json.loads((prepared/'DATA_VALIDATION.json').read_text())
    verify_hashes(prepared,validation['prepared_files_sha256'])
    raw=[]
    for acquisition in validation['acquisitions']:
        path=Path(acquisition['path'])
        if sha(path)!=acquisition['sha256']:raise ValueError('raw acquisition hash mismatch')
        raw.append(dict(path=path.relative_to(ROOT.parents[2]).as_posix(),sha256=acquisition['sha256'],rows=acquisition['rows'],raw_pages_reconciled=acquisition['raw_pages_reconciled']))
    markets={};dividends={};profiles=[]
    for symbol in ('SPY','QQQ'):
        with (prepared/f'{symbol}_market.pkl').open('rb') as stream:markets[symbol]=pickle.load(stream)
        dividends[symbol]=json.loads((prepared/f'{symbol}_dividends.json').read_text());profiles.append(validate_market(markets[symbol]))
    corp=ROOT.parents[2]/'data/noise_area_extension/corporate_actions/0001.json';actions=json.loads(corp.read_text())
    if actions.get('next_page_token'):raise ValueError('unread corporate action page')
    return markets,dividends,dict(prepared_files_sha256=validation['prepared_files_sha256'],validation_sha256=sha(prepared/'DATA_VALIDATION.json'),raw_acquisitions=raw,profiles=profiles,
        corporate_action_sha256=sha(corp),corporate_action_counts={k:len(v) for k,v in actions['corporate_actions'].items()},
        split_check='Original all-type request for SPY/QQQ, 2016-01-01 through2026-10-19 returned no split records; provider completeness not independently established.',
        dividend_reconciliation=validation['dividend_reconciliation'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');p.add_argument('--rerun-reason');args=p.parse_args(argv);out=args.out
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing execution')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter();markets,cash,profile=load_sources();features={s:prepare(markets[s],cash[s]) for s in markets}
    for symbol,f in features.items():
        f.to_csv(out/f'{symbol}_quality.csv',index=False)
        if f.loc[(f.eligibility=='eligible')&(f.signal_sign!=0),'exit_reference'].isna().any():raise ValueError('unresolved eligible exit before P&L')
    write_json(out/'DATA_SOURCE_PROFILE.json',profile)
    code=sorted([*ROOT.glob('closing_momentum/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py')])
    protocols={p.name:dict(sha256=sha(p),text=p.read_text(encoding='utf-8')) for p in (ROOT/'README.md',ROOT/'PROTOCOL_EXECUTION.md')}
    freeze=dict(utc=datetime.now(timezone.utc).isoformat(),periods=PERIODS,base_config=asdict(Config()),strategy_executions=30,reference_executions=12,
        frictions=[.01,.02,.03,.05],protocols=protocols,source=profile,code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code},
        statistics_sha256=sha(ROOT.parent/'intraday-momentum-noise-area/noise_area/statistics.py'),python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
        calendar_version=xcals.__version__,rerun_reason=args.rerun_reason,note='Frozen before first financial scenario loop. B reuses previously studied history; not blind OOS.')
    write_json(out/'PRE_EXECUTION_PROTOCOL.json',freeze)
    for path in code:
        dest=out/'code_snapshot'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    rows=[]
    for symbol in ('SPY','QQQ'):
        for period,(start,end) in PERIODS.items():
            specs=[('momentum',slip,'strategy') for slip in (.01,.02,.03,.05)]+[('long_only',.01,'strategy'),('always_long',.01,'reference'),('opposite',.01,'reference')]
            primary=None;long_reference=None
            for mode,slip,role in specs:
                label=f'{symbol}_{period}_{mode}_s{slip:g}';folder=out/label;folder.mkdir()
                fixed=primary.daily.set_index('date').target_quantity.to_dict() if role=='reference' else None
                result=simulate(markets[symbol],features[symbol],Config(mode=mode,slippage=slip),start,end,fixed_quantities=fixed)
                if mode=='momentum' and slip==.01:primary=result
                if mode=='always_long':long_reference=result
                stats=summarize(result);stats.update(label=label,symbol=symbol,period=period,mode=mode,slippage=slip,role=role)
                result.trades.to_csv(folder/'trades.csv',index=False);result.daily.to_csv(folder/'daily.csv',index=False)
                years=result.daily.assign(year=result.daily.date.str[:4]).groupby('year').agg(trades=('trades','sum'),net_pnl=('net_pnl','sum'),return_pct=('return_net',lambda x:(np.prod(1+x)-1)*100))
                years.to_csv(folder/'by_year.csv')
                for group in ('direction','half_session'):
                    result.trades.groupby(group).agg(trades=('net_pnl','size'),net_pnl=('net_pnl','sum'),mean_net_bps=('net_bps','mean')).to_csv(folder/f'by_{group}.csv')
                write_json(folder/'summary.json',stats);rows.append(stats)
                print(f'{len(rows):02d}/42 {label}: {len(result.trades)} trades; net={stats["net_pnl"]:.2f} USD',flush=True)
            write_json(out/f'{symbol}_{period}_uncertainty.json',uncertainty(primary,long_reference))
    assert len(rows)==42
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    write_json(out/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,executions=42,
        files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    print('COMPLETE',str(out),flush=True)


if __name__=='__main__':main()
