# Revues indépendantes

Deux revues en lecture seule ont été demandées selon requesting-code-review, avec contexte limité à cette étude.

## Avant premier PnL

Corrections identifiées et appliquées **avant le gel** :

- Fusion du journal avec clés répétées : TypeError éliminée et test synthétique ajouté.
- SHA des archives et provenances ajoutés au gel, en plus du code et des sources publiques.
- Diagnostic par niveau : séparation des niveaux de détection et des objectifs, priorité H1 poolée conservée.
- Moyenne R des hasards : dénominateur des seuls R définis, nombre et risque nul explicitement exportés.
- Open forcé 11:30 également contrôlé sur le tick.

Conventions précisées avant PnL : premier signal admissible dans le biais, balayage 09:30 non reporté en H2, streams date-keyed du RNG. 32 tests passent avant gel, dont le parcours synthétique de bout en bout.

## Après résultats

Pas de défaut bloquant trouvé dans les règles, cohortes, coûts, témoins, statistiques ou reconstruction. Correction d’interprétation : H3 phase 2 a un contraste positif (IC hors zéro), à décrire malgré le total non concluant et avec seulement six témoins sans balayage. La découverte, la phase 2 et l’ensemble sont maintenant exposés sans effacer ce résultat.

Oracle scalaire séparé : 173 728 plans/exécutions, 2 500 journées de signaux, 4 180 564 comparaisons de champs ; agrégats et H3 contrôlés. Réconciliation indépendante des 36 000 agrégats aléatoires, 365 012 comparaisons numériques et 720 contrôles d’inférence. Les tests finaux passent : 32.

Ces contrôles vérifient la cohérence du calcul, pas l’identité des vrais contrats MNQ/MES ni les raccords inconnus de la source continue. Les règles de trading n’ont pas été modifiées après résultat.

Contrôle documentaire final : chiffres concordants, 68 empreintes de l’étude et deux fichiers du dépôt vérifiés, 31 liens locaux résolus, aucun bloqueur restant. Les quatre figures générées ont été inspectées visuellement ; légendes, axes et comparaisons sont lisibles.
