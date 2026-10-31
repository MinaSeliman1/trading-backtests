# Validation — Turnaround Tuesday intraday

**Partage avec réserves documentées ; calculs vérifiés dans le périmètre décrit.** Aucune affirmation de profit exploitable futur ou de passage en réel. La décision est l’échec du critère IC fixé avant résultats, pas une erreur arithmétique.

## Preuve de calcul

-35tests de la nouvelle étude passent, sortie réelle conservée dans results/2026-10-31-v1/TESTS.json.31cas ont d’abord échoué sur l’interface non implémentée. Tests réels de calendrier/fériés, seuils, historique sans sauter un trou, sizing causal, gaps/stops, frais/minimum, demi-séance et inconnus.
-Deux défauts matériels ont été reproduits en revue AVANT le premier PnL puis corrigés : une séance historique invalidée par la qualité globale ne doit pas entrer dans ADR14 même avec OHLC finis ; MAE/MFE doivent employer les fills de sortie plutôt qu’un open de référence non détenu. Trois nouveaux cas rouges puis verts les couvrent. La fixture demi-séance a été corrigée pour placer le close du lundi au slot209 et non389. La définition de risque brut/net a aussi été clarifiée avant PnL.
-Le gel19:32:01UTC contient11fichiers de code/tests/audit/rapport/dépendances déclarées,15fichiers de dépendances réutilisées, les textes du protocole/recherche, versions, coûts, périodes et hashes source.84scénarios réellement calculés, sans modification financière après gel. Le helper trace stop/EOD d’IBS est réutilisé, pas réécrit ou modifié ; sa parité seule n’est pas considérée indépendante.
-Replay scalaire séparé PASS :2 919 453contrôles,84scénarios,15 786lignes de trades,151 928lignes quotidiennes. Ces lignes se chevauchent entre comptes/périodes ; elles ne sont pas autant de trades indépendants. L’oracle recalcule depuis les arrays les OHLC minute, ADR/close, jours, décisions, fills, quantités, frais, comptes, DD et excursions ; ne fait aucun appel au moteur de stratégie.
-Vérification supplémentaire indépendante ajoutée après calcul :383dates de référence ALL concordent avec A+B pour dates/prix de fill/stops ;12IC blocs5/20 et6IC clusters annuels reproduits avec sommes cumulées circulaires et même graine. Ce check partage les rendements exportés, sans appeler la bibliothèque de statistiques. Son script/proof sont inclus dans le manifest final.
-Revue indépendante :35tests exécutés, code/snapshots vérifiés, IC recalculés, chiffres/critères et quatre PNG contrôlés ; aucun problème financier important restant. Garde de périmètre Git vérifiée par l’agent principal.

## Sources et limites

Archives Alpaca SIP locales, source complète et préparations SHA vérifiées ; aucun API call ou clé nécessaire.2714séances du cache depuis2015-12-31, calendrier XNYS continu, aucun doublon de date dans les préparations ; SPY2705complètes/9incomplètes, QQQ2707/7, motif missing_minutes. L’évaluation ALL commence2016-01-04. La provenance et les dates exactes sont dans DATA_SOURCE_PROFILE.json.

La référence exige une journée courante complète après coup. resolved_prefix enlève ce filtre mais pas les exigences d’historique ou les prix nécessaires ; ses résultats égaux ici ne certifient pas une couverture continue. Les références signalent16jours exclus SPY et9QQQ, tous enA ; aucun trade non résolu dans ces références. Cela ne signifie pas qu’aucune minute ne manque dans tout le cache ou les autres variantes.

A/B sont réutilisées ; IC conditionnels, pas correction globale des essais multiples. Retours close/close bruts avec potentiel effet ex-dividende ; pas de dividende crédité overnight. Aucun split dans la requête fournisseur archivée, complétude non certifiée. Même source et chargeur dans l’oracle, pas deuxième feed de validation. Fills locaux synthétiques, pas carnet/quotes/latence/fills partiels ; risque cible hors frais et gaps conservés. DD observé n’est pas un maximum de tick certifié.

## Rapport et intégrité

Quatre figures statiques lues : equity, années, coûts et témoins. Valeurs du rapport liées aux summaries/matrice et décisions SCREENING ; causes et incertitudes séparées. Relecture éditoriale après génération : « quantités de la trajectoire originale » remplacé dans RAPPORT_FINAL.md par « rendements quotidiens ... sans recalcul des quantités » pour décrire exactement l’ablation top3. Aucun chiffre ni calcul changé, report.py et son snapshot demeurent ceux du gel. Une régénération technique reproduit les valeurs et la prose initiale ; le Markdown final relu est conservé par son SHA dans FILE_MANIFEST.json.

Le manifest final scelle chaque fichier de l’étude, sans runtime, clé ou archive complète. Les anciens résultats et bots sont hors périmètre de modification. La copie de travail et les branches distantes sont vérifiées lors de la publication. Reproduire dans une copie séparée ; aucun écrasement silencieux d’exécution de référence.
