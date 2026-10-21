# ORB QQQ : décision après le backtest

20 octobre 2026. Version de recherche d'origine conservée : commit b9776d0442bbc224e7f6492deb359369367a6070, étude opening-range-5m, principal BOTH/complete_days/stop_first/slip0,01, risque cible1 %, plafond causal1x et capital100000. Aucun réglage du stop, de 10R ou de l'horaire après résultats.

**Décision : candidate à observation prospective, pas validée pour un bot de trading.** QQQ ALL +50,93 % mais CAGR3,89 %, DD minute observé14,23 %. B réutilisée +7,76 %, DD10,45 % ; ablation des trois journées retenues par le diagnostic historique devient −0,94 %. À friction0,03USD/action/côté, ALL −4,01 % ; à0,05, B −1,35 %. Les IC descriptifs B couvrent zéro. SPY n'est pas une candidate convaincante.

Un résultat positif montre que l'idée mérite de ne pas être jetée ; il ne démontre pas un avantage net stable. Les séances manquantes omises, le filtre de séance complète connu après coup et l'open09:35 supposé empêchent d'assimiler cette courbe à celle d'un bot exécutable. La stratégie est l'ORB simplifiée à entrée09:35, sans attente de cassure ultérieure.

## Prochaine étape utile, à configurer séparément

- Conserver code/règles d'origine et journaliser des journées réellement nouvelles à partir du21/10/2026, sans relecture utilisée comme preuve prospective. Définir un traitement de panne/halt/quotes manquantes avant le lancement ; le filtre historique complete_days n'est pas une règle utilisable en direct.
- D'abord20séances pour vérifier timestamps, données, redémarrages, tailles, stop, journal/coûts. Ce jalon vérifie le fonctionnement, pas la rentabilité.
- À60séances et50trades clos, premier bilan descriptif des coûts réels/estimés, erreurs de suivi, concentration et régimes. Ne pas décider sur seul P&L positif de ce petit échantillon ; viser au moins12mois de nouvelles observations pour juger la stabilité.
- Mesurer l'accessibilité de l'open d'entrée, le spread et les fills/slippage avec quotes contemporaines ; comparer les prix extrêmes à une source indépendante avant d'attribuer un avantage.
- Avec le flux SIP gratuit différé, une simulation locale peut tester les règles et les logs, mais pas démontrer les fills en temps réel. IEX produit un univers différent. Ne pas conclure qu'une simulation différée valide un résultat d'exécution paper/réel.

Ce document est une recommandation de validation, **aucune simulation ORB ni automation supplémentaire n'est activée par cet ajout**. Le bot Noise Area QQQ existant poursuit son propre suivi. La nouvelle étude VWAP teste une autre hypothèse et ne sert pas à retoucher ORB.
