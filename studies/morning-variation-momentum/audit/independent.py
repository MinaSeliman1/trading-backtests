"""Scalar oracle: no import of strategy or statistics implementation."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
from datetime import datetime,timezone
import sys,math,json,argparse
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from variation.data import load_sources,source

def bar_valid(a,i,j):
    o,h,l,c,v=[float(a[k][i,j]) for k in ('open','high','low','close','volume')]
    return all(math.isfinite(x) for x in (o,h,l,c,v)) and min(o,l,c)>0 and h>=max(o,c) and l<=min(o,c) and v>=0
def features(m,c):
    history=[];out=[]
    for i,date in enumerate(m.dates):
        n=int(c.observation_minutes);used=history if c.history_mode=='expanding' else history[-int(c.min_history):]
        ordered=sorted(used);rank=(len(ordered)-1)*c.quantile
        threshold=(ordered[math.floor(rank)]*(1-(rank-math.floor(rank)))+ordered[math.ceil(rank)]*(rank-math.floor(rank))) if len(used)>=c.min_history else None
        x=dict(index=i,date=str(date.date()),threshold=threshold,training_count=len(used),total_previous_eligible=len(history),log_return=None,variation=None,score=None,sizing_price=None,selection_value=None)
        flag=str(m.quality.iloc[i].get('reason',''));a=m.arrays
        if m.lengths[i]!=390:why='half_session'
        elif not set(flag.split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'}) or not all(bar_valid(a,i,j) for j in range(n)):why='unknown_morning'
        else:
            last=float(a['open'][i,0]);returns=[]
            for j in range(int(c.sampling_minutes)-1,n,int(c.sampling_minutes)):
                current=float(a['close'][i,j]);returns.append(math.log(current/last));last=current
            variation=math.sqrt(math.fsum(x*x for x in returns));lr=math.log(last/float(a['open'][i,0]))
            x.update(log_return=lr,variation=variation,sizing_price=last)
            if variation<=1e-12:
                why='zero_variation';x['selection_value']=lr if c.metric=='return' else None
            else:
                x.update(score=lr/variation,selection_value=lr if c.metric=='return' else lr/variation)
                why='ready' if len(used)>=c.min_history else 'warmup';history.append(x['selection_value'])
        out.append(dict(x,reason=why))
    return out
def replay(m,fs,c,start,end):
    capital=float(c.initial_capital);peak=capital;dd=usd=0.;days=[];trades=[];unknown=[]
    for f in fs:
        date=f['date'];i=f['index']
        if not start<=date<=end:continue
        why=f['reason'];a=m.arrays
        if why=='ready':why='eligible' if c.metric=='always' or f['selection_value']>f['threshold']+1e-12 else 'no_signal'
        excluded=why.startswith('unknown_')
        if why=='eligible' and c.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        before=capital;net=fee=friction=0.;qty=minutes=0;marks=[capital]
        if why=='eligible':
            q=int((Decimal(str(capital))*Decimal(str(c.leverage_cap))/Decimal(str(f['sizing_price']))).to_integral_value(rounding=ROUND_FLOOR))
            if q<=0:why='zero_quantity'
            else:
                left=int(c.observation_minutes)+1;right=int(m.lengths[i])-1;endheld=right+(c.exit_kind=='close')
                entry=float(a['open'][i,left]);known=math.isfinite(entry) and entry>0;problem=None
                if not known:problem=('missing_entry_open',left)
                else:
                    for j in range(left,endheld):
                        if not bar_valid(a,i,j):problem=('missing_active_ohlcv',j);break
                exitref=float(a[c.exit_kind][i,right])
                if not problem and (not math.isfinite(exitref) or exitref<=0):problem=('missing_exit_reference',right)
                if problem:
                    why='unresolved_execution';excluded=True
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,reason=problem[0],first_unknown_slot=problem[1],entry_reference=entry if known else None,
                      known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*c.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=endheld-left;ep=entry+c.slippage;xp=exitref-c.slippage;fee=2*max(.35,q*.0035);friction=2*q*c.slippage
                    net=q*(xp-ep)-fee;capital+=net
                    marks=[before,before-fee/2-q*c.slippage]+[before-fee/2+q*(float(a['close'][i,j])-ep) for j in range(left,endheld)]+[capital]
                    lo=min([ep,xp]+[float(a['low'][i,j]) for j in range(left,endheld)]);hi=max([ep,xp]+[float(a['high'][i,j]) for j in range(left,endheld)])
                    opened=pd.Timestamp(m.quality.iloc[i].session_open)
                    trades.append(dict(date=date,symbol=m.symbol,direction='LONG',quality=c.quality,quantity=q,signal_slot=int(c.observation_minutes)-1,sizing_price=f['sizing_price'],
                      **{k:f[k] for k in ('score','log_return','variation','threshold','training_count')},entry_slot=left,exit_slot=right,entry_reference=entry,exit_reference=exitref,
                      entry_time=str(opened+pd.Timedelta(minutes=left)),exit_time=str(opened+pd.Timedelta(minutes=right+(c.exit_kind=='close'))),holding_minutes=minutes,
                      entry_price=ep,exit_price=xp,price_move_pnl=q*(exitref-entry),friction_cost=friction,commission=fee,borrow_fee=0.,gross_pnl=q*(xp-ep),
                      net_pnl=net,net_bps=net/(q*ep)*10000,equity_before=before,equity_after=capital,entry_leverage=q*entry/before,entry_fill_leverage=q*ep/before,
                      mae_price_usd=q*(lo-ep),mfe_price_usd=q*(hi-ep)))
        for value in marks:peak=max(peak,value);dd=max(dd,1-value/peak);usd=max(usd,peak-value)
        ret=net/before if before>0 else 0.
        days.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=None if excluded else ret,
          return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,holding_minutes=minutes,observed_close_drawdown_pct_so_far=dd*100))
    return days,trades,unknown,dd*100,usd

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
    matrix=pd.read_csv(out/'comparison_all.csv');assert len(matrix)==84 and matrix.label.is_unique
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());markets,_,profile=load_sources();assert profile==frozen['source']
    expected_labels={f'{symbol}_{period}_{name}' for symbol in ('SPY','QQQ') for period in frozen['periods'] for name in frozen['specifications']}
    assert set(matrix.label)==expected_labels
    for row in matrix.to_dict('records'):
        assert row['label']==f"{row['symbol']}_{row['period']}_{row['variant']}"
        assert [row['start'],row['end']]==frozen['periods'][row['period']]
        for key,want in frozen['specifications'][row['variant']].items():assert row[key]==want,(row['label'],key)
        summary=json.loads((out/row['label']/'summary.json').read_text())
        for key,want in summary.items():
            if want is not None and key in row:
                if isinstance(want,(int,float)) and not isinstance(want,bool):assert math.isclose(float(row[key]),want,rel_tol=1e-12,abs_tol=1e-10)
                else:assert row[key]==want
    
    for key,want in frozen['code_sha256'].items():assert source.sha(ROOT/key)==want,key
    for key,want in frozen['dependencies_sha256'].items():assert source.sha(ROOT.parents[1]/key)==want,key
    checks=0;count_days=count_trades=count_features=0;feature_cache={}
    def compare(actual,expected,context):
        nonlocal checks
        for key,want in expected.items():
            got=actual[key];checks+=1
            if want is None:assert pd.isna(got),(context,key,got,want)
            elif isinstance(want,(int,float)) and not isinstance(want,bool):
                assert math.isclose(float(got),want,rel_tol=2e-9,abs_tol=3e-6),(context,key,got,want)
            else:assert got==want,(context,key,got,want)
    for c in matrix.itertuples():
        m=markets[c.symbol];key=(c.symbol,c.variant)
        if key not in feature_cache:feature_cache[key]=features(m,c)
        fs=feature_cache[key];folder=out/c.label
        exported=pd.read_csv(out/f'{c.symbol}_{c.variant}_features.csv')
        assert len(exported)==len(fs)
        for actual,expected in zip(exported.to_dict('records'),fs):compare(actual,expected,c.label+' features');count_features+=1
        expected=replay(m,fs,c,c.start,c.end)
        for key,want in zip(('daily','trades','unresolved'),expected[:3]):
            actual=pd.read_csv(folder/f'{key}.csv');assert len(actual)==len(want),(c.label,key)
            assert actual.date.is_unique
            for x,y in zip(actual.to_dict('records'),want):compare(x,y,c.label+' '+key)
        count_days+=len(expected[0]);count_trades+=len(expected[1])
        compare(c._asdict(),dict(net_pnl=sum(x['net_pnl'] for x in expected[1]),final_equity=expected[0][-1]['equity'],
          trades=len(expected[1]),observed_close_drawdown_pct=expected[3],observed_close_drawdown_usd=expected[4]),c.label+' aggregate')
    source.write_json(ROOT/'audit/AUDIT_RESULTS.json',dict(utc=datetime.now(timezone.utc).isoformat(),passed=True,checks=checks,executions=len(matrix),
       daily_rows=count_days,trade_rows=count_trades,feature_rows=count_features,source_hashes_verified=True,financial_hashes_verified=True,
       export_sha256={f.relative_to(ROOT).as_posix():source.sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f.suffix in ('.csv','.json')},
       limitations='Same provider/cache/calendar loader; independently implemented scalar features, quantiles, ledger, fills, costs, marks. Float tolerance; no ticks or quotes.'))
    print('AUDIT PASS',checks,'checks',count_trades,'trade rows',count_days,'daily rows')
if __name__=='__main__':main()
