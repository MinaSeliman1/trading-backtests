# Vérification finale

- Suite Python exécutée sur la version livrée : **30 tests passants**, aucune erreur, dernier passage en 10,22 secondes. Les fixtures artificielles servent exclusivement aux tests.
- Le test `test_order_quantity_is_fixed_before_next_open_is_observed` a d'abord échoué sur la version initiale, puis passé après correction. La quantité ne dépend plus du prix d'ouverture suivant. La suite complète a ensuite été relancée.
- **72 scénarios historiques** exécutés sur les fichiers réels du manifeste. **26 trades** des scénarios principaux rapprochés des OHLC, des règles, des unités monétaires et des calculs de risque/P&L par `audit_historical_trades.py`. Il existe des trades communs entre variantes ; ces 26 lignes ne sont pas indépendantes.
- Les empreintes SHA-256 des modules Python courants ont été comparées au manifeste de cette exécution : concordance vérifiée.
- Figures générées et comparaison des courbes de capital inspectée visuellement.
- Pine v6 réellement compilé et ajouté au graphique TradingView, puis sauvegardé dans l'espace privé. La demande de backtest annuel a été bloquée par l'abonnement Basic. Le rapport sur la séance en cours du 19 octobre indiquait zéro trade. Aucun historique annuel Pine ni rapprochement Python/Pine complet n'est revendiqué.

## Ce qui reste non validé

- Au moins une année de performances historiques, partition IS/OOS et walk-forward sur un vrai historique long. Le test de découpage chronologique vérifie la logique de seuil ; il ne remplace pas l'exécution complète sur plusieurs années.
- Bootstrap sur des performances de marché suffisamment nombreuses. Seul l'algorithme a été testé sur une fixture, les seuils de calcul historiques n'étant pas atteints.
- Rollover historique réel entre plusieurs contrats, marges historiques datées et fermetures CME exceptionnelles. L'échantillon récent utilise un contrat daté fixe et la plage cash XNYS.
- Emprunt historique des ETF, carnet d'ordres, spread effectif, latence, volumes disponibles au prix, fills partiels et ordre subminute des touches stop/TP.
- Annulation effective d'un ordre au marché déjà envoyé si son stop ou son financement devient invalide au premier prix suivant. Le rejet de simulation reste une convention déclarée.
- Parité du broker emulator TradingView avec la convention pessimiste Python, avec ses frais complets, ses rejets et ses sorties.

Conclusion de vérification : moteur exécuté et vérifié sur un échantillon réel court, avec limites documentées. **Cela ne démontre pas un avantage statistique exploitable.**
