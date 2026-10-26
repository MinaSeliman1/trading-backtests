# Validation — rejet des extrêmes de veille

Étude Python SPY/QQQ terminée le26octobre2026. Aucun résultat TradingView ou fill broker revendiqué. Les deux bots actifs et leurs journaux n'ont pas été modifiés.

## Gel et sources

[Protocole et empreintes avant PnL](results/2026-10-26-v1/PRE_EXECUTION_PROTOCOL.json), enregistré à 2026-10-26T22:54:26.959954+00:00. Moteur, tests, scripts, audit et dépendances partagées archivés dans code_snapshot/dependency_snapshot ; aucun changement de ce code après observation. [Fin d'exécution](results/2026-10-26-v1/RUN_COMPLETE.json) :72scénarios.

Sources locales minute SIP déjà acquises, archives et préparations SHA vérifiées via le chargeur commun ; [profil](results/2026-10-26-v1/DATA_SOURCE_PROFILE.json). Ce contrôle d'intégrité et le replay ne constituent pas une seconde source de marché. Prix, dividendes, minutes manquantes et biais de sélection restent ceux du protocole.

## Tests et relecture

[Tests32/32](results/2026-10-26-v1/TESTS.log), [reçu](results/2026-10-26-v1/TESTS.json), Python3.14.6 et dépendances gelées. Premier essai rouge avant implémentation (module absent), puis cas synthétiques : veille immédiate, calendrier/demi-séances, cash ex-date, seuils exacts, première réintégration5/15min, absence de données futures, sizing figé, gaps, SL/TP simultanés, frais, emprunt, comptes et inconnus. Ces données synthétiques ne servent pas au résultat financier.

[Revue séparée](validation/REVIEW.md) avant PnL et livraison. Deux cas limites du vérificateur corrigés avant gel (entrée infinie et zéro trade), puis quatre replays synthétiques en mémoire. Revue finale des tableaux/conclusions :30lignes contrôlées sans divergence. Aucun résultat positif isolé promu.

## Replay indépendant

[Résultat audité](audit/AUDIT_RESULTS.json), statut **passed**, 3,295,388contrôles, 44,572lignes de trades et 130,224journées recouvrantes sur72scénarios ; aucune divergence. Ces lignes se recouvrent entre variantes/périodes : elles ne sont pas autant de transactions indépendantes.

[audit/independent.py](audit/independent.py) n'appelle pas le moteur ou les agrégateurs statistiques. Il reconstruit niveaux de veille/cash, candidates5/15min, première direction, filtres, fenêtre, quantité, stop/target arrondis, fills et gaps, commissions/friction/emprunt, ordre temporel, MAE/MFE, chaînage quotidien, couverture, calendrier, CAGR, WR/PF, drawdowns et ablation top3. Le reçu lie les empreintes du protocole, de la matrice et des288exports de scénario à ce run. Chargeur et flux historiques communs, pas audit d'un second fournisseur.

## Figures et intégrité

[Quatre PNG inspectés](results/2026-10-26-v1/VISUAL_REVIEW.json) : axes, unités, légendes et absence de rognage vérifiés. Voir [INTERPRETATION.md](INTERPRETATION.md) pour le libellé2016 et la distinction DD quotidien/événements.

Le vérificateur contrôle code/protocole/dépendances gelés, exports liés au replay, tests et SHA des fichiers de cette étude. Son manifest exclut caches temporaires et README global évolutif. Commande : `python scripts/verify_delivery.py --raw`. Les1977fichiers de l'import FVG ont aussi été vérifiés SHA identiques avant publication. Aucun fichier ancien d'étude ni bot édité ; seul le registre global est complété.

## Conclusion et limites

Références A/B/ALL négatives sur les deux ETF après frais. Cette formalisation est écartée pour un nouveau bot. B réutilisée, pas nouvel OOS aveugle. Comptes conditionnels, filtre complete_days connu après coup, trous de données, modèle minute plutôt que quotes/carnet, shorts et coûts variables non reconstruits. L'audit établit la cohérence des règles et comptes sur ces données ; il ne prouve pas une capacité de trading réel.
