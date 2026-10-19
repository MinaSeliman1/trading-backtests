# MISSION : BACKTEST RIGOUREUX D'UNE STRATÉGIE DE DAY TRADING

Tu es un expert en trading algorithmique, analyse quantitative, Python, Pine Script et backtesting financier.

Je souhaite tester objectivement une stratégie intraday appelée **Intraday Momentum « Noise Area » sur SPY**, publiée par Carlo Zarattini, Andrea Barbon et Andrew Aziz dans l'article *« Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY) »* (Swiss Finance Institute Research Paper N°24-97, 2024).

Mon objectif n'est pas de démontrer que cette stratégie fonctionne, mais de déterminer scientifiquement si elle possède un avantage statistique exploitable **aujourd'hui**, après des coûts réalistes, et en particulier **depuis sa publication** (mai 2024).

Je veux une véritable étude quantitative, avec des données historiques réelles, des simulations réalistes et des résultats reproductibles.

**RÈGLES ABSOLUES :**

* N'invente jamais de résultats, de statistiques ou de données historiques.
* Ne prétends jamais avoir exécuté un backtest si tu n'as pas réellement exécuté le code sur des données.
* Ne modifie jamais une règle de la stratégie pour améliorer artificiellement ses performances.
* Élimine tout lookahead bias et toute utilisation involontaire d'informations futures.
* Tiens compte des commissions, du slippage et des contraintes d'exécution.
* Documente chaque hypothèse et chaque limitation.
* Si une information est inaccessible, explique-le clairement et propose une solution réaliste.

Je préfère découvrir que la stratégie est perdante plutôt que recevoir des résultats artificiellement positifs.

---

# PARTIE 0 — SOURCE DE RÉFÉRENCE

## 0.1 Vérifier l'article original

Avant de coder, retrouve l'article original (SSRN / Swiss Finance Institute) et, si disponible, le code Python publié par les auteurs.

Les règles décrites ci-dessous sont mon résumé de l'article. **Si l'article ou le code des auteurs diffère de mon résumé sur un point, suis l'article, et liste chaque différence dans un tableau « Résumé utilisateur vs article ».**

Si tu ne peux pas accéder à l'article, indique-le clairement et applique les règles ci-dessous telles quelles, en les qualifiant d'interprétation.

## 0.2 Résultats annoncés par les auteurs (à vérifier, pas à croire)

D'après les résumés publics de l'article, sur la période mai 2007 – avril 2024, avec commissions de 0,0035 USD/action et slippage de 0,001 USD/action :

* Rendement total annoncé : environ 1 985 %.
* Rendement annualisé annoncé : environ 19,6 %.
* Ratio de Sharpe annoncé : environ 1,33 (contre environ 0,45 pour SPY buy & hold).

Ces chiffres sont **in-sample** pour les auteurs. Ils ne constituent pas une preuve. Ton travail est de les reproduire sur la partie de la période que tes données couvrent, puis de les confronter à la période **postérieure à la publication**.

---

# PARTIE 1 — DESCRIPTION DE LA STRATÉGIE

## 1. Marché et horaires

* Instrument principal : **SPY**.
* Fuseau horaire : `America/New_York`.
* Séance régulière uniquement : 9 h 30 – 16 h 00.
* Prendre correctement en compte : changements d'heure EST/EDT, jours fériés boursiers, séances écourtées (13 h 00), données manquantes.
* Aucune position overnight : tout est clôturé chaque jour.

## 2. La « zone de bruit » (Noise Area)

L'idée : chaque jour, le prix s'éloigne « normalement » de l'ouverture d'une certaine distance, qui dépend de l'heure. Tant que le prix reste dans cette zone, c'est du bruit. Quand il en sort, on suppose qu'un mouvement directionnel (momentum) est en cours.

### Calcul, pour chaque jour d et chaque minute t de la séance :

1. Mouvement depuis l'ouverture :

   `move(t, d) = | Close(t, d) / Open(9h30, d) − 1 |`

2. Mouvement moyen, à la même minute, sur les **14 séances précédentes** (le jour courant exclu) :

   `σ(t) = moyenne de move(t, d−1), …, move(t, d−14)`

3. Ajustement pour le gap overnight :

   * `Ref_haut = max(Open_aujourd'hui, Close_veille)`
   * `Ref_bas = min(Open_aujourd'hui, Close_veille)`

   `Close_veille` = clôture de la séance régulière de la veille (16 h 00), pas un prix after-hours.

4. Limites de la zone :

   * `Limite_haute(t) = Ref_haut × (1 + σ(t))`
   * `Limite_basse(t) = Ref_bas × (1 − σ(t))`

Il faut au moins 14 séances complètes d'historique avant le premier jour testé.

Les séances écourtées ne doivent pas fausser σ(t) pour les minutes après 13 h 00 : documente comment tu les traites.

## 3. VWAP intraday

Calculer le VWAP de la séance courante, recommencé chaque jour à 9 h 30 :

`VWAP(t) = Σ (prix_typique × volume) / Σ volume`, avec `prix_typique = (High + Low + Close) / 3`, sur les minutes de 9 h 30 jusqu'à t inclus.

Indique la formule exacte utilisée par les auteurs si elle diffère.

---

# PARTIE 2 — RÈGLES DE TRADING

## 4. Moments de décision

Les décisions ne sont prises **qu'aux demi-heures** : 10 h 00, 10 h 30, 11 h 00, …, 15 h 30.

Aucune décision entre deux demi-heures, ni pour entrer, ni pour sortir.

Le prix de décision est le **Close de la bougie 1 minute qui se termine à cette heure** (ex. pour 10 h 00 : la bougie 9 h 59 – 10 h 00).

Vérifie dans l'article si la première décision a lieu à 10 h 00 et adapte en le documentant.

## 5. Entrée

À chaque moment de décision, si aucune position n'est ouverte :

* **LONG** si `Prix > Limite_haute(t)`.
* **SHORT** si `Prix < Limite_basse(t)`.
* Sinon, rien.

## 6. Stop (trailing) et sortie

À chaque moment de décision, si une position est ouverte :

* **LONG** : sortir si `Prix < max(Limite_haute(t), VWAP(t))`.
* **SHORT** : sortir si `Prix > min(Limite_basse(t), VWAP(t))`.

Après une sortie, une nouvelle entrée (dans un sens ou dans l'autre) est possible au même moment de décision ou à un moment ultérieur, si les conditions d'entrée sont remplies. Vérifie la convention de l'article sur ce point (sortie seule ou retournement immédiat) et documente-la.

**Plusieurs trades par jour sont donc possibles.**

**Fin de journée :** toute position encore ouverte est fermée à la clôture de la séance (16 h 00, ou 13 h 00 les jours écourtés).

Pas de take profit fixe, pas de stop entre deux demi-heures (dans la version principale).

## 7. Exécution — deux conventions à comparer

* **Convention « article »** : exécution au prix de décision (Close de la minute), comme le font probablement les auteurs. Vérifie-le.
* **Convention « réaliste » (principale pour mes conclusions)** : exécution à l'**Open de la minute suivante**, avec slippage.

Présente les résultats des deux conventions côte à côte. Si l'écart est important, explique-le.

Clôture de fin de journée en convention réaliste : utiliser l'Open de la dernière minute de la séance (15 h 59), ou un ordre MOC simulé au prix de clôture officiel, en le documentant.

## 8. Dimensionnement de position

### Version principale (article) — ciblage de volatilité

* `σ_SPY` = écart-type des rendements journaliers de SPY (clôture à clôture) sur les **14 séances précédentes**.
* Levier cible : `levier = min(4, 2 % / σ_SPY)`.
* Nombre d'actions : `floor(Capital × levier / Open_aujourd'hui)`.
* Capital initial : 100 000 USD, capital courant ensuite (composition).

### Version sans levier (obligatoire)

* `levier = min(1, 2 % / σ_SPY)`.

Je veux savoir quelle part du résultat vient du **levier** et quelle part vient du **signal**.

Rappel : un levier intraday de 4x n'est accessible aux particuliers américains qu'avec un compte sur marge de plus de 25 000 USD (règle Pattern Day Trader). Mentionne cette contrainte dans la conclusion.

---

# PARTIE 3 — DONNÉES HISTORIQUES

## 9. Instruments

1. **SPY** — instrument principal.
2. **QQQ** — test de généralisation, **exactement les mêmes règles et paramètres**, sans réglage spécifique.
3. ES / NQ — optionnel, uniquement si tu disposes de données de futures avec échéances et raccordements vérifiables. Sinon, indique-le et passe.

Ne mélange pas les résultats des instruments.

## 10. Historique

Utilise de vraies données OHLCV 1 minute, **séance régulière**, prix **non ajustés pour l'intraday** (les ajustements de dividendes ne doivent pas modifier les niveaux intraday utilisés pour les signaux).

Source suggérée : **Alpaca, flux SIP**, qui fournit gratuitement de l'historique 1 minute depuis environ 2016 avec un compte. Vérifie la profondeur réellement disponible.

Prends l'historique le plus long disponible, idéalement **2016 → aujourd'hui**.

Si un dossier de données Alpaca existe déjà localement (projet précédent First Candle Rule), réutilise-le et complète-le, en vérifiant les empreintes et la qualité.

Ne reconstruis jamais des bougies 1 minute à partir de données plus larges. Ne génère jamais de données fictives.

## 11. Contrôle qualité

Avant chaque backtest :

* Vérifier timestamps et fuseaux horaires.
* Éliminer les doublons.
* Identifier les minutes manquantes, en particulier aux demi-heures de décision.
* Exclure les séances incomplètes, sans interpolation qui créerait de faux signaux.
* Vérifier la cohérence OHLC et la présence du volume (indispensable pour le VWAP).
* Respecter le calendrier NYSE.

Indique la provenance, la période et la qualité des données réellement utilisées.

---

# PARTIE 4 — SIMULATION RÉALISTE

## 12. Frais et slippage

Scénario de référence « article » :

* Commission : 0,0035 USD/action/côté (minimum 0,35 USD par ordre).
* Slippage : 0,001 USD/action/côté.

Puis analyse de sensibilité, scénarios identiques à l'exception des coûts :

* 1 cent (1 tick) par action et par côté.
* 2 cents.
* 3 cents.
* 5 cents.

Pour les positions SHORT : supposer l'emprunt disponible et appliquer un coût d'emprunt réaliste documenté.

Je veux savoir à partir de quel niveau de coût la stratégie cesse d'être rentable (**point mort en coûts**).

## 13. Prévention des erreurs

Vérifier notamment, avec des tests automatisés :

* σ(t) n'utilise **jamais** le jour courant ni des jours futurs.
* σ_SPY (levier) n'utilise que des clôtures passées.
* Le VWAP n'utilise que les minutes déjà terminées.
* Aucune décision hors des demi-heures prévues.
* Aucune position overnight.
* Aucun trade sur une séance exclue.
* Aucune utilisation de données after-hours pour Close_veille ou les signaux.
* Les ajustements de dividendes ne créent pas de faux gaps.

---

# PARTIE 5 — ANALYSE STATISTIQUE

## 14. Résultats demandés

Pour chaque instrument, chaque convention d'exécution et chaque version de levier :

**Performance**

* Rendement total et annualisé (CAGR).
* Ratio de Sharpe annualisé, ratio de Sortino.
* Volatilité annualisée.
* Nombre de trades, trades par jour, % de jours avec au moins un trade.
* Win rate, Profit Factor.
* Gain moyen, perte moyenne, ratio gain/perte.
* P&L moyen par trade en points de base (bps).
* Bêta et corrélation avec SPY buy & hold.

**Risque**

* Maximum drawdown (USD et %), durée du pire drawdown.
* Pire jour, pire mois, pire année.
* Plus longue série de pertes.
* Levier moyen et maximal réellement utilisé.

**Comportement**

* Résultats LONG vs SHORT.
* Résultats par heure d'entrée.
* Résultats par année.
* Résultats selon le niveau de volatilité (terciles de σ_SPY, et selon le VIX si tu as les données).
* Contribution des 10 meilleurs jours au résultat total.

**Graphiques**

1. Courbe de capital (stratégie vs SPY buy & hold), échelle logarithmique.
2. Drawdown.
3. Rendements annuels.
4. Rendements mensuels.
5. Distribution des rendements par trade.
6. Journal détaillé des trades (date, direction, heure d'entrée, prix, heure de sortie, prix, raison de sortie, actions, levier, frais, P&L net).

## 15. Benchmarks de contrôle

Pour savoir si le signal apporte vraiment quelque chose, compare la stratégie à :

1. **SPY buy & hold.**
2. **Direction aléatoire** : mêmes heures d'entrée et de sortie que la stratégie, mais sens LONG/SHORT tiré au hasard (au moins 1 000 simulations). La stratégie doit faire significativement mieux.
3. **Toujours LONG** aux mêmes moments d'entrée.

---

# PARTIE 6 — VALIDATION

## 16. Découpage temporel — LE POINT LE PLUS IMPORTANT

La stratégie a été conçue et publiée avec des données jusqu'en **avril 2024**. Découpe donc l'historique en :

* **Période A — reproduction** : début des données → 30 avril 2024. C'est de l'**in-sample** pour les auteurs. Objectif : vérifier si tu retrouves des résultats proches de ceux de l'article.
* **Période B — post-publication** : 1er mai 2024 → dernière date disponible. C'est un **vrai hors-échantillon** : les auteurs ne pouvaient pas connaître ces données. **C'est cette période qui compte le plus pour ma décision.**

Ne modifie aucun paramètre (14 jours, demi-heures, 2 % de volatilité, levier max 4) en fonction des résultats de la période B.

Ajoute un walk-forward par blocs (par exemple trimestriels ou semestriels), paramètres fixes, pour voir la stabilité dans le temps.

## 17. Robustesse (sans optimisation)

Tests de sensibilité, présentés comme tels, sans choisir le meilleur :

* Lookback de σ(t) : 10, 14, 20 jours.
* Fréquence de décision : toutes les 15 min, 30 min (principal), 60 min.
* Stop : VWAP seul, limite seule, max/min des deux (principal).
* Niveaux de coûts (cf. partie 4).

Estime l'incertitude statistique : bootstrap par blocs de jours (pas trade par trade), intervalle de confiance à 95 % du Sharpe et du rendement moyen journalier, pour la période B séparément.

## 18. Analyse critique

Réponds précisément :

1. Retrouves-tu des résultats proches de l'article sur la période A ? Sinon, pourquoi ?
2. La stratégie est-elle rentable **après publication** (période B), après frais réalistes ?
3. Fait-elle mieux que SPY buy & hold en rendement **ajusté au risque** ?
4. Bat-elle significativement le benchmark à direction aléatoire ?
5. Quelle part de la performance vient du levier ?
6. Les résultats dépendent-ils de quelques journées exceptionnelles (ex. mars 2020, avril 2025) ?
7. À partir de quel niveau de coût la stratégie devient-elle perdante ?
8. Fonctionne-t-elle sur QQQ sans réglage ?
9. Les LONG et les SHORT contribuent-ils de façon équilibrée ?
10. Les résultats suggèrent-ils un véritable avantage statistique ou simplement du hasard / un effet de période ?

Ne considère pas une stratégie comme profitable parce que son Sharpe est positif sur un petit échantillon.

---

# PARTIE 7 — CODE ET LIVRABLES

## 19. Implémentation Python

Backtest complet, vectorisé lorsque c'est possible, avec pandas / numpy / matplotlib.

Le programme doit :

* Charger les données 1 minute (Alpaca ou CSV externes).
* Calculer σ(t), les limites, le VWAP, σ_SPY et le levier.
* Simuler les décisions aux demi-heures, les entrées, les stops et la sortie de fin de journée.
* Appliquer les deux conventions d'exécution et tous les scénarios de coûts.
* Produire les tableaux, graphiques et journaux.

Fournis le code complet, les dépendances figées et les instructions d'exécution. Les clés API ne doivent jamais apparaître dans le code, les rapports ou le chat.

## 20. Pine Script v6 (TradingView)

Deuxième implémentation, graphique 1 minute :

* Calcul de σ(t) sur 14 jours (attention à la limite de bougies chargées sur un compte gratuit : documente combien de jours sont réellement testables).
* Affichage des limites haute/basse et du VWAP.
* Entrées/sorties uniquement aux demi-heures.
* Clôture en fin de séance.
* Compatible Strategy Tester, sans repainting ni information future.

Ne prétends pas avoir compilé le Pine Script dans TradingView si tu n'y as pas réellement accès.

## 21. Validation du code

* Exécuter réellement le code Python.
* Tester les fonctions critiques sur des scénarios contrôlés (petites séries artificielles **uniquement pour les tests unitaires**, jamais pour les résultats).
* Vérifier manuellement au moins 10 trades historiques (calcul des limites, du VWAP, de la décision, du P&L).
* Identifier toute fonctionnalité non testée.

---

# PARTIE 8 — RAPPORT FINAL

### A. Résumé exécutif

Conclusion objective et directe, en commençant par le résultat **post-publication (période B)**, convention réaliste, coûts de référence.

### B. Reproduction de l'article (période A)

Tableau : mes résultats vs résultats annoncés par les auteurs.

### C. Résultats post-publication (période B)

Tous les tableaux comparatifs.

### D. Risque, levier et coûts

### E. Robustesse et benchmarks de contrôle

### F. Code source et reproductibilité

Sources de données, dates, paramètres, instructions.

### G. Conclusion

Classe la stratégie dans l'une de ces catégories :

1. **Avantage statistique encourageant** — résultats positifs après frais, y compris après publication, avec validation solide.
2. **Potentiellement intéressante, mais preuves insuffisantes** — certains résultats positifs, incertitude importante.
3. **Aucun avantage démontré** — résultats non convaincants ou non robustes.
4. **Structurellement déficitaire dans les conditions testées** — pertes persistantes après frais.
5. **Impossible à évaluer sérieusement** — données ou exécution insuffisantes.

Explique les éléments qui justifient la classification.

Ne recommande pas le passage au trading réel uniquement parce que le backtest est positif.

---

# INSTRUCTION FINALE

**Ta priorité absolue est l'exactitude, pas la rentabilité apparente.**

Ne cherche pas à me convaincre que la stratégie fonctionne. Ne fabrique pas de résultats. Ne contourne pas les difficultés techniques avec des données fictives ou des hypothèses irréalistes.

Si la stratégie perd de l'argent, montre-le. Si elle semble rentable, démontre-le avec des données fiables, des frais réalistes et, surtout, sur la période postérieure à sa publication.

Si tu ne peux pas exécuter une partie du travail, indique précisément ce qui a été exécuté, ce qui reste non testé et pourquoi.

**Commence par retrouver l'article et vérifier les règles exactes, puis vérifie la disponibilité des données. Ensuite, implémente le backtest Python, exécute-le sur des données réelles, valide les résultats et réalise l'implémentation TradingView. Ne remplace jamais un résultat calculé par une estimation inventée.**