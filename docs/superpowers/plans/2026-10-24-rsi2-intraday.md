# Plan RSI(2) intraday

Spec : studies/rsi2-intraday/PROTOCOL_EXECUTION.md. Autorisation utilisateur de choisir une nouvelle piste, tester et publier.

- [x] Lire les simulations QQQ en lecture seule ; conserver un bilan horodaté sans secret.
- [x] Tests contrôlés du RSI/ATR, régime causal, séquences entrée/stop/sortie/EOD, sizing/frais et trous ; implémenter le moteur dédié.
- [x] Réutiliser les acquisitions SIP vérifiées ; figer code, dépendances et72configurations avant PnL ; exécuter A/B/ALL.
- [x] Revue et audit indépendants, rapprochement des transactions et échantillons source.
- [x] Rapport français et figures vérifiées ; bilan honnête des deux bots et pistes historiques ; empreintes, commit/push et vérification distante.

Architecture : rsi2/engine.py pour indicateurs/exécution ; rsi2/data.py pour sources existantes ; scripts/run_study.py pour exécutions immuables ; scripts/report.py pour rapport/figures ; audit/ pour vérifications indépendantes. Pas de bot ni accès aux clés.

Résultat : 72comptes,25tests, audit indépendant PASS ; SPY−5,47%,QQQ−17,18% surALL. Aucun nouveau bot. Les bilans de Noise Area/ORB sont lus sans modifier leurs états. Publication préparée après contrôle des empreintes, puis contrôle du commit distant.
