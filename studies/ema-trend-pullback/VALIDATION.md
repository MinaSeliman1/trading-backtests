# Validation — repli EMA9/20 puis reprise

Étude Python SPY/QQQ terminée le26octobre2026. Aucun résultat TradingView ou fill broker revendiqué. Aucun accès aux deux bots, runtime, clés ou coffre ; les simulations restent inchangées.

## Gel, sources et versions

[Protocole et empreintes avant PnL](results/2026-10-26-v1/PRE_EXECUTION_PROTOCOL.json), enregistré à 2026-10-26T23:30:03.477285+00:00. Moteur/tests/runner/audit/rapport/vérificateur et dépendances partagées archivés dans code_snapshot/dependency_snapshot. Aucun changement de ce code après observation. [Fin du calcul](results/2026-10-26-v1/RUN_COMPLETE.json) :72scénarios prévus, réalisés une fois.

[Sources vérifiées et SHA](results/2026-10-26-v1/DATA_SOURCE_PROFILE.json) : archives SIP minute, préparations, calendrier NYSE et rapprochement des corporate actions, via le chargeur commun. Données identiques aux études précédentes, pas deuxième source de marché. Python3.14.6, versions gelées dans protocole et requirements-lock.txt.

## Tests synthétiques et revue

[Tests31/31](results/2026-10-26-v1/TESTS.log), [reçu](results/2026-10-26-v1/TESTS.json). Premier essai rouge avant implémentation (module absent). Cas : récurrence EMA/seed prébougie, cash et échelle commune des pentes,60barres/reset, signaux/filtres/bornes temporelles, futur inchangé, sizing figé, gaps, SL/TP simultanés, dernière mèche ignorée, frais/emprunt, exclusions et comptes. Comparaison des trajectoires entières avec l'audit EWM sur fixtures avec/sans trou et cash. Données synthétiques jamais utilisées pour le PnL de marché.

[Revue séparée](validation/REVIEW.md), lecture seule avant PnL :31tests également relancés par le reviewer,9parcours d'audit en mémoire, sans marché. Contrôle des états cash étendu aux quatre états conservés après test rouge puis vert ; origine de chauffe initiale corrigée dans l'audit avant gel. Aucun changement financier après résultats.

Revue finale :63contrôles,6tableaux du rapport et années/mois/directions/couverture/incertitudes rapprochés sans divergence ; trois lignes positives isolées explicitement non promues.

## Replay intégral indépendant

[Résultat du replay](audit/AUDIT_RESULTS.json) : **passed**, 4,955,640contrôles, 86,976lignes de trades et 130,224journées recouvrantes sur72scénarios ; aucune divergence. Les périodes et variantes se recouvrent : ces lignes ne sont pas autant d'observations indépendantes.

L'audit [indicators.py](audit/indicators.py) reconstruit les EMA via segments pandas EWM sur closes+cash cumulatif passé, puis revient à l'échelle du jour. Cette méthode diffère de la récurrence des états du moteur. Il s'arrête explicitement si des cash extrêmes rendent un état conservé non positif : cas vérifié absent ici, pas fausse validation d'un cas non pris en charge.

[audit/independent.py](audit/independent.py) n'appelle ni le moteur ni les agrégateurs statistiques. Il reconstruit premier signal, pente/force/zone, exclusions/chronologie, taille, SL/TP arrondis, fills/gaps, frais, emprunt, MAE/MFE, comptes/returns, calendrier, CAGR, WR/PF, DD et ablation top3. Le reçu lie exactement protocole/matrice/288exports de scénario à ce run. Chargeur et flux communs : audit de cohérence, pas une réplication chez un autre fournisseur.

## Figures et intégrité

[Quatre PNG inspectés](results/2026-10-26-v1/VISUAL_REVIEW.json) : axes/unités/zéro/légendes lisibles, couleurs cohérentes, aucun rognage. Graphique de DD quotidien distinct des événements/closes1min du tableau.

Commande de livraison : `python scripts/verify_delivery.py --raw`. Le vérificateur contrôle code/protocole/dépendances gelés, résultats liés au replay, tests et manifest SHA des fichiers de cette étude ; caches temporaires et README global évolutif exclus. Avant publication :1977fichiers FVG et356fichiers scellés de l'étude précédente vérifiés identiques. Seuls le nouveau dossier, son plan et le registre global sont modifiés.

## Conclusion et limites

Références A/B/ALL négatives sur les deux ETF après frais ; pas de nouveau bot pour cette formalisation. B déjà réutilisée, pas nouvel OOS aveugle. Comptes conditionnels, filtre complete_days futur, trous et rechauffes, prix minute plutôt que quotes/carnet, shorts et coûts variables non reconstruits. Le replay démontre la cohérence de cette exécution sur ces sources, pas une rentabilité prospective.
