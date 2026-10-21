"""Reconciliations secondaires des exports, independantes des helpers statistiques."""
from pathlib import Path
import sys,json,hashlib
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def validate(out):
    c=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');checks_count=0;eq=lambda a,b:bool(np.isclose(a,b,atol=1e-8,rtol=1e-10))
    for row in c.itertuples():
        p=out/row.label;s=json.loads((p/'summary.json').read_text(encoding='utf-8'));d=pd.read_csv(p/'daily.csv',float_precision='round_trip');t=pd.read_csv(p/'trades.csv',float_precision='round_trip')
        for k,v in s.items():
            x=getattr(row,k)
            if isinstance(v,(int,float)):assert eq(x,v),(row.label,k)
            elif v is None:assert pd.isna(x)
            else:assert x==v
        gains=t.loc[t.net_pnl>0,'net_pnl'];losses=t.loc[t.net_pnl<0,'net_pnl']
        checks={k:float(t[k].sum()) for k in ('net_pnl','price_move_pnl','friction_cost','commission','borrow_fee')}
        checks.update(trades=len(t),mean_trade_bps=t.net_bps.mean(),median_trade_bps=t.net_bps.median(),win_rate_pct=(t.net_pnl>0).mean()*100,profit_factor=gains.sum()/-losses.sum(),mean_gain_usd=gains.mean(),mean_loss_usd=losses.mean(),
            days_with_position_pct=d.trades.mean()*100,regular_time_exposure_upper_pct=d.holding_minutes_upper.sum()/d.session_minutes.sum()*100,holding_minutes_upper_mean=t.holding_minutes_upper.mean(),
            max_actual_entry_leverage=t.entry_leverage.max(),mean_actual_entry_leverage=t.entry_leverage.mean(),max_entry_risk_pct=t.entry_risk_pct.max(),entry_risk_over_one_pct_count=(t.entry_risk_pct>1+1e-10).sum(),
            half_session_trades=t.half_session.sum(),intrabar_exit_count=t.exit_resolution.eq('intrabar_minute_unknown').sum(),vwap_exit_count=t.exit_reason.eq('vwap_next_open').sum(),stop_gap_count=t.exit_reason.eq('stop_gap').sum(),
            causal_history_abstention_sessions=d.eligibility.isin(['warmup20','invalid_prior20','zero_adr']).sum(),direction_filtered_sessions=d.eligibility.eq('direction_filtered').sum(),no_signal_sessions=((d.eligibility=='eligible')&(d.signal_sign==0)).sum(),
            worst_trade_usd=t.net_pnl.min(),worst_observed_mae_usd=t.mae_observed_usd.min(),top3_positive_profit_share_pct=gains.nlargest(3).sum()/gains.sum()*100)
        r=d.return_net.to_numpy().copy();r[d[d.return_net>0].nlargest(3,'return_net').index]=0;checks['return_without_top3_days_pct']=(np.prod(1+r)-1)*100
        r=d.return_net.to_numpy().copy();r[d.date.str.startswith('2020').to_numpy()]=0;checks['return_without_2020_daily_returns_pct']=(np.prod(1+r)-1)*100
        r=d.return_net.to_numpy();checks['sharpe']=r.mean()/r.std(ddof=1)*np.sqrt(252);checks['volatility_annual_pct']=r.std(ddof=1)*np.sqrt(252)*100;checks['daily_mean']=r.mean();checks['sortino']=r.mean()/np.sqrt(np.mean(np.minimum(r,0)**2))*np.sqrt(252)
        span=(pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1;checks['cagr_pct']=((d.equity.iloc[-1]/100000)**(365.2425/span)-1)*100
        curve=np.r_[100000,d.equity];checks['max_daily_close_drawdown_pct']=np.max(1-curve/np.maximum.accumulate(curve))*100
        for k,v in checks.items():assert eq(s[k],v),(row.label,k,s[k],v)
        for group in ('direction','half_session','exit_reason'):
            for a in pd.read_csv(p/f'by_{group}.csv').to_dict('records'):
                segment=t[t[group]==a[group]];assert a['trades']==len(segment) and eq(a['net_pnl'],segment.net_pnl.sum()) and eq(a['mean_net_bps'],segment.net_bps.mean())
        for a in pd.read_csv(p/'by_year.csv').itertuples():
            segment=d[d.date.str.startswith(str(a.year))]
            assert a.trades==segment.trades.sum() and a.data_excluded==segment.conditionally_excluded.sum() and eq(a.net_pnl,segment.net_pnl.sum()) and eq(a.return_pct,(np.prod(1+segment.return_net)-1)*100)
        for a in pd.read_csv(p/'by_eligibility.csv').itertuples():
            segment=d[d.eligibility==a.eligibility];assert a.sessions==len(segment) and eq(a.net_pnl,segment.net_pnl.sum())
        times=[pd.Timestamp(d.date.iloc[0])-pd.Timedelta(days=1),*pd.to_datetime(d.date)];peak=100000;peak_at=0;worst=0;trough=worst_peak=0
        for i,v in enumerate(curve):
            if v>=peak:peak=v;peak_at=i
            draw=1-v/peak
            if draw>worst:worst=draw;trough=i;worst_peak=peak_at
        recovered=next((i for i in range(trough+1,len(curve)) if curve[i]>=curve[worst_peak]),None)
        duration=0 if worst==0 else (times[recovered if recovered is not None else len(curve)-1]-times[worst_peak]).days
        assert s['worst_drawdown_duration_calendar_days']==duration and s['worst_drawdown_recovered']==(worst==0 or recovered is not None)
        assert d.eligibility.ne('insolvent').all();checks_count+=len(checks)
    proof=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),executions=len(c),numeric_aggregate_checks=checks_count,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='CSV/summary, sums/costs/ratios/risk/exposure, annual/direction/half/exit/eligibility groups, returns-ranked top3 and2020 ablations, volatility/CAGR/Sharpe/Sortino and drawdown duration; no insolvency.')
    (out/'AGGREGATE_VALIDATION.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');print(proof)


if __name__=='__main__':validate(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
