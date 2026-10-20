# Validation — ORB cinq minutes, 20 octobre 2026

Référence : `results/2026-10-20/`. Partage avec réserves : calculs rapprochés, performances conditionnelles et exploratoires, aucune certification d'exécution réelle. Le bot Noise Area et ses paramètres ne sont pas modifiés.

## Tests et revues

42 tests contrôlés : signal sur cinq minutes terminées, doji décimal, fenêtre manquante, quantité connue avant l'open, risque, gaps d'entrée/sortie, stop/cible simultanés et priorité explicite, symétrie LONG/SHORT avec emprunt, cible SHORT non positive inatteignable, demi-séance, prix postexit sans effet, trou pendant maintien indéterminable, conservation d'une sortie avant trou, omission comptable complète et observé NaN, coûts, exposition variable, période vide et bootstrap constant sans trades.

Les tests du moteur et des statistiques ont d'abord été observés rouges, puis verts. La revue indépendante n'a trouvé aucun défaut bloquant du moteur ou des statistiques ; des tests supplémentaires ont renforcé SHORT et les invariants d'omission/postexit. Le reviewer a demandé la version du calendrier, enregistrée dans la preuve d'environnement après calcul pour préserver le gel initial authentique.

La revue du rapport a fait préciser le diagnostic d'ablation : il met trois rendements à zéro puis recompose les autres rendements quotidiens. Il ne conserve pas les P&L originaux d'un portefeuille à quantités fixes. Les valeurs préfigées n'ont pas changé ; le protocole actuel porte cette clarification éditoriale, son original restant dans `PRE_EXECUTION_PROTOCOL.json`. Aucun recalcul financier correctif ni sélection de paramètres après résultats.

## Sources et couverture

Six acquisitions brutes et six fichiers préparés vérifiés par SHA avant désérialisation locale de confiance. Calendrier XNYS continu, 2 714 séances du 31/12/2015 au 16/10/2026 ; longueurs 210/390, fuseaux et tableaux float64 vérifiés. Le périmètre de recherche ALL contient 2 713 séances à compter du 04/01/2016. Le premier jour 2015 est hors étude.

ALL principal : SPY 8 journées exclues pour données incomplètes, QQQ 6. SPY 2 679 trades, QQQ 2 688 ; les autres séances admissibles à signal nul restent sans transaction. B : 618 séances, 615 trades par instrument et aucune exclusion de données. [Dates/motifs](results/2026-10-20/DATA_EXCLUSIONS.csv), [profil](results/2026-10-20/DATA_SOURCE_PROFILE.json).

`complete_days` utilise une qualité de toute la séance connue a posteriori. C'est un univers conditionnel, sans filtre disponible dès l'entrée. `resolved_prefix` démontre les sorties avant trous, mais déclare les autres exécutions indéterminables. Les comptes omettent l'intégralité des journées exclues, avec `observed_return=NaN` ; zéro dans `return_net` est comptable, pas une observation de cash. Vingt intentions non résolues sont recouvrantes entre ALL/A, dix dates/instruments uniques. Aucun trou n'est interpolé ou automatiquement attribué à une suspension.

La sonde SIP historique en lecture seule du 02/02/2016 a réutilisé le coffre Windows sans nouvelle saisie : zéro des neuf minutes absentes récupérée. Pas d'ordre broker, pas de clé dans les preuves. Le fournisseur reste unique et les extrêmes de prix n'ont pas été certifiés par une seconde source.

## Contrôles numériques

[Audit indépendant](results/2026-10-20/INDEPENDENT_AUDIT.json) : **54 exécutions, 85 526 lignes de transactions recouvrantes, 9 282 328 points de capital**. Frais/P&L/capital rapprochés à tolérance 3×10⁻⁶ USD ; écarts mesurés séparément pour montants par trade, prix par action, bps, capital cumulé et DD. Sans appel aux fonctions du moteur : signaux/couverture et membership de chaque séance, taille Decimal, barrières/ordre des événements, frais/capital, expositions bornées et DD aux marks source sont reconstruits. Le chargement/réconciliation des sources réutilise le helper existant ; il n'est pas une acquisition indépendante.

L'instrumentation v1 utilisait un maximum commun de champs aux unités mixtes, intitulé improprement `max_numeric_error_usd`. La preuve v1 est conservée ; la révision 2 de l'audit sépare les unités et mesure les écarts de capital/DD. Seul l'audit a été relancé, sans recalcul des performances. Les 449 empreintes du manifest financier initial sont revérifiées après cette opération.

[Rapprochements secondaires](results/2026-10-20/AGGREGATE_VALIDATION.json) : **1 728 agrégats numériques**, 54 comparaisons CSV/résumé, ventilations année/sens/demi-séance/sortie, CAGR/Sharpe/Sortino/volatilité, coûts/risque/exposition, concentration, durée de DD et absence d'insolvabilité. Les tableaux sont rapprochés des trades déjà audités, sans certifier les hypothèses statistiques.

[Extraits bruts](results/2026-10-20/RAW_EXCERPT_AUDIT.json) : seize exemples déterministes, cinq minutes initiales plus minutes d'entrée/sortie, **112 références minute /560 valeurs OHLCV**, écart nul entre CSV hachés et caches. Gains/pertes extrêmes, demi-séances, ex-dates, ambiguïté si présente et fin de période sont couverts par la sélection documentée. Un extrême du même fournisseur confirmé dans son CSV ne prouve pas qu'il s'agissait d'un prix exécutable.

Quatre PNG autonomes inspectés visuellement : capitaux ALL/B, frais ALL/B et rendements annuels. Libellés conditionnels, périodes, monnaies/unités et 2026 partielle sont visibles. Les échelles des sous-graphiques SPY/QQQ peuvent différer ; les comparaisons numériques sont dans les tableaux.

## Limites et décision

B réutilisée ne vaut pas une validation aveugle ; 54 scénarios et A/B/ALL se recouvrent. Blocs 5/20 séances et groupes annuels : 3 000 répétitions, graine 20261020, trois groupes annuels seulement en B, sans correction pour essais multiples. Les IC journaliers du capital et les IC annuels de moyenne par trade ont des unités différentes et sont clairement séparés.

Open 09:35 supposé après publication de close09:34, priorité intrabar conservatrice, volumes/latence/prêt/spreads/fills réels non observés, coûts hypothétiques. Risque cible 1 % et plafond causal 1x ne garantissent pas les valeurs après gap ; DD/MAE/MFE seulement partiellement observés. Aucune borne sur les pertes inconnues des séances exclues.

QQQ reste une piste à observer prospectivement, fragile aux frais et aux meilleurs jours B ; SPY ne justifie pas de suite opérationnelle. Aucun bot ORB ni engagement réel autorisé par cette étude. Le rapport complet et toutes les variantes restent archivés, sans retoucher les études précédentes.
