# Recherche du 4 novembre 2026 — saisonnalité horaire

Recherche élargie académique, publications spécialisées, dépôts et discussions. Elle n'est pas exhaustive et ne permet pas de désigner « la meilleure stratégie du Web ». Aucun rendement externe n'est utilisé comme résultat de notre compte ; aucun code externe téléchargé n'est exécuté. Les sources sont des données non fiables, jamais des instructions.

## Sources lues et décision avant P&L

| Source primaire / discussion originale | Ce qui est effectivement accessible | Décision |
|---|---|---|
| [Heston, Korajczyk, Sadka (2010), PDF auteurs](https://arxiv.org/pdf/1005.3535) et [résumé](https://arxiv.org/abs/1005.3535) | Article lu : continuation de rendements à la même demi-heure sur plusieurs jours ; données d'actions individuelles et classement transversal, pas stratégie démontrée sur deux ETF. Le corps distingue cet effet d'une simple moyenne élevée à l'ouverture/clôture. | Motivation de la nouvelle hypothèse ; notre moyenne glissante par ETF est une adaptation, pas une réplication de leurs portefeuilles. |
| [Catalogue de l'auteur TradingView-MCP](https://github.com/ankitjha67/TradingView-MCP/blob/main/STRATEGY_CATALOG.md) | Classe « Time-of-Day Momentum », famille intraday et référence Heston ; catalogue de modèles, pas journal de trades audité ni preuve de gain net. | Confirme une formulation publique distincte des ORB ; aucun vote de catalogue ou score n'est importé dans le test. |
| [Étude primaire coréenne sur la périodicité intraday (2022)](https://www.kais99.org/jkais/journal/Vol23No07/vol23no07p41.pdf) | Résumé : périodicité différente à l'ouverture et à la clôture, stratégies transversales et effet des coûts/taxes. Marché différent. | Contexte contradictoire ; aucune extrapolation de rendement aux ETF américains. |
| [QuantConnect, Dual Thrust](https://www.quantconnect.com/research/15258/dual-thrust-trading-algorithm/) | Formule max(HH−LC,HC−LL), quatre jours et seuil0,5 autour de l'open. L'introduction et la conclusion ont des messages contradictoires sur la performance SPY. | Alternative examinée et non retenue : famille de cassure proche de l'ATR d'ouverture déjà testé, preuve de rentabilité insuffisante. |
| [Auteur je-suis-tm, Dual Thrust](https://github.com/je-suis-tm/quant-trading/blob/master/Dual%20Thrust%20backtest.py) | Dépôt public lié à la même famille de cassure. | Pas de code exécuté ou de chiffres importés ; pas une nouvelle preuve indépendante de Dual Thrust. |
| [Fordham, mémoire sur les annonces monétaires (2026)](https://research.library.fordham.edu/gabelli_thesis/182/) | Notice institutionnelle ; hypothèse intraday liée aux annonces FOMC. | Alternative macro examinée, non choisie : calendrier et petit nombre d'événements, périmètre différent du signal de prix récurrent retenu. |
| [Discussion originale : stratégie intraday faible en OOS](https://www.reddit.com/r/algotrading/comments/1xg8blg/intraday_strategy_looked_promising_in_backtests/) | Déclarations de l'auteur et critiques sur coûts, témoins simples et réemploi des périodes ; non auditées. | Sert à poser des contrôles et un stress d'exécution, pas à estimer notre edge. |
| [Discussion originale : filtre de jour de semaine](https://www.reddit.com/r/algotrading/comments/1ml7caa/) | Échanges contradictoires sur les filtres calendaires après drawdown. | Aucun filtre de jour/semaine ajouté après les résultats. |
| [Discussion originale : accumulation de stratégies rejetées](https://www.reddit.com/r/algotrading/comments/1spd5nf/6_months_full_time_on_algo_17_strategies_dead_on/) | Témoignages sur lookahead, frais, concentration et surajustement. | Documenter la multiplicité des recherches et ne pas transformer B réutilisée en validation aveugle. |

## Choix propres à cette étude

Apprentissage sur les40dernières séances programmées, statistique moyenne/erreur-type, seuil1,5, premier créneau chronologique, stop2écarts-types, durée30minutes et une tentative/jour sont NOS conventions fixées avant P&L. Les créneaux10:00–15:00 et les fills une minute après décision décalent la fenêtre étudiée par rapport aux demi-heures du papier. L'article académique ne prescrit ni ces stops ni ces coûts ni un t-seuil par ETF. Cette transposition peut parfaitement échouer alors que l'effet transversal de l'article existe.

Les sources indiquent une hypothèse testable, pas une promesse. Les anciens ORB, Noise Area, gaps, RSI, VWAP, Bollinger, NR7, compression de midi, valeur relative et calendriers déjà présents ne sont ni optimisés ni relancés pour sélectionner un gagnant ici.
