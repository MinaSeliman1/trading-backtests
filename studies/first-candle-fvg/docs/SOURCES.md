# Sources et accès contrôlés le 19 octobre 2026

## Données et contrats

- [Documentation officielle yfinance — download](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) : restriction générale de l'intraday récent ; ne constitue pas la promesse d'un an en 1 minute. Ici les bougies ont été obtenues directement par l'endpoint chart public de Yahoo, sans yfinance, avec requêtes de sept jours dans une période récente de 28 jours. Les URL exactes et réponses brutes sont enregistrées dans `data/*/acquisition.json`. La disponibilité effective est attestée par ces réponses ; aucune garantie de rétention future n'est supposée.
- [ES — spécifications CME](https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html) : multiplicateur 50 USD/point, tick 0,25 point / 12,50 USD.
- [NQ — spécifications CME](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html) : multiplicateur 20 USD/point, tick 0,25 point / 5 USD.
- [NYSE — horaires et calendrier](https://www.nyse.com/markets/hours-calendars) : séance cash et clôtures écourtées. Le moteur s'appuie sur XNYS dans exchange-calendars, version figée dans le manifeste ; un fichier de calendrier explicite peut le remplacer.
- [Databento — OHLCV](https://databento.com/docs/schemas-and-data-formats/ohlcv) et [offre historique](https://databento.com/pricing/) : piste pour obtenir un historique long de véritables bougies 1 minute et des contrats identifiés. Aucun achat ni accès authentifié Databento n'a été réalisé. Vérifier la couverture et le coût du jeu de données avant de commander.

## Frais

- [IBKR — commissions actions](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php) : référence pour l'hypothèse de 0,005 USD/action, minimum 1 USD, plafond 1 % de la valeur. Réserve réglementaire additionnelle hypothétique : 0,0001 USD/action/côté. Cela ne reproduit pas exactement toutes les catégories de frais selon date, compte et lieu d'exécution.
- [IBKR — commissions futures](https://www.interactivebrokers.com/en/pricing/commissions-futures.php) : courtage et frais de marché doivent être distingués. Le montant tout compris retenu de 2,50 USD/contrat/côté est une hypothèse arrondie, pas un tarif officiel constaté pour votre compte. Les marges ES 25 000 / NQ 40 000 USD sont également des hypothèses. Le connecteur IBKR disponible a répondu « reauthentication required » ; aucune donnée de compte n'a été consultée.

## TradingView

- [Fonctionnement du Deep Backtesting](https://www.tradingview.com/support/solutions/43000666265-how-deep-backtesting-works/) et [profondeur disponible](https://www.tradingview.com/support/solutions/43000668210-how-much-data-is-available-for-deep-backtesting/) : Premium ou supérieur, plafond jusqu'à deux millions de bougies disponibles, selon le symbole. L'interface de votre session connectée a affiché « Current plan Basic » et proposé Premium lors de la demande Last 365 days. Aucun abonnement acheté.
- [Export des données du graphique](https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/) : export des données chargées. La boîte d'export a été atteinte ici ; aucun fichier n'a été reçu lors de l'essai. Aucun CSV TradingView n'est utilisé dans les résultats Python livrés.
- [Pine — stratégies et broker emulator](https://www.tradingview.com/pine-script-docs/concepts/strategies/) : exécution, intrabougie, slippage et commissions.
- [TradingView — risques de lookahead avec calc_on_order_fills](https://www.tradingview.com/support/solutions/43000614705-strategy-produces-unrealistically-good-results-by-peeking-into-the-future/) : l'avertissement affiché lors de la compilation doit être pris au sérieux. Le script fourni réserve le recalcul après fill au prix réellement exécuté et au stop déjà fixé ; il ne détecte pas de nouveaux signaux dans ce recalcul. Le rapprochement historique complet Python/TradingView demeure non effectué.
