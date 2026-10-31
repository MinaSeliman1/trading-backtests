# Plan — Turnaround Tuesday intraday

Mandat utilisateur : choisir, rechercher, backtester et publier une nouvelle piste QQQ/SPY avec les mêmes frais ; ne pas modifier les deux bots actifs. Implémentation autonome dans branche codex/turnaround-tuesday-intraday, étude indépendante, aucun accès API/coffre.

- [x] Lire les études existantes et sources primaires/forums/code ; choisir une hypothèse différente et décrire les différences overnight.
- [x] Écrire PROTOCOL_EXECUTION.md et RESEARCH.md avant PnL :14variantes,84comptes, seuils de présélection et B réutilisée.
- [x] Tests comportementaux rouges : lundi baissier, calendrier/fériés, historique, causalité, stops, frais/minimum, inconnus, demi-séance.
- [x] Implémenter tuesday/engine.py ; source dans tuesday/data.py ; run_study.py gèle le code/dépendances puis calcule les84scénarios.
- [x] Audit indépendant scalaire dans audit/independent.py ; vérification de matrice, signaux, fills, comptes et chiffres publiés ; revue indépendante.
- [x] Rapport Markdown et figures PNG dans results/2026-10-31-v1, validation, empreintes ; vérifier livraison et tests ; conserver toutes les sensibilités.
- [x] Ajouter uniquement nouvelle étude, plan et registre README ; commit et push atomique avec garde sur main.

Fonctions : prepare(market,cash) -> features causales ; signal(market,feature,cfg) -> état/ordre ; simulate -> daily/trades/unresolved. Réutiliser trace stop/EOD existante sans modifier son module ; comptabilité explicitement vérifiée par oracle indépendant. Tout correctif financier après résultats nécessite version datée neuve, jamais écrasement silencieux.

Résultats calculés et audités :84scénarios,35tests,2 919 453checks.4/5critères passent par ETF, ICblocs20 échoue pour les deux ; aucun bot ajouté. Rapport et figures revus, sources gelées intactes ; publication seulement après seal et garde Git.
