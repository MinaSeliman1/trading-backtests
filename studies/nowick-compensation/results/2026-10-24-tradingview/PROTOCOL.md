# Exécution TradingView demandée le24octobre2026

**Statut initial : en attente d'accès à l'éditeur ; aucune performance observée.** Objectif obligatoire : au moins100transactions fermées distinctes par paire, avec règles et coûts inchangés. Moins de100 signifie objectif non atteint, pas un échantillon validé.

## Référence figée avant résultats

Source prévue : TradingView, flux OANDA, GBPUSD/USDJPY/AUDUSD, chandeliers ordinaires15m. Fichiers Pine USD et JPY du commit `c16a44b9640a45c59ab7a6998201d20c859c0c0c`, éventuellement corrigés uniquement pour une erreur de compilation/exécution ou enrichis de métadonnées d'audit ; toute modification sera explicitée avec ses empreintes avant réexécution.

Structure5, Nowick sans tolérance, limite à l'ouverture, durée9barres, front-runON, buffer3pips, SL5–30pips, TP1R, risque de prix1%, quatre filtresOFF. Devise de cotation, pointvalue1, frais aller-retour1pip par commission cash/unité/côté (.00005USD ou .005JPY), slippage0. Pénétration ceil(1pip/mintick), habituellement10ticks, appliquée aux limites d'entrée et de TP. Ni recalcul au fill, ni calcul à chaque tick, ni remplissage sur clôture. Aucun ordre broker.

## Accès et profondeur

Le navigateur est connecté et affiche le forfait Basic. Une promotion initiale «Ad blocker detected» a recouvert l'éditeur ; l'autorisation des publicités a été demandée à l'utilisateur, sans modifier ses réglages de confidentialité. L'application Desktop est séparément non connectée. Aucun nom de compte, courriel, cookie ou secret n'est archivé.

La documentation annonce environ5000barres intraday pour Basic, et le Deep Backtesting pour Premium et supérieur. Cette limite ne suffit pas, à elle seule, à déterminer le nombre de trades. Exécuter la référence sur la couverture réellement accessible, relever sa date de début/fin et son compte de transactions ; ne pas déclarer100trades sans les observer.

Si moins de100trades : vérifier les moyens natifs disponibles pour étendre l'historique, notamment Bar Replay selon les droits du compte. Un écran d'abonnement n'est pas contourné et aucun abonnement/essai payant n'est acheté. Si l'extension est inaccessible, documenter la limite et garder l'objectif100non atteint. Ne modifier ni tolérance, ni pivots, ni paire, ni paramètres pour multiplier artificiellement les trades ; ne dupliquer aucun segment historique. Un moteur externe serait une autre exécution, à ne pas présenter comme TradingView.

## Résultats et audit attendus

- Export séparé des transactions et des métriques, octets d'origine et SHA256 conservés ; les éventuels relevés manuels sont explicitement étiquetés.
- Réglages effectifs vérifiés dans les Propriétés pour chaque devise. Bar Magnifier activé seulement si disponible ; sinon son absence est signalée. Le flux et le compte de barres ne sont pas déduits d'une date input.
- Transactions fermées uniques, dates effectives, PnL net, frais, WR/Wilson, PF, espéranceR, série de pertes, DDferméR, DDintratrade%, position ouverte finale et ambiguïtés natif/stress. Recalcul indépendant des mesures que les exports permettent réellement de reconstruire ; métriques non vérifiables indiquées comme telles.
- Résultats négatifs conservés. Le stress utilise les tailles natives et ne représente ni un autre portefeuille ni une borne garantie. Front-run natif à clôture15m et fills limites demeurent approximatifs.

## Sources consultées pour l'accès

- [Limites intraday](https://www.tradingview.com/support/solutions/43000480679-historical-intraday-data-bars-and-limits-explained/).
- [Deep Backtesting : fonctionnement et forfaits](https://www.tradingview.com/support/solutions/43000666265-how-deep-backtesting-works/).
- [FAQ des stratégies : export et Bar Replay](https://www.tradingview.com/pine-script-docs/faq/strategies/).
- [Export des données d'une stratégie](https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/).
