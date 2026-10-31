"""Independent scalar Bollinger and execution replay. No strategy/statistics imports."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
from datetime import datetime,timezone
import sys,math,json,argparse
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bb.data import load_sources,source
D=lambda x:Decimal(str(x))
FIELDS=('bar_index','decision_slot','signal_slot','entry_slot','sizing_price','stop_price','target_price','middle','lower','previous_lower','previous_close')
CACHE={}
def bar_valid(a,i,j):
    o,h,l,c,v=[float(a[k][i,j]) for k in ('open','high','low','close','volume')]
    return all(math.isfinite(x) for x in (o,h,l,c,v)) and min(o,l,c)>0 and h>=max(o,c) and l<=min(o,c) and v>=0
def dataset(m,b):
    key=(id(m),b)
    if key not in CACHE:
        rows=[]
        for i,n in enumerate(m.lengths):
            closes=[];lows=[];prefix=[];bad=0
            for j in range(int(n)):
                bad+=not bar_valid(m.arrays,i,j);prefix.append(bad)
                if (j+1)%b==0:
                    closes.append(float(m.arrays['close'][i,j]));lows.append(min(float(m.arrays['low'][i,k]) for k in range(j+1-b,j+1)))
            rows.append((closes,lows,prefix))
        CACHE[key]=rows
    return CACHE[key]
def features(m,c):
    out=[]
    for i,(closes,lows,bad) in enumerate(dataset(m,int(c.bar_minutes))):
        x=dict(index=i,date=str(m.dates[i].date()),session_minutes=int(m.lengths[i]),**{k:None for k in FIELDS})
        flag=str(m.quality.iloc[i].get('reason',''))
        if m.lengths[i]!=390:out.append(dict(x,reason='half_session'));continue
        if not set(flag.split('|')).issubset({'','nan','missing_minutes','invalid_ohlcv'}):out.append(dict(x,reason='unknown_source'));continue
        b=int(c.bar_minutes);n=int(c.lookback);why='no_signal'
        first=max(n,math.ceil(c.start_minute/b)-1)
        for j in range(first,len(closes)):
            end=(j+1)*b
            if end>c.end_minute:break
            if bad[end-1]:why='unknown_scan';break
            current=closes[j-n+1:j+1];previous=closes[j-n:j]
            avg=math.fsum(current)/n;pa=math.fsum(previous)/n
            std=math.sqrt(math.fsum((v-avg)**2 for v in current)/n);ps=math.sqrt(math.fsum((v-pa)**2 for v in previous)/n)
            lower=avg-c.band*std;plower=pa-c.band*ps
            setup=closes[j-1]<plower-1e-10 and closes[j]>lower+1e-10 if c.entry_rule=='reentry' else closes[j]<lower-1e-10
            if not setup:continue
            stop=float(D(min(lows[j-1],lows[j])).quantize(D('.01'),rounding=ROUND_FLOOR)-D('.01'))
            raw=D(avg).quantize(D('.00000001')) if c.target_kind=='middle' else 2*D(closes[j])-D(stop)
            target=float(raw.quantize(D('.01'),rounding=ROUND_FLOOR))
            if not D(0)<D(stop)<D(closes[j])<D(target):continue
            x.update(bar_index=j,decision_slot=end,signal_slot=end-1,entry_slot=end+int(c.entry_delay),sizing_price=closes[j],stop_price=stop,target_price=target,
              middle=avg,lower=lower,previous_lower=plower,previous_close=closes[j-1]);why='eligible';break
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
                left=int(f['entry_slot']);entry=float(a['open'][i,left]);known=math.isfinite(entry) and entry>0;problem=None;held=[];lows=[];highs=[];amb=False;resolution='bar_open'
                if not known:problem=('missing_entry_open',left)
                else:
                    for j in range(left,int(m.lengths[i])):
                        op=float(a['open'][i,j]);stop=f['stop_price'];target=f['target_price']
                        if not math.isfinite(op) or op<=0:problem=('missing_active_open',j);break
                        if op<=stop:exitref=op;exitwhy='entry_marketable_stop' if j==left else 'stop_gap';break
                        if op>=target:exitref=op;exitwhy='entry_marketable_target' if j==left else 'target_gap';break
                        if j==int(m.lengths[i])-1:exitref=op;exitwhy='eod_open';break
                        if not bar_valid(a,i,j):problem=('invalid_active_bar',j);break
                        hitstop=float(a['low'][i,j])<=stop;hittarget=float(a['high'][i,j])>=target
                        if hitstop or hittarget:
                            exitref=stop if hitstop else target;exitwhy='stop_intrabar' if hitstop else 'target_intrabar';amb=hitstop and hittarget;resolution='intrabar_minute_unknown';break
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
                      exit_reason=exitwhy,exit_resolution=resolution,ambiguous_bar=amb,holding_minutes=minutes,entry_price=ep,exit_price=xp,
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
       limitations='Same provider/cache/calendar loader; independently implemented scalar aggregation, population bands, first setup, stop/target, ledger, fills, costs and marks. Float tolerance; no quotes/tick ordering.'))
    print('AUDIT PASS',checks,'checks',count_trades,'trade rows',count_days,'daily rows')
if __name__=='__main__':main()
