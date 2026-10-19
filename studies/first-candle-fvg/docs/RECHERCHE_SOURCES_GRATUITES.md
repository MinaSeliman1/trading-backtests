# Recherche d'une source gratuite longue — 19 octobre 2026

## Source retenue pour l'acquisition SPY/QQQ

**Alpaca SIP historique**, avec le compte Alpaca existant de l'utilisateur. La [FAQ officielle](https://docs.alpaca.markets/us/docs/market-data-faq) autorise le SIP historique sans abonnement pour des requêtes terminées au moins quinze minutes avant l'instant présent. Le [guide de l'API de marché](https://docs.alpaca.markets/us/docs/about-market-data-api) distingue données consolidées et flux IEX. L'acquisition authentifiée est terminée : **773 977 bougies SPY et 807 421 bougies QQQ**, du 3 janvier 2023 au 18 septembre 2026, y compris hors séance avant filtrage. Réponses brutes, pagination et SHA-256 sont conservés dans `data/alpaca_sip_2023_2026`. La validation de la stratégie est documentée séparément dans `results/alpaca_sip_long`.

Le téléchargeur a été préparé et testé sur des réponses contrôlées (pagination, prix raw, protection des identifiants, arrêt sur jeton répété). Les identifiants sont saisis en console locale masquée et conservés uniquement en mémoire. Aucun endpoint de trading ni de compte n'est utilisé.

Période fixée avant les nouveaux P&L : 2023-01-01 à 2026-09-21 exclu. Les séances déjà étudiées à partir du 21 septembre sont ainsi exclues de la nouvelle validation. Voir `PROTOCOLE_HISTORIQUE_LONG.md`.

## Autres sources effectivement examinées

| Source | Couverture annoncée/vérifiée | Restriction déterminante | Usage retenu |
|---|---|---|---|
| [HF Data Library](https://hfdatalibrary.com/) | Minutes depuis mars 2022, SPY et QQQ annoncés | Une seule place IEX ; accès complet authentifié et conditions académiques | Piste secondaire, pas une substitution au SIP |
| [BARS](https://github.com/kfccolonel1/BARS) | Originaux téléchargés : ES 2025-06-20–2026-10-09, NQ 2024-08-04–2026-10-08 | Continus sans échéance dans chaque barre ; amont AlfordLabs inaccessible au contrôle | Audit seulement ; pas une validation finale des contrats datés |
| [IBKR Futures History Downloader](https://github.com/AnthonyZJiang/ibkr_futures_data) | Code d'acquisition de vrais contrats 1 minute | Le dépôt fournit un téléchargeur, pas les fichiers ; compte/TWS et droits de données nécessaires | Ne résout pas l'accès gratuit immédiat |
| [FirstRate Data](https://firstratedata.com/free-intraday-data) | Page actuelle : deux semaines, 21 septembre–2 octobre 2026 | L'extrait de recherche annonçant un an ne correspond plus au contenu accessible | Insuffisant |
| [Kibot](https://www.kibot.com/api/api-overview.html) | Données longues disponibles commercialement | Accès gratuit : daily et quelques échantillons, pas une année SPY/QQQ minute | Insuffisant gratuitement |
| [QQQ public sur Hugging Face](https://huggingface.co/datasets/THULab/timeseries-1m-QQQ-10y) | Conversion annoncée 2014–2024 | Le mainteneur indique absence de description/provenance détaillée et extrêmes anormaux dans l'original | Pas retenu pour remplacer une source officielle disponible |

Les séries CFD ou explicitement synthétiques ne sont pas retenues comme historiques des instruments demandés. Aucune acquisition payante ni création d'abonnement n'a été effectuée.

Une autre piste, [HF Market Data](https://www.hfmarketdata.io/), annonçait des échéances futures individuelles. La page et le schéma OpenAPI ont échoué à la consultation web (502) puis à l'accès HTTPS direct (connexion interrompue). Ni disponibilité gratuite, ni provenance, ni qualité n'ont pu être vérifiées ; aucune donnée de cette piste n'est utilisée.

## Contrôle des fichiers futures publics

L'audit a effectivement compté **329 séances complètes ES sur 477 jours calendaires**, et **547 séances complètes NQ sur 795 jours**, selon la politique de qualité du moteur. Leur longueur est donc réelle.

Sur le chevauchement avec les contrats décembre 2026 acquis chez Yahoo, le maximum d'écart sur O/H/L/C par minute est inférieur ou égal à un tick dans 97,74 % des 5 850 minutes ES comparées, mais seulement 52,12 % des 5 460 minutes NQ. L'écart maximal NQ observé est 17,5 points. Ces différences peuvent venir des sources, conditions d'agrégation, transactions tardives ou erreurs ; ce contrôle ne permet pas d'en attribuer la cause. Elles peuvent changer des FVG stricts. Surtout, ce rapprochement récent n'identifie pas les échéances des périodes anciennes.

Les originaux, catalogue, URL et SHA-256 sont archivés dans `data/free_sources/BARS`, avec les résultats de qualité dans `results/source_audit_2026-10-19`. Aucun identifiant de contrat n'a été inventé et aucune performance de ces continus n'a été présentée comme OOS final.
