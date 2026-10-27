# Validation — rebond après choc intraday

Étude Python du26octobre2026 sur SPY/QQQ. Aucun résultat TradingView ou fill broker revendiqué. Deux bots QQQ, runtime, clés/coffre, paramètres, journaux, tâches et suivi inchangés ; aucun ordre.

## Gel et provenance

[Protocole et empreintes](results/2026-10-26-v1/PRE_EXECUTION_PROTOCOL.json) enregistrés à2026-10-27T00:36:49.183931+00:00, soirée du26octobre à Toronto.9sources code/tests/runner/rapport/audit/vérificateur et12dépendances archivées, avec recherche/protocole textuels. Aucun code financier ou protocole modifié après premier PnL.

[Sources vérifiées](results/2026-10-26-v1/DATA_SOURCE_PROFILE.json) : mêmes archives SIP1minute et préparations que les études précédentes ; SHA, calendrier NYSE et rapprochement corporate actions vérifiés via chargeur commun. Pas de deuxième flux. Python3.14 et versions dans protocole/requirements-lock.txt.

[Exécution complète](results/2026-10-26-v1/RUN_COMPLETE.json) :72scénarios prédéfinis, un run,192,94secondes. Aucune sélection d'un gagnant après performance. Les six exports de décisions correspondent à référence, z1.5/z2.5, sans confirmation/sans z et miroir SHORT ; les variations de coûts/RR/prefix partagent les mêmes décisions avant qualité/exécution.

## Tests synthétiques

[38tests passent](results/2026-10-26-v1/TESTS.log), [reçu](results/2026-10-26-v1/TESTS.json). Développement depuis cas rouges, puis corrections avant gel. Couverture : moyenne/sigma ddof1 sur20séances passées à même heure, prix futurs absents, invariance d'échelle/cash intraday, demi-séances structurelles, lacunes non sautées, chauffe/variance nulle, seuil/signe/confirmation, premier signal, stop/TP/gaps/arrondis, SL/TP simultanés, EOD avant mèche, frais/emprunt, causalité du sizing, quantités nulles, compte composé et exclusions/prefix.

Test intégral de l'audit sur24scénarios synthétiques : source patchée et sorties temporaires isolées, aucun reçu marché écrasé. Reproduit d'abord un ancien champ cfg.bar_minutes absent, puis passe après suppression. Régressions rouges/vertes du rejet de signe avant baseline inconnue et de la variance nulle. Aucun PnL de marché dans ces tests.

## Revue distincte

[Preuves de revue](validation/REVIEW.md). Avant PnL :38tests relancés indépendamment, smoke du rapport sur72exports synthétiques et4figures ; aucun blocage restant. Après calcul :23empreintes et profil source rapprochés,271963contrôles de décisions/features via une troisième reconstruction scalaire, puis7953contrôles d'agrégats des72scénarios, sans écart.

Intervalles blocs5/20 et clusters annuels des6références recalculés séparément depuis CSV. Critères CANDIDACY=false confirmés ; quatre figures inspectées. Aucune nouvelle simulation de stratégie ni modification de fichiers par le reviewer.

## Replay intégral séparé

[Audit lié au run](audit/AUDIT_RESULTS.json) : **passed**, **4276184contrôles**, **68102lignes de trades**, **130224journées** sur72scénarios, aucune divergence. Variantes/périodes recouvrantes : ces lignes ne sont pas autant d'observations indépendantes.

[features.py](audit/features.py) utilise des deques de20séances ouvertes et NumPy, distincts du rolling pandas décalé du moteur. [independent.py](audit/independent.py) vérifie premier signal, données nécessaires/chronologie, sizing figé, stops/targets/gaps, frais/emprunt, MAE/MFE, comptes/returns, calendrier/périodes, CAGR/WR/PF/DD et top3, sans appeler le moteur. Empreintes de protocole/matrice/288exports liées au run. Chargeur et données communs : cohérence, pas réplication chez un autre fournisseur.

## Couverture et limites

Principal72séances exclues SPY,58QQQ ;19séances de chauffe connues sans ordre chacune. Historique nécessaire inconnu64/52, fenêtre inconnue5/5, filtre futur de journée entière3/1. Une seule lacune peut affecter20séances suivantes. Aucune exclusion en B pour ces références, mais B a déjà été explorée.

Prefix ajoute2/1trades résolus, reste négatif et conserve70/57séances exclues, dont un trade actif SPY non résolu. Coûts d'entrée connus exportés. Aucun trade actif QQQ non résolu ne signifie pas absence de ses57opportunités inconnues avant signal. Pas d'interpolation ; zéro comptable d'exclusion n'est pas cash observé.

Adaptation clock-time de recherches NBBO/event-time ou actions, coûts fixes et élargissement du spread de choc non reconstruit, fills sans carnet, ordre des ticks inconnu, shorts non garantis, choix d'hypothèses répétés et marchés corrélés. Aucun nouveau OOS aveugle, pas de conclusion causale ni de rentabilité prospective.

## Figures et intégrité de livraison

[4PNG inspectés](results/2026-10-26-v1/VISUAL_REVIEW.json) : axes/unités/zéro/légendes lisibles, aucun rognage ; DD quotidien graphique distinct du DD aux événements/closes1minute du tableau.

Commande : `python scripts/verify_delivery.py --raw`. Le vérificateur contrôle gel, résultats liés à l'audit,38tests et manifest de cette seule étude ; caches et README global évolutif exclus.371empreintes de l'étude calendaire et362de l'étude EMA vérifiées identiques avant publication. Seuls ce dossier, son plan et le registre global changent.

Décision : [piste écartée dans cette formalisation](INTERPRETATION.md), six références négatives, variantes positives isolées non promues ; aucun nouveau bot.
