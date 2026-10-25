# Validation RSI(2) intraday

**Partage avec réserves explicites de couverture et d’exécution.** Exécution `results/2026-10-24-v1`, 72 configurations fixées avant performances. Les références A/B/ALL sont négatives sur SPY et QQQ. Aucun bot nouveau, aucune modification des bots Noise Area/ORB.

## Tests et corrections avant marché

25tests contrôlés passent. Les tests ont d’abord échoué sur les interfaces non implémentées, puis vérifié RSI Wilder(2), ATR Wilder(14), initialisation/plat/trous, confirmation5min, régime strictement antérieur, horaires, sizing causal, stops/gaps, sortie next-open, demi-séance, frais, comptes et qualité/prefix. La preuve fraîche est archivée dans `results/2026-10-24-v1/TESTS.json`.

La revue a trouvé un écart au protocole : le filtre de close journalier exigeait initialement des OHLCV complets sur sa dernière minute, alors que seul le close fini/positif était requis. Une régression contrôlée reproduit ce rejet indu avec volume/high manquants ; le correctif et les25tests passent **avant toute boucle financière de marché**. Aucun résultat de marché antérieur n’a été remplacé. Une fixture de gap a également été corrigée pour que son High contienne bien son Open ; elle ne constituait pas une observation de marché.

## Audit indépendant

[Script](audit/independent_audit.py), [preuves](audit/AUDIT_RESULTS.json), [revue](audit/REVIEW.md). Aucun helper du moteur ou d’analyse n’est utilisé pour recalculer l’arithmétique ; seul le loader historique retrouve et vérifie les sources.

- **72comptes, 78646lignes de transactions et130224lignes journalières**, avec recouvrement entre variantes/ALL/A/B. Ce ne sont pas78646événements de marché indépendants.
- **3691214contrôles**, aucune divergence ; écart absolu maximal environ1,56×10⁻⁸, dû aux flottants/export.
- RSI/ATR, régime200closes/dividendes, sélection du premier signal, horaires, sizing, prix d’entrée/sortie, stops et sorties RSI/EOD reconstruits depuis les arrays minute.
- Frais/capital/marks/MAE-MFE et métriques exportées refaits avec math/Decimal ; code financier courant identique aux empreintes figées.
- **480minutes OHLCV** confrontées à12pages originales issues des6acquisitions, avec leurs SHA. Échantillonnage, pas relecture indépendante de chaque prix fournisseur.

La revue indépendante n’a aucun P1/P2 ouvert après le correctif. L’audit vérifie l’implémentation déclarée, pas la validité économique de RSI ni un nouvel OOS aveugle.

## Données et interprétation

Archives SIP déjà étudiées, jusqu’au16octobre2026 ; B01/05/2024–16/10/2026 réutilisée. 2714séances préparées dont2015-12-31 sans observations suffisantes, 2713séances dans la période évaluée. Chauffe200séances ; SPY201dates avec un close antérieur manquant dans sa fenêtre, QQQ1. Les contrôles de régime utilisent les200séances immédiatement précédentes, pas200observations sélectionnées après suppression des trous.

Sur ALL référence : SPY1591trades,3séances conditionnellement exclues ; QQQ1713trades,1séance exclue. Le filtre complete_days est connu après la séance. Les simulations resolved_prefix retirent ce filtre : SPY1592trades et résultat−5,24%, QQQ1713trades et−17,18%. Les intentions non résolues restent exportées par scénario. L’absence éventuelle de différence ne certifie pas les opportunités manquantes ; la chauffe et l’absence de régime peuvent expliquer causalement l’absence d’ordre sur un jour incomplet.

Les comptes sont conditionnels, pas des performances continues sur tout jour inconnu. Les prix minute sont des trades SIP et non un bid/ask ou un carnet ; aucune exécution garantie au prix du backtest. Les coûts fixes sont des hypothèses communes de recherche. Les intervalles bootstrap sont descriptifs et ne corrigent ni la recherche multiple ni les exclusions. Les quatre figures ont été inspectées pour unités, axes, légendes, dates et cohérence des valeurs.

## Reproduire et vérifier

Depuis ce dossier, avec les dépendances des études ETF installées :

```powershell
python -m pytest -q -p no:cacheprovider --basetemp=.test_tmp_rsi2
python scripts/verify_delivery.py
python scripts/verify_delivery.py --raw
python scripts/run_study.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

La vérification standard ne demande pas les historiques complets. `--raw` exige le cache local et vérifie les sources et leur profil. Le runner refuse d’écraser une exécution. Le protocole, le code financier, tous les modules de dépendance et leurs snapshots sont figés avant PnL. Les scripts d’audit/rapport/livraison ajoutés ensuite sont couverts par le manifest final. Les historiques complets, clés et journaux des bots restent locaux et ignorés par Git.

Le [bilan des pistes et bots](../../docs/research/2026-10-24-pistes-et-bots.md) distingue les comptes historiques, les observations prospectives qualifiées et les rattrapages. Le snapshot des monitors ne contient que leur état de simulation, sans clé ni identifiant broker.
