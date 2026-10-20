"""Rapprochements secondaires des exports, sans appel aux statistiques du moteur."""
from pathlib import Path
import json,sys,hashlib
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def validate(out):
    c=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');n=0
    close=lambda a,b:bool(np.isclose(a,b,atol=1e-8,rtol=1e-10))
    for row in c.itertuples():
        p=out/row.label;s=json.loads((p/'summary.json').read_text());d=pd.read_csv(p/'daily.csv',float_precision='round_trip');t=pd.read_csv(p/'trades.csv',float_precision='round_trip')
        for k,v in s.items():
            seen=getattr(row,k)
            if isinstance(v,(float,int)):assert close(seen,v),(row.label,k)
            elif v is None:assert pd.isna(seen)
            else:assert seen==v
        checks={k:float(t[k].sum()) for k in ('net_pnl','price_move_pnl','friction_cost','commission','borrow_fee')}
        checks.update(mean_trade_bps=t.net_bps.mean(),median_trade_bps=t.net_bps.median(),win_rate_pct=(t.net_pnl>0).mean()*100,
            profit_factor=t.loc[t.net_pnl>0,'net_pnl'].sum()/-t.loc[t.net_pnl<0,'net_pnl'].sum(),
            holding_minutes_upper_mean=t.holding_minutes_upper.mean(),regular_time_exposure_upper_pct=d.holding_minutes_upper.sum()/d.session_minutes.sum()*100,
            max_actual_entry_leverage=t.entry_leverage.max(),mean_actual_entry_leverage=t.entry_leverage.mean(),
            max_entry_risk_pct=t.entry_risk_pct.max(),entry_risk_over_one_pct_count=(t.entry_risk_pct>1+1e-10).sum(),
            ambiguous_trades=t.ambiguous_bar.sum(),intrabar_exit_count=(t.exit_resolution=='intrabar_minute_unknown').sum(),half_session_trades=t.half_session.sum(),
            entry_marketable_stop_count=(t.exit_reason=='entry_marketable_stop').sum(),stop_gap_count=(t.exit_reason=='stop_gap').sum(),target_gap_count=(t.exit_reason=='target_gap').sum(),
            days_with_position_pct=d.trades.mean()*100,worst_trade_usd=t.net_pnl.min(),worst_observed_mae_usd=t.mae_observed_usd.min(),
            top3_positive_profit_share_pct=t.loc[t.net_pnl>0,'net_pnl'].nlargest(3).sum()/t.loc[t.net_pnl>0,'net_pnl'].sum()*100)
        r=d.return_net.to_numpy().copy();best=d[d.net_pnl>0].nlargest(3,'net_pnl').index;r[best]=0;checks['return_without_top3_days_pct']=(np.prod(1+r)-1)*100
        r=d.return_net.to_numpy();checks['sharpe']=r.mean()/r.std(ddof=1)*np.sqrt(252)
        checks['volatility_annual_pct']=r.std(ddof=1)*np.sqrt(252)*100;checks['daily_mean']=r.mean()
        downside=np.sqrt(np.mean(np.minimum(r,0)**2));checks['sortino']=r.mean()/downside*np.sqrt(252)
        elapsed=(pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1
        checks['cagr_pct']=((d.equity.iloc[-1]/100000)**(365.2425/elapsed)-1)*100
        curve=np.r_[100000,d.equity];checks['max_daily_close_drawdown_pct']=np.max(1-curve/np.maximum.accumulate(curve))*100
        for k,w in checks.items():assert close(s[k],w),(row.label,k,s[k],w)
        for group in ('direction','half_session','exit_reason'):
            stored=pd.read_csv(p/f'by_{group}.csv')
            for a in stored.to_dict('records'):
                g=t[t[group]==a[group]];assert a['trades']==len(g) and close(a['net_pnl'],g.net_pnl.sum()) and close(a['mean_net_bps'],g.net_bps.mean())
        for a in pd.read_csv(p/'by_year.csv').itertuples():
            g=d[d.date.str.startswith(str(a.year))]
            assert a.trades==g.trades.sum() and a.data_excluded==g.conditionally_excluded.sum() and close(a.net_pnl,g.net_pnl.sum()) and close(a.return_pct,(np.prod(1+g.return_net)-1)*100)
        peak=100000;peak_at=0;worst=0;trough=worst_peak=0
        times=[pd.Timestamp(d.date.iloc[0])-pd.Timedelta(days=1),*pd.to_datetime(d.date)]
        for i,v in enumerate(curve):
            if v>=peak:peak=v;peak_at=i
            draw=1-v/peak
            if draw>worst:worst=draw;trough=i;worst_peak=peak_at
        recovery=next((i for i in range(trough+1,len(curve)) if curve[i]>=curve[worst_peak]),None)
        duration=0 if worst==0 else (times[recovery if recovery is not None else len(curve)-1]-times[worst_peak]).days
        assert s['worst_drawdown_duration_calendar_days']==duration
        assert s['worst_drawdown_recovered']==(worst==0 or recovery is not None)
        assert not (d.eligibility=='insolvent').any();n+=len(checks)
    proof=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),executions=len(c),numeric_aggregate_checks=n,
        scope='CSV-summary equality, costs/ratios/holding bounds/exposure, annual/direction/half-session/exit exports, ablation/CAGR/Sharpe/Sortino/volatility/drawdown duration; no insolvency.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'AGGREGATE_VALIDATION.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');print(proof)


if __name__=='__main__':validate(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
