# Validation — premier retest après opening range

Étude Python terminée le28octobre2026, exclusivement sur archives locales SIP vérifiées. Aucun résultat TradingView, fill broker, changement de bot/runtime/coffre/clé/tâche ou ordre revendiqué.

## Gel, sources et tests

[Protocole enregistré](results/2026-10-28-v1/PRE_EXECUTION_PROTOCOL.json) à 2026-10-28T19:28:27.306570+00:00, avant premier PnL.12fichiers de code/tests/audit/rapport/vérificateur/lock et12dépendances archivés avec SHA, plus recherche et règles textuelles. Aucun code gelé ou protocole modifié après calcul. L’exécution des72scénarios a pris 172,05 secondes.

[Profil source](results/2026-10-28-v1/DATA_SOURCE_PROFILE.json) : archives brutes/préparations identiques aux études précédentes, SHA, calendrier NYSE et corporate actions vérifiés via chargeur commun. Aucun deuxième fournisseur. Historique principal4janvier2016–16octobre2026, A jusqu’au30avril2024, B dès1mai2024. B déjà explorée.

[42tests passent](results/2026-10-28-v1/TESTS.json). Cas : range confirmé, mèche sans cassure, retest distinct, premier toucher raté terminal, égalité/tolérance, dernier délai/cutoff inclus, demi-séances, données nécessaires manquantes, données futures inutiles, filtre directionnel sur première cassure commune, sizing causal, stops/TP/gaps/arrondis, stop prioritaire, EOD avant mèche, coûts/minimum/emprunt, compte composé et qualité/prefix. Sept cas de replay intégral sur24scénarios synthétiques chacun. Cinq nouveaux cas de matrice ont échoué avant implémentation ; fixture JSON rendue stricte avant gel.

[Revue avant PnL](validation/PREFREEZE_REVIEW.md) :42tests relancés indépendamment, aucun blocage. Smoke du rapport sur72lignes synthétiques et4figures, sans PnL marché. La première tentative de revue avait des erreurs de TEMP non accessible, corrigées par le répertoire de tests autorisé, sans changement de logique.

## Audit de chaque scénario

[Replay scalaire séparé](audit/AUDIT_RESULTS.json) : **3032271contrôles**, **30612lignes de trades**, **130224journées**,72scénarios, aucune divergence. Scénarios et périodes se recouvrent : ces lignes ne sont pas autant d’observations indépendantes.

[bars.py](audit/bars.py) agrège minute par minute hors moteur. [independent.py](audit/independent.py) reconstruit range, première cassure/premier toucher, raisons terminales, quantité, stop/cible/fill, frais/emprunt, calendrier, MAE/MFE, capital et DD aux marques. [matrix.py](audit/matrix.py) impose le produit cartésien unique attendu, paramètres et bornes figés, égalité des schémas et valeurs résuméJSON/matriceCSV.290exports/protocole/matrice liés par empreinte à cet audit. Même source et chargeur : cohérence indépendante du moteur, pas réplication de flux.

## Revue numérique et figures

[Revue après calcul](validation/POSTRUN_REVIEW.json) : **15187contrôles séparés**, aucune erreur.12hashes propres et12dépendances rapprochés entre original/gel/snapshot,72scénarios et agrégats recomputés depuisCSV, tables années/mois/directions/concentration/qualité, six bootstraps blocs5/20 et clusters annuels reproduits avec le seed prévu. Un problème de type d’année dans la comparaison du reviewer a été normalisé en chaîne ; aucun résultat de l’étude modifié.

[Quatre figures inspectées](results/2026-10-28-v1/VISUAL_REVIEW.json), valeurs cohérentes, unités et zéro lisibles, aucun rognage. Les panneaux de coûts/sensibilités ont leurs propres amplitudes verticales : lire leurs graduations. Les graphes DD utilisent les clôtures quotidiennes, moins fines que le DD aux frais/closes minute/sortie du tableau. Année2026 arrêtée au16octobre.

## Limites et intégrité

Principal :5exclusions SPY et4QQQ ; prefix :4chacune et aucun trade actif non résolu. Un trade SPY ajouté par prefix est perdant. Pas d’interpolation, et absence d’exécution non résolue ne signifie pas absence de signal potentiel dans les quatre journées inconnues. Comptes conditionnels ; aucun passif à exposition comparable ni résultat futur garanti.

Limites d’ordre des ticks, spreads variables, disponibilité SHORT, essais multiples non corrigés, B réutilisée, ETF corrélés et adaptation de travaux descriptifs. Quatre critères prédéfinis sur cinq échouent ; QQQ B positif n’est pas promu en preuve prospective. [Interprétation](INTERPRETATION.md).

`python scripts/verify_delivery_v2.py --raw` vérifie gel, source, tests et manifest de cette seule étude. Le contrôle final de publication compare aussi l’inventaire exact des fichiers de l’étude au manifest pour exclure tout ajout non listé. Les anciennes études sont vérifiées sans modification. Seuls cette étude, son plan et le registre global sont publiés.

## Correctif non financier du vérificateur de livraison

Après PnL, le premier scellement a échoué avant écriture du manifest : un importsys local à la branche --raw rendait sys local dans toute la fonction et provoquait UnboundLocalError avant le contrôle de matrice. Le fichier initial, gelé et audité, est conservé identique. [verify_delivery_v2.py](scripts/verify_delivery_v2.py) retire uniquement cet import local redondant ; aucun moteur, test gelé, source, rapport numérique, protocole ou résultat n’a été changé, aucun nouveau backtest nécessaire. [Empreintes et portée du correctif](validation/DELIVERY_CORRECTION.json). La version2 est créée après calcul et n’est pas présentée comme gelée avant PnL.
