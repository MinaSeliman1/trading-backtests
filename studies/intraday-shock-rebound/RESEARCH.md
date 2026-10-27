# Recherche élargie — rebond après choc intraday

26octobre2026, avant premier PnL de cette formalisation. L'utilisateur élargit explicitement la recherche au-delà des forums/GitHub, à tout le Web. Comparaison qualitative de familles, sans lancer des milliers de paramètres sur notre historique. Aucune promesse d'avoir identifié la meilleure stratégie possible.

## Sources et sélection

| Source consultée | Ce qu'elle apporte ; limite |
| --- | --- |
| [Vlasiuk/Smirnov2025, Push-response anomalies](https://arxiv.org/html/2511.06177v1) | Texte méthodologique consulté : SPY NBBO, temps événementiel, réponses conditionnelles asymétriques après fortes baisses. Normalisation descriptive sur leur échantillon ; ce n'est pas un signal causal prêt à trader. Notre moyenne/écart-type sont exclusivement passés, fenêtre30minutes et barres5minutes propres : adaptation, pas réplication de leurs résultats/ticks. |
| [Zawadowski/Andor/Kertesz2004](https://arxiv.org/abs/cond-mat/0406696) | Abstract lu : retours après mouvements intraday extrêmes sur actions, mais élargissement du spread susceptible d'absorber le profit. Instruments/période différents des ETF actuels ; motive les stress de friction, pas un rendement importé. |
| [Rif/Utz2021, Short-term stock price reversals](https://www.sciencedirect.com/science/article/pii/S1062976921000922) | Abstract indexé lu : chutes extrêmes minute des constituants Nasdaq100 et rebond minute suivante. Page directe403 ; texte intégral non lu. Notre horizon plus lent ne reproduit pas cette opportunité HFT. |
| [Brogaard/Han/Kim, Intraday Price Pressures](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4731947) | Abstract indexé consulté, page directe403 : réversion des résidus30minutes sur actions du S&P500, pas une preuve sur deux ETF ou une règle univariée. |
| [Leung/Li2015, coûts et stop](https://arxiv.org/abs/1411.5062) | Abstract lu : entrée/sortie et coûts sous hypothèse OU. Ne démontre ni OU ni rentabilité de SPY/QQQ ; souligne que stop/TP/coûts font partie du modèle. |
| [Martin/Schöneborn, Mean Reversion Pays, but Costs](https://arxiv.org/abs/1103.4934) | Abstract lu : les frictions changent les décisions optimales. Pas de résultat ETF actuel repris. |
| [Chen/Alexiou2025, ETF pairs](https://link.springer.com/article/10.1057/s41260-025-00416-0) | Article accessible : corrélation et cointégration stable diffèrent, fenêtres de validité limitées. Paires à écarter comme évidence automatique de retour à la moyenne. |
| [ExeQution, investigation intraday](https://exequtionanalytics.com/wp-content/uploads/2024/12/Pairs-Trading-An-Intraday-Investigation.pdf) | Rapport lu, actions TOPIX100 et choix de paires à5minutes. Données japonaises/tick ; coûts et validité de cointégration restent des limites reconnues, pas validation QQQ/SPY. |
| [QuantConnect, Pairs Trading US ETFs](https://www.quantconnect.com/league/19265/pairs-trading-us-etfs/) | Thèse publique d'une paire QQQ/SPY à moyennes mobiles, sans preuve prospective que nous pourrions reprendre. |
| [clockkaya/kalman-filter](https://github.com/clockkaya/kalman-filter) et [strategy.py](https://github.com/clockkaya/kalman-filter/blob/master/strategy.py) | README et page de code consultés : estimation dynamique et seuils résiduels, état conservé sur disque. Aucune validation indépendante de sa qualification «production-ready», aucun code tiers exécuté ni connexion FTS. |
| [Pratikbhanuse/SPY_QQQ-pair-trading](https://github.com/Pratikbhanuse/SPY_QQQ-pair-trading) | README et page du script Quantopian consultés. Dépendances historiques, corrélation ne prouvant pas une relation exploitable actuelle. |
| [Lead-Lag-Alpha-Research](https://github.com/KianTakizawa-06/Lead-Lag-Alpha-Research) | README lu : historique7jours, normalisation full-sample et sélection de lag, fragilité test. Rejeter comme preuve à long terme ; aucun chiffre externe promu. |
| [Forum, frais de paires](https://www.reddit.com/r/quant/comments/15pcu35/etf_transaction_costs/) | Discussion rappelant les deux jambes ; pas journal de fills auditable. |
| [Forum, capitulation intraday](https://www.reddit.com/r/algotrading/comments/1sm6y5g/backtested_intraday_mean_reversion/) | Règles de filtre incomplètes et résultats futures déclaratifs. Ne pouvons pas reproduire ses conditions cachées ni extrapoler ces résultats aux ETF. |
| [Concretum, Improving ORB,8juillet2026](https://concretumgroup.substack.com/p/improving-the-opening-range-breakout) | Introduction lue : frais absorbant l'ORB simple et améliorations annoncées. Corps payant, règles exactes non accessibles ; pas d'achat, contournement ou invention d'une réplication. |
| [QuantConnect/Gao, ETF momentum](https://www.quantconnect.com/research/15348/intraday-etf-momentum/) | Exemple ouvert consulté, mais momentum de clôture déjà étudié dans ce dépôt ; ne pas le rebaptiser nouvelle piste. |
| [GitHub, mean reversion SPY](https://github.com/BozcaFevzi/Systematic-Trading-Intraday-Mean-Reversion-on-SPY/blob/main/README.md) | README : combinaison VWAP/Bollinger/RSI. Familles déjà abandonnées ou étudiées ; non retenue. |

## Choix avant performance

Retenir la réversion d'un choc baissier sur chaque ETF séparément, après confirmation de rebond. Motivation empirique explicite, données OHLC disponibles et coûts testables à fréquence plus lente ; pas de RSI, VWAP, calendrier ou réplication de la paire. Autres familles considérées : paires/lead-lag (stabilité, deux jambes, vitesse), ORB amélioré (proximité des études actives et règles payantes), réversion overnight/IBS (ne respecte pas le périmètre day trading), stratégies options/GEX (archives historiques nécessaires absentes). On ne prétend pas avoir cherché littéralement toutes les pages du Web ni connaître une stratégie universellement meilleure.

Fenêtre30minutes normalisée par20séances passées à même heure, seuil−2sigma, confirmation5minutes, entrée minute suivante, stop mèche et TP2R/EOD. Ces choix précis sont les nôtres, fixés avant PnL. Prix SIP minute plutôt que NBBO/temps événementiel : le test vérifie cette adaptation seulement. Les ETF et périodes sont déjà explorés, y compris B ; aucun nouvel OOS aveugle.
