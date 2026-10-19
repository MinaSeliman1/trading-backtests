# Intraday Momentum « Noise Area »

**Statut : à faire. Aucun backtest exécuté, aucune performance calculée et aucune conclusion disponible pour cette stratégie.**

Le [cahier des charges reçu](MISSION.md) est enregistré pour la prochaine étude. Il demande notamment de vérifier l'article original de Zarattini, Barbon et Aziz avant toute implémentation, puis de comparer une exécution au close à une exécution causale au prochain open.

Périmètre demandé : SPY principal, QQQ sans réglage particulier, zone de bruit sur 14 séances, décisions aux demi-heures, VWAP, ciblage de volatilité avec plafonds de levier 4x et 1x, coûts et robustesse, période post-publication séparée et benchmarks de contrôle.

La date de coupure annoncée dans la mission (1er mai 2024), les règles de l'article, sa date de publication et les chiffres cités restent à vérifier à la source. Ils ne constituent pas des faits validés par ce dépôt. Le découpage temporel final devra refléter cette vérification.

L'historique Alpaca local du projet FVG pourra servir de point de départ après contrôle des hashes. Son extension vers 2016 et jusqu'à la dernière séance disponible n'a pas encore été réalisée. L'implémentation Python, les tests spécifiques, les résultats et le Pine seront ajoutés dans ce dossier lorsqu'ils auront été produits et validés.
