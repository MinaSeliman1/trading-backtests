import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import sys
import pandas as pd
import numpy as np
from .data import load_csv
from .engine import Config, INSTRUMENTS, run
from .report import export_run, split_sessions, table


def main():
    p=argparse.ArgumentParser(description="Backtest causal First Candle Rule + FVG")
    p.add_argument("--data",action="append",required=True,metavar="SYMBOL=CSV")
    p.add_argument("--timezone",help="obligatoire si timestamps CSV sans fuseau")
    p.add_argument("--timestamp-at",choices=["open","close"],default="open")
    p.add_argument("--out",type=Path,default=Path("results"))
    p.add_argument("--rolls",type=Path); p.add_argument("--margins",type=Path); p.add_argument("--calendar",type=Path)
    p.add_argument("--allow-continuous",action="store_true"); p.add_argument("--strict-futures",action="store_true")
    p.add_argument("--sensitivity",action="store_true")
    p.add_argument("--bootstrap-reps",type=int,default=5000)
    p.add_argument("--config",type=Path,help="JSON contenant des valeurs du dataclass Config")
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    config=Config(**json.loads(a.config.read_text(encoding="utf-8"))) if a.config else Config()
    summaries=[]; manifests=[]; coverage=[]
    for specification in a.data:
        symbol,path=specification.split("=",1)
        if symbol not in INSTRUMENTS: p.error("symbols: SPY QQQ ES NQ")
        d=load_csv(path,symbol,a.timezone,a.timestamp_at,a.rolls,a.margins,a.calendar,a.allow_continuous,a.strict_futures)
        manifests.append(d.manifest); folder=a.out/symbol; folder.mkdir(exist_ok=True)
        d.quality.to_csv(folder/"data_quality.csv",index=False)
        if not d.sessions:
            coverage.append(dict(instrument=symbol,status="NO_VALID_SESSIONS",valid_sessions=0)); continue
        span=(d.sessions[-1].index[0].date()-d.sessions[0].index[0].date()).days+1
        segments=split_sessions(d.sessions,span)
        # In continuous mode all results remain exploratory, regardless of span.
        if d.manifest["continuous_unverified"]: segments={"exploratoire_continuous":d.sessions}
        coverage.append(dict(instrument=symbol,status="exploratoire" if len(segments)==1 else "IS_OOS",valid_sessions=len(d.sessions),span_days=span))
        thresholds=None
        if "IS" in segments:
            opening=np.array([(s.high.iloc[:5].max()-s.low.iloc[:5].min())/((s.high.iloc[:5].max()+s.low.iloc[:5].min())/2) for s in segments["IS"]])
            thresholds=np.quantile(opening,[1/3,2/3]).tolist()
        variants=[("principal",15,2)]
        if a.sensitivity: variants += [("retest10",10,2),("retest20",20,2),("confirmation0",15,0),("confirmation1",15,1),("confirmation3",15,3)]
        for segment,sessions in segments.items():
            for stop in ["A","B"]:
                for ticks in [1,2,3,5]:
                    for name,retest,confirmation in variants:
                        # Slippage sensitivities crossed only with principal; other tests vary one parameter.
                        if ticks!=1 and name!="principal": continue
                        c=replace(config,stop_variant=stop,slippage_ticks=ticks,retest_minutes=retest,confirmation_bars=confirmation)
                        t,e,r=run(sessions,INSTRUMENTS[symbol],c)
                        label=f"{symbol}_{segment}_{stop}_slip{ticks}_{name}"
                        s=export_run(folder/label,t,e,r,sessions,c,label,a.bootstrap_reps,thresholds)
                        s.update(instrument=symbol,stop_variant=stop,slippage_ticks=ticks,test=name,segment=segment,
                                 retest_minutes=retest,confirmation_bars=confirmation)
                        summaries.append(s)
        if len(d.sessions)>=504 and "IS" in segments:
            for offset in range(252,len(d.sessions),63):
                test=d.sessions[offset:offset+63]
                if len(test)<30: continue
                training=d.sessions[offset-252:offset]
                opening=[(s.high.iloc[:5].max()-s.low.iloc[:5].min())/((s.high.iloc[:5].max()+s.low.iloc[:5].min())/2) for s in training]
                cut=np.quantile(opening,[1/3,2/3]).tolist()
                for stop in ["A","B"]:
                    c=replace(config,stop_variant=stop,slippage_ticks=1)
                    t,e,r=run(test,INSTRUMENTS[symbol],c)
                    label=f"{symbol}_WF{offset}_{stop}"
                    s=export_run(folder/label,t,e,r,test,c,label,a.bootstrap_reps,cut)
                    s.update(instrument=symbol,stop_variant=stop,slippage_ticks=1,test="walk_forward_fixed",segment="WF_OOS",training_first=str(training[0].index[0].date()),training_last=str(training[-1].index[0].date()))
                    summaries.append(s)
    result=pd.DataFrame(summaries)
    result.to_csv(a.out/"comparison_all.csv",index=False)
    (a.out/"coverage.json").write_text(json.dumps(coverage,indent=2),encoding="utf-8")
    versions={}
    for name in ["pandas","numpy","matplotlib","exchange-calendars","pytest","yfinance"]:
        try: versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: pass
    sources={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path("fvg_backtest").glob("*.py")}
    manifest=dict(generated_utc=datetime.now(timezone.utc).isoformat(),command=sys.argv,python=platform.python_version(),
                  packages=versions,config=asdict(config),instruments={k:asdict(v) for k,v in INSTRUMENTS.items()},
                  inputs=manifests,source_hashes=sources,bootstrap_reps=a.bootstrap_reps,seed=20261019)
    (a.out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    if len(result):
        base=result[(result.test=="principal")&(result.slippage_ticks==1)]
        columns=["instrument","segment","stop_variant","valid_sessions","trades","winners","losers","win_rate","profit_factor","net_pnl","net_return_pct","expectancy_r","max_drawdown_usd"]
        overview=table(base[columns])
        costs=table(result[result.test=="principal"][["instrument","segment","stop_variant","slippage_ticks","trades","net_pnl","expectancy_r"]])
    else: overview=costs="Aucun résultat calculable."
    inadequate=not coverage or any(c["status"]!="IS_OOS" for c in coverage) or set(c["instrument"] for c in coverage)!={"SPY","QQQ","ES","NQ"}
    report=f"""# Étude First Candle Rule + FVG

## Conclusion exécutive

{'**Couverture partielle des quatre instruments demandés.** Le statut et les segments de chaque instrument figurent dans `coverage.json` et les tableaux ci-dessous : un segment IS/OOS reste une validation chronologique pour son instrument, même si un autre instrument manque. Une série exploratoire ne devient pas OOS du fait de sa présence dans le même rapport. Aucune conclusion commune aux quatre marchés ne peut être tirée avec cette couverture.' if inadequate else '**Résultats IS/OOS disponibles.** Leur existence ne démontre pas à elle seule un avantage ; examiner les intervalles, le nombre de trades et la stabilité des variantes avant toute classification favorable.'}

Les chiffres proviennent exclusivement des fichiers OHLCV indiqués dans `manifest.json`. Capital indépendant de 100 000 USD par instrument, variante et segment. Les nombres ne s'additionnent pas en portefeuille. Les scénarios artificiels des tests sont exclus de ce rapport.

## Résultats principaux, un tick de slippage par côté

{overview}

## Sensibilité des coûts

{costs}

Les signaux suivent les mêmes règles dans ces scénarios. Le prix exécuté modifie le risque, la quantité entière et l'objectif à 3R ; des sorties et des trades acceptés peuvent donc différer. Le spread et les commissions restent constants. `slippage_usd` inclut aussi le spread et l'arrondi défavorable ; `nominal_slippage_usd` isole l'hypothèse nominale de slippage.

## Risque, incertitude et comportement

`comparison_all.csv` et chaque `summary.json` contiennent toutes les statistiques. Les drawdowns sont mesurés aux clôtures 1 minute et aux exécutions ; les excursions intraminute sont inconnues. Le risque initial en R exclut les frais, alors que le dimensionnement les réserve. Des gaps peuvent perdre plus que le budget de 0,5 %. Les durées de trades intrabougie sont des bornes inférieures à une précision d'une minute.

Chaque dossier contient `trades.csv`, `equity_intraday.csv`, `daily.csv`, `monthly.csv`, les regroupements direction/heure/régime et `diagnostics.png`. Les séances sans trade sont conservées. Le bootstrap n'est calculé qu'avec au moins 20 trades et 60 séances, seuil de calcul qui ne garantit pas une puissance statistique suffisante. Deux méthodes : séances indépendantes et blocs circulaires de cinq séances. Les IC sont conditionnels aux hypothèses de stabilité de la série. Les sensibilités ne sélectionnent jamais un gagnant automatiquement.

## Réponses critiques

1. Profitabilité après frais : consulter le P&L net pour chaque variante ; aucun chiffre brut ne constitue la conclusion.
2. Validation nouvelle : seuls les segments OOS et WF_OOS y répondent. Leur absence signifie non testé.
3. Instrument le plus solide : aucune conclusion comparative crédible si les quatre instruments n'ont pas de couverture longue et comparable.
4. LONG/SHORT : regroupements exportés ; une faible différence avec quelques trades ne prouve rien.
5. Stop le plus robuste : A et B restent deux hypothèses distinctes ; pas de choix rétrospectif recommandé.
6. Régimes : seuils fixés sur l'IS seulement ; données exploratoires laissées sans classement.
7. Concentration : `pnl_excluding_best_3_sessions` et `pnl_excluding_best_3_trades` montrent l'effet du retrait des meilleurs gains. Ce sont des diagnostics, pas un nouveau backtest optimisé.
8. Slippage : comparer 1/2/3/5 ticks dans le tableau ci-dessus.
9. Taille d'échantillon : le nombre de trades, la période couverte et les IC doivent être considérés ensemble.
10. Hasard ou avantage : un PF supérieur à 1, à lui seul, ne permet pas de conclure.

## Limites et travail non vérifié

Pas de carnet d'ordres, d'horodatage subminute, de remplissages partiels, ni d'historique d'emprunt vérifié. La quantité est plafonnée à 1 % du volume de la bougie de confirmation déjà connue, ce qui reste un proxy de liquidité. Vente à découvert des ETF supposée disponible avec coût annuel hypothétique 1 %, facturé une journée pour chaque aller-retour intraday. Commissions et marges par défaut sont des hypothèses paramétrables, pas des archives de tarifs. Tout historique futures continu non vérifié demeure exploratoire. La qualité de la source et les exclusions peuvent biaiser les observations.

Pine Script : voir le statut distinct dans `tradingview/README.md` à la racine du projet. Une lecture de code Python ne vaut pas compilation TradingView. Le broker emulator ne garantit pas la règle stop d'abord ni les mêmes réserves de frais pour le dimensionnement. La quantité Python est fixée au close de confirmation ; les gaps peuvent écarter le risque effectif de la cible. Le rejet d'un ordre devenu invalide au prochain open reste une convention de simulation, pas une annulation de marché prouvée réalisable.

Consulter `docs/PROTOCOLE.md`, `README.md` et les sources officielles dans `docs/SOURCES.md` pour reproduire l'étude. Aucun passage au trading réel n'est déduit de ces résultats.
"""
    (a.out/"RAPPORT.md").write_text(report,encoding="utf-8")
    print(overview)
    print(f"Report: {(a.out/'RAPPORT.md').resolve()}")


if __name__=="__main__": main()
