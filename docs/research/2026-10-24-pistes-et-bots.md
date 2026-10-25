# Pistes retenues et simulations — bilan du 24 octobre 2026

**Aucune stratégie n’a encore démontré un avantage prospectif avec nos bots.** Les deux expériences QQQ à poursuivre sont Noise Area en priorité et ORB cinq minutes en second. « Prometteuse historiquement » et « rentable en simulation prospective » restent deux constats différents.

Les chiffres historiques ci-dessous reprennent B du 1er mai 2024 au 16 octobre 2026, déjà explorée. Ils utilisent la friction0,01USD/action/côté, commission0,0035/action/côté minimum0,35, empruntSHORT1%/360. Pour faciliter la lecture, le tableau utilise le plafond1x des deux études ; les règles de sizing et le temps d’exposition restent différents, sans prétendre à une comparaison à risque égal.

| Piste QQQ | Historique B au plafond1x, après frais | Appréciation | Bot actuel |
| --- | --- | --- | --- |
| Noise Area, entrée next-open | +27,17%, 504trades, PF1,319, DD minute7,48% | La plus intéressante de nos pistes historiques ; à confirmer sur nouvelles observations | Oui, simulation locale SIP différée16min ; version installée à cible de volatilité2%, plafond4x |
| ORB cinq minutes, stop prioritaire | +7,76%, 615trades, PF1,067, DD minute10,45% | Avantage historique faible : B devient−0,94% en mettant à zéro ses trois meilleurs jours | Oui, simulation locale SIP différée16min, risque1%, plafond1x |
| Opening Gap Reversal | +8,47%, 18trades | Échantillon B trop petit ; piste de réserve, pas une stratégie validée | Non |

Sources : [Noise Area](../../studies/intraday-momentum-noise-area/results/2026-10-19/comparison_all.csv), [ORB](../../studies/opening-range-5m/results/2026-10-20/comparison_all.csv), [Gap Reversal](../../studies/opening-gap-reversal/results/2026-10-20-v3/comparison_all.csv). Paramètres d’extraction Noise : QQQ, principal, B, next_open, leverage_cap1, slippage0.01. ORB : QQQ, B, both, complete_days, stop_first, slippage0.01. Gap : QQQ, B, reversal, complete_days, slippage0.01.

La version Noise Area installée a un **plafond4x**, pas une exposition constante4x. Son historique B correspondant aux coûts0,01 est +54,30%, PF1,307, DD16,11%. Il ne faut pas la comparer directement au bot ORB1x en concluant que le rendement supplémentaire est un meilleur signal. Le compte de Noise Area n’est pas remis à zéro pour cette note.

## État réellement observé des bots

Lecture seule des deux monitors le 24 octobre, heure de Toronto ; [snapshot horodaté](../../studies/rsi2-intraday/results/2026-10-24-v1/BOT_STATUS_READONLY.json). Aucun appel API, lecture de clés, ordre ou changement de journal/paramètres pour ce bilan.

- **Noise Area QQQ** : moteur actif, en attente de séance ; à plat, aucun ordre en attente. Référence prospective à partir du21octobre, **zéro séance entièrement prospective qualifiée**. Les21/22/23octobre ont des défauts de couverture ou des rattrapages. Le solde simulé réalisé est97567,76USD ; variation depuis le solde de référence99237,20USD : **−1669,43USD**, comprenant les observations non qualifiées/rattrapées. Ce résultat n’est pas une performance prospective validée, et le zéro des trades qualifiés ne veut pas dire qu’aucune transaction globale n’a été simulée.
- **ORB QQQ** : moteur actif, en attente hors séance ; solde100000USD, aucune transaction. Première séance éligible **lundi26octobre2026**. Aucun trade ou avantage prospectif encore observé.

Les deux protections contre la veille automatique sur secteur sont actives au moment du contrôle. Le couvercle, les arrêts manuels, la connexion et les pannes peuvent encore interrompre la couverture. Le correctif de veille du24octobre ne requalifie pas les séances antérieures manquées.

Ces bots simulent des fills localement sur données consolidées SIP retardées de16minutes. Ils n’envoient **aucun ordre paper ou réel**. Les prochaines revues doivent mesurer couverture à l’heure, coûts, drawdowns et concentration sur de nouvelles séances ; aucun passage automatique en réel. Les seuils20séances, puis60séances/50trades, déclenchent une revue et ne prouvent pas une rentabilité.

## Pistes écartées et nouvelle étude

**RSI(2) intraday** vient d’être testé, sans installer de bot : référence ALL SPY−5,47%/1591trades, QQQ−17,18%/1713trades ; A et B négatives. [Rapport complet](../../studies/rsi2-intraday/results/2026-10-24-v1/RAPPORT_FINAL.md). La variante seuil10 positive uniquement en B ne remplace pas la référence après observation ; elle demeure négative en A et sur ALL. Cette formalisation est archivée.

Nowick est abandonnée conformément à la demande de Mina ; ses résultats restent archivés. FVG, momentum de clôture, retour VWAP et NR7 n’ont pas fourni de preuve suffisante pour installer un nouveau bot. Les conclusions restent propres à chaque formalisation et à la couverture testée.

**Aucun bot SPY n’est installé.** Il n’existe à ce jour ni nouvelle piste SPY retenue pour simulation, ni stratégie de ce dépôt autorisée à passer en réel sur la seule base des backtests.
