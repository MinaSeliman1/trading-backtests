# Piste : retour après un grand gap d'ouverture

**Statut au 20 octobre 2026 : hypothèse documentée et comptage de faisabilité seulement. Aucun backtest de rentabilité, aucune transaction du bot.**

Après un grand écart entre la clôture précédente et l'ouverture, tester une position opposée au gap pendant la première demi-heure. Cette logique de retour à la moyenne explore un comportement différent de la poursuite de mouvement de Noise Area. Sa complémentarité financière reste à mesurer.

## Source et adaptation causale

Le [code publié par Concretum Group](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/) contient une composante de gap reversal : seuil absolu de 2 %, sens opposé au gap, sortie après la première demi-heure. La source la combine avec la stratégie de momentum ; une performance de leur combinaison ne prouve pas celle du reversal isolé.

La source suppose une entrée au prix d'ouverture qui sert aussi au calcul du signal. Notre protocole attend la fin de la minute 09:30 puis entre à **09:31**, et sort à **10:00**. C'est une adaptation explicite pour respecter l'information disponible, pas une reproduction exacte de l'entrée originale.

## Protocole fixé avant calcul du P&L

1. Instruments : SPY et QQQ évalués séparément, données Alpaca SIP raw, heures régulières de New York.
2. Gap : `open_09:30 / (close_RTH_précédent - dividende_ex_date) - 1`. Ne pas traiter le détachement du dividende comme un signal.
3. Condition unique : `abs(gap) > 0,02`. Acheter après un gap négatif ; vendre à découvert après un gap positif.
4. Connaître le signal à 09:31 ; entrer à l'open 09:31 ; sortir à l'open 10:00. Un seul trade par séance, sans maintien overnight. Aucune entrée si les minutes nécessaires ou la clôture précédente ne sont pas valides.
5. Capital initial 100 000 USD ; exposition principale 1x, actions entières, capital recomposé. Aucun levier 4x dans la première comparaison.
6. Commission 0,0035 USD/action/côté, minimum 0,35 USD/ordre, emprunt SHORT 1 %/360 minimum un jour. Scénarios de friction adverse 0,01 / 0,02 / 0,03 / 0,05 USD/action/côté. Ce sont des hypothèses à confronter aux coûts observés.
7. Première version sans objectif de gain ni stop ajouté après observation. Mesurer la perte adverse intratrade, les pertes extrêmes, jours de suspension et ouvertures perturbées ; ne pas considérer un open comme exécutable pendant un halt.
8. Aucun balayage de seuil ou d'horaire avant ce test fixé. Une modification ultérieure sera une nouvelle hypothèse et ne bénéficiera pas d'un nouveau label hors échantillon sur le même historique.

## Faisabilité réellement calculée

Le script [count_events.py](scripts/count_events.py) a seulement compté les gaps de plus de 2 %, avec les données préparées déjà utilisées dans Noise Area. Les empreintes sources et dates sont dans [la preuve JSON](evidence/feasibility_2026-10-20.json).

| Instrument | 2016–16/10/2026 : événements / séances utilisables | A : jusqu'au 30/04/2024 | B : 01/05/2024–16/10/2026 |
|---|---:|---:|---:|
| SPY | 42 / 2 696 | 31 / 2 078 | 11 / 618 |
| QQQ | 77 / 2 700 | 59 / 2 082 | 18 / 618 |

Ces nombres ne sont ni des trades exécutés, ni des résultats de stratégie. Le filtre de journées complètes de l'étude exclut notamment plusieurs séances avec halts de mars 2020 ; les comptes sont conditionnels à cet univers. Le prochain backtest devra auditer explicitement ces séances et distinguer exclusion pour qualité des données et impossibilité d'exécuter.

Le faible nombre d'événements, surtout en B, est une limite forte de puissance statistique. Ne pas abaisser le seuil après ce constat uniquement pour obtenir davantage de trades. Aucun rendement, Sharpe ou taux de réussite n'a été calculé.

## Validation à réaliser

Les périodes A et B ci-dessus servent de comparaison chronologique exploratoire. L'historique a déjà été étudié pour d'autres stratégies et le comptage vient d'être consulté : **B ne sera pas présenté comme un nouveau test aveugle**. Le protocole est daté du 20 octobre ; une observation prospective intacte peut commencer le 21 octobre 2026.

Pour chaque instrument et coût, publier trades détaillés, P&L net, drawdown, distribution des pertes, exposition, nombre de trades par année et par sens, concentration des gains et incertitude des moyennes. Comparer à l'absence de position et à un trade dans le sens du gap sur les mêmes créneaux. Mesurer ensuite la corrélation des P&L quotidiens avec Noise Area, sans supposer de diversification.

Les intervalles devront respecter la dépendance des événements par crise et année. Un faible échantillon positif sera une piste à suivre, pas une preuve suffisante pour lancer un bot. La stratégie n'est pas intégrée au bot QQQ livré.

## Reproduire uniquement le comptage

Avec les dépendances et les pickles locaux de l'étude Noise Area :

```powershell
python studies/opening-gap-reversal/scripts/count_events.py
```

Les historiques minute et pickles restent locaux et ignorés par Git. Ne charger que des pickles de confiance.
