"""Net quote-currency accounting; descriptive metrics, no model selection."""
import math
import numpy as np
from reference import wilson,r_stats

def summarize(out,start,end,initial=100000.0):
    trades=out['trades']; n=len(trades)
    pnl=np.array([t['net_pnl'] for t in trades],float)
    rs=[t['net_r'] for t in trades]
    wins=int((pnl>0).sum())
    gains=float(pnl[pnl>0].sum()); losses=float(-pnl[pnl<0].sum())
    ci=wilson(wins,n)
    rsummary=r_stats(rs)
    gaps=[t for t in trades if t['exit_reason']=='COVERAGE_GAP_STOP']
    resolved=[t for t in trades if t['exit_reason']!='COVERAGE_GAP_STOP' and not t['crossed_gap']]
    equity=float(out['ending_equity'])
    years=(end-start)/86400/365.2425
    top3=sorted((float(v) for v in pnl if v>0),reverse=True)[:3]
    return {'closed_trades':n,'resolved_closed_trades':len(resolved),'minimum_100_resolved':len(resolved)>=100,
            'wins':wins,'win_rate_pct':100*wins/n if n else None,'wilson_low_pct':100*ci[0] if ci else None,'wilson_high_pct':100*ci[1] if ci else None,
            'profit_factor':gains/losses if losses>0 else None,'profit_factor_infinite':losses==0 and gains>0,
            'gross_pnl':sum(t['gross_pnl'] for t in trades),'commission':sum(t['commission'] for t in trades),'net_pnl':float(pnl.sum()),
            'ending_balance':float(out['ending_balance']),'ending_equity':equity,'return_pct':100*(equity/initial-1),
            'cagr_pct':100*((equity/initial)**(1/years)-1) if equity>0 and years>0 else None,
            'expectancy_r':rsummary['mean_r'],'sum_r':sum(rs),'max_closed_dd_r':rsummary['max_closed_dd_r'],
            'longest_loss_streak':rsummary['longest_loss_streak'],'max_marked_dd_pct':out['max_marked_dd_pct'],
            'coverage_penalty_trades':len(gaps),'coverage_penalty_net_pnl':sum(t['net_pnl'] for t in gaps),
            'resolved_only_net_pnl_diagnostic':sum(t['net_pnl'] for t in resolved),
            'ambiguous_front_run_trades':sum(t['ambiguous_front_run'] for t in trades),'dual_touch_trades':sum(t['dual_touch'] for t in trades),
            'crossed_gap_trades':sum(t['crossed_gap'] for t in trades),'open_position_end':out['open_position'] is not None,
            'long_trades':sum(t['d']==1 for t in trades),'short_trades':sum(t['d']==-1 for t in trades),
            'overnight_24h_trades':sum(t['holding_minutes']>=1440 for t in trades),
            'top3_positive_pnl':sum(top3),'net_less_top3_cash_diagnostic':float(pnl.sum())-sum(top3),
            **out['counters']}
