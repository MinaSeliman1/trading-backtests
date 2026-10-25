# RSI(2) intraday — protocole fixé avant performances

Choix de recherche du 24 octobre 2026, à la demande de Mina : nouvelle piste QQQ/SPY, mêmes coûts, code/résultats/rapport publiés dans trading-backtests. Aucun nouveau bot ni modification des simulations existantes. Nowick est abandonnée comme piste de bot ; ses preuves archivées sont conservées.

## Hypothèse et alternatives

RSI(2) de retour à la moyenne, inspiré des écrits de Larry Connors sur les replis et les sorties dynamiques. Les textes sources portent sur des stratégies journalières ; la version 5 minutes, son stop et sa liquidation RTH ci-dessous sont **notre adaptation exploratoire**, pas une reproduction ou une rentabilité attribuée à Connors. Une fausse cassure du range de veille a été envisagée, mais resterait proche des études de cassure/gap déjà menées. La poursuite du VWAP a aussi été écartée car déjà testée. RSI apporte ici un signal différent ; aucun résultat de cette nouvelle formalisation n’a été consulté.

Sources primaires : [Connors : sorties RSI(2) 70/30](https://tradingmarkets.com/recent/dynamic_exits_how_to_properly_exit_a_trade-641067), [TradingMarkets : replis RSI(2) et tendance 200 jours](https://tradingmarkets.com/recent/buying_weakness_and_selling_strength-684961), [TradeStation : calcul Wilder RSI](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/function/rsi_function_.htm). Leurs performances commerciales ne servent pas de preuve dans notre rapport.

## Données et périodes

Même historique minute Alpaca SIP local et vérifié que NR7/ORB : 4 janvier 2016–16 octobre 2026. A = début–30 avril 2024, B = 1er mai 2024–16 octobre 2026. B déjà utilisée dans plusieurs recherches : validation chronologique réutilisée, aucun nouveau OOS aveugle. Comptes indépendants 100000 USD. Sources, corporate actions et dépendances hashées avant les boucles financières ; aucun téléchargement ni clé requis.

Bougies 5 minutes depuis l’ouverture NYSE, 5 minutes OHLCV valides exigées. Indicateurs intraday réinitialisés à chaque séance. RSI Wilder(2) initialisé par la moyenne des deux premières variations de closes, puis récurrence alpha1/2 ; plat gain=perte=0 =>50, perte0/gain>0=>100, gain0/perte>0=>0. ATR Wilder(14), premier true range = H−L, suivants max(H−L,|H−Cprécédent|,|L−Cprécédent|) ; moyenne initiale des14TR, puis alpha1/14. Toute barre incomplète rend la suite du signal intraday inconnue, sans interpolation.

Régime journalier connu avant la séance : dernier close RTH minute de la veille contre moyenne des200closes RTH précédents, veille incluse. Les200observations correspondent aux200séances immédiatement précédentes, sans substituer une séance plus ancienne si un close manque. Seul ce close valide est requis pour ce filtre passé, pas la complétude des390minutes antérieures. Correction cash additive : close + dividendes cumulés jusqu’à sa date ; comparaison invariante à une translation future commune, pas de prix ajusté par des dividendes futurs. Ce proxy n’est pas un rendement total composé. Aucun split retourné par la source existante ; complétude fournisseur non garantie. Chauffe200séances en début d’historique, explicitement sans trade.

## Référence

LONG uniquement : régime haussier strict et premier close5m avec RSI2<5, ATR14 fini et positif. Nouvelle entrée à l’open1m suivant ce close, seulement entre10:00incluse et15:00exclue New York, et au plus tard avant la dernière minute RTH. La chauffe ATR repousse de fait le premier signal au14e close5m (10:40 pour une séance normale). Une transaction maximum par séance, aucune pyramide.

SL figé au signal = closeSignal − 2ATR14, arrondi vers le bas au centime ; SHORT symétrique vers le haut. Taille entière floor(min(capital/closeSignal,1%capital/distanceCloseSignalStop)), décidée avant le futur open. Un gap peut dépasser le risque1%/plafond1x réalisés. Un open au-delà du stop n’annule pas rétroactivement le trade : aller-retour immédiat avec frais.

Sortie : stop actif dès la minute d’entrée, gap défavorable à l’open ; sinon stop touché au niveau. Après un close5m RSI2>70, sortie au prochain open1m ; SHORT RSI2<30. Stop à l’open prioritaire en cas de simultanéité avec sortie programmée (même prix open). Dernier open RTH15:59/12:59 pour toute position restante. Aucun TP fixe, break-even, financement overnight ou position après séance. Stops intraminute contrôlés avant toute décision de sortie5m. Aucune clôture post-sortie utilisée comme marque/MAE/MFE.

## Frais et couverture

Commission0,0035USD/action/côté, minimum0,35/côté ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360, minimum un jour, identiques aux études ETF précédentes. Stress0,02/0,03/0,05. Hypothèses de recherche, pas promesse du barème ou des fills Alpaca ; frais réglementaires variables non séparés. Prix de trades minute, pas bid/ask ni file d’attente reconstitués.

Principal complete_days : journées courantes incomplètes exclues après coup ; ce filtre n’est pas utilisable prospectivement et rend le compte conditionnel. Variante resolved_prefix sans ce filtre futur : trou avant décision => signal inconnu ; trou actif => trade entier non résolu omis des performances conditionnelles, intention et coûts d’entrée connus exportés. Aucune interpolation, aucun zéro assimilé à du cash observé. Une absence de régime éligible connue avant séance peut être classée sans trade sans données courantes. Ne pas affirmer qu’un prefix prouve la couverture de toutes les journées exclues.

## 72 exécutions préfixées

2instruments ×3périodes ×12configurations : référence LONG avec4frictions ; BOTH ; SHORT seul ; LONG sans régime ; RSIentrée10 ; SL1ATR ; SL3ATR ; sortieRSI80 ; resolved_prefix. Les variantes conservent autrement la référence. BOTH ajoute SHORT lorsque régime baissier et RSI2>95 (ou100−seuilentrée). Les modes cherchent leur premier signal directionnel éligible. Pas de choix après résultats.

Mesurer net/coûts/PF/win rate, drawdowns de clôtures minute/événements et quotidiens, exposition, séries de pertes, concentration top3jours et2020, années/mois, bootstrap descriptif blocs5/20jours et années (3000tirages, seed20261024). Courbes conditionnelles et données manquantes clairement identifiées. Comparer surtout A/B et les coûts, pas sélectionner une variante gagnante. Audit indépendant des signaux/sizing/fills/comptes, échantillons des acquisitions originales, tests contrôlés puis publication vérifiée.
