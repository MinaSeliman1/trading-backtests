# Interprétation

Référence après frais : SPY +1.59 % / 78 trades ; QQQ +0.47 % / 97 trades. Les gains faibles sur ALL ne prouvent pas un avantage robuste ; examiner les périodes et le nombre de transactions.

SPY : 78 trades, seuil préétabli100. A -0.11 %, B +1.70 %, ALL sans top3 -0.33 %, ALL friction doublée +1.15 %. IC95 quotidien blocs20 [-0.065, 0.196] bps. Critères échoués : trades_all_ge100, reference_A_B_ALL_positive, all_without_top3_positive, A_double_friction_positive, all_block20_ci_lower_positive.

SPY, variante compression0.50 : 299 trades / +3.71 %. Elle n’est pas substituée à la référence pour atteindre un nombre de trades après avoir vu les résultats.

QQQ : 97 trades, seuil préétabli100. A +2.36 %, B -1.85 %, ALL sans top3 -3.67 %, ALL friction doublée -0.39 %. IC95 quotidien blocs20 [-0.203, 0.289] bps. Critères échoués : trades_all_ge100, reference_A_B_ALL_positive, all_without_top3_positive, all_block20_ci_lower_positive.

QQQ, variante compression0.50 : 295 trades / -3.62 %. Elle n’est pas substituée à la référence pour atteindre un nombre de trades après avoir vu les résultats.

Décomposition avec les quantités du compte net, pas portefeuille gratuit recalculé. Sans top3 neutralise ces retours sans nouvelles quantités. Filtre de journée entière futur dans complete_days ; resolved_prefix et inconnus publiés. Aucun carnet, tick ou preuve d’exécution réelle.

Les choix d’heures, seuils et variantes ont été figés avant PnL. Ces archives A/B ont déjà servi à de nombreuses recherches, SPY/QQQ corrélés et IC descriptifs sans correction de sélection multiple. Piste écartée pour un nouveau bot : les critères fixés avant les résultats ne sont pas tous satisfaits. Aucun nouveau bot ni passage au réel.
