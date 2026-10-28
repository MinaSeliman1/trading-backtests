# Le premier retest ne fournit pas ici un avantage suffisamment robuste

Recherche reprise le28octobre2026 sur des règles établies le26 avant tout PnL. Publications universitaires, dépôts primaires, blogs spécialisés et forums ont été comparés ; les références de retest décrivent un comportement, pas la rentabilité de notre règle exécutable. [Sources et alternatives](RESEARCH.md).

| ETF | Trades ALL | Net cumulé | CAGR | Profit factor | DD observé |
| --- | --- | --- | --- | --- | --- |
| SPY | 497 | -6,16 % | -0,59 % | 0,853 | 8,80 % |
| QQQ | 509 | -5,50 % | -0,52 % | 0,907 | 10,71 % |

SPY perd en A (-4,95 %), B (-1,26 %) et ALL. QQQ gagne en B (2,78 %,138trades) mais perd en A (-8,06 %) et ALL. Le gain récent QQQ correspond à seulement 1,12 % annualisé dans ce compte ; ses intervalles bootstrap de B comprennent zéro. Marchés et B déjà explorés, aucune nouvelle preuve aveugle.

Les critères ≥100trades ALL/ETF passent, mais les quatre autres échouent : six références positives, ALL sans top3 positif, A à friction doublée positive et borne basse IC95 blocs20 ALL positive sur les deux ETF. Retirer les trois meilleures journées laisse ALL à -8,58 % SPY et -8,66 % QQQ. A à friction doublée donne -7,16 % et -11,23 %.

## Ce que les coûts et contrôles montrent

L’attribution de mouvement de prix est de -2030,61 USD SPY et 302,29 USD QQQ. SPY perd donc déjà avant attribution des coûts ; le faible gain de prix QQQ est absorbé par friction, commissions et emprunt. Cette attribution conserve les quantités du compte composé après frais : ce n’est pas un nouveau portefeuille recalculé sans frais.

Sans retest, ALL vaut -29,35 % SPY et -19,84 % QQQ. L’exposition RTH borne haute passe de 1,23 % à 11,53 % SPY, et de 1,57 % à 12,97 % QQQ. Stops, sizing et nombre de trades diffèrent aussi. Moins perdre ne prouve ni un avantage exploitable ni une causalité propre à l’attente. Ce contrôle OR15/2R n’est pas le bot ORB5minutes/10R actif.

15 lignes sur72sont positives, principalement sur B réutilisée ; elles se recouvrent. QQQ SHORTseul est positif sur ALL (4,58 %) et en B (5,48 %) mais négatif en A (-0,85 %). Cette variante ne remplace pas la référence après observation.

## Couverture et décision

Le principal exclut5séances SPY et4QQQ : trois ranges inconnus et une fenêtre de signal inconnue chacun, plus une journée SPY rejetée par le filtre futur OHLCV complet. Prefix retire ce filtre, ajoute un trade SPY perdant et donne -6,22 % ; QQQ reste à -5,50 %. Aucun trade entré non résolu, mais quatre opportunités de journée inconnues restent exclues par ETF. Zéro comptable d’exclusion n’est pas un résultat cash observé.

Décision : archiver cette formalisation, sans nouveau bot ni promotion d’un sous-ensemble gagnant. Fills sur OHLC minute sans carnet, ordre des ticks inconnu, frais fixes et emprunt non garanti, échantillons corrélés, recherches répétées et même source limitent les conclusions. Les deux bots QQQ Noise Area et ORB, leurs paramètres et journaux, restent inchangés par cette étude.
