"""Rapprochements secondaires sur les fichiers dont chaque trade est audite en Decimal."""
from pathlib import Path
import argparse,json,hashlib
from datetime import datetime,timezone
import numpy as np
import pandas as pd


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);out=p.parse_args(argv).out
    rows=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');checked=[]
    close=lambda a,b:bool(np.isclose(a,b,atol=1e-8,rtol=1e-10))
    for row in rows.itertuples():
        folder=out/row.label;summary=json.loads((folder/'summary.json').read_text());d=pd.read_csv(folder/'daily.csv',float_precision='round_trip');t=pd.read_csv(folder/'trades.csv',float_precision='round_trip')
        for name,value in summary.items():
            observed=getattr(row,name)
            if isinstance(value,(int,float)):assert close(observed,value),(row.label,name,'comparison')
            elif value is None:assert pd.isna(observed),(row.label,name,'null')
            else:assert observed==value,(row.label,name,'label')
        assert t.direction.tolist()==['LONG' if s>0 else 'SHORT' for s in t.sign]
        assert (pd.to_datetime(t.exit_time,utc=True)-pd.to_datetime(t.entry_time,utc=True)).dt.total_seconds().eq(29*60).all()
        checks={name:float(t[name].sum()) for name in ('net_pnl','price_move_pnl','friction_cost','commission','borrow_fee')}
        checks.update(mean_trade_bps=float(t.net_bps.mean()),median_trade_bps=float(t.net_bps.median()),
            win_rate_pct=float((t.net_pnl>0).mean()*100),days_with_position_pct=float(d.trades.mean()*100),regular_time_exposure_pct=float(d.trades.sum()*29/d.session_minutes.sum()*100),
            mean_actual_entry_leverage=float(t.entry_leverage.mean()),max_actual_entry_leverage=float(t.entry_leverage.max()),
            top3_positive_profit_share_pct=float(t.loc[t.net_pnl>0,'net_pnl'].nlargest(3).sum()/t.loc[t.net_pnl>0,'net_pnl'].sum()*100),
            profit_factor=float(t.loc[t.net_pnl>0,'net_pnl'].sum()/-t.loc[t.net_pnl<0,'net_pnl'].sum()),worst_trade_usd=float(t.net_pnl.min()),
            trades_with_missing_holding_minutes=int((t.missing_holding_minutes>0).sum()),half_session_trades=int(t.half_session.sum()))
        returns=d.return_net.to_numpy().copy();best=d[d.net_pnl>0].sort_values('net_pnl',ascending=False).head(3).index;returns[best]=0
        checks['return_without_top3_days_pct']=float((np.prod(1+returns)-1)*100)
        returns=d.return_net.to_numpy();checks['sharpe']=float(returns.mean()/returns.std(ddof=1)*np.sqrt(252))
        elapsed=(pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1
        checks['cagr_pct']=float(((d.equity.iloc[-1]/100000)**(365.2425/elapsed)-1)*100)
        for name,want in checks.items():assert close(summary[name],want),(row.label,name,summary[name],want)
        annual=pd.read_csv(folder/'by_year.csv')
        for a in annual.itertuples():
            segment=d[d.date.str.startswith(str(a.year))]
            assert a.trades==segment.trades.sum() and close(a.net_pnl,segment.net_pnl.sum())
            assert close(a.return_pct,(np.prod(1+segment.return_net)-1)*100)
        for group in ('direction','half_session'):
            stored=pd.read_csv(folder/f'by_{group}.csv')
            for a in stored.to_dict('records'):
                segment=t[t[group]==a[group]]
                assert a['trades']==len(segment) and close(a['net_pnl'],segment.net_pnl.sum()) and close(a['mean_net_bps'],segment.net_bps.mean())
        curve=[100000.,*d.equity.tolist()];times=[pd.Timestamp(d.date.iloc[0])-pd.Timedelta(days=1),*pd.to_datetime(d.date)]
        peak=curve[0];peak_at=0;worst=0;trough=0;worst_peak=0
        for idx,value in enumerate(curve):
            if value>=peak:peak=value;peak_at=idx
            draw=1-value/peak
            if draw>worst:worst=draw;trough=idx;worst_peak=peak_at
        finish=next((i for i in range(trough+1,len(curve)) if curve[i]>=curve[worst_peak]),len(curve)-1)
        duration=0 if worst==0 else (times[finish]-times[worst_peak]).days
        assert summary['worst_drawdown_duration_calendar_days']==duration,(row.label,'DD duration')
        assert d.eligibility.ne('insolvent').all()
        checked.append(dict(label=row.label,aggregate_fields=len(checks),annual_rows=len(annual),group_exports=2,duration_checked=True))
    value=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),executions=len(checked),checks=checked,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='CSV-to-summary consistency, aggregate costs/wins/ratios/exposure/ablation/CAGR/Sharpe, annual returns/counts, direction/half-session groups, corrected drawdown duration, no insolvency.',
        limitation='These are secondary reconciliations of audited exports, not a second raw-data acquisition. Monte-Carlo intervals have controlled tests and explicit methodological caveats, not independent statistical certification.')
    (out/'AGGREGATE_VALIDATION.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print('PASS secondary aggregates:',len(checked),'executions',flush=True)


if __name__=='__main__':main()
