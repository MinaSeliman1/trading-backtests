# Nowick Python — Implementation Plan

**Goal:** Tester trois paires FX sur2015–2024, au moins100trades chacune, publier les résultats honnêtes.
**Architecture:** Archives FXCM1m immuables et manifest ; features15m causales ; moteur minute déterministe en ticks entiers ; export/audit/rapport séparés. Aucune interaction Windows ni clé API.
**Spec:** studies/nowick-compensation/PYTHON_PROTOCOL.md et MISSION.md.

- [x] Tests d'acquisition/qualité puis téléchargement parallèle borné et préparation.
- [x] Tests de causalité, stops/limites, front-run, TTL, sessions/DST, risques et trous ; implémentation minimale jusqu'à réussite.
- [x] Exécuter configurations figées, ALL et A/B, vérifier100trades de référence par paire.
- [x] Revue de code et audit indépendant, corriger les défauts puis refaire les résultats concernés dans une nouvelle version si nécessaire.
- [x] Rapport complet, tableaux et figures Python ; vérifications finales, empreintes et publication GitHub.

Validation : 126 exécutions, 70 tests, audit indépendant complet de 243 466 contrôles sans erreur ; trois seuils de 100 trades résolus atteints. Publication préparée après scellement, puis vérification du commit distant. Les réserves de couverture et le statut Pine non compilé sont conservés.
