"""Recalcul Decimal depuis sources, sans import ni appel au moteur/statistiques nouveaux."""
from pathlib import Path
import sys,json
from decimal import Decimal,ROUND_FLOOR
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from vwap_reversion.data import load_sources,source
D=lambda x:Decimal(str(x))
TOL=3e-6


def coherent(m,i,n):
    a=m.arrays;p=np.array([a[k][i,:n] for k in ('open','high','low','close')]);v=a['volume'][i,:n]
    return bool(np.isfinite(p).all() and p.min()>0 and np.isfinite(v).all() and v.min()>=0 and np.all(p[1]>=p.max(axis=0)) and np.all(p[2]<=p.min(axis=0)))


def features(m):
    result=[];a=m.arrays
    for i,day in enumerate(m.dates):
        f=dict(reason='eligible',excluded=False,side=0,adr=None,pv=None,vol=None,mean=None,price=None)
        if i<20:f['reason']='warmup20'
        elif not all(m.valid[j] and coherent(m,j,int(m.lengths[j])) for j in range(i-20,i)):f['reason']='invalid_prior20'
        else:
            adr=sum((D(max(a['high'][j,:int(m.lengths[j])]))-D(min(a['low'][j,:int(m.lengths[j])])) for j in range(i-20,i)),D(0))/20;f['adr']=adr
            if adr<=0:f['reason']='zero_adr'
            elif not coherent(m,i,60) or not any(a['volume'][i,:60]>0) or any(not np.isfinite(a['vwap'][i,j]) or a['vwap'][i,j]<=0 for j in range(60) if a['volume'][i,j]>0):f.update(reason='invalid_firsthour',excluded=True)
            else:
                v=sum((D(x) for x in a['volume'][i,:60]),D(0));pv=sum((D(a['volume'][i,j])*D(a['vwap'][i,j]) for j in range(60) if a['volume'][i,j]>0),D(0));price=D(a['close'][i,59]);mean=pv/v;gap=price-mean
                f.update(side=-1 if gap>adr/4 else 1 if gap<-adr/4 else 0,pv=pv,vol=v,mean=mean,price=price)
        result.append(f)
    return result


def replay(m,i,f,policy,q,slip):
    a=m.arrays;side=f['side'];n=int(m.lengths[i]);entry=D(a['open'][i,60])
    if not entry.is_finite() or entry<=0:return None,'missing_entry_open',60
    stop=entry-side*f['adr'];pv=f['pv'];volume=f['vol'];scheduled=None;closes=[];adverse=[entry];favorable=[entry];resolution='bar_open'
    for j in range(60,n):
        o=D(a['open'][i,j])
        if not o.is_finite() or o<=0:return None,'missing_active_open',j
        if side*(o-stop)<=0:ref=o;reason='stop_gap';break
        if scheduled is not None:ref=o;reason='vwap_next_open';break
        if j==n-1:ref=o;reason='eod_open';break
        h,l,c,v=[D(a[k][i,j]) for k in ('high','low','close','volume')]
        if not all(x.is_finite() for x in (h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,l,c) or l>min(o,h,c):return None,'invalid_active_bar',j
        if (side>0 and l<=stop) or (side<0 and h>=stop):ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        closes.append(c);adverse.append(l if side>0 else h);favorable.append(h if side>0 else l)
        if policy=='vwap':
            vw=D(a['vwap'][i,j])
            if v>0:
                if not vw.is_finite() or vw<=0:return None,'missing_active_vwap',j
                pv+=v*vw;volume+=v
            if side*(c-pv/volume)>=0:scheduled=j
    s=D(slip);fill=entry+side*s;exit_fill=ref-side*s;fee=max(D('.35'),q*D('.0035'));borrow=q*fill*D('.01')/360 if side<0 else D(0)
    gross=q*side*(exit_fill-fill);net=gross-2*fee-borrow;marks=[D(0),-fee-q*s,*[-fee+q*side*(c-fill) for c in closes],net];adverse.append(ref);favorable.append(ref)
    return dict(entry_reference=entry,exit_reference=ref,entry_price=fill,exit_price=exit_fill,stop_price=stop,adr20=f['adr'],sizing_price=f['price'],vwap_at_signal=f['mean'],stretch_adr=(f['price']-f['mean'])/f['adr'],
        commission=2*fee,borrow_fee=borrow,friction_cost=2*q*s,price_move_pnl=q*side*(ref-entry),gross_pnl=gross,net_pnl=net,net_bps=net/(q*fill)*10000,
        exit_slot=j,exit_reason=reason,exit_resolution=resolution,exit_signal_slot=scheduled,holding_minutes_upper=j-60+int(resolution=='intrabar_minute_unknown'),
        mae_observed_usd=min(D(0),min(q*side*(x-fill) for x in adverse)),mfe_observed_usd=max(D(0),max(q*side*(x-fill) for x in favorable)),marks=marks),None,None


def audit(out):
    markets,_,_=load_sources();fs={s:features(m) for s,m in markets.items()};comparison=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');rows=[];unknown=[];marks_count=checks=0
    maxima={k:0. for k in ('currency_trade_usd','price_usd_per_share','trade_bps','dimensionless','capital_usd','drawdown_pct','drawdown_usd')}
    monetary={'commission','borrow_fee','friction_cost','price_move_pnl','gross_pnl','net_pnl','mae_observed_usd','mfe_observed_usd'}
    for s in comparison.itertuples():
        m=markets[s.symbol];folder=out/s.label;daily=pd.read_csv(folder/'daily.csv',float_precision='round_trip');t=pd.read_csv(folder/'trades.csv',float_precision='round_trip');u=pd.read_csv(folder/'unresolved.csv')
        expected=[str(x.date()) for x in m.dates if source.PERIODS[s.period][0]<=str(x.date())<=source.PERIODS[s.period][1]];assert daily.date.tolist()==expected
        tmap={r.date:r for r in t.itertuples()};umap={r.date:r for r in u.itertuples()};ix={str(d.date()):i for i,d in enumerate(m.dates)};cap=D(100000);peak=cap;dd=dd_usd=D(0);count=upper_sum=0
        for d in daily.itertuples():
            i=ix[d.date];f=fs[s.symbol][i];side=f['side'];why=f['reason'];excluded=f['excluded'];before=cap;p=None;q=0
            filtered=(s.mode=='long_only' and side<0) or (s.mode=='short_only' and side>0)
            if filtered:why='direction_filtered'
            elif why=='eligible' and s.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
            if cap<=0:why='insolvent'
            if why=='eligible' and side:
                q=int(min(cap/f['price'],cap*D('.01')/f['adr']).to_integral_value(rounding=ROUND_FLOOR))
                if q<=0:why='zero_quantity'
                else:
                    p,error,slot=replay(m,i,f,s.exit_policy,q,s.slippage)
                    if error:
                        why='unresolved_execution';excluded=True;ur=umap[d.date];assert ur.quantity==q and ur.reason==error and ur.first_unknown_slot==slot and ur.omitted_entire_trade
                        unknown.append(dict(label=s.label,date=d.date,reason=error,slot=slot,quantity=q));q=0
            assert d.eligibility==why and bool(d.conditionally_excluded)==excluded and d.signal_sign==side
            assert (pd.isna(d.observed_return) if excluded else abs(d.observed_return-d.return_net)<1e-12)
            assert d.session_minutes==m.lengths[i]
            if p:
                r=tmap[d.date];assert r.sign==side and r.quantity==q and r.direction==('LONG' if side>0 else 'SHORT')
                currency_delta=0.
                for k,v in p.items():
                    if isinstance(v,Decimal):
                        delta=abs(float(v)-float(getattr(r,k)));assert delta<TOL,(s.label,d.date,k,delta)
                        category='currency_trade_usd' if k in monetary else 'trade_bps' if k=='net_bps' else 'dimensionless' if k=='stretch_adr' else 'price_usd_per_share';maxima[category]=max(maxima[category],delta)
                        if k in monetary:currency_delta=max(currency_delta,delta)
                for k in ('exit_slot','exit_reason','exit_resolution','holding_minutes_upper'):assert getattr(r,k)==p[k]
                assert (pd.isna(r.exit_signal_slot) if p['exit_signal_slot'] is None else r.exit_signal_slot==p['exit_signal_slot'])
                assert abs(r.entry_risk_pct-float(q*f['adr']/before*100))<1e-10 and abs(r.entry_leverage-float(q*p['entry_reference']/before))<1e-10
                opening=pd.Timestamp(m.quality.iloc[i].session_open)
                assert pd.Timestamp(r.entry_time)==opening+pd.Timedelta(minutes=60) and pd.Timestamp(r.exit_time)==opening+pd.Timedelta(minutes=p['exit_slot'])
                assert bool(r.half_session)==(m.lengths[i]==210)
                maxima['capital_usd']=max(maxima['capital_usd'],abs(r.equity_before-float(cap)));assert abs(r.equity_before-float(cap))<TOL
                for offset in p['marks']:
                    value=cap+offset;peak=max(peak,value);dd=max(dd,(peak-value)/peak);dd_usd=max(dd_usd,peak-value);marks_count+=1
                cap+=p['net_pnl'];maxima['capital_usd']=max(maxima['capital_usd'],abs(r.equity_after-float(cap)));assert abs(r.equity_after-float(cap))<TOL
                assert abs(d.net_pnl-float(p['net_pnl']))<TOL and abs(d.commission-float(p['commission']))<TOL and abs(d.borrow_fee-float(p['borrow_fee']))<TOL
                upper_sum+=p['holding_minutes_upper'];count+=1;rows.append(dict(label=s.label,date=d.date,quantity=q,max_currency_trade_field_error_usd=currency_delta,exit_reason=p['exit_reason'],marks=len(p['marks'])))
            else:assert d.date not in tmap and d.net_pnl==0 and d.commission==0 and d.borrow_fee==0
            maxima['capital_usd']=max(maxima['capital_usd'],abs(d.equity-float(cap)));assert abs(d.equity-float(cap))<TOL and d.trades==int(p is not None) and d.quantity==q
            assert abs(d.return_net-float((cap-before)/before))<1e-10
            error=abs(d.observed_close_drawdown_pct_so_far-float(dd*100));maxima['drawdown_pct']=max(maxima['drawdown_pct'],error);assert error<1e-8
        assert count==s.trades==len(t) and len(u)==s.unresolved_sessions and int(daily.conditionally_excluded.sum())==s.data_excluded_sessions
        for actual,want in [(s.final_equity,float(cap)),(s.net_pnl,float(cap-100000)),(s.total_return_pct,float((cap/100000-1)*100)),(s.observed_close_drawdown_pct,float(dd*100)),(s.observed_close_drawdown_usd,float(dd_usd)),(s.regular_time_exposure_upper_pct,upper_sum/daily.session_minutes.sum()*100)]:assert abs(actual-want)<TOL;checks+=1
        maxima['drawdown_usd']=max(maxima['drawdown_usd'],abs(s.observed_close_drawdown_usd-float(dd_usd)))
        print('AUDITED',s.label,flush=True)
    pd.DataFrame(rows).to_csv(out/'INDEPENDENT_TRADE_AUDIT.csv',index=False);pd.DataFrame(unknown,columns=['label','date','reason','slot','quantity']).to_csv(out/'INDEPENDENT_UNKNOWN_AUDIT.csv',index=False)
    proof=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),executions=len(comparison),trade_rows=len(rows),source_marks=marks_count,unresolved_rows=len(unknown),summary_numeric_checks=checks,
        maximum_errors=maxima,absolute_currency_tolerance=TOL,method='Independent ADR20, first-hour source VWAP, strict signals, Decimal sizing/trace/costs/capital/close marks, all date membership/omissions; no engine/statistics functions called.',
        limitation='Source loader reused, single vendor; periods/variants overlap. Observed drawdown is partial, not tick risk; no provider completeness or actual-fill certification.')
    source.write_json(out/'INDEPENDENT_AUDIT.json',proof);print(proof,flush=True)


if __name__=='__main__':audit(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
