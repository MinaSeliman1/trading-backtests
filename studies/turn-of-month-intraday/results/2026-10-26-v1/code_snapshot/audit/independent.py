"""Independent scalar replay of exports. Does not import strategy or statistics code."""
from pathlib import Path
import sys,json,math,argparse,hashlib
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tom.data import load_sources
import exchange_calendars as xcals
D=lambda x:Decimal(str(x))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-26-v1');out=p.parse_args().out.resolve()
    markets,cash,_=load_sources();matrix=pd.read_csv(out/'comparison_all.csv');checks=rows=days=0;failures=[]
    def check(condition,message):
        nonlocal checks
        checks+=1
        if not condition and len(failures)<40:failures.append(message)
    def near(a,b,message):check(math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=2e-6),message)
    calendar=xcals.get_calendar('XNYS',start='2015-01-01',end='2027-12-31');month_cache={};valid_by_symbol={}
    for symbol,m in markets.items():
        a=m.arrays;valid=[]
        for i in range(len(m.dates)):
            p=np.stack([a[k][i,:int(m.lengths[i])] for k in ['open','high','low','close']],axis=1)
            valid.append(np.all(np.isfinite(p),axis=1)&np.all(p>0,axis=1)&(p[:,1]>=np.max(p,axis=1))&(p[:,2]<=np.min(p,axis=1)))
        valid_by_symbol[symbol]=valid
    for cfg in matrix.itertuples():
        m=markets[cfg.symbol];a=m.arrays;slip=D(cfg.slippage);valid=valid_by_symbol[cfg.symbol]
        d=pd.read_csv(out/cfg.label/'daily.csv');t=pd.read_csv(out/cfg.label/'trades.csv');u=pd.read_csv(out/cfg.label/'unresolved.csv')
        expected_dates=[str(x.date()) for x in m.dates if cfg.start<=str(x.date())<=cfg.end]
        check(d.date.tolist()==expected_dates,f'{cfg.label} complete expected calendar')
        td={r.date:r for r in t.itertuples()};ud={r.date:r for r in u.itertuples()};capital=100000.;peak=capital;maxdd=0.;dollar_dd=0.
        lookup={str(x.date()):i for i,x in enumerate(m.dates)}
        for day in d.itertuples():
            days+=1;i=lookup[day.date];n=int(m.lengths[i]);barok=valid[i];side=0;slot=5;why='eligible';price=stop=None
            timestamp=pd.Timestamp(day.date);month=str(timestamp.to_period('M'))
            if month not in month_cache:
                first=timestamp.replace(day=1);last=first+pd.offsets.MonthEnd(0)
                month_cache[month]=calendar.sessions_in_range(first,last).strftime('%Y-%m-%d').tolist()
            dates=month_cache[month];ordinal=dates.index(day.date)+1;remaining=len(dates)-ordinal;tom=ordinal<=3 or remaining==0
            include={'tom':tom,'first1':ordinal==1,'last1':remaining==0,'first3':ordinal<=3,'first5_last1':ordinal<=5 or remaining==0,'other_days':not tom,'all_days':True}[cfg.mode]
            if not include:why='calendar_filtered'
            elif not barok[4]:why='unknown_sizing_bar'
            else:
                side=1;price=float(a['close'][i,4]);stop=float((D(price)*(D(1)-D(cfg.stop_pct))).quantize(D('.01'),rounding=ROUND_FLOOR))
            if why=='eligible' and cfg.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day'
            if capital<=0:why='insolvent'
            before=capital;net=0.;marks=[capital];q=0;resolved=False;fee=borrow=upper=0
            if why=='eligible':
                q=int(min(D(capital)/D(price),D(capital)*D('.01')/(side*(D(price)-D(stop)))).to_integral_value(rounding=ROUND_FLOOR))
                if q<=0:why='zero_quantity'
                else:
                    entry=float(a['open'][i,slot]);known_entry=math.isfinite(entry) and entry>0
                    risk=side*(D(entry)-D(stop)) if known_entry else D(0)
                    target=None
                    closes=[];unknown=None;resolution='bar_open';amb=False
                    for j in range(slot,n):
                        op=float(a['open'][i,j])
                        if not math.isfinite(op) or op<=0:unknown=('missing_entry_open' if j==slot else 'missing_active_open',j);break
                        if cfg.stop_enabled and side*(D(op)-D(stop))<=0:exitref=op;reason='entry_marketable_stop' if j==slot else 'stop_gap';break
                        if j==n-1:exitref=op;reason='eod_open';break
                        if not barok[j]:unknown=('invalid_active_bar',j);break
                        sh=cfg.stop_enabled and a['low'][i,j]<=stop
                        if sh:exitref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
                        closes.append(a['close'][i,j])
                    if unknown:
                        why='unresolved_execution';check(day.date in ud,f'{cfg.label} missing unresolved {day.date}')
                        if day.date in ud:
                            x=ud[day.date];check(x.reason==unknown[0] and x.first_unknown_slot==unknown[1],f'{cfg.label} unresolved reason')
                            near(x.quantity,q,'unresolved qty');near(x.known_entry_commission,max(.35,q*.0035) if math.isfinite(entry) and entry>0 else 0,'unresolved fee')
                    else:
                        resolved=True
                        rows+=1;check(day.date in td,f'{cfg.label} missing fill {day.date}')
                        if day.date not in td:continue
                        x=td[day.date];executed=entry+side*float(slip);fee=2*max(.35,q*.0035);borrow=q*executed*.01/360 if side<0 else 0.;friction=2*q*float(slip);move=q*side*(exitref-entry);net=move-friction-fee-borrow
                        for actual,expected,name in [(x.quantity,q,'qty'),(x.entry_slot,slot,'entry slot'),(x.signal_slot,slot-1,'signal slot'),(x.exit_slot,j,'exit slot'),(x.stop_price,stop,'stop'),
                            (x.entry_reference,entry,'entry'),(x.exit_reference,exitref,'exit'),(x.entry_price,executed,'executed entry'),(x.exit_price,exitref-side*float(slip),'executed exit'),
                            (x.price_move_pnl,move,'price move'),(x.gross_pnl,move-friction,'gross'),(x.sizing_price,price,'sizing price'),(x.month_ordinal,ordinal,'month ordinal'),(x.sessions_to_end,remaining,'remaining sessions'),(x.month_sessions,len(dates),'full month sessions'),
                            (x.commission,fee,'fee'),(x.borrow_fee,borrow,'borrow'),(x.friction_cost,friction,'friction'),(x.net_pnl,net,'net'),(x.equity_before,capital,'before'),(x.equity_after,capital+net,'after')]:near(actual,expected,f'{cfg.label} {day.date} {name}')
                        check(pd.isna(x.target_price) and x.month==month and x.is_tom==tom and x.stop_enabled==cfg.stop_enabled,'calendar/noTP/stop fields')
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
        scope='Separate per-month XNYS calendar and scalar signal/entry/exit/sizing/fees/account/mark-drawdown replay from verified prepared arrays; no strategy calls. Shared raw loader and same source, not independent market feed. Rows/scenarios overlap.')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=[out/'PRE_EXECUTION_PROTOCOL.json',out/'comparison_all.csv',out/'XNYS_CALENDAR.csv',*[out/r.label/name for r in matrix.itertuples() for name in ['daily.csv','trades.csv','unresolved.csv','summary.json']]]
    result.update(run_id=out.relative_to(ROOT).as_posix(),export_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    (ROOT/'audit/AUDIT_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='export_sha256'}))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
