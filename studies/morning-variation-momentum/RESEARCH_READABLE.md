# Transcription lisible de la recherche gelée

Correction d’encodage uniquement. L’original RESEARCH.md, conservé sans changement, fait autorité dans le gel avant PnL. Aucun choix de stratégie ni chiffre ajouté par cette transcription.

# Recherche Web et choix — 31 octobre 2026

Hypothèse nouvelle ici : qualité du parcours matinal relativement à sa variation réalisée, puis détention de la suite de séance. Ni paire relative ni nouveau réglage du calendrier. Recherche large ne certifie pas une meilleure stratégie universelle ; aucune performance externe copiée dans nos résultats.

- [SharpeTwo, recherche primaire2026](https://sharpetwo.com/research/spys-quiet-rally-what-happens-after-a-big-move-with-little-volatility) : matinée normalisée, seuil empirique passé et entrée décalée. Sourcequote-midpoints2min, panierETF et sorties différentes ; certains résultats gross et sous-périodes fragiles. Nous utilisons SPY/QQQ séparés, tradebarsSIP et tous nos coûts. Pas de données de flux pour attribuer une cause institutionnelle. Le ratio n'est pas une statistique de Sharpe ou une prévision normale.
- [Gao et al., primaire2018](https://profiles.wustl.edu/en/publications/market-intraday-momentum/) : première demi-heure/prédiction de dernière demi-heure, famille déjà étudiée dans closing-momentum. Le nouveau test porte sur l'état à10:30 et la détention de l'après-midi ; pas réplication du papier ni de ses résultats.
- [QuantSeeker2026, introduction publique](https://www.quantseeker.com/p/revisiting-intraday-momentum) : question de robustesse/régimes ; règles détaillées payantes non lues ni reconstruites.
- [StockCharts TTM Squeeze, documentation primaire](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze) : compression de bandes et momentum, alternative examinée. Différences de formule Keltner selon plateformes ; famille cassure proche des études déjà nombreuses, non retenue cette fois.
- [AndrBene, README GitHub primaire](https://github.com/AndrBene/Volatility-Breakouts-Trading-ETFs/blob/master/readme.md) : stratégieATR de cassure ETF, capitalisation et pipeline de filtres à auditer ; code non exécuté, aucune clé demandée. Alternative non sélectionnée, pas résultat certifié importé.
- [Forum sur les lookbacks intraday](https://www.reddit.com/r/algotrading/comments/1df4c1o/) : repéré dans la recherche ; ouverture complète refusée par cache miss, contexte de choix d'horizon et bruit, pas preuve de rendement. Notre minimum252 et quantile sont fixés avant PnL, non optimisés sur ce témoignage.
- [Variance réalisée, document primaire d'auteurs](https://public.econ.duke.edu/~boller/Published_Papers/rfs_18.pdf) : somme des retours intraday au carré ; ne démontre pas cette règle de trading. Les tradebars ne remplacent pas les quotes de la source.

Les pistes déjà testées (ORB/retest/volume, VWAP, RSI, IBS, EMA, gaps, NR7, fin de mois, mardi, spread) restent archivées. Les contrôles raw_momentum et always_long testeront les comparaisons de rendement, sans affirmer une expérience causale isolée. L’absence de nuit détenue, les fills et le risque sans stop sont décrits précisément dans le protocole, sans prétendre reproduire un portefeuille164ETF brut.
