"""Rejoue réellement tout B QQQ avec le bot shadow et rapproche l'étude figée.

Prix réellement acquis SIP ; aucun appel API, aucun ordre, aucune donnée synthétique.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse
import hashlib
import json
import pickle
import numpy as np
import pandas as pd
from qqq_paper.strategy import Parameters,Session,STUDY,verify_frozen_strategy
from qqq_paper.ledger import Store
from qqq_paper.runner import Controller


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,default=STUDY/'data/prepared')
    p.add_argument('--output',type=Path,default=Path('validation/replay_2026-10-20.json'));args=p.parse_args()
    verify_frozen_strategy()
    market_path=args.prepared/'QQQ_market.pkl'
    assert hashlib.sha256(market_path.read_bytes()).hexdigest()=='67e5ae72288b8878777683c67343174491895b6069c41f331b13aff422e06711'
    with market_path.open('rb') as stream:m=pickle.load(stream)
    cash=json.loads((args.prepared/'QQQ_dividends.json').read_text())
    reference=STUDY/'results/2026-10-19/QQQ/B_next_open_L4_s0.01_principal'
    expected=pd.read_csv(reference/'daily.csv');decisions=pd.read_csv(reference/'decisions.csv') if (reference/'decisions.csv').exists() else pd.read_csv(STUDY/'results/2026-10-19/QQQ/B_next_open_L4_s0.001_principal/decisions.csv')
    # Price/band/VWAP targets are cost-independent; position quantity is checked against the 1-cent scenario.
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    folder=Path('runtime')/('replay-'+stamp);store=Store(folder/'state.sqlite',Parameters(),'shadow','sip');controller=Controller(store,mode='shadow')
    ndecisions=0;days=0;max_pnl_error=0.;max_feature_error=0.
    for day in expected.itertuples():
        i=list(m.dates.strftime('%Y-%m-%d')).index(day.date)
        history=SimpleNamespace(dates=m.dates[:i],arrays={k:v[:i] for k,v in m.arrays.items()},lengths=m.lengths[:i],valid=m.valid[:i])
        opening=pd.Timestamp(day.date+' 09:30',tz='America/New_York');session=Session(opening,opening+pd.Timedelta(minutes=int(m.lengths[i])))
        idx=pd.date_range(session.open,session.close,inclusive='left',freq='min')
        frame=pd.DataFrame({k:v[i,:len(idx)] for k,v in m.arrays.items()},index=idx)
        before=store.balance;controller.step(history,frame,session,session.close,cash.get(day.date,0.))
        assert store.position==0 and store.get('paused_day')!=day.date,('unexpected skipped day',day.date)
        error=abs(store.balance-before-day.net_pnl);max_pnl_error=max(max_pnl_error,error)
        assert error<1e-6,(day.date,error,store.balance-before,day.net_pnl)
        assert abs(store.balance-day.equity)<1e-6,(day.date,'equity')
        size=dict(store.db.execute('SELECT * FROM days WHERE day=?',(day.date,)).fetchone())
        assert size['quantity']==day.quantity
        for d in decisions[decisions.date==day.date].itertuples():
            key=day.date+':'+pd.Timestamp(d.decision_time).strftime('%H%M')
            row=store.db.execute('SELECT data FROM decisions WHERE key=?',(key,)).fetchone();actual=json.loads(row[0])
            assert actual['target']==d.target
            for feature in ['price','upper','lower','vwap']:
                delta=abs(actual[feature]-getattr(d,feature));max_feature_error=max(max_feature_error,delta)
                assert delta<1e-8,(day.date,feature,delta)
            ndecisions+=1
        days+=1
        if days%100==0:print(f'{days}/{len(expected)} seances reelles rapprochees',flush=True)
    net=store.balance-100000;summary=json.loads((reference/'summary.json').read_text())
    assert abs(net-summary['net_pnl'])<1e-6
    result=dict(status='passed',utc=datetime.now(timezone.utc).isoformat(),source='Alpaca SIP raw acquisition validated 2026-10-19',
                symbol='QQQ',period='2024-05-01/2026-10-16',sessions=days,decisions=ndecisions,fill_events=len(store.fills()),
                expected_trades=summary['trades'],mode='offline shadow replay, no broker orders',slippage=.01,
                net_pnl=net,expected_net_pnl=summary['net_pnl'],max_daily_pnl_error_usd=max_pnl_error,
                max_feature_abs_error=max_feature_error,market_sha256=hashlib.sha256(market_path.read_bytes()).hexdigest(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limits='Verifies historical strategy and ledger parity; not real-time IEX/SIP parity, real fills or future profitability.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    store.close();print(json.dumps(result,indent=2))


if __name__=='__main__':main()
