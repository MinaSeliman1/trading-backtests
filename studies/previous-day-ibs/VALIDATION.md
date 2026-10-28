# Validation — exécution du 28 octobre 2026

- Gel avant premier PnL : 2026-10-28T21:13:39.407186+00:00 ; 13 fichiers propres et 12 dépendances archivés. Recherche et protocole liés par SHA. Les fichiers gelés restent identiques aux snapshots.
- 48 tests synthétiques passent. Cycle rouge/vert constaté : absence initiale du moteur ; cas d'arrondi du stop instable corrigé avant marché ; dix tests de corruption d'exports ajoutés avant renforcement de l'audit. Une comparaison de dictionnaires NaN a été corrigée dans le test, sans changer un signal de marché.
- Un pipeline entièrement artificiel de 72 comptes a validé runner, audit et rapport avant calcul de marché. Ses résultats restent dans .test_tmp_smoke, ignoré ; ils ne sont jamais présentés comme résultats de marché.
- Audit du marché : **passed**, 3212571 contrôles, 34778 lignes de trades recouvrantes, 130224 lignes quotidiennes recouvrantes, 72 scénarios. Ces répétitions ne sont pas des observations indépendantes.
- Recalcul scalaire séparé depuis les tableaux vérifiés : agrégation OHLC minute, IBS précédent, ADR14, SMA200 strictement antérieurs sans saut, critères de décision, sizing, stop/entrée/sortie, commissions, friction, emprunt, soldes et DD observé. Le replay ne fait aucun appel au moteur de stratégie ou aux fonctions de statistiques.
- Contrôle exact des ensembles de dates exportées pour trades et non résolus, unicité et métadonnées sign/direction/symbol/mode/quality ; matrice cartésienne complète liée aux paramètres/périodes gelés et à chaque résumé JSON. Les coûts s'attribuent une seule fois et le compte se réconcilie.
- Les synthétiques couvrent seuils inclusifs, neutralité du range nul, causalité, trou passé, warmup, filtre200, gaps d'entrée sans resize, stops intrabar/gap, mèche du dernier open, commissions minimales, emprunt SHORT, données actives inconnues, complétude ex-post et prefix.
- Sources identiques aux autres études, vérifiées par SHA et calendrier NYSE ; chargement d'archives localement déjà connues, aucune clé/API. Le rapprochement de la source n'est pas un deuxième fournisseur indépendant. Aucune compilation Pine ou exécution TradingView revendiquée.

Revue indépendante du moteur avant PnL : aucun défaut financier critique/important identifié ; contrôles supplémentaires de bornes de fenêtre200 et fills après trou. Les remarques sur ensembles de dates et titre du rapport ont été corrigées AVANT gel, puis les48tests ont été reproduits par le reviewer. La revue finale des exports/figures est conservée dans FINAL_REVIEW.json après réalisation.

Voir audit/AUDIT_RESULTS.json, results/2026-10-28-v1/TESTS.json, PRE_EXECUTION_PROTOCOL.json, RUN_COMPLETE.json et FILE_MANIFEST.json. Le vérificateur refuse les fichiers manquants/modifiés et les fichiers ajoutés non listés dans cette étude ; le registre global du dépôt reste évolutif.

Limites : comptes conditionnels avec trous, sélection répétée d'hypothèses sur B réutilisée, absence des ticks/quotes/carnet/shortabilité, stop et frictions modélisés, faible nombre de clusters annuels ; ni gain prospectif ni disponibilité d'un bot nouveau démontrés.
