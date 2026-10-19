# Étude First Candle Rule + FVG

## Conclusion exécutive

**Couverture partielle des quatre instruments demandés.** Le statut et les segments de chaque instrument figurent dans `coverage.json` et les tableaux ci-dessous : un segment IS/OOS reste une validation chronologique pour son instrument, même si un autre instrument manque. Une série exploratoire ne devient pas OOS du fait de sa présence dans le même rapport. Aucune conclusion commune aux quatre marchés ne peut être tirée avec cette couverture.

Les chiffres proviennent exclusivement des fichiers OHLCV indiqués dans `manifest.json`. Capital indépendant de 100 000 USD par instrument, variante et segment. Les nombres ne s'additionnent pas en portefeuille. Les scénarios artificiels des tests sont exclus de ce rapport.

## Résultats principaux, un tick de slippage par côté

| instrument | segment | stop_variant | valid_sessions | trades | winners | losers | win_rate | profit_factor | net_pnl | net_return_pct | expectancy_r | max_drawdown_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | IS | A | 651 | 154 | 34 | 120 | 0.2208 | 0.7674 | -2212.1853 | -2.2122 | -0.2497 | 3360.7531 |
| SPY | IS | B | 651 | 146 | 40 | 106 | 0.2740 | 1.0314 | 282.9070 | 0.2829 | -0.0555 | 1311.8836 |
| SPY | OOS | A | 279 | 75 | 16 | 59 | 0.2133 | 0.7224 | -1325.9789 | -1.3260 | -0.2561 | 1771.0071 |
| SPY | OOS | B | 279 | 73 | 16 | 57 | 0.2192 | 0.5407 | -2429.8689 | -2.4299 | -0.2653 | 2891.2759 |
| QQQ | IS | A | 651 | 158 | 42 | 116 | 0.2658 | 0.9022 | -1376.6844 | -1.3767 | -0.0356 | 3614.9965 |
| QQQ | IS | B | 651 | 152 | 42 | 110 | 0.2763 | 0.8898 | -1629.2724 | -1.6293 | -0.0054 | 2873.9531 |
| QQQ | OOS | A | 280 | 58 | 12 | 46 | 0.2069 | 0.9484 | -246.6196 | -0.2466 | -0.2469 | 1989.5796 |
| QQQ | OOS | B | 280 | 56 | 10 | 46 | 0.1786 | 0.7962 | -1096.5497 | -1.0965 | -0.3729 | 2222.9288 |

## Sensibilité des coûts

| instrument | segment | stop_variant | slippage_ticks | trades | net_pnl | expectancy_r |
|---|---|---|---|---|---|---|
| SPY | IS | A | 1 | 154 | -2212.1853 | -0.2497 |
| SPY | IS | A | 2 | 153 | -2455.2379 | -0.2726 |
| SPY | IS | A | 3 | 154 | -3528.8078 | -0.3820 |
| SPY | IS | A | 5 | 154 | -4351.9856 | -0.4547 |
| SPY | IS | B | 1 | 146 | 282.9070 | -0.0555 |
| SPY | IS | B | 2 | 147 | 7.6832 | -0.1303 |
| SPY | IS | B | 3 | 148 | -792.7829 | -0.2254 |
| SPY | IS | B | 5 | 149 | -1930.0858 | -0.3724 |
| SPY | OOS | A | 1 | 75 | -1325.9789 | -0.2561 |
| SPY | OOS | A | 2 | 75 | -1442.1328 | -0.2773 |
| SPY | OOS | A | 3 | 75 | -1562.7809 | -0.2971 |
| SPY | OOS | A | 5 | 75 | -1807.5728 | -0.3336 |
| SPY | OOS | B | 1 | 73 | -2429.8689 | -0.2653 |
| SPY | OOS | B | 2 | 73 | -2647.4148 | -0.3399 |
| SPY | OOS | B | 3 | 73 | -2769.1602 | -0.3587 |
| SPY | OOS | B | 5 | 73 | -3338.2065 | -0.5030 |
| QQQ | IS | A | 1 | 158 | -1376.6844 | -0.0356 |
| QQQ | IS | A | 2 | 157 | -1572.6780 | -0.0519 |
| QQQ | IS | A | 3 | 157 | -2514.1993 | -0.0993 |
| QQQ | IS | A | 5 | 158 | -3610.5847 | -0.1705 |
| QQQ | IS | B | 1 | 152 | -1629.2724 | -0.0054 |
| QQQ | IS | B | 2 | 153 | -1855.3524 | -0.0396 |
| QQQ | IS | B | 3 | 153 | -2749.6845 | -0.0870 |
| QQQ | IS | B | 5 | 154 | -3603.9960 | -0.1843 |
| QQQ | OOS | A | 1 | 58 | -246.6196 | -0.2469 |
| QQQ | OOS | A | 2 | 58 | -351.4125 | -0.2636 |
| QQQ | OOS | A | 3 | 58 | -461.7239 | -0.2795 |
| QQQ | OOS | A | 5 | 58 | -678.1493 | -0.3094 |
| QQQ | OOS | B | 1 | 56 | -1096.5497 | -0.3729 |
| QQQ | OOS | B | 2 | 56 | -1206.4174 | -0.3876 |
| QQQ | OOS | B | 3 | 57 | -1338.8470 | -0.5837 |
| QQQ | OOS | B | 5 | 58 | -1590.1323 | -0.6279 |

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
