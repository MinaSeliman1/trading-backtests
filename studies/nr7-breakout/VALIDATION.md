# Validation NR7 — livraison du24octobre2026

Statut : **partageable avec les limites décrites**. Aucun avantage suffisamment établi pour installer un bot NR7. [Rapport](results/2026-10-24/RAPPORT_FINAL.md), [comparaisons](results/2026-10-24/comparison_all.csv).

- 16 tests contrôlés passent : NR7 strict/égalité, sept séances sans remplacement, dividendes, première clôture, entrée suivante, sizing causal, frais/emprunt, gaps, stop, prix futurs après sortie, trous avant signal/en position, demi-séance et stress aux quatre frictions. Aucune donnée synthétique dans les performances de marché.
- 48 scénarios prédéfinis exécutés. Source : mêmes archives Alpaca SIP minute que les autres études ; six acquisitions OHLCV, six fichiers préparés, calendrier continu et tailles/dtypes recontrôlés. [Provenance](results/2026-10-24/DATA_SOURCE_PROFILE.json).
- Audit indépendant sans appeler les fonctions prepare/simulate/trace : **5428 features**, **19510 lignes de trades recouvrantes**, **86816 lignes journalières**, **6392716 marks**. Recalcul Decimal des règles/fills/coûts/sizing/capital et contrôles des principaux agrégats, dont CAGR, Sharpe, profit factor et coûts. [Preuve](results/2026-10-24/AUDIT_INDEPENDENT.json).
- Rapprochement direct de **16 séances**, **30300 champs OHLCV** et **108 lignes d'extraits** avec les six CSV d'acquisition hachés. Inclut QQQ2020-03-09 et ses minutes absentes. C'est un contrôle échantillonné complémentaire, pas un nouveau téléchargement indépendant. [Preuve](results/2026-10-24/AUDIT_RAW_SAMPLES.json), [extraits](results/2026-10-24/RAW_SOURCE_EXCERPTS.csv).
- Revue de code et vérification indépendante des48sorties : pas de défaut P1/P2 relevé ; dates attendues, un trade maximum/jour, nombres de trades, coûts, PF, moyenne bps, CAGR, Sharpe et flags de rendements manquants contrôlés. Les réserves sur la couverture et le libellé des contrôles sont intégrées au rapport.
- Quatre figures inspectées : compte/drawdown quotidien, sensibilité aux frictions, rendements annuels et distribution des trades. Le drawdown des closes quotidiens et celui des marks intrajournaliers restent des métriques distinctes.

## Gel et reproductibilité

Le [protocole avant exécution](results/2026-10-24/PRE_EXECUTION_PROTOCOL.json) et `code_snapshot/` conservent exactement le moteur, les tests, les dépendances et les règles avant la boucle financière. Le moteur, les tests, data.py et run_study.py n'ont pas été modifiés après le calcul. Les scores, daily/trades/summary et le manifest initial ne sont pas écrasés.

L'audit et le rapport ont ensuite été enrichis : contrôles statistiques supplémentaires, annualisation inclusive365,2425 conforme à la définition existante, cas non résolu QQQ2020-03-09 et améliorations des figures. Le premier contrôle d'annualisation de l'audit utilisait365,25 sans jour final inclus : il a échoué ; sa définition a été corrigée, sans changement de P&L ni de métrique publiée. Les scripts finaux et leurs empreintes se trouvent dans `verification_code_snapshot/` et `POST_EXECUTION_CHECKS.json`. La notice de reproduction a été clarifiée ; seul le calcul refuse d'écraser une exécution, les fichiers dérivés d'audit/rapport sont régénérables.

Le [manifest de livraison](results/2026-10-24/DELIVERY_MANIFEST.json) couvre les fichiers finaux. Lancer `python scripts/verify_delivery.py` pour vérifier les empreintes financières initiales, le gel du moteur et des dépendances, les preuves et les résultats de livraison.

## Réserves qui restent

B a été réutilisée après d'autres études, avec trois années partielles/complètes seulement : aucun nouveau test aveugle, aucune correction de recherche multiple. Les intervalles de blocs5/20jours et clusters annuels sont descriptifs et conditionnels.

Le principal filtre après coup les journées incomplètes qui auraient déclenché un trade. QQQ2020-03-09 est exclue ; resolved_prefix omet le même trade non résolu, avec entrée SHORT59actions et coûts connus exportés. Leur égalité de rendement n'est pas une preuve de robustesse. Aucun portefeuille continu n'est revendiqué sur les jours inconnus et aucun cash n'est inventé pour observed_return.

Le modèle ne prouve ni des fills réalisables ni l'ordre des ticks, ni la disponibilité de l'emprunt SHORT. Les frais réglementaires variables sont absents ; friction/commissions/emprunt sont des hypothèses communes aux études, avec stress. Les gaps peuvent dépasser le risque1% et le plafond1x effectifs. Les ablations annulent des rendements déjà calculés, sans reconstituer un compte à nouvelles quantités ; les trois meilleurs jours sont classés par PnL net positif en USD. Les variantes et périodes se recouvrent ; leurs lignes ne sont pas des observations indépendantes.
