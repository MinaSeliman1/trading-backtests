"""Independent raw-array/Decimal reconstruction; does not call engine/features/trace."""
from pathlib import Path
import sys,json,argparse
from decimal import Decimal,ROUND_FLOOR
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from nr7.data import load_sources,source
D=lambda x:Decimal(str(x))


def independent_features(m,cash):
    a=m.arrays;out=[];history=[]
    for i,day in enumerate(m.dates):
        n=int(m.lengths[i]);prices=np.stack([a[k][i,:n] for k in ('open','high','low','close')],axis=1);v=a['volume'][i,:n]
        good=np.isfinite(prices).all(1)&np.isfinite(v)&(v>=0)&(prices.min(1)>0)&(prices[:,1]>=prices.max(1))&(prices[:,2]<=prices.min(1))
        history.append((max(map(D,a['high'][i,:n])),min(map(D,a['low'][i,:n]))) if m.valid[i] and good.all() and sum(v)>0 else None)
        f=dict(history_reason='warmup7' if i<7 else 'invalid_prior7' if any(x is None for x in history[i-7:i]) else 'eligible',nr7=False,side=0,slot=None,signal_reason='no_breakout',good=good)
        if f['history_reason']=='eligible':
            ranges=[x[0]-x[1] for x in history[i-7:i]];f['nr7']=ranges[-1]<min(ranges[:-1]);div=D(cash.get(str(day.date()),0))
            f['hi'],f['lo']=history[i-1][0]-div,history[i-1][1]-div
            for j in range(n-2):
                if not good[j]:f['signal_reason']='unknown_signal';break
                c=D(a['close'][i,j])
                if c>f['hi'] or c<f['lo']:
                    f.update(side=1 if c>f['hi'] else -1,slot=j,signal_reason='eligible');break
        out.append(f)
    return out


def independent_trade(m,i,f,capital,slip):
    a=m.arrays;side=f['side'];left=f['slot']+1;stop=f['lo'] if side>0 else f['hi'];sizing=D(a['close'][i,f['slot']]);risk=side*(sizing-stop)
    q=int(min(capital/sizing,capital*D('.01')/risk).to_integral_value(rounding=ROUND_FLOOR))
    if q<=0:return dict(why='zero_quantity')
    held=[];entry=D(a['open'][i,left]);resolution='bar_open'
    if not entry.is_finite() or entry<=0:return dict(why='unresolved_execution',quantity=q,unknown=left,known_fee=0.)
    for j in range(left,int(m.lengths[i])):
        opening=D(a['open'][i,j])
        if not opening.is_finite() or opening<=0:return dict(why='unresolved_execution',quantity=q,unknown=j,known_fee=float(max(D('.35'),q*D('.0035'))))
        if side*(opening-stop)<=0:exit=opening;reason='entry_marketable_stop' if j==left else 'stop_gap';break
        if j==int(m.lengths[i])-1:exit=opening;reason='eod_open';break
        if not f['good'][j]:return dict(why='unresolved_execution',quantity=q,unknown=j,known_fee=float(max(D('.35'),q*D('.0035'))))
        if (D(a['low'][i,j])<=stop if side>0 else D(a['high'][i,j])>=stop):exit=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        held.append(D(a['close'][i,j]))
    ef=entry+side*slip;xf=exit-side*slip;fee=max(D('.35'),q*D('.0035'));borrow=q*ef*D('.01')/360 if side<0 else D(0);net=q*side*(xf-ef)-2*fee-borrow
    marks=[capital,capital-fee-q*slip,*[capital-fee+q*side*(x-ef) for x in held],capital+net]
    adv=[entry,exit,*map(D,a['low' if side>0 else 'high'][i,left:j])];fav=[entry,exit,*map(D,a['high' if side>0 else 'low'][i,left:j])]
    return dict(why='eligible',quantity=q,entry_slot=left,exit_slot=j,entry_reference=float(entry),exit_reference=float(exit),entry_price=float(ef),exit_price=float(xf),stop_price=float(stop),
        commission=float(2*fee),borrow_fee=float(borrow),friction_cost=float(2*q*slip),price_move_pnl=float(q*side*(exit-entry)),net_bps=float(net/(q*ef)*10000),entry_leverage=float(q*entry/capital),
        entry_risk_pct=float(q*max(D(0),side*(entry-stop))/capital*100),mae_observed_usd=float(min(D(0),min(q*side*(x-ef) for x in adv))),
        mfe_observed_usd=float(max(D(0),max(q*side*(x-ef) for x in fav))),net_pnl=float(net),net_decimal=net,exit_reason=reason,exit_resolution=resolution,marks=marks)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24');out=p.parse_args().out
    markets,cash,profile=load_sources();features={s:independent_features(m,cash[s]) for s,m in markets.items()};comparison=pd.read_csv(out/'comparison_all.csv');rows=marks_count=days_count=0;checks=[]
    for s,m in markets.items():
        stored=pd.read_csv(out/f'{s}_features_quality.csv')
        for i,f in enumerate(features[s]):
            assert stored.iloc[i].history_reason==f['history_reason']
            assert bool(stored.iloc[i].nr7)==bool(f['nr7'])
            assert stored.iloc[i].signal_reason==f['signal_reason']
            assert int(stored.iloc[i].signal_sign)==f['side']
            if f['slot'] is not None:assert int(stored.iloc[i].signal_slot)==f['slot']
    for number,row in enumerate(comparison.itertuples(index=False)):
        m=markets[row.symbol];fs=features[row.symbol];folder=out/row.label;daily=pd.read_csv(folder/'daily.csv');trades=pd.read_csv(folder/'trades.csv');unresolved=pd.read_csv(folder/'unresolved.csv')
        byday={t.date:t for t in trades.itertuples()};unknown={t.date:t for t in unresolved.itertuples()};capital=D(100000);peak=capital;dd=D(0);count=0;net_sum=D(0);events=[];returns=[]
        for day in daily.itertuples():
            i=m.dates.get_loc(pd.Timestamp(day.date));f=fs[i];why=f['history_reason'];excluded=False;net=D(0);path=None;values=[capital]
            if why=='eligible':
                if row.require_nr7 and not f['nr7']:why='not_nr7'
                else:
                    why=f['signal_reason'];excluded=why=='unknown_signal'
                    if why=='eligible' and ((row.mode=='long_only' and f['side']<0) or (row.mode=='short_only' and f['side']>0)):why='direction_filtered'
                    if why=='eligible' and row.quality=='complete_days' and not m.valid[i]:why='excluded_incomplete_day';excluded=True
            if capital<=0:why='insolvent'
            if why=='eligible':
                path=independent_trade(m,i,f,capital,D(row.slippage));why=path['why']
                if why=='unresolved_execution':
                    excluded=True;u=unknown[day.date];assert u.quantity==path['quantity'] and u.first_unknown_slot==path['unknown'];assert abs(u.known_entry_commission-path['known_fee'])<1e-9
                elif why=='eligible':
                    t=byday[day.date];count+=1;rows+=1
                    for key in ('quantity','entry_slot','exit_slot','entry_reference','exit_reference','entry_price','exit_price','stop_price','commission','borrow_fee','friction_cost','net_pnl','net_bps','entry_leverage','entry_risk_pct','mae_observed_usd','mfe_observed_usd'):
                        assert abs(float(getattr(t,key))-path[key])<1e-6,(row.label,day.date,key)
                    assert t.exit_reason==path['exit_reason'] and t.exit_resolution==path['exit_resolution']
                    assert abs(float(capital)-t.equity_before)<1e-5
                    net=path['net_decimal'];values=path['marks'];capital+=net;net_sum+=net
                    events.append(path)
                    assert abs(float(capital)-t.equity_after)<1e-5
            if why!='eligible':assert day.date not in byday,(row.label,day.date,'extra trade')
            assert why==day.eligibility and bool(day.conditionally_excluded)==excluded,(row.label,day.date,why,day.eligibility)
            assert pd.isna(day.observed_return)==excluded
            assert abs(float(capital)-day.equity)<1e-5 and abs(float(net)-day.net_pnl)<1e-6
            returns.append(float(net/values[0]))
            for value in values:
                peak=max(peak,value);dd=max(dd,(peak-value)/peak);marks_count+=1
            days_count+=1
        assert count==len(trades)
        assert abs(float(capital)-row.final_equity)<1e-5 and abs(float(net_sum)-row.net_pnl)<1e-5
        assert abs(float(dd*100)-row.observed_close_drawdown_pct)<1e-7
        assert abs(float((capital/D(100000)-1)*100)-row.total_return_pct)<1e-7
        # Governing metric: inclusive calendar days and Gregorian mean year.
        years=((pd.Timestamp(daily.date.iloc[-1])-pd.Timestamp(daily.date.iloc[0])).days+1)/365.2425
        assert abs(((float(capital)/100000)**(1/years)-1)*100-row.cagr_pct)<1e-8
        r=np.array(returns);vol=r.std(ddof=1)
        assert abs(r.mean()/vol*np.sqrt(252)-row.sharpe)<1e-8
        for key in ('commission','borrow_fee','friction_cost','price_move_pnl'):
            assert abs(sum(e[key] for e in events)-getattr(row,key))<1e-5
        netvalues=np.array([e['net_pnl'] for e in events]);loss=netvalues[netvalues<0]
        assert abs(netvalues[netvalues>0].sum()/-loss.sum()-row.profit_factor)<1e-8
        assert abs((netvalues>0).mean()*100-row.win_rate_pct)<1e-8
        assert abs(np.mean([e['net_bps'] for e in events])-row.mean_trade_bps)<1e-8
        checks.append(dict(label=row.label,trades=count,final_equity=float(capital),drawdown_pct=float(dd*100)))
        print(f'AUDIT {number+1}/48 {row.label}',flush=True)
    pd.DataFrame(checks).to_csv(out/'AUDIT_SCENARIOS.csv',index=False)
    source.write_json(out/'AUDIT_INDEPENDENT.json',dict(status='passed',scenarios=len(checks),feature_rows=sum(len(x) for x in features.values()),trade_rows_including_overlapping_periods=rows,
        daily_rows=days_count,observed_marks=marks_count,method='Independent raw-array validity/ranges/signals and Decimal fills/sizing/fees/capital/marks; no calls to prepare/simulate/trace.',
        checked_aggregates=['trade_count','final_equity','net_pnl','total_return','CAGR','Sharpe','observed_marks_drawdown','commissions','borrow','friction','price_move','profit_factor','win_rate','mean_trade_bps'],
        conditional_accounts=True,source_revalidated=True))


if __name__=='__main__':main()
