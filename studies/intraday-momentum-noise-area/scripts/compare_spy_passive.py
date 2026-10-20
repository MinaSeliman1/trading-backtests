"""Complète les intervalles de B contre SPY passif, sans changer le backtest."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from noise_area.statistics import block_bootstrap,return_statistics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    args=p.parse_args();out=args.results
    frame=pd.read_csv(out/'comparison_all.csv')
    rows=[]
    for x in frame[(frame.period=='B')&(frame.kind=='principal')&(frame.slippage==.001)].itertuples():
        daily=pd.read_csv(out/x.instrument/x.label/'daily.csv')
        rows.append(dict(instrument=x.instrument,label=x.label,execution=x.execution,leverage_cap=x.leverage_cap,
                         bootstrap=block_bootstrap(daily.return_net.to_numpy(),daily.SPY_buyhold_return.to_numpy()),
                         SPY_buyhold=return_statistics(daily.SPY_buyhold_return.to_numpy(),daily.date.to_numpy())))
    (out/'B_VS_SPY_PASSIVE.json').write_text(json.dumps(dict(results=rows,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print(f'PASS: {len(rows)} comparaisons appariées avec SPY passif.')


if __name__=='__main__':main()
