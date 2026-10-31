# Validation de la livraison

**Calculs vérifiés dans le périmètre décrit, résultats à partager avec les réserves de couverture et d'exécution.** La piste est négative ; aucun avantage exploitable futur ou bot nouveau n'est revendiqué.

## Tests et défauts fermés avant PnL

- 35 tests ont d'abord échoué sur l'interface non implémentée, puis sont devenus verts. Ils couvrent calibration passée, calendrier partagé, demi-séances, seuils, taille avant fill, quatre commissions, frictions, emprunt, stops aux closes, inconnus et absence de réentrée.
- La revue a reproduit deux cas rouges avant PnL : close manquant sur un créneau à variance nulle qui devait être ignoré ; étiquette de sortie delay2 devant être EOD lorsque l'ordre programmé l'emporte. Correctifs et régressions verts. Le test du filtre de coût a été renforcé pour exercer un vrai rejet puis une poursuite du scan.
- Trois tests de l'oracle utilisent des attentes manuelles (moyenne/écart-type, paire avec quatre frais, coûts connus d'une position inconnue).
- La fusion paramètres/statistiques du runner produisait une erreur de mot-clé initial_capital en double. Cas synthétique rouge puis fusion corrigée avant le premier PnL.
- La suite complète compte 41 tests passants ; sortie réelle dans TESTS.json, preuve datée avant le gel. Revue indépendante : même suite exécutée et passante. Aucun accès coffre, API, tâche Windows ou journal actif par ces tests.

## Gel et exécution

Gel financier 2026-10-31T20:22:21.822304UTC, dix sources financières/tests/oracle et douze dépendances réutilisées, leurs snapshots, protocole/recherche, coûts/périodes et source. Les 42 comptes ont été calculés en 102,02 s ; aucun changement financier depuis le premier PnL. Les scripts de présentation et le contrôle statistique supplémentaire sont explicitement hors gel financier initial et inclus au scellement final.

Oracle scalaire séparé PASS : 1 972 227 contrôles, 42 comptes, 14638 lignes de paires, 29276 jambes et 75964 lignes quotidiennes. Les lignes se chevauchent entre sensibilités/périodes : elles ne sont pas autant d'observations indépendantes. Le replay recalcule les historiques aux mêmes créneaux, choix/tailles, deux fills, quatre frais, emprunt, comptes, DD et exclusions sans appeler les fonctions financières du moteur. Source/chargeur communs, pas deuxième fournisseur.

Contrôle post-calcul séparé PASS : 378 calculs numériques descriptifs sur les 42 comptes (moments, Sharpe, volatilité, Sortino, DD/durées et extrêmes calendaires), six IC bootstrap recomputés par sommes cumulées circulaires avec même seed, 539 dates/prix/stops de référence ALL concordant avec A+B. Ce contrôle partage les rendements exportés et n'est pas une validation des hypothèses statistiques. Valeurs A/B ont leurs propres quantités et capitaux composés.

La revue finale a contrôlé les chiffres arrondis, les critères, les quatre PNG, les contributions par jambe et les liens locaux ; 212 exports audités, dix sources et douze dépendances toujours conformes aux hashes. Aucun enjeu matériel restant. Le périmètre Git est vérifié séparément par l'agent principal.

## Données et portée

Archives Alpaca SIP locales 1 minute vérifiées par SHA, calendrier XNYS et longueurs/horaires validés. Le cache contient 2714 séances depuis 2015-12-31 ; évaluation ALL depuis 2016-01-04. SPY 2705 séances complètes/9 incomplètes, QQQ 2707/7, motifs missing_minutes. Les calendriers des deux actifs doivent correspondre exactement. Les réglages des bots et leurs bases ne sont ni lus pour le backtest ni modifiés.

La référence ALL a 124 exclusions : 121 unknown_history, deux unknown_signal et une journée incomplète ; 19 séances d'évaluation restent en warmup connu. Observed_return reste NaN sur les exclusions, return_net vaut zéro seulement pour le chaînage conditionnel. Aucune paire de référence non résolue. resolved_prefix peut utiliser les données nécessaires avant une lacune ultérieure, sans sauter un signal inconnu pour trouver un trade favorable.

Le filtre de journée complète du principal est connu après coup. L'historique global incomplet n'est pas sauté ; les créneaux structurellement hors demi-séance sont seuls omis de l'estimation à même horloge. L'égalité ou proximité des comptes de couverture ne garantit pas un portefeuille sans interruption.

A/B déjà étudiées ; aucun OOS aveugle. Taux d'emprunt 1 % annuel minimum un jour fixé pour comparabilité, pas tarif/locate vérifié. Fills atomiques synthétiques aux deux opens, stop close-based, pas carnet/quotes/volume disponible/fills partiels/legging asymétrique. Pas de garantie de neutralité bêta, cointégration ou retour à la moyenne. DD aux marks observés et excursions de prix hors frais fixes ; pas pire tick certifié. Les historiques peuvent être révisés, pas archive point-in-time certifiée.

## Scellement et reproduction

Rapport Markdown et quatre figures statiques contrôlés. Le manifest final scelle tous les fichiers de la nouvelle étude, avec les textes de validation et contrôles supplémentaires ; aucune clé, runtime, base SQLite ou archive brute distribuée. L'exécution refuse un dossier de sortie déjà rempli et le scellement refuse d'écraser un manifest existant. Refaire le calcul dans une copie/worktree séparé pour préserver la preuve de référence. Voir README pour les commandes.
