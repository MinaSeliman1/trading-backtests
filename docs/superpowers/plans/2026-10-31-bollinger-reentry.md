# Bollinger reentry implementation plan

> Required workflow: executing-plans inline, test-driven-development and requesting-code-review before publication.

**Goal:** nouvelle piste SPY/QQQ, mêmes frais, backtest et publication autorisés, bots inchangés.
**Architecture:** bb/data chargeur vérifié ; bb/engine agrégation5min, bandes, première sélection et exécution1min ; audit/independent oracle scalaire ; scripts/run_study matrice84 gelée ; scripts/report et verify_delivery preuves.
**Tech Stack:** Python3.14/numpy/pandas/pytest/matplotlib/XNYS.
**Spec:** studies/bollinger-reentry/PROTOCOL_EXECUTION.md.

Ruling : mandat utilisateur répété de choisir et publier ; pas nouvelle demande d’approbation de conception. Nouvelle branche dans le checkout propre existant, aucun worktree/bot déplacé.

- [x] Lire sources et études, fixer règles/variantes/critères avant PnL.
- [x] Tests rouges puis moteur ; fixtures manuelles/cas gaps/stop&TP/données manquantes.
- [x] Oracle et runner revus avant PnL, gelSHA puis84comptes.
- [x] Vérification indépendante des comptes/statistiques/IC.
- [x] Rapport et quatre figures ; vérificateur de manifest et préparation de la publication Git protégée. Revue finale avant scellement.

## Ledger

35tests initiaux observés rouges sur stub, puis verts. Une régression supplémentaire reproduit une moyenne97.00999999999999 donnant à tort97.00 ; normalisation décimale1e-8 documentée et corrigée avant PnL.39tests passent après ajout des contrôles oracle/matrice.

Revue technique préalable sans bloqueur : comparaison sur40séances synthétiques,14variantes,307trades et29134champs. Grille, scan causal, premier setup, gap stop/TP, commissions, DD et MAE concordent. Aucun PnL marché vu avant gel.

84comptes exécutés après empreintes du code/protocole/tests/oracle/dépendances. Scripts de rapport et contrôles supplémentaires ajoutés ensuite, conformément au §12. Aucune règle financière modifiée après résultats. Ne pas promouvoir les variantes A/B isolées.

Après calcul : oracle scalaire9046744contrôles,83326lignes de trades et151928quotidiens,864contrôles agrégés et6comptes bootstrap.39tests verts. Les références A/B/ALL sont négatives pour chaque ETF ; les28scénarios ALL sont négatifs.

Revue finale sans bloqueur :39tests,10fichiers financiers/15dépendances/2protocoles/463exports,84résumés,356champs du rapport et4figures vérifiés. Relecteur :84202contrôles arithmétiques additionnels, IC blocs et clusters annuels concordants. Deux libellés précisés sans changement financier.
