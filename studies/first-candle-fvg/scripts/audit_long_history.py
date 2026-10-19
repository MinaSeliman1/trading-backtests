"""Rapprochement indépendant des scénarios ETF principaux avec les OHLCV Alpaca.

Ne réutilise ni le détecteur, ni les fonctions de prix, dimensionnement ou P&L du moteur.
Les assertions vérifient les transactions réalisées, pas l'exhaustivité de tous les signaux.
"""
from pathlib import Path
from math import floor, ceil
from decimal import Decimal
import argparse
import csv
import gzip
import hashlib
import json
import sys
import pandas as pd
import numpy as np


MINUTE = pd.Timedelta(minutes=1)


def local_timestamp(value):
    # CSV offsets are fixed-offset zones; normalize before mixing them with the
    # calendar's named NY zone in a pandas slice, including winter and summer.
    return pd.Timestamp(value).tz_convert('America/New_York')


def near(actual, expected, message):
    assert abs(actual-expected) < 1e-6, (message, actual, expected)


def rounded(price, direction):
    return (ceil(price/.01-1e-8) if direction > 0 else floor(price/.01+1e-8))*.01


def fill(price, direction):
    return rounded(price+direction*.015, direction)


def commission(q, price):
    return min(max(1., .005*q), q*price*.01)+.0001*q


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path('results/alpaca_sip_long'))
    parser.add_argument('--data-dir',type=Path,default=Path('data/alpaca_sip_2023_2026'))
    parser.add_argument('--instruments',nargs='+',choices=['SPY','QQQ'],default=['SPY','QQQ'])
    args=parser.parse_args()
    checked=[]; excerpts=[]; reconciliation=[]; receipts=[]
    comparison_path=args.results/'comparison_all.csv'
    comparisons=pd.read_csv(comparison_path) if comparison_path.exists() else pd.DataFrame([
        json.loads(p.read_text()) for symbol in args.instruments
        for p in (args.results/symbol).glob('*_slip1_principal/summary.json')])
    profiles=json.loads((args.results/'PRE_EXECUTION_SPLIT.json').read_text())
    for symbol in args.instruments:
        manifest=json.loads((args.data_dir/f'{symbol}_manifest.json').read_text())
        assert manifest['status']=='complete' and manifest['parameters']['feed']=='sip'
        assert manifest['parameters']['adjustment']=='raw'
        source=Path(manifest['path'])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['sha256']
        rows_verified=0
        with source.open(newline='',encoding='utf-8') as stream:
            records=csv.DictReader(stream)
            for page in manifest['pages']:
                path=Path(page['path'])
                assert hashlib.sha256(path.read_bytes()).hexdigest()==page['sha256']
                original=json.loads(gzip.decompress(path.read_bytes()))['bars'] or []
                assert len(original)==page['rows']
                for bar in original:
                    record=next(records)
                    assert record['timestamp']==bar['t']
                    for column,key in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]:
                        assert float(record[column])==float(bar[key]), (column,record['timestamp'])
                    rows_verified+=1
            assert next(records,None) is None
        assert rows_verified==manifest['rows']
        bars=pd.read_csv(source,float_precision='round_trip')
        bars.index=pd.to_datetime(bars.pop('timestamp'),utc=True).dt.tz_convert('America/New_York')
        quality=pd.read_csv(args.results/symbol/'data_quality.csv')
        accepted=quality[quality.status=='accepted']
        profile=next(p for p in profiles if p['instrument']==symbol)
        assert len(accepted)==profile['valid_sessions']
        assert profile['IS_last']<profile['OOS_first']
        assert profile['OOS_last']<'2026-09-21'
        closes=dict(zip(accepted.date,pd.to_datetime(accepted.session_close,utc=True)))
        receipts.append(dict(instrument=symbol,pages_verified=len(manifest['pages']),
                             bars_verified_against_raw_response=rows_verified,
                             retained_sessions=len(accepted),csv_sha256=manifest['sha256']))
        for segment in ['IS','OOS']:
            for variant in ['A','B']:
                label=f'{symbol}_{segment}_{variant}_slip1_principal'
                folder=args.results/symbol/label
                trades=pd.read_csv(folder/'trades.csv')
                summary=json.loads((folder/'summary.json').read_text())
                assert not trades.date.duplicated().any()
                assert trades.date.is_monotonic_increasing
                capital=100000.
                independent_marks=[capital]
                for _,r in trades.iterrows():
                    form=local_timestamp(r.formation_time); retest=local_timestamp(r.retest_time)
                    signal=local_timestamp(r.signal_time); entry=local_timestamp(r.entry_time)
                    exit_time=local_timestamp(r.exit_time); d=1 if r.direction=='LONG' else -1
                    assert profile[f'{segment}_first']<=r.date<=profile[f'{segment}_last']
                    opening=bars.loc[r.date+' 09:30':r.date+' 09:34']
                    triple=bars.loc[form-3*MINUTE:form-MINUTE]
                    assert len(opening)==5 and len(triple)==3
                    assert triple.index[0].strftime('%H:%M')>='09:35'
                    h=opening.high.max(); l=opening.low.min(); b1,b2,b3=(triple.iloc[i] for i in range(3))
                    if d==1:
                        assert b3.low>b1.high and b2.open<=h and b2.close>h
                        lower,upper=b1.high,b3.low
                    else:
                        assert b3.high<b1.low and b2.open>=l and b2.close<l
                        lower,upper=b3.high,b1.low
                    near(r.opening_high,h,'opening high'); near(r.opening_low,l,'opening low')
                    near(r.fvg_low,lower,'FVG low'); near(r.fvg_high,upper,'FVG high')
                    assert 0<(retest-form).total_seconds()<=900
                    prior=bars.loc[form:retest-2*MINUTE]
                    assert not ((prior.low<=upper)&(prior.high>=lower)).any(), 'not first retest'
                    rb=bars.loc[retest-MINUTE]
                    assert rb.low<=upper and rb.high>=lower
                    assert 0<=(signal-retest).total_seconds()<=120
                    confirm=bars.loc[signal-MINUTE]; prev=bars.loc[signal-2*MINUTE]
                    if d==1:
                        assert confirm.close>confirm.open and prev.close<prev.open
                        assert confirm.open<=prev.close and confirm.close>=prev.open
                    else:
                        assert confirm.close<confirm.open and prev.close>prev.open
                        assert confirm.open>=prev.close and confirm.close<=prev.open
                    assert entry==signal and entry.strftime('%H:%M')<'11:00'
                    assert entry.strftime('%Y-%m-%d')==exit_time.strftime('%Y-%m-%d')==r.date
                    window=bars.loc[retest-MINUTE:signal-MINUTE]
                    if d==1:
                        expected=rounded((window.low.min() if variant=='A' else lower)-.01,-1)
                    else:
                        expected=rounded((window.high.max() if variant=='A' else upper)+.01,1)
                    near(r.stop,expected,'stop')
                    near(r.entry_reference,bars.loc[entry,'open'],'next open')
                    near(r.entry_price,fill(r.entry_reference,d),'entry execution')
                    estimate=fill(confirm.close,d)
                    near(r.estimated_entry_at_order,estimate,'quantity price known at signal close')
                    per=abs(estimate-r.stop)+.02+(estimate*.01/360 if d<0 else 0)
                    q=floor(min(capital*.005/per,capital/estimate,confirm.volume*.01))
                    while q and (q*per+commission(q,estimate)+commission(q,r.stop)>capital*.005
                                 or q*estimate+commission(q,estimate)>capital):
                        q-=1
                    assert r.quantity==q and q>0 and int(q)==q
                    near(r.target,rounded(r.entry_price+d*3*abs(r.entry_price-r.stop),d),'target')
                    assert d*(r.entry_price-r.stop)>0
                    independent_marks.append(capital-commission(q,r.entry_price))
                    expected_exit=None
                    # Decimal comparisons are independent of the engine's float tolerance.
                    stop_decimal=Decimal(str(r.stop)).quantize(Decimal('.01'))
                    target_decimal=Decimal(str(r.target)).quantize(Decimal('.01'))
                    last=closes[r.date].tz_convert('America/New_York')-MINUTE
                    after=bars.loc[entry:last]
                    for ts,bar in after.iterrows():
                        op,hi,lo=(Decimal(str(bar[k])) for k in ['open','high','low'])
                        if ts==last:
                            expected_exit=(ts,bar.open,'session_end'); break
                        if (op<=stop_decimal if d==1 else op>=stop_decimal):
                            expected_exit=(ts,bar.open,'stop_gap'); break
                        if (op>=target_decimal if d==1 else op<=target_decimal):
                            expected_exit=(ts,r.target,'target'); break
                        stop_hit=(lo<=stop_decimal if d==1 else hi>=stop_decimal)
                        target_hit=(hi>=target_decimal if d==1 else lo<=target_decimal)
                        if stop_hit:
                            expected_exit=(ts,r.stop,'stop'); break
                        if target_hit:
                            expected_exit=(ts,r.target,'target'); break
                        independent_marks.append(capital-commission(q,r.entry_price)+(bar.close-r.entry_price)*d*q)
                    assert expected_exit is not None
                    ts,reference,reason=expected_exit
                    assert exit_time==ts and reason==r.exit_reason, (label,r.date,exit_time,r.exit_reason,ts,reason)
                    near(r.exit_reference,reference,'exit reference')
                    near(r.exit_price,fill(reference,-d),'adverse exit execution')
                    borrow=q*r.entry_price*.01/360 if d<0 else 0.
                    fees=commission(q,r.entry_price)+commission(q,r.exit_price)+borrow
                    near(r.fees,fees,'fees and one-day short borrow')
                    net=(r.exit_price-r.entry_price)*d*q-fees
                    risk=abs(r.entry_price-r.stop)*q
                    near(r.net_pnl,net,'net P&L'); near(r.result_r,net/risk,'R')
                    near(r.initial_risk_usd,risk,'initial actual risk')
                    estimated_loss=(abs(estimate-r.stop)+abs(r.stop-fill(r.stop,-d)))*q
                    estimated_loss+=commission(q,estimate)+commission(q,r.stop)+(q*estimate*.01/360 if d<0 else 0)
                    near(r.estimated_loss_at_order_usd,estimated_loss,'estimated loss at order')
                    assert estimated_loss<=capital*.005+1e-6
                    assert q*r.entry_price+commission(q,r.entry_price)<=capital+1e-6
                    capital+=net
                    independent_marks.append(capital)
                    checked.append(dict(label=label,date=r.date,direction=r.direction,formation=str(form),
                                        retest=str(retest),signal=str(signal),quantity=q,entry=r.entry_price,
                                        stop=r.stop,target=r.target,exit_time=str(exit_time),exit_price=r.exit_price,
                                        exit_reason=reason,net_pnl=net,result_r=net/risk))
                    # Chronological first long/short examples, independent of their profitability.
                    if not any(x['label']==label and x['direction']==r.direction for x in excerpts):
                        for ts,bar in bars.loc[form-3*MINUTE:entry].iterrows():
                            excerpts.append(dict(label=label,direction=r.direction,trade_date=r.date,
                                                 timestamp=str(ts),open=bar.open,high=bar.high,low=bar.low,
                                                 close=bar.close,volume=bar.volume))
                net=float(trades.net_pnl.sum())
                near(summary['net_pnl'],net,'summary P&L')
                near(capital,100000+net,'final capital')
                winners=trades.net_pnl>0; losses=trades.net_pnl<0
                assert summary['trades']==len(trades)
                assert summary['winners']==int(winners.sum()) and summary['losers']==int(losses.sum())
                if len(trades):
                    near(summary['expectancy_r'],float(trades.result_r.mean()),'expectancy')
                    if losses.any():
                        near(summary['profit_factor'],float(trades.loc[winners,'net_pnl'].sum()/-trades.loc[losses,'net_pnl'].sum()),'PF')
                daily=pd.read_csv(folder/'daily.csv'); monthly=pd.read_csv(folder/'monthly.csv')
                near(float(daily.net_pnl.sum()),net,'daily sum'); near(float(monthly.net_pnl.sum()),net,'monthly sum')
                curve=np.r_[100000,pd.read_csv(folder/'equity_intraday.csv').equity.to_numpy()]
                peaks=np.maximum.accumulate(curve)
                near(summary['max_drawdown_usd'],float((peaks-curve).max()),'intraday drawdown USD')
                near(summary['max_drawdown_pct'],float(((peaks-curve)/peaks*100).max()),'intraday drawdown percent')
                independent_curve=np.array(independent_marks)
                independent_peaks=np.maximum.accumulate(independent_curve)
                near(summary['max_drawdown_usd'],float((independent_peaks-independent_curve).max()),'drawdown rebuilt from source closes')
                near(summary['max_drawdown_pct'],float(((independent_peaks-independent_curve)/independent_peaks*100).max()),'percent drawdown rebuilt from source closes')
                row=comparisons[comparisons.label==label].iloc[0]
                near(row.net_pnl,net,'comparison P&L')
                reconciliation.append(dict(label=label,trades=len(trades),net_pnl=net,final_capital=capital))
    suffix='' if set(args.instruments)=={'SPY','QQQ'} else '_'+ '_'.join(args.instruments)
    pd.DataFrame(checked).to_csv(args.results/f'audited_trades{suffix}.csv',index=False)
    pd.DataFrame(excerpts).to_csv(args.results/f'audited_ohlc_excerpts{suffix}.csv',index=False)
    result=dict(status='passed',auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                trades_checked=len(checked),source_receipts=receipts,reconciliations=reconciliation,
                scope=f'All IS/OOS principal trades for {args.instruments}, stop A/B, slippage 1; not all sensitivity/WF signal paths',
                limits='OHLC cannot establish subminute sequencing, actual fills, borrow availability, or omitted signals')
    (args.results/f'audit{suffix}_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
