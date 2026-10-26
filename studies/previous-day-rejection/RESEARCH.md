# Hypothèse : rejet des extrêmes de veille

Recherche du26octobre2026 avant nouveau PnL. Hypothèse de retour après fausse cassure d'un niveau déjà connu ; aucune affirmation sur une intervention institutionnelle, un carnet ou des stops réellement observés. Les OHLC ne prouvent pas la cause d'un mouvement.

Sources primaires d'implémentations ouvertes :

- [ikeawesom/xauusd-backtest](https://github.com/ikeawesom/xauusd-backtest), [README](https://github.com/ikeawesom/xauusd-backtest/blob/main/README.md) : formalise dépassement des extrêmes précédents et retour. Univers or, biais et sorties différents ; son win rate annoncé n'est pas transféré à nos ETF et ne constitue pas une validation indépendante.
- [frankabingale1111/smc-backtest](https://github.com/frankabingale1111/smc-backtest) : détection d'une mèche au-delà d'un extrême suivi d'une clôture de retour, couplée à d'autres règles. Sert à identifier une primitive testable ; aucun code tiers exécuté ou installé, aucun résultat tiers importé.
- [baturdenada/gold-sweep-backtester](https://github.com/baturdenada/gold-sweep-backtester) : plusieurs familles de signaux et sorties, plus de paramètres que nécessaire. Source de comparaison de définitions, pas notre protocole financier.

L'ebook repéré sur le domaine de Linda Raschke n'a pas pu être récupéré (404). Il n'est donc pas utilisé comme référence de règles lues ; cette étude ne revendique pas de reproduire la stratégie originale Turtle Soup.

Choix : simple rejet des niveaux RTH de la veille sur bougies5minutes. Contrairement à la recherche déjà archivée, l'entrée demande une réintégration après dépassement du niveau ; aucune compression NR7, aucun gap minimal, aucune bande VWAP/RSI ou cassure de plage d'ouverture. Le filtre d'ouverture à l'intérieur du range distingue la référence d'une stratégie de retournement de gap.

La familiarité de ces motifs, les témoignages et les dépôts ouverts ne prouvent pas leur rentabilité. Les ETF, les dates A/B et d'autres familles ont déjà été explorés dans ce dépôt : biais de sélection de recherche et essais multiples explicitement conservés.

Lecture du code : `TradeSimulation.py` chez ikeawesom passe bien `prevDate` aux fonctions de niveaux et de biais ; aucune accusation de lookahead n'est déduite de leur nom. Ses sorties utilisent les opens successifs et ne reproduisent pas nos SL/TP. Chez frankabingale1111, la roadmap du README laisse encore les vrais SL/TP dans les tâches à faire : l'exemple de performance n'est donc pas une preuve d'exécution conservatrice. Gold Strategy Lab propose de nombreuses combinaisons sur l'échantillon complet ; ce classement ne devient pas notre sélection de paramètres.
