# Validation

46 tests passent : estimations strictement passées, ADR 14 exact, jours verts zéro, compte rouge plafonné2, première candidate, géométrie, délai, taille, coûts, gap/stop/EOD, inconnus et parité scalaire synthétique.

Oracle : 9175504 contrôles, 84 comptes, 227976 lignes de caractéristiques, 79080 lignes de trades, 151928 lignes quotidiennes recouvrantes. 864 calculs agrégés et 6 comptes bootstrap blocs5/20 reproduits. Recouvrements entre variantes/périodes, pas autant d’observations indépendantes.

Gel avant premier PnL : 10 fichiers code/tests/runner/oracle/verifier, 15 dépendances et2protocoles avec leur contenu. Présentation ajoutée après gel ; manifest final distinct. Prix bruts : les notes de dividendes héritées du profil source n’ajustent pas le corps ni l’ADR de ce test.

SPY : eligible=1520, no_signal=1036, unknown_history=112, half_session=21, warmup=20, excluded_incomplete_day=2, unknown_scan=2

QQQ : eligible=1513, no_signal=1095, unknown_history=63, half_session=21, warmup=20, unknown_scan=1

Revue pré-PnL dip_pre_review :42 tests vérifiés, aucun bloqueur financier ; P3 du filtre red2 corrigé avant calcul, puis 46 tests verts, dont régression et cas scalaires gap/inconnu. RED initial observé sur module absent ; corrections de fixtures OHLC et de frontière documentées dans le plan. Aucune règle modifiée après PnL.

Oracle sans import du moteur/statistiques, même source et chargeur ; cache par identité supposant les marchés immuables et maintenus en vie pendant main. Aucun deuxième fournisseur, carnet ou tick. complete_days sélectionne sur disponibilité future ; resolved_prefix révèle les inconnus actifs. Zéro de chaînage d’une exclusion n’est pas du cash observé.

[Tests](results/2026-10-31-v1/TESTS.json) · [Audit](audit/AUDIT_RESULTS.json) · [Agrégats](audit/ADDITIONAL_CHECKS.json) · [Gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json) · [Sources](WEB_SOURCE_STATUS.json). Quatre PNG vérifiés visuellement avant publication. Recalcul/audit dans une copie séparée avec données locales ; --out de l’oracle sous le dossier de l’étude, preuve d’audit fixe protégée. verify_delivery.py --raw est une vérification en lecture seule.
