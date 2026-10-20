"""Rejeu independant depuis les OHLCV source : Decimal, aucune fonction moteur appelee."""
from pathlib import Path
import sys,importlib.util,json
from decimal import Decimal,ROUND_FLOOR
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('orb_audit_sources',ROOT.parent/'closing-momentum/scripts/run_study.py')
src=importlib.util.module_from_spec(spec);spec.loader.exec_module(src)
D=lambda v:Decimal(str(v))
TOL=3e-6


def replay(m,i,side,q,slip,priority):
    a=m.arrays;n=int(m.lengths[i]);entry=D(a['open'][i,5]);stop=D(a['low'][i,:5].min() if side==1 else a['high'][i,:5].max())
    if not entry.is_finite() or entry<=0:return None,'missing_entry_open',5
    risk=side*(entry-stop);target=entry+side*10*risk;s=D(slip);fee=max(D('.35'),q*D('.0035'));fill=entry+side*s
    borrow=q*fill*D('.01')/360 if side<0 else D(0)
    marks=[D(0),-fee-q*s];amb=False;resolution='bar_open'
    adverse=[entry];favorable=[entry]
    if risk<=0:j=5;exit_ref=entry;reason='entry_marketable_stop'
    else:
        for j in range(5,n):
            o=D(a['open'][i,j])
            if not o.is_finite() or o<=0:return None,'missing_active_open',j
            if side*(o-stop)<=0:exit_ref=o;reason='stop_gap';break
            if side*(o-target)>=0:exit_ref=target;reason='target_gap';break
            if j==n-1:exit_ref=o;reason='eod_open';break
            h,l,c,v=[D(a[k][i,j]) for k in ('high','low','close','volume')]
            if not all(x.is_finite() for x in (h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,l,c) or l>min(o,h,c):return None,'invalid_active_bar',j
            hit_stop=l<=stop if side>0 else h>=stop;hit_target=h>=target if side>0 else l<=target
            if hit_stop or hit_target:
                amb=bool(hit_stop and hit_target);choose_stop=hit_stop and (not hit_target or priority=='stop_first')
                exit_ref=stop if choose_stop else target;reason='stop_intrabar' if choose_stop else 'target_intrabar';resolution='intrabar_minute_unknown';break
            marks.append(-fee+q*side*(c-fill));adverse.append(l if side>0 else h);favorable.append(h if side>0 else l)
    gross=q*side*((exit_ref-side*s)-fill);net=gross-2*fee-borrow;marks.append(net);adverse.append(exit_ref);favorable.append(exit_ref)
    return dict(entry_reference=entry,exit_reference=exit_ref,entry_price=fill,exit_price=exit_ref-side*s,stop_price=stop,target_price=target,
        entry_risk_unit=max(D(0),risk),commission=2*fee,borrow_fee=borrow,friction_cost=2*q*s,price_move_pnl=q*side*(exit_ref-entry),gross_pnl=gross,net_pnl=net,
        net_bps=net/(q*fill)*10000,exit_slot=j,exit_reason=reason,exit_resolution=resolution,ambiguous_bar=amb,holding_minutes_upper=j-5+int(resolution=='intrabar_minute_unknown'),
        mae_observed_usd=min(D(0),min(q*side*(x-fill) for x in adverse)),mfe_observed_usd=max(D(0),max(q*side*(x-fill) for x in favorable)),marks=marks),None,None


def audit(out):
    markets,_,_=src.load_sources();comparison=pd.read_csv(out/'comparison_all.csv');rows=[];unknown=[];marks_count=0;max_error=0.;summary_checks=0
    currency_error=price_error=bps_error=capital_error=dd_pct_error=dd_usd_error=0.
    monetary={'commission','borrow_fee','friction_cost','price_move_pnl','gross_pnl','net_pnl','mae_observed_usd','mfe_observed_usd'}
    for s in comparison.itertuples():
        m=markets[s.symbol];folder=out/s.label;daily=pd.read_csv(folder/'daily.csv');t=pd.read_csv(folder/'trades.csv');u=pd.read_csv(folder/'unresolved.csv')
        expected=[str(d.date()) for d in m.dates if src.PERIODS[s.period][0]<=str(d.date())<=src.PERIODS[s.period][1]]
        assert daily.date.tolist()==expected
        tmap={r.date:r for r in t.itertuples()};umap={r.date:r for r in u.itertuples()};idx={str(d.date()):i for i,d in enumerate(m.dates)}
        cap=D(100000);peak=cap;dd=D(0);dd_usd=D(0);count=0;all_upper=0
        for d in daily.itertuples():
            i=idx[d.date];a=m.arrays;before=cap;sign=0;q=0;excluded=False;why='eligible';path=None
            p=np.column_stack([a[k][i,:5] for k in ('open','high','low','close')]);v=a['volume'][i,:5]
            good=np.isfinite(p).all() and np.isfinite(v).all() and p.min()>0 and v.min()>=0 and np.all(p[:,1]>=p.max(axis=1)) and np.all(p[:,2]<=p.min(axis=1)) and v.sum()>0
            if not good:why='invalid_opening_window';excluded=True
            else:
                x,y=D(a['close'][i,4]),D(a['open'][i,0]);sign=int(x>y)-int(x<y)
                if s.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
            original=sign
            if s.mode=='long_only':sign=max(sign,0)
            elif s.mode=='short_only':sign=min(sign,0)
            elif s.mode=='inverse':sign=-sign
            if cap<=0:why='insolvent'
            if why=='eligible' and sign:
                price=D(a['close'][i,4]);stop=D(a['low'][i,:5].min() if sign>0 else a['high'][i,:5].max());risk=sign*(price-stop)
                if risk<=0:why='zero_known_risk'
                else:
                    q=int(min(cap/price,cap*D('.01')/risk).to_integral_value(rounding=ROUND_FLOOR))
                    if not q:why='zero_quantity'
                    else:
                        path,error,minute=replay(m,i,sign,q,s.slippage,s.priority)
                        if error:
                            why='unresolved_execution';excluded=True;ur=umap[d.date]
                            assert ur.quantity==q and ur.reason==error and ur.first_unknown_slot==minute and ur.omitted_entire_trade
                            unknown.append(dict(label=s.label,date=d.date,reason=error,slot=minute,quantity=q));q=0
            assert d.eligibility==why and bool(d.conditionally_excluded)==excluded
            assert (pd.isna(d.observed_return) if excluded else abs(d.observed_return-d.return_net)<1e-12)
            assert d.signal_sign==original and d.session_minutes==m.lengths[i]
            if path:
                r=tmap[d.date];assert r.sign==sign and r.quantity==q and r.exit_reason==path['exit_reason'] and r.exit_resolution==path['exit_resolution']
                error=0.
                for key,value in path.items():
                    if isinstance(value,Decimal):
                        delta=abs(float(value)-float(getattr(r,key)));assert delta<TOL,(s.label,d.date,key,delta);error=max(error,delta)
                        if key in monetary:currency_error=max(currency_error,delta)
                        elif key=='net_bps':bps_error=max(bps_error,delta)
                        else:price_error=max(price_error,delta)
                for key in ('exit_slot','holding_minutes_upper','ambiguous_bar'):assert getattr(r,key)==path[key]
                assert abs(r.entry_leverage-float(q*path['entry_reference']/before))<1e-10
                assert abs(r.entry_risk_pct-float(q*path['entry_risk_unit']/before*100))<1e-10
                assert bool(r.half_session)==(m.lengths[i]==210)
                opening=pd.Timestamp(m.quality.iloc[i].session_open)
                assert pd.Timestamp(r.entry_time)==opening+pd.Timedelta(minutes=5) and pd.Timestamp(r.exit_time)==opening+pd.Timedelta(minutes=path['exit_slot'])
                capital_error=max(capital_error,abs(r.equity_before-float(cap)));assert abs(r.equity_before-float(cap))<TOL
                for offset in path['marks']:
                    value=cap+offset;peak=max(peak,value);dd=max(dd,(peak-value)/peak);dd_usd=max(dd_usd,peak-value);marks_count+=1
                cap+=path['net_pnl'];capital_error=max(capital_error,abs(r.equity_after-float(cap)));assert abs(r.equity_after-float(cap))<TOL
                assert abs(d.net_pnl-float(path['net_pnl']))<TOL and abs(d.commission-float(path['commission']))<TOL and abs(d.borrow_fee-float(path['borrow_fee']))<TOL
                all_upper+=path['holding_minutes_upper'];count+=1
                rows.append(dict(label=s.label,date=d.date,quantity=q,max_numeric_field_error_mixed_units=error,exit_reason=path['exit_reason'],source_marks=len(path['marks'])))
                max_error=max(max_error,error)
            else:assert d.date not in tmap and d.net_pnl==0 and d.commission==0 and d.borrow_fee==0
            capital_error=max(capital_error,abs(d.equity-float(cap)));assert abs(d.equity-float(cap))<TOL and d.trades==int(path is not None) and d.quantity==q
            assert abs(d.return_net-float((cap-before)/before))<1e-10
            dd_pct_error=max(dd_pct_error,abs(d.observed_close_drawdown_pct_so_far-float(dd*100)));assert abs(d.observed_close_drawdown_pct_so_far-float(dd*100))<1e-8
        assert count==s.trades==len(t) and len(umap)==len(u) and len(u)==s.unresolved_sessions
        assert int(daily.conditionally_excluded.sum())==s.data_excluded_sessions
        for actual,expected_value in [(s.final_equity,float(cap)),(s.net_pnl,float(cap-100000)),(s.total_return_pct,float((cap/100000-1)*100)),(s.observed_close_drawdown_pct,float(dd*100)),(s.observed_close_drawdown_usd,float(dd_usd)),(s.regular_time_exposure_upper_pct,all_upper/daily.session_minutes.sum()*100)]:
            assert abs(actual-expected_value)<TOL,(s.label,actual,expected_value);summary_checks+=1
        dd_usd_error=max(dd_usd_error,abs(s.observed_close_drawdown_usd-float(dd_usd)));dd_pct_error=max(dd_pct_error,abs(s.observed_close_drawdown_pct-float(dd*100)))
        print('AUDITED',s.label,flush=True)
    pd.DataFrame(rows).to_csv(out/'INDEPENDENT_TRADE_AUDIT.csv',index=False)
    pd.DataFrame(unknown,columns=['label','date','reason','slot','quantity']).to_csv(out/'INDEPENDENT_UNKNOWN_AUDIT.csv',index=False)
    proof=dict(utc=datetime.now(timezone.utc).isoformat(),status='passed',audit_revision=2,executions=len(comparison),trade_rows=len(rows),independent_source_marks=marks_count,unresolved_rows=len(unknown),summary_numeric_checks=summary_checks,
        max_numeric_field_error_mixed_units=max_error,max_currency_trade_field_error_usd=currency_error,max_price_error_usd_per_share=price_error,max_net_bps_error=bps_error,
        max_capital_error_usd=capital_error,max_drawdown_pct_error=dd_pct_error,max_drawdown_usd_error=dd_usd_error,capital_and_summary_absolute_tolerance=TOL,
        revision_note='Audit instrumentation only: separate measurement units and capital/DD errors. Financial simulation and initial manifest unchanged; original proof preserved in INDEPENDENT_AUDIT_V1.json.',
        method='Independent first-five signals, Decimal sizing/levels/costs/PnL, source minute replay, capital and close-mark drawdowns, complete date membership incl conditional exclusions; no engine functions called.',
        caveat='Source remains Alpaca SIP; no cross-provider validation. Overlapping scenarios/periods are not independent trades. Partial observed drawdown is not tick drawdown.')
    src.write_json(out/'INDEPENDENT_AUDIT.json',proof);print(proof,flush=True)


if __name__=='__main__':audit(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
