# Protocole figé avant performances — ORB confirmé et volume relatif

Décision de recherche du24/10/2026. RSI abandonné à la demande de l'utilisateur. Les sources de `RESEARCH.md` ont été consultées avant ce protocole. Aucune performance de cette nouvelle règle n'a été calculée au moment de l'écriture.

Il s'agit d'une extension de notre ORB, pas d'une reproduction du portefeuille Stocks in Play : deux ETF au lieu de milliers d'actions, pas de classement top20, stop de range au lieu de10% ATR, confirmation close puis open suivant, objectif10R conservé de notre ORB. Les résultats publicitaires d'autres univers ne sont pas transférables.

## Règle principale

- SPY et QQQ séparément, RTH NYSE, historique SIP minute identique aux études précédentes, 100000USD initiaux par scénario, aucun intérêt de cash.
- Première plage09:30–09:35 : direction LONG si clôture09:34 > open09:30, SHORT si inverse, aucun trade en doji. Extrêmes calculés sur ces cinq minutes.
- RVOL = somme des volumes des cinq premières minutes aujourd'hui / moyenne des sommes des cinq premières minutes des14 séances immédiatement précédentes. Ces14 fenêtres doivent être intégralement valides, finies et de volume strictement positif. Ne pas remplacer une séance manquante par une autre. Au moins14 séances de chauffe, zéro ordre pendant une chauffe insuffisante. Le volume futur de la journée n'intervient jamais.
- RVOL >=1.0 pour le principal. Dès09:35, chercher la première clôture minute strictement au-delà du haut (LONG) / bas (SHORT) de la plage, seulement dans sa direction initiale. Entrer à l'open minute suivant, au plus tard11:29NY : entry_slot<120. Une entrée maximum par séance, aucun retournement/re-entry. Pour plage15min, mêmes règles avec volume15min.
- Quantité entière figée à la clôture du signal : floor(min(capital/prix_signal,1% capital/distance(prix_signal,stop))). Aucun redimensionnement avec l'open futur, ni annulation d'un ordre à cause de son futur gap.
- Stop à l'extrême opposé de la plage. TP10R calculé avec l'open d'entrée de référence et le stop figé, sans inclure les frais dans R. Open déjà au-delà du stop : entrée et sortie immédiates avec tous les coûts. Sinon stop/TP fixes ; stop prioritaire si les deux touchent dans la même minute. Stop gap au prix d'ouverture défavorable, TP gap au prix cible sans amélioration. Sortie sinon à l'open de dernière minute RTH (15:59,12:59 en demi-séance), avant son H/L.
- Frais inchangés : commission0.0035USD/action/côté, minimum0.35/côté ; friction défavorable0.01USD/action/côté ; emprunt SHORT1%/an, minimum1jour/360 sur notionnel d'entrée exécuté. Frictions stress0.02,0.03,0.05. Ce modèle de recherche n'est pas une cotation garantie de courtier.
- Aucun ordre broker ni changement des bots existants. Dividendes : pas de position overnight, aucun crédit de dividende ; aucune histoire de prix ajustée rétroactivement pour la règle d'ouverture.

## Couverture et calculs

Principal `complete_days` conditionnel à une journée complète, critère connu après coup : ne pas appeler cela un portefeuille continu observé. Diagnostic `resolved_prefix` sans ce filtre : un trou avant première décision possible rend le signal inconnu ; un trou pendant position rend la transaction entière non résolue et ses frais d'entrée connus sont exportés. Pas d'interpolation. Le compte conditionnel omet ces transactions ; zéro comptable n'est pas un rendement observé.

Les chauffe/filtres RVOL sont décisions sans ordre connues avant entrée ; fenêtres de volume inconnues explicitement comptées comme couverture insuffisante. Les marques de drawdown comprennent coût d'entrée, clôtures des minutes entièrement détenues et sortie nette ; les mèches de la minute de sortie intrabar ne sont pas considérées intégralement détenues. Le DD observé ne certifie pas le pire DD intrabar.

ALL2016-01-04–2026-10-16, A2016-01-04–2024-04-30, B2024-05-01–2026-10-16. Capital redémarré à100000 dans chaque période. B déjà explorée, pas nouvel OOS aveugle.

## Matrice fixée :12 variantes ×2 ETF ×3 périodes =72

`reference`, `cost_0.02`, `cost_0.03`, `cost_0.05`, `no_volume`, `volume_1.5`, `volume_2`, `range15`, `cutoff60`, `long_only`, `short_only`, `resolved_prefix`.

Comparer également l'ancien ORB (résultats archivés, entrée09:35 sans confirmation ni volume). Les variantes sont des sensibilités descriptives ; aucune n'est promue après observation. Une règle de volume sans confirmation ne fait pas partie de cette étude. Aucun balayage massif pour choisir un vainqueur.

Exporter transactions, journées, lacunes, features, agrégats annuels, mois, directions, concentration, stress, intervalles bootstrap par blocs et clusters annuels. Audit séparé des signaux, tailles, fills, frais et comptes. Toute correction après observation nécessite une nouvelle version documentée.
