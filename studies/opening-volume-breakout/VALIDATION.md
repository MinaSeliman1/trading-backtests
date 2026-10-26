# Validation ORB confirmé + RVOL

Exécution `results/2026-10-24-v1` :72scénarios, protocole et code figés avant première boucle PnL. Référence QQQ ALL+44,75%, SPY−5,04% ; ces montants sont des comptes historiques conditionnels. Aucun nouveau bot.

## Tests et revue

29tests synthétiques passent, preuve fraîche dans TESTS.json/log. Première collecte échouée sur package absent, puis implémentation et fixtures rendues cohérentes (mèches contenant les closes et absence de touche involontaire du stop). Aucun PnL de marché n'avait été calculé lors de ces corrections.

Vérifications : RVOL sur14séances immédiatement précédentes, pas de volume futur, chauffe et trou sans remplacement, confirmation sur clôture puis next-open, égalité non-cassante, frontières11:29/11:30, filtres/direction/doji, fenêtres15min, gap d'entrée sans annulation ni redimensionnement, quantité limitée par risque ou levier, commissions minimum/au-dessus, emprunt SHORT minimum1jour, stops prioritaires longs/shorts, gap stop/TP, demi-séances, frais d'intention inconnue et chaînage du compte.

[Revue séparée](audit/REVIEW.md) : aucun P1/P2 du moteur ouvert. Les demandes sur exports et intégrité de l'audit ont été traitées avant le gel et leur présence confirmée. La revue ne remplace pas le replay de marché.

## Audit des résultats

[Replay indépendant](audit/independent.py), [preuves](audit/AUDIT_RESULTS.json) :72scénarios,39114lignes de transactions et130224journées recouvrantes ;2789472contrôles, aucune divergence.

Le replay ne fait aucun appel aux fonctions de signal, d'exécution ou de statistiques du moteur. Il reconstruit depuis les arrays minute : calendrier attendu, validité de fenêtre,14volumes antérieurs, direction, premier signal, heure d'entrée, sizing Decimal avant open, stop/target/fills, coûts, PnL, prix exécutés, marks/DD, MAE/MFE, quantités/returns journaliers et principaux agrégats (net/CAGR/PF/WR/coûts/concentration).

Les preuves portent les SHA du protocole et de289fichiers (matrice et exports de72scénarios) ; le vérificateur rejette une preuve issue d'autres octets ou d'une autre exécution. L'audit partage le loader de source vérifié et les mêmes préparations ; ce n'est pas une seconde source indépendante de prix, ni une certification du fournisseur. Les lignes de variantes/ALL/A/B se recouvrent et ne sont pas autant de trades indépendants.

## Données et couverture

Archives SIP préexistantes et préparations vérifiées par SHA au chargement.2714séances préparées dont padding2015-12-31,2713dans la période évaluée2016–16/10/2026. Fichiers `_session_quality.csv`, `_gaps.csv`, `_features.csv` et daily/unresolved documentent les absences sans interpolation. Les14fenêtres consécutives ne sont jamais remplacées par des fenêtres plus anciennes.

ALL référence : SPY18séances marquées inconnues, QQQ17 ;14fenêtres de chauffe nominales peuvent être classées doji/direction avant chauffe selon la règle, ce qui explique les comptes warmup12/13. Aucun trade n'est créé sur des données inconnues. L'absence de différence principal/prefix ne résout pas les opportunités manquantes : certains jours sont bloqués avant le signal par leur volume, une fenêtre antérieure ou une lacune de prix. Aucun unresolved actif dans cette référence ; cela ne constitue pas une garantie de couverture complète.

Le principal utilise un filtre de journée complète après coup sur les séances éligibles à une entrée. Les exclusions sont conditionnelles, les zéros du compte ne sont pas des rendements de cash observés. Les comptes B sont redémarrés avec100000USD, même filtre et mêmes14fenêtres issues de l'historique précédent, pas de nouvelle chauffe artificielle à la coupure.

## Contrôle du rapport

Quatre PNG relus visuellement : axes, unités, légendes, fenêtres, rendu, cohérence avec la matrice. Les points manquants sont interrompus, pas interpolés comme prix observés ; les autres jours sans ordre sont des décisions connues. Les snapshots contiennent le rapporteur et les scripts de contrôle figés avant calcul. [Interprétation par ETF](INTERPRETATION.md) précise la fragilité de QQQ en A et la non-supériorité universelle du filtre de volume.

La période B a déjà servi à d'autres études. Bootstrap circulaire5/20séances et clusters annuels,3000tirages seed20261024 : descriptifs, aucune correction des essais multiples ou de la sélection de famille. Prix de trades consolidés, pas quotes broker ; fills1min et coûts fixes ne garantissent pas l'exécution. Aucun nouveau OOS aveugle, aucune preuve prospective ou de rendement réel.

## Conservation et reproduction

`python scripts/verify_delivery.py` contrôle le code, ses copies, les protocoles, les dépendances, les exports audités et le manifest final. `--raw` recharge et rapproche les sources locales. Le runner refuse l'écrasement des résultats. Les historiques complets et les secrets ne sont pas publiés.

Les autres études/bots restent byte-identiques à leur livraison précédente. Le README global est un registre évolutif ; son empreinte conservée dans l'ancien manifest RSI se vérifie au commit historique `dbcefe96d1f6215242c0f9fa5e5ec736f051344f`, alors que les octets des autres fichiers de ce manifest sont toujours vérifiables dans le checkout. Le nouveau manifest fige seulement le dossier de cette étude, sans empêcher les futures mises à jour du registre global.
