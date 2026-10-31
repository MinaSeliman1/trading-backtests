# Validation

- 39 tests passent : agrégation et bandes population, reset quotidien, premier signal causal, fenêtre, stop/TP, gap d’entrée sans redimensionnement, coûts minimums, ambiguïtés, couverture et cas d’arrondi au cent.
- Rejeu scalaire indépendant : 9,046,744 contrôles, 84 comptes, 227,976 lignes de features, 83,326 lignes de trades et 151,928 lignes quotidiennes. Ces lignes se chevauchent entre périodes/variantes et ne constituent pas des observations indépendantes.
- 864 vérifications agrégées supplémentaires, six comptes bootstrap reproduits, dates/signaux/fills ALL réconciliés avec A/B ; capitaux et quantités restent distincts par période.
- 10 fichiers financiers/tests/oracle/runner gelés avant premier PnL et 15 dépendances snapshotées. Protocole et recherche conservés. Présentation et contrôles supplémentaires ajoutés après le calcul, scellés au manifest final.

Source SIP et calendrier XNYS/hash des acquisitions/caches vérifiés avant chargement. Aucun accès API, clé ou coffre Windows. Oracle scalaire distinct des agrégations/bandes/signaux/exécutions/comptes, mais même chargeur et fournisseur : pas une seconde source de prix.

Revue pré-PnL :39tests relancés ;40séances synthétiques,14variantes,307trades et29134champs confrontés entre moteur et oracle. Le défaut d’arrondi binaire97.00999999999999→97.00 a été reproduit par un test rouge puis corrigé avant tout résultat de marché, avec convention décimale explicite. Aucun réglage issu des performances.

Couverture ALL :2713séances par ETF,21demi-séances exclues comme inactivité connue. SPY :1637trades,1047sans signal,7unknown_scan et1exclusion de séance complète après signal. QQQ :1608trades,1078sans signal,6unknown_scan. Aucun trade non résolu en référence. Deux résolutions stop+TP ambiguës sur SPY, zéro sur QQQ. resolved_prefix ajoute un trade SPY ; tous les cas sont publiés.

Les quatre figures et le rapport présentent les rendements conditionnels, les coûts, les risques et les sensibilités sans nouvelle promotion. A/B réutilisées, multiples hypothèses déjà explorées, zéro comptable d’exclusion distinct d’un cash observé. Les IC sont descriptifs et conditionnels. DD minute observé, pas pire tick garanti. Prix révisables et fills locaux sans quotes, profondeur, partiels ou latence réelle.

[Tests](results/2026-10-31-v1/TESTS.json) · [Audit](audit/AUDIT_RESULTS.json) · [Agrégats](audit/ADDITIONAL_CHECKS.json) · [Gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json) · [Sources](WEB_SOURCE_STATUS.json).

La livraison se vérifie par scripts/verify_delivery.py --raw, avec PYTHONUTF8=1 sous Windows et PYTHONDONTWRITEBYTECODE=1. Le manifest ne contient ni archives brutes ni secret. Aucun bot, SQLite, tâche Windows, pause, transaction ou paramètre de simulation existante modifié.
