# Recherche — effet fin/début de mois en intraday

26 octobre 2026, avant PnL. Famille calendaire distincte des signaux EMA, réintégrations, RSI, ORB et VWAP déjà étudiés. Tester si une saisonnalité connue en rendements quotidiens subsiste dans les seules heures régulières.

| Source consultée | Observation et limite |
| --- | --- |
| [Forum r/algotrading, End-of-Month Rally](https://www.reddit.com/r/algotrading/comments/q1pmqj/endofmonth_rally/) | Auteur teste des maintiens sur plusieurs jours et choisit après optimisation des décalages. Source d'idée, pas preuve de notre intraday. Nous ne reprenons ni ses chiffres ni son optimisation2–22jours. |
| [Forum r/quant](https://www.reddit.com/r/quant/comments/h7ri1s/turn_of_the_month/) | Question sur l'explication du phénomène ; aucun journal de transactions accessible dans la page lue. Pas une validation. |
| [paappraiser/almanac-trading-strategies](https://github.com/paappraiser/almanac-trading-strategies) | README présente14règles, un composite/poids optimisés et une fenêtre finmois+4premières séances, différente de la fenêtre classique+3. Les résultats du composite ne sont pas ceux d'une stratégie calendaire intraday isolée. Le README a été lu ; les fichiers source demandés n'ont pas pu être récupérés (cache miss), aucune prétention d'audit de leur code. Aucun code tiers exécuté. |
| [QuantConnect, Turn of the Month](https://www.quantconnect.com/research/15377/turn-of-the-month-in-equity-indexes/) | Exemple explicite : achat SPY en fin de mois, maintien3séances. Sert à préciser le dernier jour et les3premiers. Notre variante ferme chaque jour : adaptation volontaire, pas réplication du maintien overnight. |
| [Thaler1987, page AEA](https://www.aeaweb.org/articles?id=10.1257/jep.1.2.169) | Page et abstract lus : anomalies calendaires, dont fin/début de mois et effets intraday. Ne fournit aucune performance actuelle de nos ETF. |
| [McConnell/Xu, Equity Returns at the Turn of the Month](https://www.tandfonline.com/doi/abs/10.2469/faj.v64.n2.11) | Référence primaire repérée par recherche ; accès direct bloqué403 et SSRN503. Résumé indexé repère la fenêtre dernière séance+3premières, mais texte intégral non lu et aucun chiffre de l'article utilisé pour nos conclusions. |

Comparaison initiale : relative strength SPY/QQQ pourrait demander un modèle à deux jambes et double coût ; Dual Thrust reste une cassure proche de familles déjà examinées. La saisonnalité offre une hypothèse différente, un signal connu à l'avance et un contrôle simple : exactement les mêmes ordres les autres jours.

Choix propre : LONG uniquement dernier jour de bourse et3premiers du mois, achat09:35NY, stop fixe1%depuis le close09:34, sortie dernier open RTH. Les décisions de calendrier ne regardent aucun prix futur ; le calendrier historique reconstruit n'est toutefois pas un fichier point-in-time des annonces de fermetures exceptionnelles.

Cette étude ne prouve pas des flux de fonds comme cause, ni que la saisonnalité quotidienne vient des heures intraday. Pas de rendement overnight importé, ni choix de fenêtre après PnL. Même source et périodes déjà explorées : sélection d'hypothèse supplémentaire, B pas nouveau holdout aveugle.
