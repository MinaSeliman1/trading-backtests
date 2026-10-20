"""Comptage de faisabilité uniquement : aucun P&L, aucun backtest de stratégie."""
from pathlib import Path
import sys
import hashlib
import json
import pickle
import numpy as np
import pandas as pd
STUDY=Path(__file__).resolve().parents[2]/'intraday-momentum-noise-area'
sys.path.insert(0,str(STUDY))


def main():
    results=[]
    for symbol in ['SPY','QQQ']:
        path=STUDY/'data/prepared'/f'{symbol}_market.pkl'
        with path.open('rb') as stream:m=pickle.load(stream)
        cash_path=STUDY/'data/prepared'/f'{symbol}_dividends.json'
        cash=json.loads(cash_path.read_text())
        close=m.arrays['close'][np.arange(len(m.dates)),m.lengths-1]
        previous=pd.Series(close).shift(1).to_numpy()
        div=np.array([cash.get(str(d.date()),0.) for d in m.dates])
        gap=m.arrays['open'][:,0]/(previous-div)-1
        usable=m.valid & np.r_[False,m.valid[:-1]] & np.isfinite(gap)
        rows=[]
        for name,start,end in [('all','2016-01-01','2026-10-16'),('A','2016-01-01','2024-04-30'),('B','2024-05-01','2026-10-16')]:
            mask=usable & (m.dates>=start)&(m.dates<=end);events=mask&(np.abs(gap)>.02)
            rows.append(dict(period=name,usable_sessions=int(mask.sum()),gap_gt_2pct=int(events.sum()),
                             dates=[str(d.date()) for d in m.dates[events]]))
        results.append(dict(symbol=symbol,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),dividends_sha256=hashlib.sha256(cash_path.read_bytes()).hexdigest(),counts=rows))
    out=Path(__file__).resolve().parents[1]/'evidence/feasibility_2026-10-20.json';out.parent.mkdir(parents=True,exist_ok=True)
    obj=dict(status='event_count_only_no_strategy_test',threshold=.02,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source='Validated Alpaca SIP raw, previous-close adjusted for ex-dividend cash',results=results,
             caveat='Complete-day filter excludes several March 2020 halt days; counts are conditional on available valid sessions. No profitability or predictive power calculated.')
    out.write_text(json.dumps(obj,indent=2),encoding='utf-8');print(json.dumps(obj,indent=2))


if __name__=='__main__':main()
