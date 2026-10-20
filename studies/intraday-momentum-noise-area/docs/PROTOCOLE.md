# Protocole Noise Area — fixé avant le premier P&L

Date : 19 octobre 2026. Spécification utilisateur : `../MISSION.md`. Objectif : mesurer le signal après frais, sans optimiser sur la période récente. Étude indépendante de First Candle FVG ; ses performances antérieures ne constituent pas des résultats Noise Area.

## Sources vérifiées et différences

Papier : [SFI 24-97, copie officielle](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf). Première version datée du 10 mai 2024 ; SSRN indique une mise en ligne le 14 mai 2024. Le PDF accessible est révisé au 22 septembre 2025. L'ancienne version n'a pas été obtenue séparément ; cette limitation interdit de qualifier toute la période B de test prospectif de cette révision.

Code des auteurs : [Python](https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/). Le tutoriel Alpaca ajoute un portefeuille de mean reversion : il est exclu de notre stratégie momentum.

| Sujet | Résumé utilisateur | Source vérifiée / choix appliqué |
|---|---|---|
| Publication | Période B dès le 1er mai 2024 | Garder B demandée ; ajouter C dès le 15 mai 2024 et D dès le 23 septembre 2025, après la révision consultée |
| Entrée | Dépassement de bande | Code des auteurs : dépassement de bande **et** VWAP dans le même sens ; filtre appliqué |
| Gap ex-dividende | Clôture précédente brute | Code : soustraire le dividende du jour à la clôture précédente pour la référence des bandes ; les OHLC minute restent bruts |
| Quantité | Arrondi inférieur | Formule du papier : floor ; code de tutoriel : round. Suivre le papier |
| Volatilité | 14 rendements précédents, veille incluse | Formule du papier suivie, écart-type ddof=1 ; le tutoriel exclut la veille par sa tranche `d-15:d-1` |
| Historique minute | 14 observations passées | 14 observations complètes exigées ; le tutoriel en tolère 13 au démarrage |
| Retournement | À vérifier | À une décision, clôturer l'ancienne direction puis ouvrir la direction opposée si son signal est actif ; deux commissions par ordre de retournement complet |
| Prix d'exécution | Close vs prochain open | Comparaison explicite ; le décalage d'exposition du tutoriel correspond à une détention close-à-close, pas à une garantie d'exécution au prochain open |
| Slippage | 0,001 USD/action/côté | Papier : oui ; tutoriel affiché sans ligne de slippage distincte. Appliquer le coût du papier dans les deux conventions |

## Données et causalité

- SPY principal ; QQQ avec exactement les mêmes paramètres, volatilité de QQQ pour son propre dimensionnement. Comptes séparés de 100 000 USD.
- Réutiliser les CSV Alpaca SIP raw 2023–2026 en vérifiant leurs hashes ; demander les extensions 2016–2022 et 21 septembre–16 octobre 2026. La période réelle sera déterminée par les acquisitions réussies, sans inventer l'historique manquant.
- Calendrier XNYS, America/New_York, dates réelles de clôture, barres horodatées au début de minute. Doublons identiques retirés ; doublons contradictoires, OHLCV invalides ou minutes manquantes excluent la séance entière.
- Zone de bruit : moyenne des 14 dernières observations de séances complètes disponibles à la même minute ; jours écourtés contribuent avant leur clôture, puis sont absents de l'historique des minutes ultérieures. Ces dernières utilisent donc 14 observations sur plus de 14 séances calendaires. Les séances exclues n'alimentent pas cet historique. Aucun remplissage.
- Volatilité : les 14 rendements close-à-close d'une séance NYSE terminée, ddof=1, tous passés ; ne pas calculer un rendement de plusieurs séances comme un rendement journalier après une clôture manquante. Historique insuffisant : aucune position.
- Les dividendes servent à corriger le gap et au benchmark de rendement total ; aucune réécriture des OHLC intraday. Disponibilité historique de l'annonce non auditée ; la date ex-dividende est supposée connue avant l'ouverture.

## Simulation principale

- Lookback 14, décisions toutes les 30 minutes écoulées depuis 09:30 : première à 10:00, dernière strictement avant la clôture XNYS. Décision au close de la minute terminée ; VWAP HLC3 cumulé jusqu'à cette minute, aucune donnée ultérieure.
- Entrée LONG : prix > UB et VWAP ; SHORT : prix < LB et VWAP. Maintien LONG si prix >= max(UB,VWAP), SHORT si prix <= min(LB,VWAP). Égalité n'est pas un franchissement ; sortie seulement sur franchissement strict. Sortie puis éventuel retournement à la même décision.
- Quantité fixée à l'ouverture : floor(capital de la veille × min(plafond,0,02/volatilité) / prix d'ouverture). Plafonds 4 et 1. Même quantité toute la séance, sans redimensionnement après un trade. Cible au prix d'ouverture ; l'exposition effective peut varier avec le cours et les pertes. Ni liquidation de marge intraday ni garantie d'exécution réelle.
- Close de décision ou open suivant, même signaux. Aucune entrée à la clôture. Fermeture obligatoire à l'open de la dernière minute (15:59/12:59) dans **les deux** conventions pour isoler l'effet d'exécution aux décisions ; prix officiel MOC non disponible. Pas de position overnight.
- Commissions fixes 0,0035/action/côté, minimum 0,35/ordre. Slippage adverse exact, fractions de cent autorisées : 0,001 puis 0,01/0,02/0,03/0,05. Ces montants représentent les frictions de prix simulées, sans autre spread ajouté. Emprunt SHORT disponible supposé, 1 % annuel, au moins un jour/360 par trade ; sensibilité 0 % et 3 %. Pas d'intérêt sur les liquidités ni de frais de financement intraday distincts.

## Scénarios et statistiques

- A jusqu'au 30 avril 2024 ; B dès le 1er mai ; C et D ci-dessus. Les périodes sont autonomes : capital réinitialisé, indicateurs réchauffés uniquement avec le passé. A/B/C/D se recouvrent en partie et ne sont pas additionnables.
- Comparer 2 instruments × 2 exécutions × 2 plafonds × 5 coûts pour A et B. C et D : paramètres principaux, deux exécutions et deux plafonds. Sensibilités de B : lookbacks 10/20, décisions 15/60 minutes, stop bande seule/VWAP seul, chacune modifiée isolément ; paramètres non sélectionnés. Fenêtre de volatilité de dimensionnement reste 14.
- Walk-forward B par trimestres civils, règles fixes, historique des indicateurs antérieur à chaque bloc, capital autonome ; blocs descriptifs, pas optimisation ni validation indépendante du même B.
- Benchmarks : buy & hold de chaque ETF et SPY sur les mêmes dates ; rendements de prix et de rendement total si dividendes disponibles, fractions d'actions et réinvestissement théoriques, frais de passif non simulés. Toujours LONG et 1 000 directions aléatoires aux **mêmes** entrées/sorties que chaque scénario principal B : mêmes règles de coûts, quantité recalculée sur le capital simulé du benchmark. Conditionnement sur les temps de la stratégie : contrôle descriptif, pas preuve causale de signal.
- Bootstrap circulaire de blocs de 5 séances, 5 000 réplications, seed 20261019 : moyenne quotidienne, Sharpe (taux sans risque 0) et différence de Sharpe avec buy & hold. Sortino : déviation des rendements négatifs rapportée à toutes les séances. Année boursière 252 séances ; CAGR sur durée calendaire ; drawdown aux closes minute et exécutions, non tick par tick.
- Seuil de coûts : point mort du P&L B obtenu par bissection en rejouant les mêmes signaux et la composition, commissions et emprunt inchangés ; pas d'extrapolation déclarée comme scénario effectivement calculé.
- Terciles de volatilité : seuils estimés sur A seulement puis gelés pour B ; pas de seuils appris sur B. VIX d'ouverture CBOE si disponible. Années/mois partiels marqués comme tels. Contribution des dix meilleurs jours et retrait descriptif de ces dix jours.

## Plan d'implémentation et validation

1. `noise_area/data.py` : lecture, provenance et qualité ; tests DST, demi-séances, doublons, gaps et ex-dividendes.
2. `noise_area/features.py` : calculs causaux et décision ; tests de perturbation du futur, valeurs manuelles, premières décisions et maintien/sortie.
3. `noise_area/engine.py` : carnet des ordres, coûts, trades et marques ; tests de prix d'exécution, retournements, coûts, dimensionnement connu et fin de séance.
4. `noise_area/statistics.py` et `scripts/run_study.py` : scénarios, benchmarks, bootstrap et exports ; contrôler séparément les agrégats et les périodes.
5. `scripts/audit_study.py` : recalcul indépendant sur les CSV bruts d'au moins dix trades sélectionnés chronologiquement ; rapprochement des trades et du P&L quotidiens. Conserver les calculs manuels détaillés.
6. Figures, rapport critique répondant aux dix questions, Pine v6 et statut explicite de sa compilation réelle. Lire les figures produites. Tests complets avant toute conclusion.

Les résultats restent locaux dans cette branche ; l'ajout au GitHub viendra ensuite conformément à la demande. Aucun paramètre principal ne sera modifié en fonction de la performance.
