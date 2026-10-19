# Examen de trades historiques et rapprochements arithmétiques

Les deux exemples SPY ci-dessous sont les premiers LONG et SHORT chronologiques du scénario IS A, sans sélection selon leur résultat. Les valeurs ont été relues dans le CSV Alpaca, distinctement du journal. Horaires New York ; les timestamps des bougies sources sont leurs ouvertures.

## SPY — LONG du 4 janvier 2023, stop A

Opening range 09:30–09:34 : H = 383,28 ; L = 381,90. Triple FVG 09:35, 09:36, 09:37 : high de la première = 383,27 ; low de la troisième = 383,325. La bougie centrale ouvre à 383,16 ≤ H et clôture à 383,48 > H. Le FVG [383,27 ; 383,325] n'existe qu'au close 09:38.

La bougie 09:38 descend seulement à 383,35 : aucun retest. La bougie 09:39 touche [383,032 ; 383,38], donc reteste ; information connue à 09:40. La bougie 09:40 ouvre à 383,19 ≤ close précédent 383,20 et clôture à 383,79 ≥ open précédent 383,38. Elle est haussière après une bougie baissière : confirmation connue à 09:41.

Stop : plus bas retest–confirmation 383,032, moins un tick, arrondi vers le bas = **383,02**. Estimation d'entrée au passage de l'ordre à partir du close 383,79 : 383,81 après friction/arrondi ; quantité fixée à **260 actions**, principalement contrainte par l'exposition sans levier. L'open suivant, 09:41, vaut 383,78 : fill simulé 383,80 après friction. Le TP dépend de ce fill : 383,80 + 3 × 0,78 = **386,14**.

À 09:44, le low 382,44 traverse le stop. Sortie défavorable simulée 383,00. P&L brut : (383,00 − 383,80) × 260 = −208,00 USD. Frais : 1,326 USD par côté, soit 2,652 USD. **Net −210,652 USD ; risque initial 202,80 USD ; résultat −1,038718R.** La taille est fixée avant lecture de l'open d'entrée.

## SPY — SHORT du 9 février 2023, stop A

Opening range : H = 414,57 ; L = 413,76. Triple 09:53, 09:54, 09:55 : low de la première 413,63 ; high de la troisième 413,525, donc FVG baissier [413,525 ; 413,63] connu à 09:56. La bougie centrale ouvre à 413,86 ≥ L et clôture à 413,4884 < L.

Premier retest : bougie 09:56, fourchette [413,42 ; 413,66], connue à 09:57. La bougie précédente à la confirmation, 09:57, est haussière (413,55 → 413,62). La confirmation 09:58 est baissière : open 413,63 ≥ close précédent 413,62 ; close 413,30 ≤ open précédent 413,55. Signal connu à 09:59.

Plus haut depuis retest = 413,81 ; stop = **413,82**. Prix estimé à l'ordre 413,28 ; **243 actions** fixées avant le prochain open. Open réel de 09:59 = 413,26 ; fill SHORT après friction = **413,24**. Risque unitaire 0,58 ; TP **411,50**. Le high de la bougie 10:08 atteint 413,88 ; stop exécuté défavorablement à 413,84.

P&L brut : (413,24 − 413,84) × 243 = −145,80 USD. Commissions/réserve aller-retour = 2,4786 USD ; emprunt hypothétique d'une journée = 243 × 413,24 × 0,01 / 360 = 2,78937 USD. **Net −151,06797 USD ; risque initial 140,94 USD ; résultat −1,071860R.**

## QQQ — SHORT du 4 janvier 2023, stop A

Premier SHORT chronologique QQQ IS A. Opening range : H = 266,82 ; L = 264,88. Triple 09:59, 10:00, 10:01 : low initial 265,17 ; high final 265,05. La bougie centrale ouvre à 265,33 ≥ L et clôture à 264,54 < L ; FVG [265,05 ; 265,17] connu à 10:02. La bougie 10:02 le reteste et monte jusqu'à 266,26. La bougie 10:03 est baissière après une haussière : 265,52 ≥ close précédent 265,51, puis 264,765 ≤ open précédent 264,86. Signal connu à 10:04.

Estimation de vente au passage de l'ordre : 264,75 ; quantité **321 actions**, respectant un budget estimé de **499,9748875 USD** frais compris. L'open suivant 264,80 donne un fill **264,78** après friction et arrondi. Stop **266,27**, risque exécuté 1,49 × 321 = **478,29 USD** ; TP **260,31**. La bougie 11:31 atteint le stop et le fill simulé est **266,29**. Brut −484,71 USD ; commissions/réserve 3,2742 USD ; emprunt 2,360955 USD. **Net −490,345155 USD ; −1,025205R.** La différence entre risque estimé et exécuté vient du prix d'ouverture suivant, sans modification rétroactive de la quantité.

## QQQ — LONG du 9 janvier 2023, stop A

Premier LONG chronologique QQQ IS A. H = 271,91 ; L = 270,82. Triple 09:44–09:46 : high initial 271,975 ; low final 272,15 ; bougie centrale 271,88 → 272,189 traversant H. FVG [271,975 ; 272,15], connu à 09:47. Retest par la bougie 09:47 dont le low est 272,11, connu à 09:48. L'englobante 09:48 ouvre à 272,32, égal au close précédent, puis clôture à 272,58 ≥ open précédent 272,34. Signal connu à 09:49.

Open suivant 272,59 ; entrée simulée **272,61**, stop **272,10**, TP **274,14**, quantité **363 actions**. La bougie 10:35 atteint 274,18, au-dessus du TP. Sortie déclenchée avec friction **274,12** ; brut 548,13 USD ; frais 3,7026 USD. **Net +544,4274 USD ; risque initial 185,13 USD ; +2,940784R.** Cet exemple positif est retenu parce qu'il est le premier LONG, sans condition sur son résultat.

## Séance SPY exclue

Le 5 juin 2023, les quatre minutes absentes sont 09:52, 09:53, 09:54 et 09:55. Les cinq premières minutes sont présentes. La politique stricte, fixée avant les résultats, exclut toute la séance, sans reconstruire de bougies ni conserver seulement ses parties complètes.

Ces lectures sont des contrôles d'exemples, pas un contrôle manuel de tous les trades. L'audit automatisé indépendant complet des scénarios principaux est documenté séparément dans `audit_validation.json`.
