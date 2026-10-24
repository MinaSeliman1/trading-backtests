# Nowick Compensation — Implementation Plan

**Goal:** Livrer une stratégie Pine v6 et un protocole honnête pour trois paires FX.
**Architecture:** Ordres natifs TradingView, audit des ambiguïtés séparé, devise de cotation et variante JPY générée. Oracle Python de scénarios contrôlés uniquement.
**Spec:** studies/nowick-compensation/MISSION.md ; demande détaillée de Mina.

- [x] Écrire les tests contrôlés des pips, pivots confirmés, horaires DST/news, TTL, sizing, coûts, Wilson, pertes et stress ; observer leur échec avant implémentation. 27tests passent.
- [x] Implémenter l'oracle, puis le Pine ; aucun ordre réel ni modification des deux bots QQQ.
- [x] Tenter TradingView et conserver le statut exact : interface réduite/interrompue, code jamais collé ni compilé. Statut Pine non confirmé, protocole100trades non exécuté.
- [x] Revue indépendante du code, corriger les défauts, refaire les vérifications concernées. Aucun P1/P2 confirmé restant dans le périmètre statique.
- [x] Instructions débutant, seuil de rentabilité, limites et matrice de tests ; registre mis à jour. Publication après vérifications locales et contrôle du diff.

Non acquis : compilation/runtime Pine et backtest marché FX. La livraison du code ne clôt pas ces étapes de validation.

Points de revue : annulation front-run intrabar, expiration exacte 9 bougies, dernière entrée avant08h, news datées, JPY/commission/pointvalue, profit net sans double commission, entrée et sortie dans la même bougie, confirmation HTF/pivots, absence de résultats inventés.
