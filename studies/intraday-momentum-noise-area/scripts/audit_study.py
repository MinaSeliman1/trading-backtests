"""Audit indépendant : formules scalaires sur les données brutes, P&L par expositions.

Ne fait appel ni aux indicateurs, ni à la décision, ni au simulateur de production.
Le cache OHLCV a été rapproché des acquisitions CSV/pages avant les performances.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
import pickle
import numpy as np
import pandas as pd


def near(a,b,label,tolerance=1e-6):
    assert abs(float(a)-float(b))<=tolerance,(label,a,b)


def indicators(m,i,cash):
    arrays=m.arrays;opening=arrays['open'][i,0];n=int(m.lengths[i])
    if i<15 or not m.valid[i-15:i+1].all():
        # Even when earlier data is missing, exact prior-day close may exist;
        # the daily volatility window still requires 15 consecutive valid closes.
        volatility=np.nan
    else:
        closes=[float(arrays['close'][k,m.lengths[k]-1]) for k in range(i-15,i)]
        returns=[closes[k]/closes[k-1]-1 for k in range(1,15)]
        mean=math.fsum(returns)/14
        volatility=math.sqrt(math.fsum((r-mean)**2 for r in returns)/13)
    previous=arrays['close'][i-1,m.lengths[i-1]-1] if i>0 and m.valid[i-1] else np.nan
    adjusted=previous-cash.get(str(m.dates[i].date()),0.)
    rows=[]
    for j in range(29,n-1,30):
        eligible=[k for k in range(i) if m.valid[k] and np.isfinite(arrays['close'][k,j])][-14:]
        moves=[abs(arrays['close'][k,j]/arrays['open'][k,0]-1) for k in eligible]
        sigma=math.fsum(moves)/14 if len(moves)==14 else np.nan
        volume=math.fsum(arrays['volume'][i,:j+1])
        vwap=math.fsum((arrays['high'][i,k]+arrays['low'][i,k]+arrays['close'][i,k])*arrays['volume'][i,k] for k in range(j+1))/(3*volume) if volume else np.nan
        rows.append(dict(j=j,price=arrays['close'][i,j],sigma=sigma,vwap=vwap,
                         upper=max(opening,adjusted)*(1+sigma),lower=min(opening,adjusted)*(1-sigma),
                         past_dates=[str(m.dates[k].date()) for k in eligible],past_moves=moves,
                         previous_close=previous,previous_close_adjusted=adjusted,opening=opening,volatility=volatility))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    parser.add_argument('--prepared',type=Path,default=Path('data/prepared'))
    args=parser.parse_args();out=args.results
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['code_sha256'].items():
        path=Path(name) if name.startswith('noise_area/') else Path('scripts')/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,('executed source changed',path)
    comparison=pd.read_csv(out/'comparison_all.csv')
    assert len(comparison)==220 and comparison.label.groupby(comparison.instrument).nunique().sum()==220
    exports=[]
    for row in comparison.itertuples():
        folder=out/row.instrument/row.label
        trades=pd.read_csv(folder/'trades.csv');daily=pd.read_csv(folder/'daily.csv')
        summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        near(trades.net_pnl.sum(),row.net_pnl,'comparison')
        near(daily.net_pnl.sum(),row.net_pnl,'daily sum')
        near(daily.equity.iloc[-1],100000+row.net_pnl,'ledger')
        near(np.prod(1+daily.return_net)*100000,daily.equity.iloc[-1],'compounding')
        assert len(trades)==summary['trades']==row.trades
        assert int(daily.trades.sum())==len(trades)
        assert np.allclose(trades.gross_pnl-trades.commission-trades.borrow_fee,trades.net_pnl,atol=1e-7,rtol=0)
        if len(trades):
            assert (trades.quantity>0).all() and (trades.quantity%1==0).all()
            entry=pd.to_datetime(trades.entry_time,utc=True).dt.tz_convert('America/New_York')
            exit_time=pd.to_datetime(trades.exit_time,utc=True).dt.tz_convert('America/New_York')
            assert (entry.dt.date==exit_time.dt.date).all()
            elapsed=entry.dt.hour*60+entry.dt.minute-570
            assert (elapsed%int(row.frequency)==0).all() and (elapsed>=int(row.frequency)).all()
        near(daily.max_drawdown_pct_so_far.iloc[-1]*100,summary['max_drawdown_pct'],'DD export')
        exports.append(dict(instrument=row.instrument,label=row.label,trades=len(trades),net_pnl=float(trades.net_pnl.sum())))
    primary=comparison[(comparison.kind=='principal')&(comparison.slippage==.001)]
    assert len(primary)==32
    caches={};manual=[];checked=0;decisions_checked=0;reference_days=0;reconciliations=[]
    for symbol in ['SPY','QQQ']:
        with (args.prepared/f'{symbol}_market.pkl').open('rb') as stream:m=pickle.load(stream)
        cash=json.loads((args.prepared/f'{symbol}_dividends.json').read_text())
        date_indices={str(d.date()):i for i,d in enumerate(m.dates)}
        for row in primary[primary.instrument==symbol].itertuples():
            folder=out/symbol/row.label
            trades=pd.read_csv(folder/'trades.csv');daily=pd.read_csv(folder/'daily.csv');trace=pd.read_csv(folder/'decisions.csv')
            grouped_trades={date:g for date,g in trades.groupby('date')};grouped_trace={date:g for date,g in trace.groupby('date')}
            capital=100000.
            for d in daily.itertuples():
                i=date_indices[d.date]
                if d.eligibility!='eligible':
                    near(d.net_pnl,0,'flat excluded day');assert d.date not in grouped_trades
                    continue
                key=(symbol,d.date)
                if key not in caches:caches[key]=indicators(m,i,cash)
                inputs=caches[key];vol=inputs[0]['volatility']
                assert np.isfinite(vol),('unexpected eligible window',row.label,d.date)
                leverage=min(row.leverage_cap,.02/vol) if vol>0 else row.leverage_cap
                q=math.floor(capital*leverage/m.arrays['open'][i,0])
                actual_trace=grouped_trace[d.date];assert len(inputs)==len(actual_trace)
                position=0;targets=[];refs=[];prior=[]
                for indicator,actual in zip(inputs,actual_trace.itertuples()):
                    for name in ['price','upper','lower','vwap']:near(getattr(actual,name),indicator[name],name,1e-9)
                    price=indicator['price'];ub=indicator['upper'];lb=indicator['lower'];vwap=indicator['vwap']
                    wanted=1 if price>max(ub,vwap) else -1 if price<min(lb,vwap) else 0
                    if position==1 and price==max(ub,vwap):wanted=1
                    if position==-1 and price==min(lb,vwap):wanted=-1
                    assert int(actual.position_before)==position and int(actual.target)==wanted
                    assert int(actual.quantity)==q
                    j=indicator['j'];reference=m.arrays['close'][i,j] if row.execution=='close' else m.arrays['open'][i,j+1]
                    near(actual.execution_reference,reference,'execution reference',1e-10)
                    prior.append(position);targets.append(wanted);refs.append(reference);position=wanted
                    decisions_checked+=1
                refs=np.r_[refs,m.arrays['open'][i,m.lengths[i]-1]]
                changes=np.abs(np.diff(np.r_[0,targets,0]));orders=int(changes.sum())
                gross_reference=q*float(np.dot(targets,np.diff(refs)))
                commission=orders*max(.35,q*.0035)
                short_entries=[k for k,(before,after) in enumerate(zip(prior,targets)) if after==-1 and before!=-1]
                borrow=math.fsum(q*(refs[k]-row.slippage)*row.borrow_rate/360 for k in short_entries)
                net=gross_reference-orders*q*row.slippage-commission-borrow
                near(net,d.net_pnl,'independent exposure P&L')
                capital+=net;near(capital,d.equity,'independent daily equity')
                day_trades=grouped_trades.get(d.date,pd.DataFrame())
                assert len(day_trades)==int(sum(after!=0 and after!=before for before,after in zip(prior,targets)))
                for trade in day_trades.itertuples():
                    sign=1 if trade.direction=='LONG' else -1
                    near(trade.entry_price,trade.entry_reference+sign*row.slippage,'entry fill',1e-9)
                    near(trade.exit_price,trade.exit_reference-sign*row.slippage,'exit fill',1e-9)
                    near(trade.commission,2*max(.35,q*.0035),'two-sided commission')
                    loan=q*trade.entry_price*row.borrow_rate/360 if sign==-1 else 0
                    near(trade.borrow_fee,loan,'borrow')
                    near(trade.net_pnl,(trade.exit_price-trade.entry_price)*sign*q-trade.commission-loan,'trade P&L')
                    assert int(trade.quantity)==q
                    expected_exit=next((x['j'] for x,t in zip(inputs,targets) if x['j']>trade.entry_decision_index and t!=sign),None)
                    if expected_exit is None:assert trade.exit_reason=='session_end'
                    else:assert int(trade.exit_decision_index)==expected_exit
                    checked+=1
                reference_days+=1
            reconciliations.append(dict(instrument=symbol,label=row.label,trades=len(trades),final_capital=capital))
            if row.period=='B' and row.execution=='next_open' and row.leverage_cap==4:
                for trade in list(trades.itertuples())[:5]:
                    data=next(x for x in caches[symbol,trade.date] if x['j']==int(trade.entry_decision_index))
                    manual.append(dict(instrument=symbol,date=trade.date,direction=trade.direction,
                                       entry_time=trade.entry_time,exit_time=trade.exit_time,
                                       **data,quantity=trade.quantity,entry_reference=trade.entry_reference,entry_price=trade.entry_price,
                                       exit_reference=trade.exit_reference,exit_price=trade.exit_price,commission=trade.commission,
                                       borrow_fee=trade.borrow_fee,net_pnl=trade.net_pnl,equity_at_day_start=trade.equity_at_day_start,
                                       target_leverage=trade.target_leverage,exit_reason=trade.exit_reason))
    pd.DataFrame([{k:v for k,v in item.items() if not isinstance(v,list)} for item in manual]).to_csv(out/'manual_10_trades.csv',index=False)
    (out/'manual_10_inputs.json').write_text(json.dumps(manual,indent=2),encoding='utf-8')
    result=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),scenarios_exports_checked=len(exports),
                primary_scenarios_independently_rebuilt=len(primary),primary_trade_rows_checked=checked,
                halfhour_decisions_checked=decisions_checked,independent_calendar_days=reference_days,
                manual_sample_count=len(manual),reconciliations=reconciliations,
                auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limits='Shared validated raw OHLCV cache; does not establish real fills, borrow availability, intrabar price order or future tradability.')
    (out/'AUDIT_HISTORIQUE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='reconciliations'},indent=2))


if __name__=='__main__':main()
