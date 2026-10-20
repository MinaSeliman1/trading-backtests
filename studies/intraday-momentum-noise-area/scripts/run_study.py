"""Exécute les scénarios préfixés Noise Area sur les seules données réelles validées."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import json
import pickle
import platform
import time
import numpy as np
import pandas as pd
from noise_area.features import compute_features
from noise_area.engine import Config,simulate
from noise_area.statistics import summarize,return_statistics,block_bootstrap,timed_benchmarks


def clean(obj):
    if isinstance(obj,dict): return {str(k):clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)): return [clean(v) for v in obj]
    if isinstance(obj,(np.integer,)): return int(obj)
    if isinstance(obj,(float,np.floating)): return float(obj) if np.isfinite(obj) else None
    return obj


def write_json(path,obj):
    path.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def passive_series(market,dividends,yahoo_path):
    close=market.arrays['close'][np.arange(len(market.dates)),market.lengths-1].copy()
    frame=pd.read_csv(yahoo_path)
    values=dict(zip(frame.iloc[:,0].astype(str).str[:10],frame['Close']))
    fallback=[]
    for i,day in enumerate(market.dates):
        date=str(day.date())
        if not np.isfinite(close[i]) and date in values:
            close[i]=values[date];fallback.append(date)
    previous=pd.Series(close).shift(1).to_numpy()
    cash=np.array([dividends.get(str(d.date()),0.) for d in market.dates])
    return pd.DataFrame(dict(date=market.dates.strftime('%Y-%m-%d'),price_return=close/previous-1,total_return=(close+cash)/previous-1,
                             close=close,dividend=cash)),fallback


def grouped_exports(result,folder,thresholds,vix):
    trades=result.trades.copy()
    trades['entry_clock']=trades.entry_time.str[11:16]
    trades['volatility_regime']=pd.cut(trades.daily_volatility,[-np.inf,*thresholds,np.inf],labels=['low','medium','high']).astype(str)
    trades['vix_open']=trades.date.map(vix)
    trades['vix_regime']=pd.cut(trades.vix_open,[-np.inf,15,25,np.inf],labels=['below15','15to25','above25']).astype(str)
    for col in ['direction','entry_clock','volatility_regime','vix_regime']:
        trades.groupby(col,dropna=False).agg(trades=('net_pnl','size'),net_pnl=('net_pnl','sum'),mean_net_bps=('net_bps','mean')).to_csv(folder/f'by_{col}.csv')
    daily=result.daily.copy();daily['month']=daily.date.str[:7];daily['year']=daily.date.str[:4]
    for col in ['month','year']:
        grouped=daily.groupby(col).agg(net_pnl=('net_pnl','sum'),sessions=('date','size'),trades=('trades','sum'))
        grouped['return_pct']=daily.groupby(col).return_net.apply(lambda r:(np.prod(1+r)-1)*100)
        grouped.to_csv(folder/f'by_{col}.csv')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--prepared',type=Path,default=Path('data/prepared'))
    parser.add_argument('--out',type=Path,default=Path('results/2026-10-19'))
    args=parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()): raise SystemExit('Refusing to overwrite an execution; choose a new output directory.')
    args.out.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();sources=args.workspace/'data/noise_area_sources'
    markets={};dividends={};features={};passive={};fallbacks={}
    for symbol in ['SPY','QQQ']:
        with (args.prepared/f'{symbol}_market.pkl').open('rb') as stream: markets[symbol]=pickle.load(stream)
        dividends[symbol]=json.loads((args.prepared/f'{symbol}_dividends.json').read_text(encoding='utf-8'))
        for lookback in [10,14,20]: features[symbol,lookback]=compute_features(markets[symbol],dividends[symbol],lookback)
        passive[symbol],fallbacks[symbol]=passive_series(markets[symbol],dividends[symbol],sources/f'{symbol}_daily_yahoo.csv')
        passive[symbol].to_csv(args.out/f'{symbol}_passive_daily.csv',index=False)
    vix_frame=pd.read_csv(sources/'VIX_History.csv')
    vix=dict(zip(pd.to_datetime(vix_frame.DATE).dt.strftime('%Y-%m-%d'),vix_frame.OPEN))
    protocols={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('docs').glob('*.md')}
    code_hashes={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('noise_area').glob('*.py')}
    code_hashes[Path(__file__).name]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    validation=json.loads((args.prepared/'DATA_VALIDATION.json').read_text(encoding='utf-8'))
    for filename,expected in validation['prepared_files_sha256'].items():
        assert hashlib.sha256((args.prepared/filename).read_bytes()).hexdigest()==expected,filename
    periods={};thresholds={}
    for symbol in markets:
        m=markets[symbol];f=features[symbol,14]
        eligible=m.valid&np.isfinite(f['volatility'])&np.isfinite(f['upper'][:,359])
        first=str(m.dates[np.flatnonzero(eligible)[0]].date());last=str(m.dates[-1].date())
        periods[symbol]=dict(A=(first,'2024-04-30'),B=('2024-05-01',last),C=('2024-05-15',last),D=('2025-09-23',last))
        training=f['volatility'][(m.dates<'2024-05-01')&m.valid&np.isfinite(f['volatility'])]
        thresholds[symbol]=np.quantile(training,[1/3,2/3]).tolist()
    freeze=dict(utc=datetime.now(timezone.utc).isoformat(),periods=periods,config=asdict(Config()),
                volatility_terciles_from_A=thresholds,protocol_sha256=protocols,code_sha256=code_hashes,
                note='Frozen before first performance simulation. Retrospective study; current paper revision dated 2025-09-22.')
    write_json(args.out/'PRE_EXECUTION_PROTOCOL.json',freeze)
    rows=[];primary_results={}

    def run(symbol,period,cfg,kind='principal',lookback=14,start=None,end=None,label_suffix=''):
        lower,upper=periods[symbol][period] if period!='WF' else (start,end)
        label=f'{period}_{cfg.execution}_L{cfg.leverage_cap:g}_s{cfg.slippage:g}_{kind}{label_suffix}'
        folder=args.out/symbol/label;folder.mkdir(parents=True)
        result=simulate(markets[symbol],features[symbol,lookback],cfg,lower,upper)
        assert not result.daily.empty
        index=result.daily.date.tolist()
        b=passive[symbol].set_index('date').loc[index]
        spy=passive['SPY'].set_index('date').loc[index]
        assert np.isfinite(b.total_return).all() and np.isfinite(spy.total_return).all()
        stats=summarize(result,b.total_return,spy.total_return)
        stats.update(instrument=symbol,period=period,execution=cfg.execution,leverage_cap=cfg.leverage_cap,
                     slippage=cfg.slippage,kind=kind,lookback=lookback,frequency=cfg.frequency,stop=cfg.stop,
                     borrow_rate=cfg.borrow_rate,label=label)
        result.trades.to_csv(folder/'trades.csv',index=False)
        result.daily['buyhold_return']=b.total_return.to_numpy()
        result.daily['SPY_buyhold_return']=spy.total_return.to_numpy()
        result.daily.to_csv(folder/'daily.csv',index=False)
        primary=kind=='principal' and cfg.slippage==.001
        if primary:
            result.decisions.to_csv(folder/'decisions.csv',index=False)
            grouped_exports(result,folder,thresholds[symbol],vix)
            stats['buyhold_total_return']=return_statistics(b.total_return,index)
            stats['buyhold_price_return']=return_statistics(b.price_return,index)
        if primary and period=='B':
            stats['bootstrap_block5']=block_bootstrap(result.daily.return_net,b.total_return)
            control=timed_benchmarks(result.trades,result.daily,cfg.slippage,cfg.borrow_rate)
            random_sharpe=np.asarray(control['random_sharpe'])
            control['p_random_sharpe_ge_strategy']=(1+int(np.sum(random_sharpe>=stats['sharpe'])))/1001
            control['p_random_final_equity_ge_strategy']=(1+int(np.sum(np.asarray(control['random_final_equity'])>=stats['final_equity'])))/1001
            control['random_final_equity_ci95']=np.quantile(control['random_final_equity'],[.025,.975]).tolist()
            write_json(folder/'controls.json',control)
            stats['control_summary']={k:v for k,v in control.items() if not k.startswith('random_') and k!='always_long_daily'}
            primary_results[symbol,cfg.execution,cfg.leverage_cap]=result
        write_json(folder/'summary.json',stats)
        row={k:v for k,v in stats.items() if not isinstance(v,(dict,list))}
        rows.append(row)
        print(f'{len(rows):03d} {symbol} {label}: {len(result.trades)} trades, net={stats["net_pnl"]:.2f}',flush=True)
        return result

    for symbol in ['SPY','QQQ']:
        for period in ['A','B']:
            for execution in ['close','next_open']:
                for cap in [1.,4.]:
                    for cost in [.001,.01,.02,.03,.05]:
                        run(symbol,period,Config(execution=execution,leverage_cap=cap,slippage=cost))
        for period in ['C','D']:
            for execution in ['close','next_open']:
                for cap in [1.,4.]:run(symbol,period,Config(execution=execution,leverage_cap=cap))
        for cap in [1.,4.]:
            base=Config(leverage_cap=cap)
            for lookback in [10,20]:run(symbol,'B',base,kind=f'lookback{lookback}',lookback=lookback)
            for frequency in [15,60]:run(symbol,'B',replace(base,frequency=frequency),kind=f'frequency{frequency}')
            for stop in ['band','vwap']:run(symbol,'B',replace(base,stop=stop),kind=f'stop_{stop}')
            for borrow in [0.,.03]:run(symbol,'B',replace(base,borrow_rate=borrow),kind=f'borrow{borrow:g}')
            # Data convention check; declared, never selected on performance.
            features[symbol,99]=compute_features(markets[symbol],{},14)
            run(symbol,'B',base,kind='unadjusted_gap',lookback=99)
        last=periods[symbol]['B'][1]
        quarters=pd.period_range('2024Q2',pd.Timestamp(last).to_period('Q'),freq='Q')
        for quarter in quarters:
            lower=max('2024-05-01',str(quarter.start_time.date()));upper=min(last,str(quarter.end_time.date()))
            for execution in ['close','next_open']:
                for cap in [1.,4.]:
                    run(symbol,'WF',Config(execution=execution,leverage_cap=cap),kind=str(quarter),start=lower,end=upper)
    comparison=pd.DataFrame(rows);comparison.to_csv(args.out/'comparison_all.csv',index=False)
    # Exact scenario replay for cost break-even; no linear extrapolation of fixed quantities.
    breakeven=[]
    for symbol in ['SPY','QQQ']:
        for cap in [1.,4.]:
            lower,upper=periods[symbol]['B'];base=Config(leverage_cap=cap)
            zero=simulate(markets[symbol],features[symbol,14],replace(base,slippage=0),lower,upper).summary['final_equity']-100000
            if zero<=0:
                breakeven.append(dict(instrument=symbol,leverage_cap=cap,status='already_losing_at_zero_slippage',zero_slippage_net_pnl=zero,slippage_per_side_usd=None));continue
            lo=0.;hi=.05
            while hi<10:
                pnl=simulate(markets[symbol],features[symbol,14],replace(base,slippage=hi),lower,upper).summary['final_equity']-100000
                if pnl<=0:break
                hi*=2
            for _ in range(16):
                middle=(lo+hi)/2
                pnl=simulate(markets[symbol],features[symbol,14],replace(base,slippage=middle),lower,upper).summary['final_equity']-100000
                if pnl>0:lo=middle
                else:hi=middle
            breakeven.append(dict(instrument=symbol,leverage_cap=cap,status='root_bracketed',zero_slippage_net_pnl=zero,slippage_per_side_usd=(lo+hi)/2,bracket=[lo,hi]))
    write_json(args.out/'COST_BREAKEVEN.json',breakeven)
    manifest=dict(status='completed',utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
                  scenarios=len(rows),runtime_seconds=time.perf_counter()-started,periods=periods,
                  code_sha256=code_hashes,protocol_sha256=protocols,data_validation=validation,
                  dividend_files_sha256={s:hashlib.sha256((args.prepared/f'{s}_dividends.json').read_bytes()).hexdigest() for s in markets},
                  benchmark_fallback_dates=fallbacks,random_repetitions=1000,bootstrap_repetitions=5000,seed=20261019)
    write_json(args.out/'manifest.json',manifest)
    print(f'COMPLETE: {len(rows)} scenarios, {manifest["runtime_seconds"]:.1f} seconds',flush=True)


if __name__=='__main__':main()
