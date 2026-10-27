# Validation — fin/début de mois intraday

Étude Python SPY/QQQ du26octobre2026, sans modification des deux bots QQQ, de leurs clés, coffre, paramètres, runtime, journaux ou tâches Windows. Aucun ordre broker.

## Gel et provenance

[Protocole enregistré avant premier PnL](results/2026-10-26-v1/PRE_EXECUTION_PROTOCOL.json) à2026-10-27T00:02:16.742847+00:00 (soirée du26octobre à Toronto).9fichiers de code/tests/audit/rapport/vérificateur et12dépendances archivés avec leurs empreintes. Recherche et protocole textuels figés également. Aucun de ces fichiers modifié après observation des performances.

Calendrier XNYS étendu aux mois complets au-delà des sources, [CSV et empreinte figés](results/2026-10-26-v1/XNYS_CALENDAR.csv). Ne déduit pas la fin de mois des limites A/B ou de la dernière observation source. Calendrier historique reconstruit, sans archive point-in-time des annonces exceptionnelles.

[Profil source](results/2026-10-26-v1/DATA_SOURCE_PROFILE.json) : mêmes archives SIP1minute et préparations que les études précédentes, vérification SHA et rapprochement des corporate actions via le chargeur commun. Pas de deuxième fournisseur. Dépendances exactes dans requirements-lock.txt et protocole.

[Exécution complète](results/2026-10-26-v1/RUN_COMPLETE.json) :72scénarios prévus, réalisés une seule fois ; aucune variante ajoutée après PnL.

## Tests et revue

[30tests passent](results/2026-10-26-v1/TESTS.log), [reçu](results/2026-10-26-v1/TESTS.json). Premier essai rouge avant implémentation ; régressions calendaires non ouvrées également rouges avant correction, puis vertes. Tests : vrais ordinaux/fin de mois, holidays/fermeture exceptionnelle/demi-séances, troncature source et A/B, filtres calendaires, sizing09:34/entrée09:35 sans futur, stops/gaps/pas de TP, no_stop virtuel, dernière mèche, frais, données inconnues, couverture prefix, compounding et contraste mensuel connu.

[Revue distincte](validation/REVIEW.md), lecture seule avant PnL :28tests initiaux,24scénarios synthétiques/4276contrôles d'audit en mémoire et500parcours aléatoires. Problème de bornes civiles non ouvrées corrigé avant gel ;30tests relancés indépendamment avec succès. Aucun PnL de marché pour cette validation synthétique.

Revue finale :17862contrôles sans divergence, empreintes du code/source,72résumés et tableaux du rapport rapprochés. Reconstruction séparée des étiquettes XNYS par mois et des6contrastes/IC95,520lignes mensuelles recouvrantes. Les intervalles ALL comprennent zéro sur les deux ETF ; critère de candidature prédéfini non satisfait.

## Replay intégral séparé

[Résultat](audit/AUDIT_RESULTS.json) : **passed**, **2992740contrôles**, **37684lignes de trades**, **130224journées** sur72scénarios, aucune divergence. Ces variantes/périodes se recouvrent ; ces lignes ne sont pas autant d'observations indépendantes.

[Audit scalaire](audit/independent.py) indépendant du moteur/statistiques : calendrier construit mois par mois, sélection des jours, minute connue, tailles/arrondis, stops/gaps, absence de TP, EOD avant mèche, données inconnues, frais, MAE/MFE, comptes/returns, CAGR/WR/PF, drawdowns événements/closes et ablation top3. Le moteur cherche le premier événement dans des tableaux ; l'audit parcourt chaque minute. Chargeur et données communs : cohérence sur ces sources, pas réplication de marché indépendante. Empreintes de protocole, calendrier, matrice et288exports liées au run.

## Couverture et limites

Comptes conditionnels. Principal : trois séances éligibles exclues SPY, une QQQ ; elles deviennent trois/un trades actifs non résolus dans prefix, intégralement omis du compte. Frais d'entrée connus exportés dans unresolved.csv. Mêmes performances principal/prefix ne signifient pas couverture complète ni absence d'exposition sur ces journées. Aucun remplacement de prix inconnu.

B déjà explorée, sélection d'hypothèses répétées, aucune validation aveugle nouvelle. Fills SIP minute sans bid/ask ni carnet, coûts fixes de recherche, calendrier non point-in-time, mois incomplets/partiels et corrélation des ETF. Le contraste est descriptif, non causal et sans correction des essais multiples. Positivité historique ne garantit pas rentabilité prospective.

## Figures et livraison

[Quatre PNG inspectés](results/2026-10-26-v1/VISUAL_REVIEW.json) : axes/unités/zéro/légendes lisibles, aucun rognage. DD graphique quotidien distinct du DD événements/closes1minute du tableau.

`python scripts/verify_delivery.py --raw` contrôle code/dépendances/protocoles/calendrier gelés, lien aux exports audités,30tests et manifest SHA. Le manifest couvre seulement cette étude, sans README global évolutif ni caches.362empreintes de l'étude EMA et356de l'étude Rejet de veille vérifiées inchangées avant publication. Seuls ce dossier, son plan et le registre global sont ajoutés/modifiés.

Décision : [observation positive mais insuffisante pour un nouveau bot](INTERPRETATION.md). Aucune variante plus flatteuse promue après résultats ; les deux simulations existantes restent inchangées.
