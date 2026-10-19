"""Rapport chiffré de l'étude Alpaca ; exige une interprétation humaine enregistrée."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fvg_backtest.report import table


def main():
    out=Path('results/alpaca_sip_long')
    data=pd.read_csv(out/'comparison_all.csv')
    audit=json.loads((out/'audit_validation.json').read_text())
    assert audit['status']=='passed'
    interpretations=(out/'INTERPRETATION.md').read_text(encoding='utf-8')
    primary=data[(data.test=='principal')&(data.slippage_ticks==1)].copy()
    idcols=['instrument','segment','stop_variant']
    performance=primary[idcols+['valid_sessions','trades','winners','losers','win_rate','profit_factor','net_pnl','net_return_pct','expectancy_r']]
    risk=primary[idcols+['max_drawdown_usd','max_drawdown_pct','longest_loss_streak','longest_win_streak','actual_risk_mean_pct','max_exposure_pct']]
    behavior=primary[idcols+['average_win_r','average_loss_r','win_loss_ratio','trades_per_calendar_week','average_duration_minutes','pnl_excluding_best_3_sessions']]
    boot=[]; groups=[]; examples=[]; rejections=[]; fill_risks=[]
    for _,row in primary.iterrows():
        folder=out/row.instrument/row.label
        s=json.loads((folder/'summary.json').read_text())
        b=s['bootstrap_block5']; iid=s['bootstrap_iid']
        boot.append(dict(instrument=row.instrument,segment=row.segment,stop=row.stop_variant,trades=row.trades,
                         expectancy_r=row.expectancy_r,IC95_bloc5=str(b.get('expectancy_r_ci95','non calculé')),
                         IC95_iid=str(iid.get('expectancy_r_ci95','non calculé'))))
        for grouping in ['direction','entry_hour','volatility_regime']:
            frame=pd.read_csv(folder/f'by_{grouping}.csv')
            frame.insert(0,'instrument',row.instrument); frame.insert(1,'segment',row.segment)
            frame.insert(2,'stop',row.stop_variant); frame.insert(3,'grouping',grouping)
            frame=frame.rename(columns={grouping:'group'})
            groups.append(frame)
        rejected=pd.read_csv(folder/'rejected_signals.csv')
        for reason,n in rejected.groupby('reason').size().items():
            rejections.append(dict(instrument=row.instrument,segment=row.segment,stop=row.stop_variant,raison=reason,intentions=int(n)))
        t=pd.read_csv(folder/'trades.csv')
        before=100000+t.net_pnl.cumsum().shift(1,fill_value=0)
        fill_risks.append(dict(instrument=row.instrument,segment=row.segment,stop=row.stop_variant,
                               risque_moyen_USD=float(t.initial_risk_usd.mean()),risque_max_USD=float(t.initial_risk_usd.max()),
                               perte_stop_projetee_max_pct=float((t.planned_loss_usd/before*100).max()),
                               trades_perte_stop_projetee_sup_0_5pct=int((t.planned_loss_usd>before*.005+1e-6).sum())))
        if row.segment=='OOS':
            for _,r in t.groupby('direction',sort=False).head(1).iterrows():
                examples.append(dict(instrument=row.instrument,stop=row.stop_variant,date=r.date,direction=r.direction,
                                     signal=r.signal_time,entree=r.entry_price,stop_prix=r.stop,TP=r.target,
                                     quantite=r.quantity,sortie=r.exit_price,frais=r.fees,net=r.net_pnl,R=r.result_r))
    costs=data[(data.test=='principal')&(data.segment=='OOS')][idcols+['slippage_ticks','trades','net_pnl','profit_factor','expectancy_r']]
    sensitivity=data[(data.segment=='OOS')&(data.slippage_ticks==1)][idcols+['test','trades','net_pnl','profit_factor','expectancy_r']]
    wf=data[data.segment=='WF_OOS'].copy()
    wf_records=[]
    for (symbol,stop),frame in wf.groupby(['instrument','stop_variant']):
        total=frame.trades.sum()
        wf_records.append(dict(instrument=symbol,stop=stop,blocs=len(frame),blocs_positifs=int((frame.net_pnl>0).sum()),
                               seances=int(frame.valid_sessions.sum()),trades=int(total),somme_PnL_blocs=float(frame.net_pnl.sum()),
                               esperance_R_ponderee=float((frame.expectancy_r*frame.trades).sum()/total) if total else None))
    pd.DataFrame(wf_records).to_csv(out/'walk_forward_overview.csv',index=False)
    pd.concat(groups,ignore_index=True).to_csv(out/'behavior_primary.csv',index=False)
    pd.DataFrame(rejections).to_csv(out/'rejections_primary.csv',index=False)
    pd.DataFrame(fill_risks).to_csv(out/'risk_after_fill_primary.csv',index=False)
    wf_table=wf[['instrument','stop_variant','first_session','last_session','trades','net_pnl','profit_factor','expectancy_r']]
    profiles=pd.DataFrame(json.loads((out/'PRE_EXECUTION_SPLIT.json').read_text()))
    quality=[]
    for symbol in ['SPY','QQQ']:
        manifest=json.loads((Path('data/alpaca_sip_2023_2026')/f'{symbol}_manifest.json').read_text())
        q=pd.read_csv(out/symbol/'data_quality.csv')
        quality.append(dict(instrument=symbol,bougies_acquises=manifest['rows'],pages=len(manifest['pages']),
                            seances_retenues=int((q.status=='accepted').sum()),seances_exclues=int((q.status!='accepted').sum()),
                            minutes_manquantes=int(q.missing_minutes.sum()),OHLCV_invalides=int(q.invalid_ohlcv.sum()),
                            doublons_conflictuels=int(q.conflicting_rows.sum())))
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    text=f'''# First Candle Rule + FVG — validation historique longue SPY / QQQ

Étude exécutée le 19 octobre 2026. Source : Alpaca SIP, vraies bougies 1 minute, prix raw. Résultats propres à chaque instrument, stop et segment ; comptes indépendants de 100 000 USD, sans addition en portefeuille.

{interpretations}

## Périmètre, qualité et dates fixées

{table(pd.DataFrame(quality))}

{table(profiles[['instrument','first','last','IS_first','IS_last','OOS_first','OOS_last']])}

Prix non ajustés, horodatages d'ouverture UTC convertis en America/New_York ; seules les minutes régulières du calendrier XNYS sont utilisées, avec jours fériés, DST et clôtures écourtées. SPY : séance du 5 juin 2023 exclue pour quatre minutes absentes, hors opening range ; QQQ : aucune séance régulière exclue. Toute séance incomplète est exclue entière, aucune interpolation. Cette sélection qualité rétrospective peut différer d'une décision en temps réel. Les heures étendues acquises ne créent aucun signal. Une seule année est demandée au minimum : les données retenues couvrent ici 1 355 jours calendaires et plus de trois années.

La fin de demande, 21 septembre 2026 exclu, écarte les journées déjà étudiées dans le test Yahoo préliminaire. `PRE_EXECUTION_SPLIT.json` a été écrit avant les nouveaux calculs de performance. Le seuil 70/30 est appliqué aux séances conservées, d'où un jour de différence entre ETF. Les deux historiques sont comparables sans être strictement identiques à leur frontière. Le protocole a été figé après l'exploration récente et avant ces nouveaux calculs : c'est une validation historique rétrospective sur une période réservée, pas une preuve prospective d'un modèle enregistré avant 2025.

Une correction numérique des contacts stop/TP a été nécessaire après l'audit du premier calcul partiel. L'étude présentée ici est entièrement recalculée avec ce correctif symétrique, sur les dates initiales inchangées. Des résultats partiels avaient été vus avant la correction ; cette étape de débogage et ses tests sont détaillés dans `CORRECTION_NUMERIQUE.md`. Les sorties provisoires archivées ne sont pas la référence. Le correctif ne modifie aucune fenêtre, aucun filtre ni aucun coût de la stratégie.

## Performances principales — 1 tick par exécution

{table(performance)}

`win_rate` est une fraction, `net_return_pct` un pourcentage. P&L et rendement sont nets de frais et d'emprunt hypothétique. Les sensibilités et les stops représentent des hypothèses distinctes ; leurs trades ne sont pas des observations indépendantes supplémentaires.

## Risque et comportement

{table(risk)}

{table(behavior)}

{table(pd.DataFrame(fill_risks))}

Le drawdown inclut les marques aux clôtures des minutes et aux exécutions, pas les excursions au sein des minutes. Le risque en R utilise le risque initial au fill, hors frais ; le budget de dimensionnement réserve les frais et la friction de sortie. Des pertes légèrement inférieures à −1R sont donc normales. La moyenne de risque effectivement engagé peut être bien inférieure à 0,5 %, notamment du fait de l'exposition ETF plafonnée à 100 % du capital.

Les durées intrabougie sont des bornes inférieures à une précision d'une minute ; le journal fournit aussi une borne supérieure. Les instants du stop/TP sont connus seulement à l'intérieur de leur minute, contrairement aux exécutions programmées à l'open.

## Incertitude — 5 000 rééchantillonnages

{table(pd.DataFrame(boot))}

IC percentile à 95 % de l'espérance moyenne en R par trade. Les jours sans trade sont inclus et les trades sont regroupés par séance. Deux schémas : séances indépendantes et blocs circulaires de cinq séances. Les intervalles supposent que le rééchantillonnage représente les dépendances pertinentes ; ils ne garantissent ni stabilité future ni correction de toutes les comparaisons multiples. Le seuil technique de 20 trades / 60 séances ne constitue pas une démonstration de puissance. Une fraction de réplications positives n'est ni une probabilité bayésienne d'avantage ni une p-value.

## Dégradation des coûts sur la période OOS

{table(costs)}

Le slippage nominal 1/2/3/5 ticks est appliqué à chaque entrée et sortie, avec les mêmes règles de signal. Le spread ETF total supposé est un tick, réparti par moitié et arrondi défavorablement au tick. Les fills peuvent donc subir deux ticks effectifs au scénario nominal un tick. Le prix exécuté change le risque, la quantité prévue, le TP et parfois l'acceptation d'un ordre : les journaux ne sont pas mécaniquement identiques. Les commissions restent inchangées.

## Sensibilités de règles, sans sélection du meilleur résultat

{table(sensitivity)}

Version principale : retest sous 15 minutes ; confirmation sur le retest ou les deux minutes suivantes. Tests séparés : retest 10/20 minutes, confirmation 0/1/3 minutes. La traversée du niveau par le corps de la deuxième bougie du FVG reste stricte. Les paramètres ne sont ni optimisés sur IS ni choisis selon OOS.

Le délai de 15 minutes porte sur la survenue du premier retest, mesurée à son close. Une confirmation deux bougies après un retest situé à cette limite peut être connue jusqu'à 17 minutes après formation. Cette convention de fenêtres séparées est conservée pour tous les scénarios.

## Walk-forward à paramètres fixes

{table(pd.DataFrame(wf_records))}

252 séances antérieures pour définir seulement les seuils descriptifs de volatilité, puis 63 séances test, avancées de 63 séances ; dernier bloc conservé s'il contient au moins 30 séances. Aucun entraînement des règles. Le capital repart de 100 000 USD pour chaque bloc : la somme des P&L de blocs est un diagnostic à capital réinitialisé, pas une courbe de compte composé. Les fenêtres WF couvrent en partie les segments IS et OOS de l'autre découpage ; elles ne constituent pas une seconde collection indépendante à ajouter aux trades OOS.

{table(wf_table)}

## LONG, SHORT, horaires et volatilité

Les tableaux `behavior_primary.csv` et `by_direction.csv`, `by_entry_hour.csv`, `by_volatility_regime.csv` dans chaque scénario contiennent les décompositions complètes. Les régimes low/middle/high sont les terciles de l'amplitude de la première bougie rapportée à son milieu : ce proxy de volatilité ne décrit pas tout le marché. Seuils estimés sur IS seulement pour IS/OOS, sur les 252 séances précédentes pour WF. Une différence de groupe est descriptive et ne justifie pas de modifier le filtre après observation.

## Rapprochement indépendant et exemples historiques

La suite exécutée comporte **41 tests réussis**. Les exports des **{len(data)} scénarios** ont aussi été contrôlés pour leurs effectifs, totaux, regroupements, budgets, absence d'overnight et limites d'entrée. Les empreintes du code et des données concordent avec le manifeste ; le découpage original est inchangé. Six figures de synthèse et trois diagnostics représentatifs ont été examinés visuellement, en complément du contrôle structurel et des empreintes des 122 PNG. Voir `VALIDATION.md` et `OUTPUT_VALIDATION.json`.

**{audit['trades_checked']} lignes de trades IS/OOS principales vérifiées**, stops A/B à un tick : opening range, FVG après 9:35, corps de traversée, premier retest, englobante, chronologie, quantité calculée avant le prochain open, fills, stop, TP, premier événement de sortie, stop avant TP ambigu, frais, budget et P&L. Les pages brutes et CSV ont été vérifiés par SHA-256. Totaux journaliers/mensuels, PF, espérance, capital et drawdowns sont rapprochés indépendamment ; détails dans `audit_validation.json` et `audited_trades.csv`. L'audit ne réexécute pas indépendamment tous les chemins des sensibilités/WF et ne prouve pas l'exhaustivité de tous les signaux omis.

Premiers trades LONG/SHORT chronologiques OOS de chaque combinaison, sélectionnés sans condition de profit :

{table(pd.DataFrame(examples))}

Les bougies correspondantes figurent dans `audited_ohlc_excerpts.csv`. Ces contrôles ne révèlent pas l'ordre réellement suivi par les prix dans une minute et ne valident pas un carnet d'ordres ou des capacités d'emprunt historiques.

## Hypothèses d'exécution conservées

- Un seul trade par instrument et séance, première intention valide, entrée à l'open suivant la confirmation et avant 11:00 New York. Au plus tard, sortie à l'open de la dernière minute de la séance, y compris écourtée.
- Stop A sous/au-dessus des extrêmes du retest à la confirmation ; stop B derrière le FVG, chacun avec un tick de buffer. TP fixé à 3 fois le risque au fill, avec arrondi au tick. Sorties TP traitées comme marché déclenché ; ce ne sont pas des ordres limites garantis.
- Quantité entière fixée au close de confirmation. Cible de perte estimée avec frais ≤0,5 % du capital courant ; plafond d'exposition sans levier et plafond de 1 % du volume connu de confirmation. Aucune lecture du volume ou du prix de la minute suivante pour dimensionner.
- Commission hypothétique de 0,005 USD/action/côté, minimum 1 USD, plafonnée à 1 % du nominal, plus réserve 0,0001 USD/action/côté. Emprunt SHORT supposé disponible, coût 1 % annuel sur une journée de 360 jours par trade intraday. Ce modèle de frais préexistant est conservé ; utiliser Alpaca comme fournisseur n'en fait pas une simulation de sa tarification d'exécution.
- Gap stop : sortie au prix disponible avec friction. Stop et TP touchés dans la même minute : stop prioritaire, sauf si un événement déjà observable à l'open s'est produit avant les excursions. Rejet d'un ordre devenu invalide ou trop exposé au prochain open selon la convention du moteur ; une vraie intention déjà envoyée pourrait être exécutée et nécessiter une fermeture. L'effet concret de cette convention est recensé dans les rejets de signaux.

{table(pd.DataFrame(rejections))}

Ce tableau compte des intentions, dont plusieurs peuvent être rejetées pendant une même séance avant un éventuel trade. `invalid_stop_at_order` est un rejet au close connu ; `invalid_stop` et `broker_capital_or_exposure_rejection_after_gap` interviennent à l'open suivant. Ils ne sont pas des transactions fictivement effacées d'un compte réel, mais une limitation explicite du modèle d'acceptation des ordres.

Pas de ticks, bid/ask historique, profondeur, latence, remplissages partiels ou disponibilité d'emprunt vérifiée. Révisions et règles d'agrégation du fournisseur peuvent changer certains hauts/bas stricts. Pas d'ajustement de paramètres après lecture de la période réservée. ES/NQ restent séparément non validés sur historique long : les fichiers gratuits trouvés sont des continus sans échéances vérifiables ; leur audit qualité ne valide pas les raccordements. Aucun résultat de continu n'est présenté comme validation finale ES/NQ.

## Figures et fichiers livrés

![Capital et drawdown OOS](OOS_capital_drawdown.png)

![P&L mensuel OOS](OOS_monthly.png)

![Distribution des R OOS](OOS_distribution_r.png)

Les trois figures équivalentes IS sont présentes, ainsi que `diagnostics.png` dans chacun des {len(data)} scénarios. Les journaux, equity aux minutes, mois, sous-groupes et rejets sont conservés. Les graphiques de diagnostic sont rendus à nouveau depuis leurs CSV pour espacer les étiquettes mensuelles ; aucune statistique n'est changée par cette opération (`FIGURES_PROVENANCE.json`).

## Sources et reproduction

Source officielle : [FAQ Alpaca, gratuité SIP historique et agrégation des minutes](https://docs.alpaca.markets/us/docs/market-data-faq), [API de données](https://docs.alpaca.markets/us/docs/about-market-data-api). Requêtes `feed=sip`, `adjustment=raw`, `timeframe=1Min`, début 2023-01-01 inclus, fin 2026-09-21 exclu, pagination complète. Tous les fichiers sont privés et locaux ; les clés n'ont pas été sauvegardées dans les sources, données ou rapports. Aucun endpoint d'ordre ni de compte utilisé. Les alternatives examinées sont documentées dans `docs/RECHERCHE_SOURCES_GRATUITES.md`.

Environnement exécuté : Python {manifest['python']}, versions exactes et empreintes du code dans `manifest.json`, dépendances dans `requirements-lock.txt`. Depuis la racine, après installation des dépendances :

```powershell
python scripts/run_long_history.py --out results/reproduction_alpaca
python scripts/audit_long_history.py --results results/reproduction_alpaca
python scripts/render_long_figures.py --results results/reproduction_alpaca
```

Les CSV déjà acquis suffisent pour refaire les calculs, sans identifiants ni réseau. Une nouvelle acquisition exige vos propres clés en console masquée : `python scripts/download_alpaca.py --prompt-credentials`. Ne jamais les coller dans un rapport ou un chat. Le moteur ne contacte aucun courtier.

Le Pine v6 est livré dans `tradingview/first_candle_fvg.pine`, compilé et enregistré privé lors de l'étude initiale. Aucun backtest TradingView annuel ni rapprochement annuel Python/Pine n'a été exécuté : limites du compte Basic et différences du simulateur, expliquées dans `tradingview/README.md`. L'étude longue présente est réellement exécutée en Python sur les fichiers Alpaca, avec les différences de convention déjà déclarées.
'''
    (out/'RAPPORT_FINAL.md').write_text(text,encoding='utf-8')
    print('Rapport final construit depuis les résultats et l’interprétation contrôlés.')


if __name__=='__main__': main()
