"""Rapprochement indépendant des journaux et des bougies réellement acquises."""
from pathlib import Path
from math import floor, ceil
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fvg_backtest.report import table


def main():
    p=argparse.ArgumentParser(); p.add_argument("--results",type=Path,default=Path("results/etude_2026-10-19")); a=p.parse_args()
    sources={"SPY":"data/yahoo_28d/SPY_1m.csv","QQQ":"data/yahoo_28d/QQQ_1m.csv", "ES":"data/yahoo_contracts/ES_1m.csv","NQ":"data/yahoo_contracts/NQ_1m.csv"}
    checked=[]; excerpts=[]
    for symbol,path in sources.items():
        bars=pd.read_csv(path); bars.index=pd.to_datetime(bars.pop("timestamp"),utc=True).dt.tz_convert("America/New_York")
        tick=.25 if symbol in ("ES","NQ") else .01
        point={"ES":50,"NQ":20}.get(symbol,1)
        for variant in ["A","B"]:
            folder=a.results/symbol/f"{symbol}_exploratoire_{variant}_slip1_principal"
            trades=pd.read_csv(folder/"trades.csv")
            if trades.empty: continue
            assert not trades.date.duplicated().any()
            capital=100000.
            for _,r in trades.iterrows():
                form=pd.Timestamp(r.formation_time); retest=pd.Timestamp(r.retest_time); signal=pd.Timestamp(r.signal_time)
                entry=pd.Timestamp(r.entry_time); exit_time=pd.Timestamp(r.exit_time); d=1 if r.direction=="LONG" else -1
                opening=bars.loc[r.date+" 09:30":r.date+" 09:34"]
                h=opening.high.max(); l=opening.low.min(); triple=bars.loc[form-pd.Timedelta(minutes=3):form-pd.Timedelta(minutes=1)]
                assert len(opening)==5 and len(triple)==3 and triple.index[0].strftime("%H:%M")>="09:35"
                b1,b2,b3=(triple.iloc[i] for i in range(3))
                if d==1:
                    assert b3.low>b1.high and b2.open<=h and b2.close>h
                    lower,upper=b1.high,b3.low
                else:
                    assert b3.high<b1.low and b2.open>=l and b2.close<l
                    lower,upper=b3.high,b1.low
                rb=bars.loc[retest-pd.Timedelta(minutes=1)]
                assert rb.low<=upper and rb.high>=lower and retest>form
                assert (retest-form).total_seconds()<=900
                assert 0<=(signal-retest).total_seconds()<=120
                confirm=bars.loc[signal-pd.Timedelta(minutes=1)]; prev=bars.loc[signal-pd.Timedelta(minutes=2)]
                if d==1: assert confirm.close>confirm.open and prev.close<prev.open and confirm.open<=prev.close and confirm.close>=prev.open
                else: assert confirm.close<confirm.open and prev.close>prev.open and confirm.open>=prev.close and confirm.close<=prev.open
                assert entry==signal and entry.strftime("%H:%M")<"11:00"
                assert abs(r.entry_reference-bars.loc[entry,"open"])<1e-7
                window=bars.loc[retest-pd.Timedelta(minutes=1):signal-pd.Timedelta(minutes=1)]
                stop_ref=(window.low.min() if variant=="A" else lower)-tick if d==1 else (window.high.max() if variant=="A" else upper)+tick
                expected=(floor(stop_ref/tick+1e-8) if d==1 else ceil(stop_ref/tick-1e-8))*tick
                assert abs(r.stop-expected)<1e-7
                assert abs(r.target-(r.entry_price+d*3*abs(r.entry_price-r.stop)))<1e-6
                pnl=(r.exit_price-r.entry_price)*d*r.quantity*point-r.fees
                assert abs(pnl-r.net_pnl)<1e-6
                assert abs(r.result_r-r.net_pnl/(abs(r.entry_price-r.stop)*r.quantity*point))<1e-7
                assert r.estimated_loss_at_order_usd<=capital*.005+1e-6
                assert r.quantity==int(r.quantity) and r.entry_time[:10]==r.exit_time[:10]
                capital+=r.net_pnl
                checked.append(dict(instrument=symbol,stop=variant,date=r.date,direction=r.direction,formation=str(form),signal=str(signal),entry=r.entry_price,stop_price=r.stop,target=r.target,quantity=int(r.quantity),exit=r.exit_price,reason=r.exit_reason,fees=r.fees,net_pnl=r.net_pnl,result_r=r.result_r))
                if len([x for x in excerpts if x["instrument"]==symbol and x["variant"]==variant])<10:
                    for ts,b in bars.loc[form-pd.Timedelta(minutes=3):entry].iterrows():
                        excerpts.append(dict(instrument=symbol,variant=variant,trade_date=r.date,timestamp=str(ts),open=b.open,high=b.high,low=b.low,close=b.close))
    frame=pd.DataFrame(checked); frame.to_csv(a.results/"audited_trades.csv",index=False)
    pd.DataFrame(excerpts).to_csv(a.results/"audited_ohlc_excerpts.csv",index=False)
    text="# Rapprochement des trades historiques\n\n"
    text+=f"{len(frame)} trades des scénarios principaux rapprochés des OHLC acquis : opening range, FVG strict, retest, englobante, chronologie, prix open d'entrée, stop, objectif, quantité entière, budget et P&L. Ces assertions sont indépendantes de la détection et du calcul de P&L du moteur.\n\n"
    text+=table(frame)+"\n\nLes extraits des bougies sont conservés dans `audited_ohlc_excerpts.csv`. Ce contrôle ne fournit pas l'ordre réel des prix à l'intérieur d'une minute et ne valide pas un historique de marge ou d'emprunt.\n"
    (a.results/"AUDIT_TRADES.md").write_text(text,encoding="utf-8")
    print(frame.to_string(index=False)); print(f"Audited: {len(frame)} real trades")


if __name__=="__main__": main()
