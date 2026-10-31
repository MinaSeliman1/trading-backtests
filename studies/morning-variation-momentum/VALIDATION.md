# Validation de la livraison

- 42tests automatisés passent sur moteur, fixtures manuelles, absence de regard futur, sous-échantillonnage, quantiles, warmup, sizing, délais, frais minimums, excursions, lacunes, demi-séances et matrice14variantes.
- Rejeu scalaire :5437956contrôles,84comptes,227976lignes de features,23612lignes de trades,151928lignes quotidiennes. Ces lignes se chevauchent entre périodes et variantes ; ce ne sont pas des observations indépendantes.
- 864contrôles statistiques additionnels ;6comptes bootstrap blocs5/20 reproduits ; dates/signaux/fills ALL réconciliés avec A/B sans imposer des quantités identiques aux capitaux séparés.
- 10fichiers financiers/tests/oracle/runner gelés avant PnL et15dépendances locales snapshotées. Protocoles et sources écrits avant le calcul. Les scripts de présentation et de vérification supplémentaires ajoutés ensuite sont scellés au manifest final.
- Le chargeur revérifie les hashes des caches/acquisitions, le calendrier XNYS, les horaires et formes des arrays. Oracle distinct, mais même source et même chargeur : aucune prétention à un second fournisseur.

Principal ALL : chaque ETF2713séances,252warmup,21demi-séances sans trading,4matinées inconnues,0trade non résolu. SPY273trades /2163sans signal ; QQQ230trades /2206sans signal. Les quatre exclusions restent inconnues, jamais cash observé. resolved_prefix donne ici les mêmes trades et résultats que complete_days ; le biais conditionnel potentiel demeure explicite.

Revue avant PnL : défaut invalid_ohlcv après-midi pouvait retirer un matin valide du pool. Deux tests rouges reproduits puis correction avant tout résultat de marché. Conflits/décalages globaux restent bloquants. MAE/MFE incluent les deux fills après friction ; sortie open15:59 ne détient pas la mèche finale.

Le rapport contient quatre PNG statiques, les84comptes et leurs tableaux annuels. Les critères préfixés échouent : aucun nouveau bot. A/B exploratoires réutilisées, IC descriptifs non corrigés des recherches multiples, fills de barres simulés. Le DD minute observé n’est pas une garantie tick.

Fichiers de preuve : [tests](results/2026-10-31-v1/TESTS.json), [audit scalaire](audit/AUDIT_RESULTS.json), [agrégats](audit/ADDITIONAL_CHECKS.json), [gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json), [sources](WEB_SOURCE_STATUS.json). Le vérificateur final contrôle snapshots, exports audités et FILE_MANIFEST.json ; --raw relit les acquisitions locales sans API. Aucun bot, coffre, tâche Windows ou SQLite modifié par cette étude.

Reproductibilité Windows : les commandes documentées activent PYTHONUTF8=1 avant lecture des preuves JSON. Le code financier gelé reste identique. PYTHONDONTWRITEBYTECODE=1 évite des artefacts de bytecode dans le dossier.

La transcription RESEARCH_READABLE.md corrige seulement le mojibake de l’original RESEARCH.md, conservé intact conformément au gel pré-PnL.
