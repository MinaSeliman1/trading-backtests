# Décision après résultats — lecture par ETF

Référence choisie avant calcul, pas après tri des72scénarios. Aucun nouveau bot installé : la demande portait sur recherche/backtest/publication. Noise Area et ORB continuent avec leurs paramètres existants.

## QQQ : candidat historique, pas avantage confirmé

ALL+44,75%,915trades,PF1,166,drawdown observé14,26%. A+11,54%/690trades et B+29,75%/225trades. B hors calendrier A mais déjà explorée dans d'autres études ; elle n'est pas un nouvel échantillon aveugle.

Le résultat ALL reste+20,74% sans ses trois meilleurs jours, B+11,25%. En revanche A devient−0,95% avec cette ablation ; A passe de+11,54% à−2,29% en augmentant la friction de0,01 à0,03USD/action/côté. L'essentiel de l'amélioration récente est visible en2024–2025. L'intervalle bootstrap20séances de la moyenne journalière ALL inclut zéro, alors que celui de B reste positif ; ce désaccord descriptif ne se résout pas en choisissant l'intervalle favorable.

Le filtre n'est pas une amélioration garantie : confirmation seule, sans volume, ALL+54,71%/2316trades/DD18,68%, contre+44,75%/915/DD14,26% avec volume. B sans filtre+45,46%/DD7,64%, contre+29,75%/DD5,48%. Les comptes sont redimensionnés séparément ; moins d'exposition ne permet pas d'attribuer automatiquement une meilleure qualité au volume. Des seuils RVOL plus forts1,5/2 deviennent négatifs sur ALL QQQ.

Lecture : garder cette version comme candidat de comparaison future aux règles figées, sans remplacer le bot ORB actif ni conclure qu'elle est meilleure que Noise Area. Une future simulation distincte demanderait des observations nouvelles, une comparaison des fills et un échantillon prospectif suffisant ; aucun passage automatique en réel.

## SPY : ne pas retenir cette version

ALL−5,04%,899trades,PF0,969,DD13,51%. A seulement+0,44%, B−5,46%/213trades. Les variantes volume1,5/2 qui semblent positives sur ALL restent négatives en B et réduisent fortement le nombre de trades. Elles ne remplacent pas la référence après observation. Aucun bot SPY proposé.

## Ce que la recherche a réellement apporté

Une hypothèse mécanique et une comparaison reproductible, pas une stratégie universellement supérieure. Les forums aident à identifier les problèmes de réplication ; les dépôts ouverts révèlent parfois des paramètres divergents ou des recherches massives. La publication originale porte sur des actions à activité anormale, pas un simple filtre de volume sur deux ETF. Notre adaptation doit être jugée sur nos propres coûts et données conditionnelles.

Les conclusions dépendent des trades SIP1min, de la couverture, du modèle de coûts et de l'historique déjà examiné. Les résultats QQQ/SPY ne sont pas deux expériences indépendantes. Les tableaux d'incertitude et les variantes ne corrigent pas les essais multiples effectués dans ce dépôt.
