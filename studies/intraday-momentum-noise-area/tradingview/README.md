# Pine v6 — statut vérifié et limites

[Code complet](noise_area.pine). Compilé et sauvegardé réellement dans TradingView le 19 octobre 2026, sous « Noise Area | recherche v1 », version 3. Script privé, aucune publication et aucun ordre réel. [Capture du graphique](compilation_tradingview.png).

Le graphique 1 minute accessible au compte n'a fourni que la séance du 19 octobre 2026 au Strategy Tester : **zéro trade**. Cela vérifie l'acceptation du code par TradingView, pas ses performances, ses ordres historiques ni sa concordance avec Python. Le tableau de diagnostic n'a pas été observé à l'écran. Aucun résultat annuel TradingView n'est revendiqué.

Le forfait Basic annonce 5 000 bougies intraday : quatorze séances pleines représentent déjà 5 460 bougies, avant la séance courante. Les quinze clôtures nécessaires aux quatorze rendements de dimensionnement demandent encore plus d'historique. Ce forfait ne permet donc pas de valider cette stratégie correctement sur un graphique SPY 1 minute ordinaire. [Limites TradingView](https://www.tradingview.com/pricing/).

Le script trace les bandes et le VWAP HLC3 et utilise les mêmes signaux principaux, aux demi-heures seulement. Les ordres au marché sont exécutés au prochain open. Il demande un graphique 1 minute, des prix non ajustés et l'historique régulier suffisant. La fermeture est programmée pour l'open de 15:59, ou de 12:59 sur les demi-séances répertoriées de 2016 à 2026. Le calendrier doit être prolongé pour les années suivantes.

Différences documentées avec Python :

- Slippage TradingView en ticks entiers : 1 tick = 0,01 USD sur SPY/QQQ. Le coût de référence Python de 0,001 USD ne peut pas être représenté exactement par ce paramètre.
- Commission de 0,0035 USD/action, sans minimum de 0,35 USD par ordre dans cette implémentation Pine ; emprunt SHORT absent.
- Marge simulée à 25 % dans TradingView, susceptible d'entraîner des liquidations que Python ne modélise pas.
- Flux du graphique et événements de dividendes TradingView différents des acquisitions SIP et de la réconciliation Python. `request.dividends` utilise `lookahead_off`, mais la disponibilité historique des annonces n'a pas été auditée.
- Pine ne peut exclure à l'ouverture une séance dont une minute sera absente plus tard. Python applique l'exclusion complète demandée après contrôle de l'acquisition ; cette sélection de données est une limite de comparabilité en temps réel.
- La suppression ou modification ultérieure de données par le fournisseur peut affecter une relance. Aucun futur n'entre volontairement dans les indicateurs, mais la parité de signaux sur une longue période n'a pas été testée.

Pour une vérification utile : charger assez de minutes réelles, comparer les journaux aux exports Python aux mêmes dates et paramètres de coûts, puis expliquer les différences de flux et de simulateur. Le backtest de référence livré reste celui de Python.
