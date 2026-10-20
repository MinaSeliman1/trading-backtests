"""Complète l'incertitude des coûts B et de la période après révision, sur exports figés."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from noise_area.statistics import block_bootstrap,timed_benchmarks
from scripts.run_study import write_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    args=parser.parse_args();out=args.results
    table=pd.read_csv(out/'comparison_all.csv');costs=[];revised=[]
    for row in table[(table.period=='B')&(table.kind=='principal')].itertuples():
        folder=out/row.instrument/row.label;summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        daily=pd.read_csv(folder/'daily.csv')
        boot=summary.get('bootstrap_block5') or block_bootstrap(daily.return_net,daily.buyhold_return)
        costs.append(dict(instrument=row.instrument,label=row.label,execution=row.execution,leverage_cap=row.leverage_cap,
                          slippage=row.slippage,**boot))
    for row in table[(table.period=='D')&(table.kind=='principal')].itertuples():
        folder=out/row.instrument/row.label
        daily=pd.read_csv(folder/'daily.csv');trades=pd.read_csv(folder/'trades.csv')
        boot=block_bootstrap(daily.return_net,daily.buyhold_return)
        control=timed_benchmarks(trades,daily,row.slippage,row.borrow_rate)
        p=(1+int((np.asarray(control['random_sharpe'])>=row.sharpe).sum()))/1001
        revised.append(dict(instrument=row.instrument,label=row.label,execution=row.execution,leverage_cap=row.leverage_cap,
                            **boot,p_random_sharpe_ge_strategy=p,
                            note='Supplemental uncertainty assessment; no signal, parameter or P&L changed.'))
    write_json(out/'UNCERTAINTY_B_COSTS.json',costs)
    write_json(out/'POST_REVISION_VALIDATION.json',revised)
    print(f'PASS: {len(costs)} intervalles B/coûts, {len(revised)} contrôles après révision ; aucun replay de stratégie.')


if __name__=='__main__':main()
