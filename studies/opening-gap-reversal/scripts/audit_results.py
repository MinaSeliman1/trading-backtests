"""Rapprochement indépendant en Decimal, sans importer les helpers du moteur."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'intraday-momentum-noise-area'))
from decimal import Decimal,ROUND_FLOOR
from datetime import datetime,timezone
import argparse,hashlib,json,pickle
import numpy as np
import pandas as pd

D=lambda x:Decimal(str(x))


def independently_eligible(m,cash,complete,start,end):
    selected={};a=m.arrays
    for i,day in enumerate(m.dates):
        date=str(day.date())
        if i==0 or not start<=date<=end:continue
        vals=[a['open'][i,0],a['open'][i,1],a['open'][i,30],a['close'][i-1,m.lengths[i-1]-1]]
        if any(not np.isfinite(x) or x<=0 for x in vals):continue
        previous=D(vals[-1])-D(cash.get(date,0))
        if previous<=0:continue
        if any(a['volume'][i,j]<=0 for j in (0,1,30)):continue
        if complete and not (m.valid[i] and m.valid[i-1]):continue
        if any(set(str(m.quality.iloc[j].reason or '').split('|'))-{'','nan','missing_minutes'} for j in (i-1,i)):continue
        malformed=False
        for j in range(31):
            bar=[a[k][i,j] for k in ('open','high','low','close','volume')]
            if all(np.isnan(x) for x in bar):continue
            if not all(np.isfinite(x) for x in bar) or min(bar[:4])<=0 or bar[4]<0 or bar[1]<max(bar[:4]) or bar[2]>min(bar[:4]):malformed=True;break
        if malformed:continue
        opening=D(vals[0]);sgn=1 if opening>previous*D('1.02') else -1 if opening<previous*D('.98') else 0
        if sgn:selected[date]=(i,sgn,previous)
    return selected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');args=parser.parse_args();out=args.out
    src=ROOT.parent/'intraday-momentum-noise-area/data/prepared';markets={};cash={}
    for symbol in ('SPY','QQQ'):
        with (src/f'{symbol}_market.pkl').open('rb') as f:markets[symbol]=pickle.load(f)
        cash[symbol]=json.loads((src/f'{symbol}_dividends.json').read_text())
    manifest=json.loads((out/'MANIFEST.json').read_text())
    for name,sha in manifest['files'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==sha,name
    rows=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');checked=0;max_error=Decimal(0);proof=[];eligibility_cache={}
    periods={'ALL':('2016-01-04','2026-10-16'),'A':('2016-01-04','2024-04-30'),'B':('2024-05-01','2026-10-16')}
    for spec in rows.itertuples():
        folder=out/spec.label;t=pd.read_csv(folder/'trades.csv',float_precision='round_trip');daily=pd.read_csv(folder/'daily.csv',float_precision='round_trip')
        stats=json.loads((folder/'summary.json').read_text());m=markets[spec.symbol];a=m.arrays
        key=(spec.symbol,spec.profile,spec.period)
        if key not in eligibility_cache:eligibility_cache[key]=independently_eligible(m,cash[spec.symbol],spec.profile=='complete_days',*periods[spec.period])
        expected=eligibility_cache[key]
        assert t.date.tolist()==list(expected),(spec.label,'event dates')
        capital=D(100000);by_day={};peak=capital;dd=D(0)
        for row in t.itertuples():
            i,gap_sign,previous=expected[row.date];sign=gap_sign*(-1 if spec.strategy=='reversal' else 1)
            q=int((capital/D(a['open'][i,0])).to_integral_value(rounding=ROUND_FLOOR));slip=D(spec.slippage)
            entry=D(a['open'][i,1])+sign*slip;exit_price=D(a['open'][i,30])-sign*slip
            fee=max(D('.35'),q*D('.0035'));borrow=q*entry*D('.01')/360 if sign<0 else D(0)
            net=q*sign*(exit_price-entry)-2*fee-borrow
            assert row.quantity==q and row.sign==sign,(spec.label,row.date,'size/sign')
            for observed,actual in ((row.entry_reference,D(a['open'][i,1])),(row.exit_reference,D(a['open'][i,30])),(row.entry_price,entry),(row.exit_price,exit_price),(row.previous_adjusted,previous),(row.commission,2*fee),(row.borrow_fee,borrow),(row.net_pnl,net)):
                error=abs(D(observed)-actual);max_error=max(max_error,error);assert error<D('.000001'),(spec.label,row.date,observed,actual)
            assert pd.Timestamp(row.entry_time)==pd.Timestamp(row.date+' 09:31',tz='America/New_York')
            assert pd.Timestamp(row.exit_time)==pd.Timestamp(row.date+' 10:00',tz='America/New_York')
            capital+=net;by_day[row.date]=net;checked+=1
            assert abs(D(row.equity_after)-capital)<D('.000001')
        running=D(100000)
        for day in daily.itertuples():
            net=by_day.get(day.date,D(0));running+=net;peak=max(peak,running);dd=max(dd,(peak-running)/peak*100)
            assert abs(D(day.net_pnl)-net)<D('.000001') and abs(D(day.equity)-running)<D('.000001')
        assert abs(capital-running)<D('.000001')
        assert abs(D(stats['net_pnl'])-(capital-100000))<D('.000001')
        assert abs(D(stats['total_return_pct'])-(capital/100000-1)*100)<D('.00000001')
        assert abs(D(stats['max_daily_close_drawdown_pct'])-dd)<D('.00000001')
        proof.append(dict(label=spec.label,trades=len(t),expected_trades=len(expected),final_equity=float(capital)))
    audit=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),scenarios=len(rows),trade_rows=checked,max_currency_error_usd=float(max_error),
        method='Independent Decimal recomputation from source arrays; event membership, size, direction, dividend reference, prices, costs, timestamps, equity, daily drawdown and summary return. No engine/statistics helper imported.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scenarios_checked=proof,
        caveat='Validates arithmetic and source membership, not historical order executability or future profitability.')
    (out/'AUDIT_INDEPENDANT.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k!='scenarios_checked'},indent=2))


if __name__=='__main__':main()
