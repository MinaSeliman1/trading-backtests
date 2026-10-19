# Implémentation Pine v6 — statut réel

Le 19 octobre 2026, `first_candle_fvg.pine` a été collé dans l'éditeur de la session TradingView connectée, puis ajouté avec succès au graphique SPY 1 minute. L'interface affichait la stratégie active « First Candle + FVG | recherche v1 » et ses paramètres. Aucune erreur de compilation n'a été affichée. Ce constat valide la compilation et l'ajout au graphique ; il ne constitue pas un backtest annuel ni un rapprochement des trades.

Le script a ensuite été enregistré dans votre espace privé sous le nom **First Candle + FVG | recherche v1** ; ce nom et une première révision datée Today, 13:19 ont été confirmés dans l'éditeur. Il n'a pas été publié.

La demande d'une période Last 365 days a déclenché l'écran Deep Backtesting indiquant « Current plan Basic », avec recommandation Premium. Le rapport affiché ne couvrait que le 19 octobre 2026 et indiquait qu'aucun trade n'avait été pris avec les paramètres courants. Cette séance encore en cours ne constitue pas une validation historique. L'export CSV n'a pas abouti pendant l'essai. Le code est aussi disponible localement.

## Utilisation

1. Ouvrir un graphique en bougies normales de **1 minute**, choisir SPY ou QQQ, ou un contrat futures daté, avec la bonne source de marché.
2. Coller le fichier entier dans l'éditeur Pine, remplacer tout modèle existant, puis Ajouter au graphique.
3. Exécuter séparément les stops A et B. Dans Propriétés, définir le slippage à 1, 2, 3 puis 5 ticks. Aligner le champ de slippage utilisé pour le dimensionnement.
4. ETF : les valeurs par défaut représentent 0,005 USD/action/côté. Le minimum de commission et le spread ne sont pas reproduits exactement par le broker emulator. Futures : changer la commission de Propriétés en coût USD/contrat/côté (hypothèse Python 2,50 USD), mettre les frais de dimensionnement à la même valeur, le minimum à zéro et le spread à zéro. Indiquer la marge du contrat. Adapter aussi les pourcentages de marge dans Propriétés ; les valeurs par défaut 100 % sont prévues pour ETF sans levier.
5. Pour les futures, indiquer la clôture de la séance cash (16:00 ordinairement, 13:00 pour les dates écourtées pertinentes). La valeur d'un input est constante dans une exécution : une période mélangeant des jours normaux et écourtés nécessite un calendrier codé/fourni et n'est pas validée par cette version. Les fermetures de jours fériés cash ne sont pas reconnues automatiquement sur le calendrier CME ; exclure ces dates dans l'analyse ou fournir un calendrier avant une étude longue.
6. Les zones et marques visuelles sont un aide-mémoire ; l'expiration de la boîte dessinée ne signifie pas que le setup a encore une confirmation valide. La fenêtre de confirmation est calculée séparément.

## Différences matérielles avec Python

- Les deux implémentations déterminent leur quantité au close de confirmation, sans utiliser l'open suivant. Python estime le prix d'entrée avec friction, intègre les frais exacts de son modèle et vérifie la capacité d'exposition/capital ; Pine utilise une approximation de ces réserves. Un gap modifie le risque effectif et le TP calculés après fill. Si un gap rend le stop invalide, Pine peut déjà avoir exécuté l'entrée et ferme alors la position ; Python rejette l'intention selon la convention de la mission. Ce rejet Python ne démontre pas qu'un véritable ordre au marché déjà envoyé aurait pu être annulé avant exécution.
- Les sorties stop/limite de TradingView suivent le chemin du broker emulator. La règle stop avant objectif quand les deux sont touchés n'est pas garantie. Le TP limite Pine peut être exécuté sans le slippage que Python applique à sa sortie au marché déclenchée au TP. Le Bar Magnifier fournit davantage d'information, mais change les hypothèses et ne remplace pas une convention pessimiste constante.
- `calc_on_order_fills=true` sert à calculer le TP sur `strategy.position_avg_price`. TradingView affiche un avertissement général de risque de lookahead. Le bloc de recalcul ne doit jamais lire high/low/close du bar de fill pour fabriquer une décision. Le code fourni utilise uniquement le fill et le stop fixé antérieurement dans ce bloc. La parité historique complète/realtime de ce comportement reste à vérifier.
- Python liquide à l'open de la dernière minute. Pine ferme immédiatement au close de la dernière bougie régulière détectée, ou à l'heure cash indiquée pour futures. Les clôtures et prix sont différents.
- Python exclut a posteriori toute séance incomplète pour une étude propre. Pine ne peut découvrir les trous futurs au moment du signal : il invalide le reste de la journée lorsqu'un trou apparaît. Des trades déjà exécutés restent dans le rapport.
- Python applique les minima de commission, une réserve de frais, un spread et un coût d'emprunt hypothétiques. Pine ne reproduit qu'une partie de ces coûts nativement.
- Sans contrat brut, source consolidée et calendrier identiques, des divergences de H/L et de signaux sont normales. Le graphique consulté ici utilisait le flux BATS/Cboe One, différent d'un OHLC consolidé Yahoo. Les continus ES1!/NQ1! peuvent produire d'autres écarts de raccordement.

Le Pine livré est donc un outil de comparaison et de visualisation compilé, avec des limites identifiées. Il ne satisfait pas à lui seul toutes les exigences d'une simulation pessimiste stricte ; le moteur Python et ses données auditables font référence pour cette étude.
