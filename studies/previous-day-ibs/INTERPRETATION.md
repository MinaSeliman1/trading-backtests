# Décision et interprétation — IBS précédent intraday

Statut : **adaptation intraday écartée pour un nouveau bot**.

| ETF | Trades ALL | Net cumulé | CAGR | Profit factor | DD observé |
|---|---:|---:|---:|---:|---:|
| SPY | 463 | -5,70 % | -0,54 % | 0.951 | 16,31 % |
| QQQ | 463 | 13,15 % | 1,15 % | 1.094 | 10,02 % |


Le seuil de référence 0,20, le sens LONG, le stop ADR14 et la sortie intraday ont été fixés avant le premier PnL de cette étude. Les variantes favorables ne remplacent pas cette référence après observation. Ce résultat concerne cette formalisation ; il ne réfute pas toutes les stratégies IBS qui détiennent des positions overnight ou pendant plusieurs jours.

## Stabilité temporelle

| ETF | A net % | B réutilisée net % | ALL sans trois meilleurs jours % |
|---|---:|---:|---:|
| SPY | -7,83 | 2,30 | -12,45 |
| QQQ | 12,24 | 0,86 | 3,69 |

Sur B réutilisée, QQQ ne gagne que **0,86 % sur 94 trades**, avec un drawdown observé de **7,71 %**. Sans ses trois meilleures séances, il perd **5,57 %** ; ces trois jours apportent 6705,75 USD pour un bénéfice total de 858,07 USD. Ce diagnostic ne constitue pas un nouveau sizing ou un nouveau backtest. Les références QQQ ne suffisent donc pas à établir un avantage exploitable prospectivement.

## Critères fixés avant PnL

- min100trades_ALL : passe
- six_references_positive : échoue
- sans_top3_ALL_positive : échoue
- doubled_friction_A_positive : échoue
- block20_ALL_lower_positive : échoue

## Variantes et limites

Toutes les variantes sont publiées, y compris les résultats positifs. Le contrôle toujours LONG a un nombre de trades, une exposition et une capitalisation différents ; une comparaison brute ne mesure pas un effet causal isolé du filtre IBS. Le même historique et B ont servi à de nombreuses hypothèses antérieures, sans correction globale de recherche multiple. Les intervalles bootstrap sont descriptifs.

Le principal applique un filtre de complétude de la séance connu après coup. La variante prefix le retire mais ne transforme pas les jours ou trades inconnus en portefeuille observé : leurs zéros servent au chaînage comptable seulement. Historique manquant avant décision et lacunes actives explicitement exportés, pas interpolés.

IBS publié vise souvent les rendements close-to-close : notre entrée du lendemain omet toute la nuit du signal. Pas de deuxième source de prix, de quotes bid/ask ou de carnet ; stops et frictions modélisés sur OHLC minute. Capital 1x, cash non rémunéré, pas de prétention à battre le passif à exposition égale. Aucun changement des deux simulations QQQ existantes ni aucun ordre broker.
