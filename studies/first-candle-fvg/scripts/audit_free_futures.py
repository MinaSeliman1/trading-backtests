"""Audit de source : aucune identité de contrat n'est inventée pour les continus publics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
import numpy as np
from fvg_backtest.data import load_csv
from fvg_backtest.report import table


def main():
    root=Path("data/free_sources/BARS"); destination=Path("results/source_audit_2026-10-19")
    destination.mkdir(parents=True,exist_ok=True); profiles=[]
    for symbol in ["ES","NQ"]:
        raw=pd.read_csv(root/f"{symbol}_1m_raw.csv.gz",comment="#")
        raw["timestamp"]=pd.to_datetime(raw.pop("datetime")).dt.tz_localize("America/New_York",ambiguous="raise",nonexistent="raise")
        # Keep source bars only. No interpolation or transformation of OHLC/volume.
        mask=(raw.timestamp.dt.hour*60+raw.timestamp.dt.minute>=570)&(raw.timestamp.dt.hour*60+raw.timestamp.dt.minute<960)
        rth=raw.loc[mask,["timestamp","open","high","low","close","volume"]].copy()
        path=root/f"{symbol}_rth_continuous_UNVERIFIED.csv"; rth.to_csv(path,index=False)
        quality=load_csv(path,symbol,allow_continuous=True)
        quality.quality.to_csv(destination/f"{symbol}_quality.csv",index=False)
        known=pd.read_csv(f"data/yahoo_contracts/{symbol}_1m.csv")
        known["timestamp"]=pd.to_datetime(known.timestamp,utc=True)
        candidate=rth.copy(); candidate["timestamp"]=pd.to_datetime(candidate.timestamp,utc=True)
        overlap=candidate.merge(known,on="timestamp",suffixes=("_candidate","_dated"))
        fields=["open","high","low","close"]
        difference=np.column_stack([(overlap[f+"_candidate"]-overlap[f+"_dated"]).abs() for f in fields]).max(axis=1)
        complete=quality.sessions
        profile=dict(instrument=symbol,raw_rows=len(raw),rth_rows=len(rth),first_timestamp=str(raw.timestamp.min()),
                     last_timestamp=str(raw.timestamp.max()),complete_sessions=len(complete),
                     complete_span_days=(complete[-1].index[0].date()-complete[0].index[0].date()).days+1 if complete else 0,
                     metadata_contract_identity=False,overlap_minutes=len(overlap),
                     overlap_ohlc_match_half_tick_fraction=float(np.mean(difference<.125)) if len(overlap) else None,
                     upstream_original_repository_status="404 at time checked",
                     decision="not eligible for final dated-contract OOS validation")
        profiles.append(profile)
        print(json.dumps(profile),flush=True)
    (destination/"futures_profiles.json").write_text(json.dumps(profiles,indent=2),encoding="utf-8")
    columns=["instrument","raw_rows","rth_rows","complete_sessions","complete_span_days","overlap_minutes","overlap_ohlc_match_half_tick_fraction"]
    report="# Audit des historiques futures gratuits\n\n"+table(pd.DataFrame(profiles)[columns])+"\n\n"
    report+="Les deux fichiers publics contiennent effectivement plus d'un an de minutes et des volumes, sans remplissage ajouté ici. Les sessions complètes sont mesurées avec le même contrôle que le moteur. Le rapprochement récent porte sur les contrats datés décembre 2026 acquis séparément chez Yahoo ; il ne valide pas l'identité des contrats des années précédentes.\n\n"
    report+="**Limite bloquante pour une validation finale :** les fichiers contiennent le symbole racine ES/NQ mais aucune échéance ni règle de rollover authentifiable pour chaque minute. Le dépôt amont cité `kfccolonel1/AlfordLabs` renvoie 404 lors du contrôle. Aucun nom de contrat n'a été ajouté à partir d'une supposition et aucun résultat de performance n'est présenté comme validation hors échantillon de contrats datés. Les variantes de tableaux de bord communautaires ne constituent pas une provenance de marché suffisante à elles seules.\n\n"
    report+="Source : [dépôt BARS](https://github.com/kfccolonel1/BARS), catalogue et fichiers originaux archivés avec leurs URL et SHA-256 dans `data/free_sources/BARS`. Les données continuent d'être disponibles pour une exploration explicitement conditionnelle, mais ne remplacent pas une série de contrats traçable.\n"
    (destination/"FUTURES.md").write_text(report,encoding="utf-8")


if __name__=="__main__": main()
