"""Scalar oracle: independent past red bodies, daily ranges, threshold, scan and ledger."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from datetime import datetime,timezone
import sys,math,json,argparse
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dip.data import load_sources,source
D=lambda x:Decimal(str(x))
FIELDS=('average_drop','adr','previous_close','previous_red_count','opening_price','dip_level','stop_price','bar_index','decision_slot','signal_slot','entry_slot','sizing_price')
CACHE={}
def bar_valid(a,i,j):
    o,h,l,c,v=[float(a[k][i,j]) for k in ('open','high','low','close','volume')]
    return all(math.isfinite(x) for x in (o,h,l,c,v)) and min(o,l,c)>0 and h>=max(o,c) and l<=min(o,c) and v>=0
def dataset(m):
    if id(m) not in CACHE:
        rows=[]
        for i,n in enumerate(m.lengths):
            good=[bar_valid(m.arrays,i,j) for j in range(int(n))];bad=[];total=0
            for ok in good:total+=not ok;bad.append(total)
            flag=set(str(m.quality.iloc[i].get('reason','')).split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'})
            d=dict(open=float(m.arrays['open'][i,0]),high=max(float(m.arrays['high'][i,j]) for j in range(int(n))),low=min(float(m.arrays['low'][i,j]) for j in range(int(n))),close=float(m.arrays['close'][i,int(n)-1])) if bool(m.valid[i]) and flag and all(good) else None
            rows.append((d,bad,flag))
        CACHE[id(m)]=rows
    return CACHE[id(m)]
def features(m,c):
    rows=dataset(m);out=[]
    for i,(daily,bad,flag) in enumerate(rows):
        previous=rows[i-1][0] if i else None;n=int(c.window);a=int(c.adr_days)
        past=[rows[j][0] for j in range(max(0,i-n),i)];ranges=[rows[j][0] for j in range(max(0,i-a),i)]
        avg=math.fsum(max(v['open']-v['close'],0.) for v in past)/n if len(past)==n and all(v is not None for v in past) else None
        adr=math.fsum(v['high']-v['low'] for v in ranges)/a if len(ranges)==a and all(v is not None for v in ranges) else None
        red=0
        for j in range(i-1,max(-1,i-3),-1):
            prior=rows[j][0]
            if prior is None:red=None;break
            if prior['close']>=prior['open']:break
            red+=1
        op=float(m.arrays['open'][i,0])
        x=dict(index=i,date=str(m.dates[i].date()),session_minutes=int(m.lengths[i]),**{k:None for k in FIELDS})
        x.update(average_drop=avg,adr=adr,previous_close=previous['close'] if previous else None,previous_red_count=red)
        if m.lengths[i]!=390:why='half_session'
        elif not flag:why='unknown_source'
        elif i<max(n,a):why='warmup'
        elif avg is None or adr is None or c.red_filter and red is None:why='unknown_history'
        elif avg<=0:why='zero_average_drop'
        elif adr<=0:why='zero_adr'
        elif not math.isfinite(op) or op<=0:why='unknown_scan'
        else:
            drop=D(avg).quantize(D('.00000001'));ad=D(adr).quantize(D('.00000001'))
            level=float((D(op)-D(c.multiplier)*drop).quantize(D('.01'),rounding=ROUND_FLOOR));stop=float((D(level)-ad).quantize(D('.01'),rounding=ROUND_FLOOR))
            x.update(opening_price=op,dip_level=level,stop_price=stop);why='no_signal'
            if min(level,stop)<=0:why='invalid_level'
            elif c.red_filter and red<2:why='red_filtered'
            else:
                b=int(c.bar_minutes)
                for end in range(b,391,b):
                    if end<c.start_minute:continue
                    if end>c.end_minute:break
                    if bad[end-1]:why='unknown_scan';break
                    price=float(m.arrays['close'][i,end-1])
                    if price<level-1e-10:
                        x.update(bar_index=end//b-1,decision_slot=end,signal_slot=end-1,entry_slot=end+1,sizing_price=price);why='eligible' if price>stop else 'invalid_geometry';break
        out.append(dict(x,reason=why))
    return out

def replay(m,fs,c,start,end):
    capital=float(c.initial_capital);peak=capital;dd=usd=0.;days=[];trades=[];unknown=[]
    for f in fs:
        date=f['date'];i=f['index']
        if not start<=date<=end:continue
        why=f['reason'];a=m.arrays;excluded=why.startswith('unknown_')
        if why=='eligible' and c.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
        if capital<=0:why='insolvent'
        before=capital;net=fee=friction=0.;qty=minutes=0;marks=[capital]
        if why=='eligible':
            q=int(min(D(capital)*D(c.leverage_cap)/D(f['sizing_price']),D(capital)*D(c.risk_budget)/(D(f['sizing_price'])-D(f['stop_price']))).to_integral_value(rounding=ROUND_FLOOR))
            if q<=0:why='zero_quantity'
            else:
                left=int(f['entry_slot']);entry=float(a['open'][i,left]);known=math.isfinite(entry) and entry>0;problem=None;held=[];lows=[];highs=[];resolution='bar_open'
                if not known:problem=('missing_entry_open',left)
                else:
                    for j in range(left,int(m.lengths[i])):
                        op=float(a['open'][i,j]);stop=f['stop_price']
                        if not math.isfinite(op) or op<=0:problem=('missing_active_open',j);break
                        if c.stop_enabled and op<=stop:exitref=op;exitwhy='entry_marketable_stop' if j==left else 'stop_gap';break
                        if j==int(m.lengths[i])-1:exitref=op;exitwhy='eod_open';break
                        if not bar_valid(a,i,j):problem=('invalid_active_bar',j);break
                        if c.stop_enabled and float(a['low'][i,j])<=stop:
                            exitref=stop;exitwhy='stop_intrabar';resolution='intrabar_minute_unknown';break
                        held.append(float(a['close'][i,j]));lows.append(float(a['low'][i,j]));highs.append(float(a['high'][i,j]))
                if problem:
                    why='unresolved_execution';excluded=True
                    unknown.append(dict(date=date,symbol=m.symbol,quantity=q,reason=problem[0],first_unknown_slot=problem[1],entry_reference=entry if known else None,
                      known_entry_commission=max(.35,q*.0035) if known else 0.,known_entry_friction=q*c.slippage if known else 0.,omitted_entire_trade=True))
                else:
                    qty=q;minutes=j-left+int(resolution=='intrabar_minute_unknown');ep=entry+c.slippage;xp=exitref-c.slippage;fee=2*max(.35,q*.0035);friction=2*q*c.slippage
                    net=q*(xp-ep)-fee;capital+=net
                    marks=[before,before-fee/2-q*c.slippage]+[before-fee/2+q*(v-ep) for v in held]+[capital]
                    lo=min([ep,xp]+lows);hi=max([ep,xp]+highs);opened=pd.Timestamp(m.quality.iloc[i].session_open)
                    trades.append(dict(date=date,symbol=m.symbol,direction='LONG',quality=c.quality,quantity=q,**{k:f[k] for k in FIELDS},
                      exit_slot=j,entry_reference=entry,exit_reference=exitref,entry_time=str(opened+pd.Timedelta(minutes=left)),exit_time=str(opened+pd.Timedelta(minutes=j)),
                      exit_reason=exitwhy,exit_resolution=resolution,ambiguous_bar=False,holding_minutes=minutes,entry_price=ep,exit_price=xp,
                      price_move_pnl=q*(exitref-entry),friction_cost=friction,commission=fee,borrow_fee=0.,gross_pnl=q*(xp-ep),
                      net_pnl=net,net_bps=net/(q*ep)*10000,equity_before=before,equity_after=capital,entry_leverage=q*entry/before,entry_fill_leverage=q*ep/before,
                      entry_risk_pct=q*max(0,entry-f['stop_price'])/before*100,modeled_stop_net_risk_pct=(q*max(0,ep-(min(f['stop_price'],entry)-c.slippage))+fee)/before*100,
                      mae_price_usd=q*(lo-ep),mfe_price_usd=q*(hi-ep)))
        for value in marks:peak=max(peak,value);dd=max(dd,1-value/peak);usd=max(usd,peak-value)
        ret=net/before if before>0 else 0.
        days.append(dict(date=date,session_minutes=int(m.lengths[i]),eligibility=why,conditionally_excluded=excluded,observed_return=None if excluded else ret,
          return_net=ret,net_pnl=net,equity=capital,trades=int(qty>0),quantity=qty,commission=fee,friction_cost=friction,holding_minutes=minutes,observed_close_drawdown_pct_so_far=dd*100))
    return days,trades,unknown,dd*100,usd

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
    matrix=pd.read_csv(out/'comparison_all.csv');assert len(matrix)==84 and matrix.label.is_unique
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'));markets,_,profile=load_sources();assert profile==frozen['source']
    expected_labels={f'{symbol}_{period}_{name}' for symbol in ('SPY','QQQ') for period in frozen['periods'] for name in frozen['specifications']}
    assert set(matrix.label)==expected_labels
    for row in matrix.to_dict('records'):
        assert row['label']==f"{row['symbol']}_{row['period']}_{row['variant']}"
        assert [row['start'],row['end']]==frozen['periods'][row['period']]
        for key,want in frozen['specifications'][row['variant']].items():assert row[key]==want,(row['label'],key)
        summary=json.loads((out/row['label']/'summary.json').read_text(encoding='utf-8'))
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
       limitations='Same provider/cache/calendar loader; independent scalar daily red-body/ADR/mean/level/firstsetup/stop/EOD/ledger/fills/costs/marks. Float tolerance, no quotes/tick ordering.'))
    print('AUDIT PASS',checks,'checks',count_trades,'trade rows',count_days,'daily rows')
if __name__=='__main__':main()
