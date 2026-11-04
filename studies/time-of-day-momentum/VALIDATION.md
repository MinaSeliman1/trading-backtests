# Validation — Time-of-Day Momentum

## Gel avant P&L

Règles, critères, tests et code financier publiés au commit `28a4a77f45102319ae8a38b45065b2d081c72933` avant le premier calcul de marché. Le reçu `PRE_EXECUTION_PROTOCOL.json` conserve les hashes du code, des dépendances réutilisées et des protocoles, leur texte et le profil des archives sources. `verify_delivery.py` compare à la fois les sources actuelles et les snapshots ; le moteur financier n’a pas été retouché après lecture des résultats.

Les scripts `additional_checks.py` et `report.py`, l’interprétation et la documentation finale sont des ajouts après calcul. Ils lisent les exports et écrivent seulement les artefacts de contrôle, les figures et les documents. Leur contenu entre dans le manifest final ; ils ne sont pas présentés comme préenregistrés.

## Tests et audit

47 tests synthétiques ont passé avant le P&L de marché. Ils couvrent causalité des fenêtres, changement des barres futures, données inconnues, chronologie du premier candidat, demi-séances, stops/gaps, coûts et emprunt, témoins, statistiques avec masques, frontière de livraison et une exécution complète des 96 comptes sur données synthétiques. Le JUnit préexécution sert de preuve `TESTS.json`.

L’oracle scalaire séparé ne réutilise pas le moteur de stratégie. Il recalcule les rendements passés, moments statistiques, premier créneau, sens, taille, stop, exécution, frais, emprunt, capital et drawdown sur les mêmes caches vérifiés. Le résultat détaillé de chaque compte et les compteurs sont dans `INDEPENDENT_AUDIT.json`. Cela vérifie l’implémentation, pas la véracité d’un deuxième fournisseur indépendant.

`ADDITIONAL_CHECKS.json` reconstruit 24 comparaisons de bootstrap par sommation indépendante des blocs calendaires, les masques inconnus, les nombres de jours où les deux comptes tradent, les écarts appariés, Holm et les deux panneaux de 1 000 horaires à partir des exports par créneau. Les deux panneaux de 1 000 horaires utilisent une graine annoncée et un capital quotidien constant ; aucune sélection de tirage. Le compte témoin `control_random_clock` garde son propre capital composé, comme les autres comptes, et reste distinct de ces panneaux.

`verify_delivery.py` exige 96 comptes audités et rapproche journaux, attribution du P&L et capital final au centième et au-delà. Le manifest final hache tous les fichiers de l’étude sauf caches d’exécution, runtime ignoré et le manifest lui-même. Le runner refuse de remplacer une exécution existante.

## Corrections de revue

Avant P&L : masque des jours inconnus conservé dans le bootstrap économique, nombre de jours appariés strictement avec trade dans les deux comptes, liaison des sources courantes/snapshots/protocoles/profils, livraison limitée à `results/`, friction de sortie incluse dans la MAE. Tous corrigés avant le gel public.

Après calcul : le rapport utilise le maximum de `entry_fill_leverage` du journal pour le levier au fill modélisé. `summary.max_actual_entry_leverage` est conservé intact et mesure le levier au prix d’ouverture de référence, sans la friction du fill. Il s’agit d’une correction d’étiquette/présentation, sans changement de quantité ou de P&L.

## Limites

Les dates A/B sont réutilisées ; B n’est pas aveugle. Les journées exclues restent inconnues, malgré le zéro de tenue comptable du capital conditionnel. Le critère économique ignore ces zéros et conserve la structure des dates manquantes dans les blocs. Le filtre de journée complète est connu après la séance ; le candidat est fixé avant ce filtre. Le diagnostic `resolved_prefix` retire seulement ce filtre et ne prouve pas une couverture continue.

Les caches et archives SIP sont hachés et leurs lignes rapprochées, mais restent sous licence en local. Les prix minute ne représentent pas carnet, coût variable, disponibilité du prêt, fills réels ou pire tick. Aucune clé, aucun ordre broker, aucune modification des bots en cours. Les résultats ne prouvent pas un avantage prospectif.

[Rapport](results/2026-11-04-v1/RAPPORT_FINAL.md) · [Gel](results/2026-11-04-v1/PRE_EXECUTION_PROTOCOL.json) · [Audit](results/2026-11-04-v1/INDEPENDENT_AUDIT.json) · [Contrôle statistique](results/2026-11-04-v1/ADDITIONAL_CHECKS.json).
