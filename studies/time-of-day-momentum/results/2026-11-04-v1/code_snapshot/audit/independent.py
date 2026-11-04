"""Full independent scalar feature, cashflow and risk audit of every account."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'audit'))
import pandas as pd
from seasonal.data import load_sources,source
import oracle


def equal(a,b,key):
    if a is None or (isinstance(a,float) and math.isnan(a)):
        assert b is None or pd.isna(b),(key,a,b)
    elif isinstance(a,(float,int)):
        assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-7),(key,a,b)
    else:assert a==b,(key,a,b)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);out=p.parse_args().out.resolve()
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('verify_frozen',ROOT/'scripts/verify_delivery.py');verify=module_from_spec(spec);spec.loader.exec_module(verify)
    verify.execution_folder(out)
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());verify.verify_freeze(frozen,out)
    markets,_,profile=load_sources();assert profile==frozen['source'],'market source profile changed since freeze'
    accounts=[];features_checked=0;trade_checks=0;daily_checks=0
    for symbol,m in markets.items():
        history=oracle.historical_returns(m);cache={}
        for variant,c in frozen['specifications'].items():
            key=tuple(c[k] for k in ('lookback','threshold','stop_multiple','mode','seed'))
            if key not in cache:cache[key]=[oracle.feature(m,i,c,history) for i in range(len(m.dates))]
            fs=cache[key];saved=pd.read_csv(out/f'{symbol}_{variant}_features.csv')
            for i,f in enumerate(fs):
                row=saved.iloc[i]
                for k in ('reason','historical_slot','reference_sign','sign','decision_slot','entry_slot','scheduled_exit_slot','sizing_price','stop_price','history_mean','history_sigma','history_t'):
                    equal(f.get(k),row.get(k),f'{symbol}/{variant}/{i}/{k}')
                features_checked+=1
            for period,(start,end) in frozen['periods'].items():
                label=f'{symbol}_{period}_{variant}';folder=out/label;daily=pd.read_csv(folder/'daily.csv');trades=pd.read_csv(folder/'trades.csv');summary=json.loads((folder/'summary.json').read_text());bytrade={r['date']:r for r in trades.to_dict('records')}
                expected=[f for f in fs if start<=f['date']<=end];assert len(expected)==len(daily)
                capital=float(c['initial_capital']);peak=capital;dd=dd_usd=0.;seen=0;unknown_count=0
                for f,row in zip(expected,daily.to_dict('records')):
                    i=f['index'];why=f['reason'];excluded=why.startswith('unknown_');net=0.;marks=[capital];q=0;expected_trade=None
                    if why=='eligible' and c['quality']=='complete_days' and (history.bad[i][-1] or not history.flags[i]):why='excluded_incomplete_day';excluded=True
                    if capital<=0:why='insolvent'
                    if why=='eligible':
                        t=oracle.trade(m,f,c,capital)
                        if t['reason']=='unresolved_execution':why='unresolved_execution';excluded=True;unknown_count+=1
                        elif t['reason']=='zero_quantity':why='zero_quantity'
                        else:
                            expected_trade=t;net=t['net_pnl'];q=t['quantity'];marks=t['marks'];capital+=net;seen+=1
                            stored=bytrade.pop(f['date'])
                            for k in ('quantity','entry_reference','exit_reference','entry_price','exit_price','exit_slot','exit_reason','exit_resolution','commission','borrow_fee','friction_cost','net_pnl'):
                                equal(t[k],stored[k],label+'/'+f['date']+'/'+k)
                            equal(f['stop_price'],stored['stop_price'],label+'/stop');trade_checks+=1
                    for value in marks:peak=max(peak,value);dd=max(dd,(peak-value)/peak);dd_usd=max(dd_usd,peak-value)
                    for k,want in [('date',f['date']),('eligibility',why),('conditionally_excluded',excluded),('net_pnl',net),('equity',capital),('quantity',q)]:
                        equal(want,row[k],label+'/'+f['date']+'/'+k)
                    daily_checks+=1
                assert not bytrade and seen==summary['trades']
                equal(capital,summary['final_equity'],label+'/final');equal(dd*100,summary['observed_close_drawdown_pct'],label+'/dd');equal(dd_usd,summary['observed_close_drawdown_usd'],label+'/ddUSD')
                assert unknown_count==summary['unresolved_sessions']
                accounts.append(dict(label=label,features=len(fs),daily=len(daily),trades=seen,final_equity=capital))
                print('AUDIT',label,flush=True)
    assert len(accounts)==96
    result=dict(utc=datetime.now(timezone.utc).isoformat(),accounts=len(accounts),features_checked=features_checked,daily_rows_checked=daily_checks,trades_checked=trade_checks,all_matched=True,method='Scalar independent history moments, chronological candidate, paths, quantity, fees, borrow, compounding and close-mark drawdown; no strategy-engine imports in oracle',details=accounts)
    source.write_json(out/'INDEPENDENT_AUDIT.json',result)
if __name__=='__main__':main()
