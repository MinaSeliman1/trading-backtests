"""Independent scalar replay of exports. Does not import strategy or statistics code."""
from pathlib import Path
import sys,json,math,argparse,hashlib
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from retest.data import load_sources
from bars import reconstruct
from matrix import validate_matrix
D=lambda x:Decimal(str(x))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-28-v1');out=p.parse_args().out.resolve()
    matrix=pd.read_csv(out/'comparison_all.csv');checks=validate_matrix(matrix,out);markets,cash,_=load_sources();rows=days=0;failures=[]
    def check(condition,message):
        nonlocal checks
        checks+=1
        if not condition and len(failures)<40:failures.append(message)
    def near(a,b,message):check(math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=2e-6),message)
    reconstructed={symbol:reconstruct(m) for symbol,m in markets.items()}
    for cfg in matrix.itertuples():
        m=markets[cfg.symbol];a=m.arrays;slip=D(cfg.slippage)
        session_bars,valid=reconstructed[cfg.symbol]
        d=pd.read_csv(out/cfg.label/'daily.csv');t=pd.read_csv(out/cfg.label/'trades.csv');u=pd.read_csv(out/cfg.label/'unresolved.csv')
        expected_dates=[str(x.date()) for x in m.dates if cfg.start<=str(x.date())<=cfg.end]
        check(d.date.tolist()==expected_dates,f'{cfg.label} complete expected calendar')
        td={r.date:r for r in t.itertuples()};ud={r.date:r for r in u.itertuples()};capital=100000.;peak=capital;maxdd=0.;dollar_dd=0.
        lookup={str(x.date()):i for i,x in enumerate(m.dates)}
        for day in d.itertuples():
            days+=1;i=lookup[day.date];n=int(m.lengths[i]);barok=valid[i];side=0;slot=None;why='no_breakout';low=high=price=stop=None;snapshot=None
            bs=session_bars[i];opening=bs[:3];armed=False;rangehigh=rangelow=None
            if not all(b['valid'] for b in opening):why='unknown_range'
            else:
                rangehigh=max(b['high'] for b in opening);rangelow=min(b['low'] for b in opening)
                if rangehigh<=rangelow:why='zero_range'
                else:
                    for b in bs[3:]:
                        end=b['entry_slot']
                        if end>min(cfg.cutoff,n-1):break
                        if armed and end>armed_end+5*cfg.max_wait_bars:why='retest_expired';break
                        if not b['valid']:why='unknown_signal';break
                        if not armed:
                            direction=1 if b['close']>rangehigh+1e-10 else -1 if b['close']<rangelow-1e-10 else 0
                            if not direction:continue
                            if (cfg.mode=='long_only' and direction<0) or (cfg.mode=='short_only' and direction>0):why='direction_filtered';break
                            level=rangehigh if direction>0 else rangelow;breakslot=end-1;armed_end=end;delay=0
                            if cfg.entry_mode!='breakout':armed=True;why='entry_cutoff';continue
                        else:
                            touch=b['low']<=level+1e-10 if direction>0 else b['high']>=level-1e-10
                            if not touch:
                                if end==armed_end+5*cfg.max_wait_bars:why='retest_expired';break
                                continue
                            if direction*(b['close']-level)<=1e-10 or direction*(b['close']-b['open'])<=1e-10:why='retest_failed';break
                            delay=(end-armed_end)//5
                        low=b['low'];high=b['high'];price=b['close']
                        stop=float((D(low)-D('.01') if direction>0 else D(high)+D('.01')).quantize(D('.01'),rounding=ROUND_FLOOR if direction>0 else ROUND_CEILING))
                        if stop<=0 or direction*(D(price)-D(stop))<=0:why='invalid_stop';break
                        side=direction;slot=end;why='eligible';snapshot=dict(range_high=rangehigh,range_low=rangelow,breakout_slot=breakslot,breakout_level=level,wait_bars=delay);break
            if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day'
            if capital<=0:why='insolvent'
            before=capital;net=0.;marks=[capital];q=0;resolved=False;fee=borrow=upper=0
            if why=='eligible':
                q=int(min(D(capital)/D(price),D(capital)*D('.01')/(side*(D(price)-D(stop)))).to_integral_value(rounding=ROUND_FLOOR))
                if q<=0:why='zero_quantity'
                else:
                    entry=float(a['open'][i,slot]);known_entry=math.isfinite(entry) and entry>0
                    risk=side*(D(entry)-D(stop)) if known_entry else D(0)
                    target=float((D(entry)+side*D(cfg.target_r)*max(D(0),risk)).quantize(D('.01'),rounding=ROUND_FLOOR if side>0 else ROUND_CEILING)) if known_entry else None
                    closes=[];unknown=None;resolution='bar_open';amb=False
                    for j in range(slot,n):
                        op=float(a['open'][i,j])
                        if not math.isfinite(op) or op<=0:unknown=('missing_entry_open' if j==slot else 'missing_active_open',j);break
                        if side*(D(op)-D(stop))<=0:exitref=op;reason='entry_marketable_stop' if j==slot else 'stop_gap';break
                        if side*(D(op)-D(target))>=0:exitref=target;reason='target_gap';break
                        if j==n-1:exitref=op;reason='eod_open';break
                        if not barok[j]:unknown=('invalid_active_bar',j);break
                        sh=a['low'][i,j]<=stop if side>0 else a['high'][i,j]>=stop
                        th=a['high'][i,j]>=target if side>0 else a['low'][i,j]<=target
                        if sh or th:exitref=stop if sh else target;reason='stop_intrabar' if sh else 'target_intrabar';resolution='intrabar_minute_unknown';amb=bool(sh and th);break
                        closes.append(a['close'][i,j])
                    if unknown:
                        why='unresolved_execution';check(day.date in ud,f'{cfg.label} missing unresolved {day.date}')
                        if day.date in ud:
                            x=ud[day.date];check(x.reason==unknown[0] and x.first_unknown_slot==unknown[1],f'{cfg.label} unresolved reason')
                            near(x.quantity,q,'unresolved qty');near(x.known_entry_commission,max(.35,q*.0035) if math.isfinite(entry) and entry>0 else 0,'unresolved fee')
                            near(x.known_entry_friction,q*float(slip) if known_entry else 0.,'unresolved friction')
                            if known_entry:near(x.entry_reference,entry,'unresolved entry')
                            else:check(pd.isna(x.entry_reference),'missing entry remains missing')
                            check(bool(x.omitted_entire_trade),'unresolved trade omitted flag')
                    else:
                        resolved=True
                        rows+=1;check(day.date in td,f'{cfg.label} missing fill {day.date}')
                        if day.date not in td:continue
                        x=td[day.date];executed=entry+side*float(slip);fee=2*max(.35,q*.0035);borrow=q*executed*.01/360 if side<0 else 0.;friction=2*q*float(slip);move=q*side*(exitref-entry);net=move-friction-fee-borrow
                        for actual,expected,name in [(x.quantity,q,'qty'),(x.entry_slot,slot,'entry slot'),(x.signal_slot,slot-1,'signal slot'),(x.exit_slot,j,'exit slot'),(x.stop_price,stop,'stop'),(x.target_price,target,'target'),
                            (x.entry_reference,entry,'entry'),(x.exit_reference,exitref,'exit'),(x.entry_price,executed,'executed entry'),(x.exit_price,exitref-side*float(slip),'executed exit'),
                            (x.price_move_pnl,move,'price move'),(x.gross_pnl,move-friction,'gross'),(x.sizing_price,price,'sizing price'),(x.signal_low,low,'signal low'),(x.signal_high,high,'signal high'),
                            (x.commission,fee,'fee'),(x.borrow_fee,borrow,'borrow'),(x.friction_cost,friction,'friction'),(x.net_pnl,net,'net'),(x.equity_before,capital,'before'),(x.equity_after,capital+net,'after')]:near(actual,expected,f'{cfg.label} {day.date} {name}')
                        for field in ['range_high','range_low','breakout_slot','breakout_level','wait_bars']:near(getattr(x,field),snapshot[field],'signal '+field)
                        check(x.half_session==(n==210),'half session flag')
                        opening=pd.Timestamp(m.quality.iloc[i].session_open)
                        check(pd.Timestamp(x.entry_time)==opening+pd.Timedelta(minutes=slot) and pd.Timestamp(x.exit_time)==opening+pd.Timedelta(minutes=j),'fill times')
                        check(x.exit_reason==reason and x.exit_resolution==resolution and x.ambiguous_bar==amb,f'{cfg.label} {day.date} exit type')
                        upper=j-slot+int(resolution=='intrabar_minute_unknown')
                        near(x.holding_minutes_upper,upper,'holding minutes');near(x.net_bps,net/(q*executed)*10000,'net bps');near(x.entry_leverage,q*entry/before,'entry leverage')
                        near(x.entry_risk_pct,q*max(0.,float(risk))/before*100,'risk pct')
                        adverse=np.r_[entry,a['low' if side>0 else 'high'][i,slot:j],exitref];favorable=np.r_[entry,a['high' if side>0 else 'low'][i,slot:j],exitref]
                        near(x.mae_observed_usd,min(0.,min(q*side*(adverse-executed))),'MAE');near(x.mfe_observed_usd,max(0.,max(q*side*(favorable-executed))),'MFE')
                        marks=[capital,capital-fee/2-q*float(slip),*[capital-fee/2+q*side*(c-executed) for c in closes],capital+net]
                        capital+=net
            check(why==day.eligibility,f'{cfg.label} {day.date} reason {why} != {day.eligibility}')
            expected_excluded=why.startswith('unknown_') or why in ('excluded_incomplete_day','unresolved_execution')
            check(bool(day.conditionally_excluded)==expected_excluded,f'{cfg.label} {day.date} excluded')
            near(day.net_pnl,net,'day net');near(day.equity,capital,'day capital')
            near(day.signal_sign,side,'daily signal side');near(day.session_minutes,n,'session minutes');near(day.quantity,q if resolved else 0,'daily qty');near(day.trades,int(resolved),'daily trade count')
            near(day.return_net,net/before if before>0 else 0.,'daily return');near(day.commission,fee,'daily fees');near(day.borrow_fee,borrow,'daily borrow');near(day.holding_minutes_upper,upper,'daily holding')
            if expected_excluded:check(pd.isna(day.observed_return),'unknown return must be missing')
            else:near(day.observed_return,day.return_net,'observed return')
            if why!='eligible':check(day.date not in td,f'{cfg.label} unexpected trade {day.date}')
            for value in marks:
                peak=max(peak,value);maxdd=max(maxdd,(peak-value)/peak*100);dollar_dd=max(dollar_dd,peak-value)
            near(day.observed_close_drawdown_pct_so_far,maxdd,'daily cumulative drawdown')
        near(cfg.final_equity,capital,'summary final');near(cfg.net_pnl,t.net_pnl.sum(),'summary net');near(cfg.observed_close_drawdown_pct,maxdd,'summary dd');near(cfg.observed_close_drawdown_usd,dollar_dd,'summary dd usd')
        near(cfg.trades,len(t),'summary trades');g=t.loc[t.net_pnl>0,'net_pnl'].sum();loss=-t.loc[t.net_pnl<0,'net_pnl'].sum()
        near(cfg.total_return_pct,(capital/100000-1)*100,'summary return')
        years=((pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1)/365.2425
        near(cfg.cagr_pct,((capital/100000)**(1/years)-1)*100,'summary CAGR')
        if len(t):near(cfg.win_rate_pct,(t.net_pnl>0).mean()*100,'summary win rate')
        else:check(pd.isna(cfg.win_rate_pct),'empty trade set win rate is missing')
        for field in ['commission','borrow_fee','friction_cost','price_move_pnl']:near(getattr(cfg,field),t[field].sum(),'summary '+field)
        near(cfg.data_excluded_sessions,d.conditionally_excluded.sum(),'summary exclusions');near(cfg.unresolved_sessions,len(u),'summary unresolved')
        top=d.loc[d.net_pnl>0].nlargest(3,'net_pnl').index;r=d.return_net.copy();r.loc[top]=0
        near(cfg.return_without_top3_days_pct,(np.prod(1+r)-1)*100,'summary no top3')
        if loss:near(cfg.profit_factor,g/loss,'PF')
        check(len(td)==len(t),'one trade/date');check(len(ud)==len(u),'one unknown/date')
    result=dict(utc=datetime.now(timezone.utc).isoformat(),status='passed' if not failures else 'failed',scenario_count=len(matrix),trade_rows=rows,daily_rows=days,checks=checks,failures=failures,
        scope='Separate minute-loop bar aggregation and scalar opening-range/breakout/first-touch state, entry/exit/sizing/fees/account/mark-drawdown replay from verified prepared arrays; no strategy calls. Shared raw loader and same source, not independent market feed. Rows/scenarios overlap.')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=[out/'PRE_EXECUTION_PROTOCOL.json',out/'comparison_all.csv',*[out/r.label/name for r in matrix.itertuples() for name in ['daily.csv','trades.csv','unresolved.csv','summary.json']]]
    result.update(run_id=out.relative_to(ROOT).as_posix(),export_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    (ROOT/'audit/AUDIT_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='export_sha256'}))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
