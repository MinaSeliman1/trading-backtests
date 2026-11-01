# ATR opening breakout implementation plan

> Required workflow: executing-plans inline, TDD and requesting-code-review before publication.

**Goal:** nouvelle piste SPY/QQQ, mêmes frais, backtest/publication autorisés, bots inchangés.
**Architecture:** atr/data chargeur ; atr/engine historiqueTR/gaps et scan5min causal, exécutionstop/EOD ; oracle scalaire distinct ; matrice84 gelée ; rapport et manifest.
**Tech stack:** Python3.14,numpy,pandas,pytest,matplotlib,XNYS.
**Spec:** studies/atr-opening-breakout/PROTOCOL_EXECUTION.md.

Ruling : mandat autonome répété, pas de nouvelle question de conception ; branche dédiée dans checkout propre, aucun bot/worktree déplacé. Version arithmétique et LONG confirmée explicitement différente des règles externes.

- [x] Lire sources et définir règles/14variantes/critères avant PnL.
- [x] Tests rouges puis moteur et verts ; TR/gaps/temps/sizing/coûts/stop/EOD.
- [x] Oracle/runner, revue préalable, gelSHA et84comptes.
- [x] Rejeu et statistiques/IC indépendants.
- [x] Rapport et quatre figures ; préparation de la revue finale, du manifest et de la publication protégée.

## Ledger

37tests rouges initiaux ; fixtures de gaps corrigées pour OHLC cohérents, sans modification stratégique.40tests verts avec matrice et contrôles scalaires. Revue pré-PnL sans bloqueur ; dépendances transitives vérifiées.84comptes calculés après gelSHA, aucune règle financière changée après PnL.

Oracle8509072contrôles,63582trades recouvrants,864contrôles agrégés et6comptes bootstrap. Source/calendrier/hashes vérifiés. Scripts de présentation ajoutés ensuite selon protocole. Résultat : candidat historique, sans nouveau bot automatique ; SPY B à coûts doublés négatif conservé visiblement, critère original de coûts A inchangé.

Revue finale :40tests relancés,10fichiers gelés/15dépendances/2protocoles/463exports vérifiés,4figures et24liens validés. Réserves B visibles, statut candidat historique uniquement. Levier affiché4décimales et reproduction dans copie protégée corrigés, puis confirmés sans point restant. Aucune règle financière modifiée après PnL.
