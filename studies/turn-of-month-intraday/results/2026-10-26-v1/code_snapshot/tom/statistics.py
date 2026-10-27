"""Descriptive matched monthly calendar contrast; no trading decisions."""
import numpy as np
import pandas as pd

def monthly_contrast(trades,repetitions=3000,seed=20261026):
    rows=[];excluded=[]
    for month,g in trades.groupby(pd.to_datetime(trades.date).dt.to_period('M')):
        selected=(g.month_ordinal<=3)|(g.sessions_to_end==0)
        if not selected.any() or selected.all():excluded.append(str(month));continue
        a=float(g.loc[selected,'net_bps'].mean());b=float(g.loc[~selected,'net_bps'].mean())
        rows.append(dict(month=str(month),tom_trades=int(selected.sum()),other_trades=int((~selected).sum()),tom_bps=a,other_bps=b,difference_bps=a-b,
            sampled_sessions=len(g),calendar_sessions=int(g.month_sessions.iloc[0]),full_calendar_observed=len(g)==int(g.month_sessions.iloc[0])))
    values=np.asarray([x['difference_bps'] for x in rows]);rng=np.random.default_rng(seed)
    means=values[rng.integers(0,len(values),size=(repetitions,len(values)))].mean(axis=1) if len(values) else np.array([])
    return dict(qualifying_months=len(rows),months_without_both_groups=len(excluded),excluded_months=excluded,monthly_rows=rows,repetitions=repetitions,seed=seed,
        mean_difference_bps=float(values.mean()) if len(values) else None,ci95_bps=np.quantile(means,[.025,.975]).tolist() if len(means) else None,
        partial_or_incomplete_months=sum(not x['full_calendar_observed'] for x in rows),
        caveat='Descriptive conditional contrast within all_days resolved fills, equal month weights; incomplete/partial months retained and flagged. Reused dates and no multiplicity correction.')
