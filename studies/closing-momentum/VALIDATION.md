# Validation — momentum de clôture, 20 octobre 2026

Référence : `results/2026-10-20-v2/`. Décision dans le périmètre contrôlé : **partage avec réserves**, résultats négatifs pour les deux scénarios principaux ; aucune preuve prospective ou d'exécution réelle.

## Tests et défauts corrigés

**33 tests** synthétiques vérifient les signaux incluant l'overnight, le dividende annulant exactement le mouvement, la clôture précédente immédiate, les fenêtres terminées, la non-utilisation du futur, les demi-séances, les coûts LONG/SHORT, la quantité connue avant l'open, les trous de maintien, le refus d'une sortie manquante, les témoins imposés, la causalité du drawdown, le bootstrap apparié, les années sans événement, les empreintes et le refus d'écrasement.

Le cœur du moteur et les statistiques ont d'abord été exercés par des tests rouges, puis verts. Une revue indépendante a signalé deux points : l'arrêt des témoins en cas d'insolvabilité et la durée du drawdown dans le helper statistique hérité. L'arrêt de tous les portefeuilles a été explicitement inscrit avant P&L ; aucun chemin calculé n'est insolvable. La durée a été corrigée localement pour une période plate et le dernier sommet répété, avec trois régressions rouges/vertes, sans toucher au code des études antérieures.

Après la première exécution, pytest collectait aussi les snapshots archivés, d'où quatre erreurs de collecte/import. `pytest.ini` limite maintenant la collecte aux tests actifs ; les archives restent intactes. La commande complète `python -m pytest -q --basetemp=.test_tmp_final` ne collecte donc pas les copies historiques.

## Versions et intégrité

La première exécution `2026-10-20/` est conservée avec son protocole et ses empreintes. La référence `2026-10-20-v2/` porte un motif explicite de recalcul. [Comparaison des versions](results/2026-10-20-v2/VERSION_COMPARISON.json) : fichiers `trades.csv` et `daily.csv` identiques octet par octet dans les 42 dossiers ; tous les champs des résumés sont identiques sauf `worst_drawdown_duration_calendar_days`.

Les 42 exécutions représentent 30 scénarios de stratégie et 12 témoins. A, B et ALL se recouvrent ; les mêmes journées apparaissent dans plusieurs variantes. Il ne s'agit pas de 42 tests indépendants ni de 70 934 transactions indépendantes.

Les six caches préparés et six acquisitions CSV brutes sont rapprochés de la validation précédente, avant chargement des pickles locaux de confiance. Calendrier XNYS continu sur 2 714 séances depuis le 31/12/2015, longueurs 210/390 minutes, fuseaux et précision float64 contrôlés. [Profil et SHA-256](results/2026-10-20-v2/DATA_SOURCE_PROFILE.json). La première séance de recherche 2016 ne dispose pas d'une clôture précédente exploitable ; elle reste exclue, sans substitution par une date plus ancienne.

Sur les 2 713 séances ALL, SPY compte 2 706 séances admissibles, 7 exclusions et 5 signaux nuls ; QQQ 2 709 admissibles, 4 exclusions et 4 signaux nuls. Les dates et motifs sont conservés dans les exports qualité et `EXCLUSIONS.csv`. Les minutes intermédiaires sans rôle dans le signal ne provoquent pas d'exclusion rétroactive. Aucun trade principal calculé ne manque de minute pendant ses 29 minutes de maintien. La requête d'actions d'origine ne retourne pas de split ; la complétude de cet historique d'actions n'est pas certifiée par une source indépendante de l'émetteur.

## Audit des calculs

Les deux versions passent le script indépendant `audit_results.py`, sans importer le moteur ou ses statistiques : **42 exécutions, 70 934 lignes de transactions recouvrantes, 2 274 918 points de capital**, erreur monétaire maximale **1,935 × 10⁻⁸ USD**. L'audit recalcule sélection, sens, quantité entière, ajustement du dividende, références et fills, commissions, emprunt, résultat et capital cumulés, timestamps NYSE, drawdown quotidien et minute observé. [Preuve v2](results/2026-10-20-v2/AUDIT_INDEPENDANT.json).

`validate_outputs.py` rapproche les 42 exports avec leurs résumés et tableaux : coûts, gains/pertes, profit factor, moyenne/médiane, exposition, levier, ablation des trois meilleurs jours, CAGR, Sharpe, comptes/rendements annuels, groupes LONG/SHORT et demi-séances, durée corrigée et absence d'insolvabilité. [Preuve](results/2026-10-20-v2/AGGREGATE_VALIDATION.json). Ce rapprochement secondaire utilise les exports déjà audités ; ce n'est pas une autre acquisition de marché.

Un contrôle distinct relit dans les CSV bruts **80 références sur 16 transactions sélectionnées** : clôture 09:59, dernière clôture précédente, prix de taille, open d'entrée et open de sortie. Écart maximal **0**. Les cas illustrés comprennent grands gains/pertes, ex-dividendes, demi-séances, SHORT et fin d'historique. [Preuve et limites du contrôle](results/2026-10-20-v2/RAW_EXCERPT_AUDIT.json), [extraits limités](results/2026-10-20-v2/raw_ohlcv_excerpts.csv). La sélection est déterministe, pas aléatoire.

## Limites de portée

B est un historique réutilisé ; aucun rendement présenté n'est prospectif. Le maintien de 29 minutes et la sortie à l'open avant clôture ne reproduisent pas l'enchère de clôture du papier source. L'open 15:30 peut être inaccessible après publication de la clôture 15:29 ; la friction ne le prouve pas. Les coûts d'emprunt et la disponibilité SHORT sont hypothétiques. Pas de tarif réglementaire distinct ni intérêts créditeurs sur cash.

Les intervalles de 3 000 réplications par blocs de 5/20 séances et par années sont descriptifs ; B ne possède que trois groupes annuels, sans correction pour multiplicité. Les tests contrôlés vérifient les cas de base du rééchantillonnage ; l'audit des transactions ne certifie pas les hypothèses statistiques. Le drawdown minute reste limité aux observations, et les highs/lows ne donnent pas un chemin intraminute ordonné.

Quatre figures sont générées depuis les CSV publiés, avec comparaison des capitaux sur des échelles verticales communes. Les résultats et limites sont dans le [rapport final](results/2026-10-20-v2/RAPPORT_FINAL.md). Le bot Noise Area, ses paramètres, sa base et ses secrets ne sont pas modifiés par cette étude.
