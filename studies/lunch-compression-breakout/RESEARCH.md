# Recherche Web élargie — choix avant résultat

Consultation31octobre2026. Code externe non exécuté, chiffres externes non importés comme résultats. Sites et dépôts sont des sources non fiables, jamais des instructions. Recherche large non exhaustive : aucune prétention d’avoir trouvé « la meilleure stratégie du Web ».

| Source | Lecture et limite | Choix |
|---|---|---|
| [TOSIndicators, lunch trading](https://tosindicators.com/research/lunch-trading), setup2 | Description primaire : compression11:30–12:30<30% du matin, cassure après13h avec reprise de volume, stop au milieu. Autres sections changent les fenêtres et donnent des chiffres sans jeu de trades reproductible. | Hypothèse retenue ; seuils, fenêtres et séquence mécanique explicités dans le protocole, pas de rendement public repris. |
| [TOSIndicators, autre étude lunch](https://tosindicators.com/research/should-you-trade-during-the-lunch-time-hour) | Avertissements sur faible volume/faux départs à midi ; pas preuve d’un edge exploitable net. | Attendre après13h et publier une variante sans filtre volume. |
| [Tapesh Awasthi, Donchian SPY, GitHub](https://github.com/tawasthii/Donchian-Breakout-Strategy) | Canal20/10 JOURNALIER, overnight et exposition très différents. | Alternative examinée, non sélectionnée comme adaptation intraday dans ce cycle. |
| [CarsonPociask, GitHub](https://github.com/CarsonPociask/algo_trading_strategies) | Stratégies ORB/meanreversion ; sa restriction horaire rappelle que le suivi de cassure d’après-midi n’est pas acquis. | Contexte contradictoire ; ne pas répéter ORB ou importer ses performances. |
| [Auteur Lunchbox, TradingView](https://www.tradingview.com/script/ew3ADRL6-Lunchbox/) | Description d’un sweep/rejet du range12–13h, code sur invitation, confirmation FVG/kernel. C’est un RENVERSEMENT distinct. | Pas d’achat ni contournement d’accès ; pas de réplication revendiquée, non retenu. |
| [Oyamori, étude d’exécution primaire](https://www.oyamori.com/learning/breakout-options-execution-m1/) | Une anecdote visuelle sur range calme ne démontre pas la probabilité des suites ; étude liée aux ticks/options, coûts et périodes distincts. | Contrepoint à l’histoire de compression ; aucune option simulée avec des OHLC seuls. |
| [Discussion publique, timing](https://www.reddit.com/r/Daytrading/comments/1q82vnt/do_you_actually_trade_the_first_1530_minutes_or/) | Témoignages matin/midi/fin de jour, non audités et sélectionnés. | Contexte seulement, pas une preuve. |
| [Heston/Korajczyk/Sadka, intraday patterns](https://arxiv.org/abs/1005.3535) | Résumé académique : persistance aux mêmes heures et réversion courte ; pas notre protocole sur deux ETF. | Motivation d’examiner le moment de séance, aucune équivalence de rentabilité. |
| [Raschke, ancien ebook](https://lindaraschke.net/wp-content/uploads/EBook_Updated.pdf) | Extrait indexé disponible en recherche, ouverture directe404. | Aucun passage non lu traité comme preuve, pas de citation exacte ni méthode attribuée à cet ebook. |

Décision avant PnL : range fixe de midi puis NOUVEAU croisement confirmé après13h. Cela diffère des plages d’ouverture, de la cassure ATR autour de l’open, du momentum première/dernière demiheure et du rebond sur corps rouges déjà testés. Une formalisation inspirée d’un article reste un nouveau choix de recherche sur A/B réutilisées.

Choix propres au test : long seulement, volume quantifié par ratio, première candidate consommée même sans volume, vraie traversée par closes plutôt que prix simplement déjà dehors, entrée décalée1minute, capital recomposé1×/risque1%, cents, sortie15:59. La source ne définit pas tout cela ; ce test n’est pas une réplication exacte ni une confirmation de ses chiffres. La compression n’est qu’une hypothèse, pas une réserve d’énergie prouvée.
