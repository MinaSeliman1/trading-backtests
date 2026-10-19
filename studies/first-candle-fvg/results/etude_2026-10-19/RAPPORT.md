# Étude First Candle Rule + FVG

## Conclusion exécutive

**Catégorie 5 — Impossible à évaluer sérieusement avec la couverture actuelle.** Les calculs ci-dessous sont exploratoires, sans validation hors échantillon exploitable sur les quatre instruments.

Les chiffres proviennent exclusivement des fichiers OHLCV indiqués dans `manifest.json`. Capital indépendant de 100 000 USD par instrument, variante et segment. Les nombres ne s'additionnent pas en portefeuille. Les scénarios artificiels des tests sont exclus de ce rapport.

## Résultats principaux, un tick de slippage par côté

| instrument | segment | stop_variant | valid_sessions | trades | winners | losers | win_rate | profit_factor | net_pnl | net_return_pct | expectancy_r | max_drawdown_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | exploratoire | A | 20 | 2 | 0 | 2 | 0.0000 | 0.0000 | -133.4600 | -0.1335 | -1.1245 | 248.1460 |
| SPY | exploratoire | B | 20 | 2 | 0 | 2 | 0.0000 | 0.0000 | -165.7000 | -0.1657 | -1.0977 | 280.3860 |
| QQQ | exploratoire | A | 19 | 3 | 1 | 2 | 0.3333 | 1.1438 | 27.7093 | 0.0277 | 0.2511 | 238.2933 |
| QQQ | exploratoire | B | 19 | 4 | 0 | 4 | 0.0000 | 0.0000 | -494.9162 | -0.4949 | -1.0775 | 531.7077 |
| ES | exploratoire | A | 20 | 7 | 1 | 6 | 0.1429 | 0.2170 | -1497.5000 | -1.4975 | -0.5579 | 2352.5000 |
| ES | exploratoire | B | 20 | 6 | 0 | 6 | 0.0000 | 0.0000 | -2075.0000 | -2.0750 | -1.0927 | 2510.0000 |
| NQ | exploratoire | A | 20 | 1 | 0 | 1 | 0.0000 | 0.0000 | -405.0000 | -0.4050 | -1.0253 | 517.5000 |
| NQ | exploratoire | B | 20 | 1 | 0 | 1 | 0.0000 | 0.0000 | -305.0000 | -0.3050 | -1.0339 | 417.5000 |

## Sensibilité des coûts

| instrument | segment | stop_variant | slippage_ticks | trades | net_pnl | expectancy_r |
|---|---|---|---|---|---|---|
| SPY | exploratoire | A | 1 | 2 | -133.4600 | -1.1245 |
| SPY | exploratoire | A | 2 | 2 | -138.6199 | -1.1431 |
| SPY | exploratoire | A | 3 | 2 | -143.7799 | -1.1610 |
| SPY | exploratoire | A | 5 | 2 | -154.0997 | -1.1946 |
| SPY | exploratoire | B | 1 | 2 | -165.7000 | -1.0977 |
| SPY | exploratoire | B | 2 | 2 | -170.8599 | -1.1129 |
| SPY | exploratoire | B | 3 | 2 | -176.0199 | -1.1276 |
| SPY | exploratoire | B | 5 | 2 | -186.3397 | -1.1555 |
| QQQ | exploratoire | A | 1 | 3 | 27.7093 | 0.2511 |
| QQQ | exploratoire | A | 2 | 4 | -121.6861 | -0.0838 |
| QQQ | exploratoire | A | 3 | 4 | -127.0060 | -0.0970 |
| QQQ | exploratoire | A | 5 | 4 | -137.6459 | -0.1223 |
| QQQ | exploratoire | B | 1 | 4 | -494.9162 | -1.0775 |
| QQQ | exploratoire | B | 2 | 4 | -505.5961 | -1.0932 |
| QQQ | exploratoire | B | 3 | 4 | -516.2760 | -1.1081 |
| QQQ | exploratoire | B | 5 | 4 | -537.6359 | -1.1359 |
| ES | exploratoire | A | 1 | 7 | -1497.5000 | -0.5579 |
| ES | exploratoire | A | 2 | 7 | -1430.0000 | -0.6274 |
| ES | exploratoire | A | 3 | 7 | -1605.0000 | -0.6846 |
| ES | exploratoire | A | 5 | 7 | -1407.5000 | -0.7745 |
| ES | exploratoire | B | 1 | 6 | -2075.0000 | -1.0927 |
| ES | exploratoire | B | 2 | 6 | -2070.0000 | -1.1484 |
| ES | exploratoire | B | 3 | 6 | -2295.0000 | -1.1973 |
| ES | exploratoire | B | 5 | 6 | -1930.0000 | -1.2793 |
| NQ | exploratoire | A | 1 | 1 | -405.0000 | -1.0253 |
| NQ | exploratoire | A | 2 | 1 | -415.0000 | -1.0375 |
| NQ | exploratoire | A | 3 | 1 | -425.0000 | -1.0494 |
| NQ | exploratoire | A | 5 | 1 | -445.0000 | -1.0723 |
| NQ | exploratoire | B | 1 | 1 | -305.0000 | -1.0339 |
| NQ | exploratoire | B | 2 | 1 | -315.0000 | -1.0500 |
| NQ | exploratoire | B | 3 | 1 | -325.0000 | -1.0656 |
| NQ | exploratoire | B | 5 | 1 | -345.0000 | -1.0952 |

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
