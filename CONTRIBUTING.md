# Ajouter une étude

1. Créer `studies/<nom-de-strategie>/` à partir de `templates/STUDY.md`.
2. Enregistrer la mission, les règles exactes, les sources et les hypothèses avant de consulter les nouveaux résultats. Déclarer les éventuelles inspections antérieures et corrections.
3. Conserver séparément le code, les tests, les documents, le Pine et les résultats. Chaque stratégie garde ses dépendances et ses commandes d'exécution.
4. Exclure les clés et les historiques complets. Enregistrer le fournisseur, le calendrier, les dates, la qualité, les paramètres d'acquisition et les SHA-256 des fichiers réellement utilisés.
5. Écrire chaque nouvelle exécution dans `results/<date-ou-identifiant>/`. Conserver les paramètres, versions, hashes et journaux. Un recalcul ne remplace pas silencieusement une exécution archivée.
6. Exécuter les tests pertinents, rapprocher les trades et les agrégats, puis documenter les limites. Distinguer les tests unitaires, l'exécution Python, l'audit des résultats, la compilation Pine et la validation TradingView.
7. Mettre à jour le registre du README avec le statut réel : à faire, en cours, exploratoire ou validé dans le périmètre décrit. Une étude sans résultats conserve une conclusion « non évaluée ».
8. Committer les changements et les pousser dans ce dépôt après vérification des fichiers ajoutés. Aucun téléversement futur ne s'effectue automatiquement.

Les résultats déjà importés sont conservés avec leurs octets d'origine. `snapshots/fvg-import-2026-10-19.json` et `tools/verify_snapshot.py` permettent de détecter leur modification. Pour corriger ou refaire une étude, créer une nouvelle exécution et expliquer ce qu'elle remplace.
