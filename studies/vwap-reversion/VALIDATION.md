# Validation — retour VWAP après première heure

Référence `results/2026-10-20/`. **Partage avec réserves : performances conditionnelles négatives, calculs rapprochés, aucun avantage établi pour cette version.** Aucun changement du bot Noise Area ni lancement d'ORB.

## Contrat et tests

46 tests synthétiques contrôlent : ADR20 des séances immédiatement antérieures sans futur ni saut, warmup/historique invalides en abstention causale, VWAP fourni réellement pondéré, seuil strict Decimal, zéro volume et champ manquant, quantité au prix connu, stops/gaps LONG/SHORT et frais/emprunt, close de retour puis prochain open, touche intrabar insuffisante, VWAP post-signal inutile au témoin EOD, sortie connue malgré fin de barre manquante, absence de prix postexit dans le DD, demi-séance, non-résolu NaN/omission totale, exposition variable et ablation par rendement quotidien.

Moteur, données et statistiques ont été exercés rouges puis verts. Trois erreurs de fixture SHORT provenaient de high/low non réordonnés après réflexion de prix ; elles ont été corrigées avant P&L. La revue a ensuite trouvé le classement par P&L d'un helper d'ablation alors que le protocole demandait les plus grands rendements : régression vue rouge 8 %, puis verte 7,9 %. Le témoin EOD a été corrigé avant P&L pour ignorer un VWAP futur inutilisé. **Aucun correctif de règle ou de calcul financier après l'exécution réelle.**

## Sources et calendrier

Six caches préparés et six CSV historiques rapprochés de la validation Noise Area avant désérialisation locale de confiance ; calendrier XNYS, fuseaux, séquence continue et précision float64 vérifiés. Les fichiers préparés historiques n'ont pas été modifiés. 2 714 séances du31/12/2015 au16/10/2026 ; 2 713 dans ALL à compter du04/01/2016.

428 pages gzip originales vérifiées individuellement par SHA. Champs `o/h/l/c/v` de **1 054 186 barres SPY et1 054 175QQQ** RTH rapprochés des tableaux existants, champ `vw` récupéré dans de nouveaux tableaux locaux. Aucun `vw` invalide avec volume positif, hors OHLC ou volume nul observé ; le code traite ces conditions explicitement sans supposer qu'une valeur hors OHLC est forcément erronée. L'indicateur utilise le VWAP du fournisseur et ses volumes de barres ; pas de proxy HLC3 ni reconstruction indépendante du tape.

Principal ALL : SPY 127 abstentions causales d'historique (warmup20/prior20 incomplet), 5 exclusions de données actuelles, 393 trades ; QQQ 80 abstentions d'historique, 2 exclusions, 506 trades. B : aucune abstention d'historique/exclusion, 107 /129 trades respectivement sur618séances. Les autres séances admissibles n'atteignent pas le seuil. Les mêmes ADR antérieurs à B sont connus à la date de décision, sans recalibration.

Le filtre `complete_days` courant utilise une qualité connue après la séance. Les omissions ont observed_return=NaN et return_net=0 comptable ; ce n'est pas du cash réel constaté. `resolved_prefix` ne dépend que du préfixe nécessaire jusqu'à sortie : les P&L sont identiques ici et aucune position entrée n'est non résolue. Cette égalité n'est pas une preuve de complétude du fournisseur ou de continuité déployable de l'ensemble des comptes. La disponibilité ancienne de l'ADR peut être un veto causal ; elle n'efface aucune donnée future. [Couverture](results/2026-10-20/DATA_EXCLUSIONS.csv), [sources/SHA](results/2026-10-20/DATA_SOURCE_PROFILE.json).

## Audit et agrégats

[Audit Decimal indépendant](results/2026-10-20/INDEPENDENT_AUDIT.json) : **48 exécutions, 12 586 lignes de trades recouvrantes, 2 125 058 marks**, 288 rapprochements d'agrégats principaux. Reconstitue l'ADR20, VWAP/signaux, tailles, ordre des événements, coût/P&L/capital, dates et exclusions sans appel au moteur ou aux statistiques nouvelles. Le loader source est partagé ; il ne constitue pas une autre acquisition indépendante.

Écarts maximaux : champs monétaires par trade4,051×10⁻¹¹USD ; capital3,769×10⁻⁹USD ; DD monétaire3,397×10⁻⁹USD ; DD en points3,397×10⁻¹². Tolérance monétaire3×10⁻⁶USD. Prix/action, bps et ratios ont des maxima distincts dans la preuve. Les comptes/scénarios/périodes se recouvrent et ne sont pas 12 586 événements indépendants.

[Rapprochements secondaires](results/2026-10-20/AGGREGATE_VALIDATION.json) : 1 776 agrégats, tous48exports/résumés, frais/ratios/risque/exposition, classements d'ablation par rendements et exclusion algébrique de2020, CAGR/volatilité/Sharpe/Sortino/durée du DD et absence d'insolvabilité ; ventilations année/sens/demi-séance/sortie/éligibilité rapprochées.

[Extraits](results/2026-10-20/RAW_EXCERPT_AUDIT.json) : seize dates déterministes, séquences RTH jusqu'à sortie, **3 168 barres et19 008champs OHLCV/VWAP** relus dans les gzip hachés, écart nul ; VWAP première heure et conditions des sorties VWAP recalculés depuis les extraits. Les champs complets de la minute de sortie sont conservés comme contexte brut et peuvent être postérieurs au fill : ils n'entrent pas dans les marks postexit. Les jours non sélectionnés et vingt plages ADR antérieures ne sont pas tous réexportés ; ils sont contrôlés par le rapprochement complet et l'audit des sources préparées.

## Limites et décision

Version figée sans optimisation de0,25ADR/20jours/stop1ADR/10:30. Le signal contrariant est notre hypothèse, les sources Alpaca documentent les données/indicateurs sans valider cet avantage. Fills aux opens supposés après publication, spread/latence/volumes/prêt/rejets réels absents ; coûts hypothétiques sans tarif réglementaire séparé ni intérêts cash. DD/MAE/MFE partiellement observés, budget1 % et plafond causal1x ne garantissent pas les pertes ou le levier après gap.

B est une période réutilisée, pas un nouveau OOS aveugle. Blocs5/20séances et groupes annuels,3000répétitions seed20261020 ; trois groupes annuels en B, années sans événement conservées, IC de rendement quotidien du capital distincts des bps par trade, pas de correction multiplicité ni certification indépendante des hypothèses statistiques.

Principaux négatifs en A/B/ALL. SPY sans sortie VWAP légèrement positif reste un diagnostic préfigé avec son propre capital ; il ne remplace pas le principal et ne justifie pas un bot. Les variantes LONG/SHORT positives en B restent négatives ALL. Archiver cette version. [ORB QQQ](../../docs/research/2026-10-20-orb-qqq-decision.md) reste candidate à une validation prospective distincte, sans nouveau bot activé ici.
