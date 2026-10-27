# Revue séparée — choc puis rebond

## Avant premier PnL de marché

Reviewer distinct, contexte frais, lecture seule. Protocole/recherche, moteur/statistiques/tests, runner, audit, rapport et vérificateur examinés. Aucun marché, runtime, bot, clé, coffre ou ordre consulté/exécuté.

35tests initiaux relancés indépendamment. Problème trouvé : audit conservait un accès inutilisé cfg.bar_minutes absent du nouveau Config. Nouveau test d'audit24scénarios synthétiques, source patchée et reçu sous répertoire temporaire : échec AttributeError avant suppression du champ, puis vert. Aucun reçu de marché écrasé.

Deuxième point : un rendement courant connu éliminant déjà le sens ne nécessite pas sa baseline pour exclure l'ordre. Deux régressions LONG/SHORT échouent avec unknown_history, puis passent après rejet du signe avant cette vérification dans moteur/audit ; choix explicité dans protocole7. Chauffe/sigma nul restent des états connus sans ordre. Une régression de variance nulle corrige aussi avant gel une exclusion courante inutile.

Suite finale38/38, relance indépendante en12,95s. Statistiques passées20séances, fermetures structurelles/demi-séances, inconnus, confirmation/next-open, sizing/TP/SL/coûts/DD conformes. Six exports distincts de décisions documentés ; coûts/RR/prefix réutilisent ces signaux avant qualité/exécution.

Smoke du rapport entièrement synthétique/en mémoire :72exports CSV,4figures construites, rapport9539caractères et CANDIDACY=false selon les bons critères. Aucun PnL réel ou source de marché inspecté. Aucun blocage restant avant gel.

## Après exécution

23empreintes de code/snapshots/dépendances/protocoles contrôlées et profil source identique au gel. Troisième reconstruction des20observations par sommes scalaires, distincte du rolling du moteur et de la deque/NumPy de l'audit :271963contrôles des premières décisions des six variantes/SPY/QQQ, aucune divergence. Erreur maximale sigma1,48e−16 et z5,08e−13 ; stops, slots et prix identiques.

7953contrôles indépendants des72scénarios : configurations/périodes,72résumés face à matrice, comptes/jours/trades, frais/composition/exposition, PF/WR et top3 ; aucune divergence. Intervalles bootstrap blocs5/20 et clusters annuels des six références recalculés depuis CSV par sommes circulaires, identiques.

Critères CANDIDACY=false confirmés : seul le minimum100trades passe. Références ALL SPY−22,0170552%, QQQ−28,6898357% ;72/58exclusions en A, aucune en B. Quatre figures inspectées, cohérentes et lisibles. Couverture conditionnelle, propagation de trous historiques et réutilisation de B correctement exposées. Aucun autre bloqueur financier ou de rapport ; aucun rerun PnL, modification de fichiers, runtime, clé ou bot.

Le replay intégral du coordinateur et le scellement sont documentés séparément dans VALIDATION.md et les reçus liés au run.
