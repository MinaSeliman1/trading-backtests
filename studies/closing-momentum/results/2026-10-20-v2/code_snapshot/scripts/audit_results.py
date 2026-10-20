"""Audit Decimal independant : aucune fonction du moteur/statistiques importee."""
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
PERIODS=dict(ALL=('2016-01-04','2026-10-16'),A=('2016-01-04','2024-04-30'),B=('2024-05-01','2026-10-16'))


def good(m,i,j):
    v=[m.arrays[k][i,j] for k in ('open','high','low','close','volume')]
    return bool(all(np.isfinite(x) for x in v) and min(v[:4])>0 and v[4]>=0 and v[1]>=max(v[:4]) and v[2]<=min(v[:4]))


def select(m,cash,start,end):
    selected={}
    for i,day in enumerate(m.dates):
        date=str(day.date());n=int(m.lengths[i]);left=n-30
        if not i or not start<=date<=end:continue
        if not good(m,i-1,int(m.lengths[i-1])-1) or not all(good(m,i,j) for j in range(30)) or not good(m,i,left-1):continue
        if sum(m.arrays['volume'][i,:30])<=0:continue
        previous=D(m.arrays['close'][i-1,int(m.lengths[i-1])-1]);dividend=D(cash.get(date,0));adjusted=previous-dividend
        if adjusted<=0 or not np.isfinite(m.arrays['open'][i,left]) or m.arrays['open'][i,left]<=0:continue
        morning=D(m.arrays['close'][i,29]);sign=1 if morning>adjusted else -1 if morning<adjusted else 0
        selected[date]=(i,left,n-1,sign,previous,dividend,adjusted,morning)
    return selected


def amounts(m,values,qty,sign,slip):
    i,left,right,*_=values;entry_ref=D(m.arrays['open'][i,left]);exit_ref=D(m.arrays['open'][i,right])
    entry=entry_ref+sign*slip;exit_price=exit_ref-sign*slip;fee=max(D('.35'),qty*D('.0035'));borrow=qty*entry*D('.01')/360 if sign<0 else D(0)
    move=qty*sign*(exit_ref-entry_ref);friction=2*qty*slip;net=move-friction-2*fee-borrow
    return entry_ref,exit_ref,entry,exit_price,fee,borrow,move,friction,net


def primary_quantities(m,selected):
    capital=D(100000);quantities={}
    for date,values in selected.items():
        i,left,_,sign,*_=values
        q=int((capital/D(m.arrays['close'][i,left-1])).to_integral_value(rounding=ROUND_FLOOR));quantities[date]=q
        if sign and q:capital+=amounts(m,values,q,sign,D('.01'))[-1]
        assert capital>0,'Primary insolvency requires separate review'
    return quantities


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20');args=parser.parse_args(argv);out=args.out
    freeze=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());manifest=json.loads((out/'MANIFEST.json').read_text())
    for name,want in manifest['files'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==want,name
    src=ROOT.parent/'intraday-momentum-noise-area/data/prepared';markets={};cash={}
    for name,want in freeze['source']['prepared_files_sha256'].items():assert hashlib.sha256((src/name).read_bytes()).hexdigest()==want,name
    for symbol in ('SPY','QQQ'):
        with (src/f'{symbol}_market.pkl').open('rb') as f:markets[symbol]=pickle.load(f)
        cash[symbol]=json.loads((src/f'{symbol}_dividends.json').read_text())
    comparison=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip')
    expected={f'{s}_{p}_{mode}_s{slip:g}' for s in ('SPY','QQQ') for p in PERIODS for mode,slip in [('momentum',x) for x in (.01,.02,.03,.05)]+[('long_only',.01),('always_long',.01),('opposite',.01)]}
    assert len(comparison)==42 and set(comparison.label)==expected
    cache={};proof=[];checked=0;max_error=D(0);minute_marks=0
    for spec in comparison.itertuples():
        m=markets[spec.symbol];a=m.arrays;key=(spec.symbol,spec.period)
        if key not in cache:
            selected=select(m,cash[spec.symbol],*PERIODS[spec.period]);cache[key]=(selected,primary_quantities(m,selected))
        selected,fixed=cache[key];folder=out/spec.label
        t=pd.read_csv(folder/'trades.csv',float_precision='round_trip');daily=pd.read_csv(folder/'daily.csv',float_precision='round_trip');stats=json.loads((folder/'summary.json').read_text())
        actual={row.date:row for row in t.itertuples()};assert len(actual)==len(t)
        expected_dates=[];capital=D(100000);daily_peak=capital;daily_dd=D(0);minute_peak=capital;minute_dd=D(0);minute_dd_usd=D(0);pnl_by_day={}
        def check(observed,want,context,tolerance=D('.000001')):
            nonlocal max_error
            error=abs(D(observed)-want);max_error=max(max_error,error);assert error<tolerance,(spec.label,context,observed,str(want))
        for d in daily.itertuples():
            before=capital;net=D(0);marks=[before];values=selected.get(d.date);target=0;q=0
            if values is not None:
                i,left,right,raw_sign,previous,dividend,adjusted,morning=values
                target=fixed[d.date] if spec.role=='reference' else int((capital/D(a['close'][i,left-1])).to_integral_value(rounding=ROUND_FLOOR))
                sign=1 if spec.mode=='always_long' else -raw_sign if spec.mode=='opposite' else max(0,raw_sign) if spec.mode=='long_only' else raw_sign
                assert capital>0,'Witness insolvency changes comparison; requires explicit separate audit'
                if sign and target:
                    q=target;row=actual[d.date];expected_dates.append(d.date)
                    entry_ref,exit_ref,entry,exit_price,fee,borrow,move,friction,net=amounts(m,values,q,sign,D(spec.slippage))
                    assert row.quantity==q and row.sign==sign
                    for k,want in dict(sizing_price=D(a['close'][i,left-1]),previous_close=previous,dividend=dividend,previous_adjusted=adjusted,morning_close=morning,
                        entry_reference=entry_ref,exit_reference=exit_ref,entry_price=entry,exit_price=exit_price,price_move_pnl=move,friction_cost=friction,
                        gross_pnl=move-friction,commission=2*fee,borrow_fee=borrow,net_pnl=net,net_bps=net/(q*entry)*10000,equity_before=before).items():check(getattr(row,k),want,d.date+' '+k)
                    until=pd.Timestamp(m.quality.iloc[i].session_close)
                    assert pd.Timestamp(row.entry_time)==until-pd.Timedelta(minutes=30) and pd.Timestamp(row.exit_time)==until-pd.Timedelta(minutes=1)
                    marks.append(before-fee+q*sign*(entry_ref-entry));valid=[j for j in range(left,right) if good(m,i,j)]
                    marks.extend(before-fee+q*sign*(D(a['close'][i,j])-entry) for j in valid)
                    assert row.missing_holding_minutes==(29-len(valid))
                    capital+=net;marks.append(capital);check(row.equity_after,capital,d.date+' equity_after');checked+=1
            assert d.target_quantity==target and d.quantity==q and d.trades==int(q>0)
            pnl_by_day[d.date]=net;check(d.net_pnl,net,d.date+' daily_pnl');check(d.equity,capital,d.date+' daily_equity')
            check(d.return_net,net/before,d.date+' daily_return',D('.000000001'))
            daily_peak=max(daily_peak,capital);daily_dd=max(daily_dd,(daily_peak-capital)/daily_peak*100)
            for value in marks:
                minute_peak=max(minute_peak,value);minute_dd=max(minute_dd,(minute_peak-value)/minute_peak*100);minute_dd_usd=max(minute_dd_usd,minute_peak-value);minute_marks+=1
        assert t.date.tolist()==expected_dates,(spec.label,'trade membership')
        expected_days=[str(day.date()) for day in m.dates if PERIODS[spec.period][0]<=str(day.date())<=PERIODS[spec.period][1]]
        assert daily.date.tolist()==expected_days
        for k,want in dict(net_pnl=capital-100000,final_equity=capital,total_return_pct=(capital/100000-1)*100,max_daily_close_drawdown_pct=daily_dd,
            observed_close_drawdown_pct=minute_dd,observed_close_drawdown_usd=minute_dd_usd).items():check(stats[k],want,k)
        assert stats['trades']==len(t)
        years=pd.read_csv(folder/'by_year.csv')
        for year in years.itertuples():check(year.net_pnl,sum(v for day,v in pnl_by_day.items() if day.startswith(str(year.year))),str(year.year)+' pnl')
        proof.append(dict(label=spec.label,trades=len(t),final_equity=float(capital),fixed_quantities_audited=spec.role=='reference',insolvency_sessions=0))
        print('AUDITED',spec.label,flush=True)
    value=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),executions=42,trade_rows=checked,minute_marks=minute_marks,max_currency_error_usd=float(max_error),
        method='Independent Decimal selection and accounting from source arrays; exact trade membership, direction, integer sizing, dividends, costs, timestamps, cumulative equity, daily and observed-minute drawdowns, annual P&L. No engine/statistics helper imported.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scenarios=proof,
        limits='Overlapping ALL/A/B trade rows are not independent trades. Source arrays share the validated acquisition; this does not validate actual execution prices or provider completeness.')
    (out/'AUDIT_INDEPENDANT.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',checked,'trade rows;',minute_marks,'minute marks; max error',max_error,flush=True)


if __name__=='__main__':main()
