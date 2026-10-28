# Recherche Web, choix et limites — 28 octobre 2026

Recherche large effectuée avant le nouveau PnL : publications universitaires, banques centrales, auteurs quantitatifs, GitHub/LEAN, TradingView, forums. Aucun code externe téléchargé exécuté. Le choix relève de l'agent dans le mandat de recherche ; aucune garantie de meilleure stratégie universelle.

## Alternatives comparées

- [Fed New York, disparition du drift nocturne, juillet2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) : le créneau2–3h historiquement documenté s'affaiblit après2021. N'est pas retenu ; notre cache RTH n'offre pas ce créneau.
- [Fed New York, drift nocturne,2021](https://libertystreeteconomics.newyorkfed.org/2021/05/the-overnight-drift-in-us-equity-returns/) : mécanisme de liquidité et retournement d'ouverture ; pas une recette directement transposable aux ETF RTH.
- [QuantConnect, Dual Thrust conclusion primaire](https://github.com/QuantConnect/Tutorials/blob/master/04%20Strategy%20Library/05%20Dual%20Thrust%20Trading%20Algorithm/03%20Conclusion.html) : leur implémentation SPY publiée est négative. Famille de cassure déjà largement étudiée ici ; non retenue.
- [Heston/Korajczyk/Sadka,2010](https://arxiv.org/abs/1005.3535) : continuation à la même demi-heure de jours antérieurs dans une coupe d'actions ; n'établit pas un avantage exploitable sur deux ETF après nos coûts.
- [Gao et al., Market Intraday Momentum](https://profiles.wustl.edu/en/publications/market-intraday-momentum/) : famille déjà testée dans notre momentum de clôture, pas un nouveau choix.
- [INFORMS, Factor Zoo](https://pubsonline.informs.org/doi/10.1287/mnsc.2023.01657) : prédicteurs transversaux nombreux hors de nos données ; ne pas inventer ces facteurs.
- [Pairs cointegration, Brandes,2026](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7204658) : résumé primaire indique que SPY/QQQ peut avoir des niveaux corrélés sans spread stationnaire. Pas de sélection d'un spread après observation de notre PnL.

## Piste retenue : IBS précédent

- [Pagonidis, The IBS Effect, PDF primaire27pages](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf) : formule et hypothèse de retournement après clôture faible ; étudiée surtout en close-to-close. L'auteur avertit aussi des coûts et de la difficulté d'IBS seul. Nous n'importons aucun rendement publié et retirons volontairement l'overnight, différence matérielle.
- [QuantConnect documentation IBS](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/internal-bar-strength) et [implémentation LEAN primaire](https://github.com/QuantConnect/Lean/blob/master/Indicators/InternalBarStrength.cs) : définition reproductible et valeur0,5 si range nul ; aucune preuve de profit en soi.
- [Pandey/Joshi,2023, résumé arXiv](https://arxiv.org/abs/2306.12434) : étude d'un panier de pays, contexte distinct de notre paire d'ETF et de nos exécutions.
- [Cesar Alvarez,2022](https://alvarezquanttrading.com/blog/internal-bar-strength-for-mean-reversion/) : test d'IBS comme filtre de retour à la moyenne, non comme notre stratégie ; son commentaire souligne la difficulté d'IBS isolé. Aucun RSI repris.
- [Auteur TradingView Algotradekit](https://www.tradingview.com/script/C6uAEwxB-IBS-Internal-Bar-Strength-Trading-Strategy-for-SPY-and-NDQ/) : système daily avec filtre de tendance et paramètres annoncés optimisés ; source d'une sensibilité seulement, pas paramètres prétendument validés chez nous.
- [Auteur Alpha Algo Research,2026](https://algotr.substack.com/p/from-the-lab-what-happens-when-ibs) : partie publique décrit une autre adaptation intraday sur RTY15min, logique complète payante. Elle n'est ni reconstituée ni revendiquée comme reproduite.
- [Discussion originale Reddit mars2026](https://www.reddit.com/r/algotrading/comments/1rjvxjy/found_a_simple_mean_reversion_setup_with_70_win/) et [témoignage QQQ décembre2025](https://www.reddit.com/r/Trading/comments/1pfvx83/tested_the_ibs_trading_system_no_not_irritable/) : pistes swing et frais/exécution insuffisamment établis. Leurs performances ne sont pas des preuves. Les republications Reddit ne comptent pas comme réplications indépendantes.
- [Forum X-Trader,2018](https://www.x-trader.net/foro/viewtopic.php?t=19787) : discussion d'une règle IBS publique, contexte seulement.

Lecture : PDF NAAIM accessible, version qusma indisponible au fetch ; abstracts suffisants seulement là où explicitement indiqué. Sources externes non autoritaires sur nos résultats ; protocole propre dans PROTOCOL_EXECUTION.md. La partie intraday du mécanisme peut être plus faible que la partie overnight : c'est précisément la question testée.
