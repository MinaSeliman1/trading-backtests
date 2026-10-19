# MISSION : BACKTEST RIGOUREUX D'UNE STRATÉGIE DE DAY TRADING

Tu es un expert en trading algorithmique, analyse quantitative, Python, Pine Script et backtesting financier.

Je souhaite tester objectivement une stratégie intraday appelée **First Candle Rule + Fair Value Gap (FVG)**.

Mon objectif n'est pas de démontrer que cette stratégie fonctionne, mais de déterminer scientifiquement si elle possède un avantage statistique exploitable sur les marchés financiers.

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

# PARTIE 1 — DESCRIPTION EXACTE DE LA STRATÉGIE

## 1. Marchés et horaires

La stratégie fonctionne pendant la séance américaine.

Fuseau horaire : `America/New_York`.

Horaires :

* Ouverture : 9 h 30.
* Fin de séance normale : 16 h 00.
* Première bougie analysée : 9 h 30 à 9 h 35.
* Uniquement les données de la séance régulière.

Prendre correctement en compte :

* Les changements d'heure EST/EDT.
* Les jours fériés boursiers.
* Les séances écourtées.
* Les données manquantes.
* Les particularités horaires des contrats futures.

Pour ES et NQ, limiter les signaux à la plage américaine définie ci-dessus, même si ces instruments se négocient également en dehors de cette plage.

## 2. Identification des niveaux importants

Utiliser le graphique 5 minutes.

Attendre la clôture complète de la première bougie :

**9 h 30 – 9 h 35.**

Identifier :

* H = prix le plus haut de cette bougie.
* L = prix le plus bas de cette bougie.

Tracer deux niveaux horizontaux :

* Opening Range High (H).
* Opening Range Low (L).

Ces niveaux restent fixes pendant toute la journée.

Ne jamais utiliser H ou L avant 9 h 35.

Les niveaux doivent être calculés uniquement à partir des cinq bougies de 1 minute comprises entre 9 h 30 et 9 h 35.

## 3. Identification du Fair Value Gap

À partir de 9 h 35, passer sur le graphique 1 minute.

Rechercher une cassure d'un des niveaux H ou L accompagnée d'un FVG.

Le FVG doit être constitué de trois bougies consécutives entièrement formées après 9 h 35.

### Scénario acheteur (LONG)

Conditions :

1. Le prix franchit H.
2. La deuxième bougie du modèle FVG traverse H dans le sens haussier.
3. Un FVG haussier se forme.

Définition :

`Low(bougie 3) > High(bougie 1)`

La deuxième bougie doit ouvrir à H ou en dessous et clôturer strictement au-dessus de H.

La zone du FVG est comprise entre :

`High(bougie 1)` et `Low(bougie 3)`.

### Scénario vendeur (SHORT)

Conditions :

1. Le prix franchit L.
2. La deuxième bougie traverse L dans le sens baissier.
3. Un FVG baissier se forme.

Définition :

`High(bougie 3) < Low(bougie 1)`

La deuxième bougie doit ouvrir à L ou au-dessus et clôturer strictement en dessous de L.

La zone du FVG est comprise entre :

`High(bougie 3)` et `Low(bougie 1)`.

### Important

Une simple cassure sans FVG ne constitue pas un signal.

Un FVG n'existe qu'après la clôture de sa troisième bougie.

Ne jamais utiliser une bougie encore en formation pour confirmer un signal.

L'obligation que la deuxième bougie traverse le niveau avec son corps constitue une interprétation stricte de la stratégie. Elle doit être clairement identifiée comme telle.

---

# PARTIE 2 — CONDITIONS D'ENTRÉE

## 4. Retest du FVG

Après la formation complète du FVG, attendre que le prix revienne tester sa zone.

Un retest est validé lorsque la fourchette High-Low d'une bougie ultérieure intersecte la zone du FVG.

Pour éviter les ambiguïtés, utiliser initialement les hypothèses suivantes :

* Le retest doit arriver après la formation complète du FVG.
* Le FVG reste actif pendant 15 minutes maximum.
* Si aucun retest n'arrive dans ce délai, abandonner ce FVG.
* Ne jamais anticiper le retest.

Ces 15 minutes constituent une hypothèse de backtest, et non une règle explicitement confirmée par la vidéo.

Ne pas optimiser arbitrairement cette durée pour améliorer les résultats.

## 5. Confirmation par une bougie englobante

Après le retest, rechercher une bougie englobante dans le sens de la cassure.

### LONG

La bougie de confirmation doit :

* Être haussière.
* Suivre une bougie baissière.
* Avoir un corps englobant entièrement le corps de la bougie précédente.

Conditions :

`Open(actuelle) <= Close(précédente)`

`Close(actuelle) >= Open(précédente)`

### SHORT

La bougie de confirmation doit :

* Être baissière.
* Suivre une bougie haussière.
* Englobler entièrement le corps de la bougie précédente.

Conditions :

`Open(actuelle) >= Close(précédente)`

`Close(actuelle) <= Open(précédente)`

### Fenêtre de confirmation

Pour la version principale :

* La bougie englobante peut être celle du retest.
* Elle peut également apparaître dans les deux bougies suivantes.
* Au-delà, le setup est abandonné.

Cette fenêtre est une hypothèse de modélisation qui devra être explicitement documentée.

## 6. Exécution de l'entrée

Lorsque toutes les conditions sont validées :

* Attendre la clôture complète de la bougie englobante.
* Envoyer un ordre au marché.
* Simuler l'exécution à l'ouverture de la bougie suivante.
* Appliquer les coûts et le slippage.

Ne jamais supposer automatiquement que l'ordre est exécuté au prix de clôture de la bougie ayant généré le signal.

Utiliser le premier setup complet et valide de la journée.

Maximum : **1 trade par jour et par instrument.**

Heure limite d'entrée : 11 h 00, heure de New York.

Si aucun setup n'est confirmé avant cette limite, aucun trade n'est pris.

---

# PARTIE 3 — STOP LOSS ET TAKE PROFIT

## 7. Stop Loss

La vidéo ne précise pas exactement le positionnement du stop-loss.

Je souhaite donc comparer deux variantes distinctes.

### Variante A — Stop basé sur le retest

LONG :

Stop sous le plus bas observé depuis le début du retest jusqu'à la confirmation, avec un buffer de 1 tick.

SHORT :

Stop au-dessus du plus haut observé pendant cette même période, avec un buffer de 1 tick.

### Variante B — Stop basé sur le FVG

LONG :

Stop sous la limite inférieure du FVG, avec un buffer de 1 tick.

SHORT :

Stop au-dessus de la limite supérieure du FVG, avec un buffer de 1 tick.

Tester séparément ces deux variantes.

Ne pas sélectionner rétroactivement la meilleure sans validation sur de nouvelles données.

Rejeter les trades dont le stop est invalide ou dont le risque initial est nul ou négatif.

## 8. Take Profit

Objectif fixe :

**Risk/Reward = 1:3**

Pour un LONG :

`TP = prix_entrée + 3 × risque_initial`

Pour un SHORT :

`TP = prix_entrée - 3 × risque_initial`

Calculer le risque à partir du prix réellement simulé d'entrée.

Respecter la taille de tick de chaque instrument.

Aucun trailing stop.

Aucun déplacement du stop au break-even.

Aucune prise de profit partielle.

Toute position encore ouverte en fin de séance doit être liquidée, selon une hypothèse d'exécution réaliste clairement expliquée.

## 9. Gestion du capital

Capital initial simulé : 100 000 USD.

Risque cible : 0,5 % du capital courant par trade.

Calculer la taille de position en fonction :

* De la distance entre entrée et stop.
* De la valeur monétaire du tick.
* Du capital disponible.
* Des unités négociables.
* Des éventuelles contraintes de marge et d'exposition.

Pour les ETF, utiliser des nombres entiers d'actions.

Pour les futures, utiliser des contrats entiers.

Ne pas supposer qu'il est toujours possible de risquer exactement 0,5 %.

Si le capital, la marge ou les contraintes d'exposition empêchent le trade, le signal doit être rejeté.

Documenter les règles de dimensionnement utilisées.

---

# PARTIE 4 — DONNÉES HISTORIQUES

## 10. Instruments

Tester séparément :

1. SPY — S&P 500 ETF.
2. QQQ — Nasdaq-100 ETF.
3. ES — E-mini S&P 500 Futures.
4. NQ — E-mini Nasdaq-100 Futures.

Ne pas mélanger les résultats de ces instruments.

Tenir compte des caractéristiques propres à chacun.

Pour les futures :

* Respecter la taille de tick.
* Respecter la valeur monétaire du tick.
* Gérer correctement les changements de contrat.
* Éviter les faux signaux dus aux raccordements des contrats continus.

## 11. Historique

Je souhaite au minimum un an de données historiques de 1 minute.

Idéalement :

**3 années ou plus**, si disponibles.

Utiliser de vraies données OHLCV de 1 minute.

Ne pas reconstruire artificiellement des bougies de 1 minute à partir de données 5 minutes.

Ne pas générer de données aléatoires pour les présenter comme des données de marché réelles.

Tu peux utiliser :

* yfinance pour un test exploratoire récent si les données sont effectivement disponibles.
* Un fournisseur fiable de données intraday historiques.
* Des fichiers CSV réels si une source directe est inaccessible.

Vérifie les limitations exactes de chaque fournisseur avant de lancer les tests.

Si tu ne peux pas obtenir un historique suffisant, indique-le clairement.

Fournis alors un programme exécutable permettant de charger des données historiques provenant d'un autre fournisseur.

## 12. Contrôle qualité des données

Avant chaque backtest :

* Vérifier les timestamps.
* Convertir correctement les fuseaux horaires.
* Éliminer les doublons.
* Identifier les minutes manquantes.
* Exclure les séances dont les cinq premières minutes sont incomplètes.
* Vérifier la cohérence des OHLC.
* Respecter les calendriers boursiers.
* Ne pas remplir artificiellement les prix manquants d'une manière qui créerait de faux signaux.

Indiquer la provenance, la période et la qualité des données réellement utilisées.

---

# PARTIE 5 — SIMULATION RÉALISTE

## 13. Frais et slippage

Le backtest doit inclure :

* Les commissions à l'entrée.
* Les commissions à la sortie.
* Le slippage à l'entrée.
* Le slippage à la sortie.
* Les contraintes de tick.
* Une hypothèse de spread lorsque cela est pertinent.

Utiliser des hypothèses de commissions réalistes et documentées pour chaque instrument.

Simuler au minimum 1 tick de slippage défavorable par exécution.

Puis effectuer une analyse de sensibilité avec :

* 1 tick.
* 2 ticks.
* 3 ticks.
* 5 ticks.

Les scénarios doivent être identiques, à l'exception des coûts d'exécution.

Je veux savoir si la stratégie reste profitable lorsque les conditions d'exécution se dégradent.

## 14. Gestion des bougies ambiguës

Si le stop-loss et le take-profit sont atteints dans la même bougie de 1 minute et que leur ordre chronologique est inconnu :

**Considérer que le stop-loss a été touché en premier.**

Ne pas attribuer automatiquement une victoire.

Si le marché ouvre au-delà d'un stop, simuler une exécution réaliste au prix disponible, avec le slippage applicable.

Ne jamais attribuer un meilleur prix d'exécution simplement parce qu'il améliore les résultats.

## 15. Prévention des erreurs

Vérifier notamment :

* Aucune information future.
* Aucun trade avant 9 h 35.
* Aucun signal FVG avant la clôture de la troisième bougie.
* Aucun retest antérieur à la formation du FVG.
* Aucune entrée avant confirmation.
* Maximum un trade quotidien.
* Aucun trade hors séance.
* Aucune utilisation involontaire des données overnight.
* Aucun trade artificiel lié à des données manquantes.
* Aucune utilisation incorrecte de la valeur des points futures.

Ajouter des tests automatisés pour vérifier ces propriétés.

---

# PARTIE 6 — ANALYSE STATISTIQUE

## 16. Résultats demandés

Pour chaque instrument et chaque variante de stop-loss, fournir :

**Performance**

* Nombre total de trades.
* Nombre de trades gagnants.
* Nombre de trades perdants.
* Win rate.
* Profit Factor.
* Rendement net après frais.
* P&L total en dollars.
* Espérance par trade en R.
* Gain moyen en R.
* Perte moyenne en R.
* Ratio gain moyen / perte moyenne.

**Risque**

* Maximum drawdown en dollars.
* Maximum drawdown en pourcentage.
* Plus longue série de pertes.
* Plus longue série de gains.
* Risque effectivement engagé.
* Exposition maximale.

**Comportement**

* Nombre moyen de trades par semaine.
* Résultats par mois.
* Résultats LONG vs SHORT.
* Performances par tranche horaire.
* Durée moyenne d'un trade.
* Résultats selon les conditions de volatilité.

Produire également :

1. Une courbe de capital.
2. Un graphique du drawdown.
3. Un graphique des résultats mensuels.
4. Une distribution des résultats par trade en R.
5. Un tableau comparatif des instruments.
6. Un journal détaillé des trades.

Pour chaque trade, enregistrer :

Date, instrument, direction, heure du signal, heure d'entrée, prix d'entrée, stop, objectif, heure de sortie, prix de sortie, frais, slippage, P&L net et résultat en R.

---

# PARTIE 7 — VALIDATION DE LA STRATÉGIE

## 17. In-sample et Out-of-sample

Je ne veux pas uniquement une stratégie qui semble rentable sur les données historiques utilisées pour choisir ses paramètres.

Lorsque suffisamment de données sont disponibles :

Diviser chronologiquement l'historique en deux parties :

* 70 % pour le développement et l'analyse initiale.
* 30 % pour la validation hors échantillon.

Ne jamais choisir les paramètres en fonction des résultats de la période de validation.

Tester les deux variantes de stop-loss séparément.

Si l'historique est suffisamment long, effectuer également une validation walk-forward.

Indiquer explicitement si les résultats sont :

* In-sample.
* Out-of-sample.
* Ou simplement exploratoires.

## 18. Robustesse

Je souhaite savoir si les performances dépendent fortement de paramètres très précis.

Examiner notamment :

* Différentes durées maximales de retest.
* Différentes fenêtres de confirmation.
* Différents niveaux de slippage.
* Différentes périodes historiques.
* Différents régimes de volatilité.

Ne pas transformer cette analyse en recherche automatique des paramètres qui produisent le meilleur profit.

Conserver la stratégie principale inchangée et présenter les variantes comme des tests de sensibilité.

Lorsque la taille de l'échantillon le permet, estimer l'incertitude statistique des résultats, notamment à l'aide d'un bootstrap respectant le regroupement des trades par séance.

## 19. Analyse critique

Je veux des réponses précises aux questions suivantes :

1. La stratégie est-elle profitable après tous les frais ?
2. Est-elle profitable sur des données non utilisées pour choisir ses paramètres ?
3. Quel instrument présente les résultats les plus solides ?
4. Les positions LONG sont-elles plus rentables que les SHORT ?
5. Quel stop-loss donne les résultats les plus robustes ?
6. La stratégie fonctionne-t-elle uniquement pendant certaines conditions de marché ?
7. Les résultats sont-ils fortement dépendants de quelques grosses journées gagnantes ?
8. La stratégie supporte-t-elle une augmentation réaliste du slippage ?
9. Le nombre de trades est-il suffisant pour tirer des conclusions crédibles ?
10. Les résultats suggèrent-ils un véritable avantage statistique ou simplement du hasard ?

Ne considère pas automatiquement qu'une stratégie est profitable parce que son Profit Factor dépasse 1 sur un petit échantillon.

Explique clairement les limites statistiques.

---

# PARTIE 8 — CODE ET LIVRABLES

## 20. Implémentation Python

Créer un backtest Python complet et fonctionnel.

Utiliser si nécessaire :

* pandas.
* numpy.
* matplotlib.
* Une bibliothèque de backtesting adaptée, si elle permet de respecter fidèlement les règles.

Le programme doit :

* Charger les données historiques.
* Détecter la première bougie 5 minutes.
* Identifier les cassures H/L.
* Identifier les FVG.
* Détecter les retests.
* Vérifier les bougies englobantes.
* Simuler les entrées et sorties.
* Calculer les frais.
* Calculer les performances.
* Générer les tableaux et graphiques.

Fournir le code complet, les dépendances et les instructions d'exécution.

Le backtest doit pouvoir fonctionner avec des fichiers CSV externes contenant les données OHLCV de 1 minute.

## 21. Pine Script TradingView

Créer une deuxième implémentation en **Pine Script v6**.

Elle doit :

* Fonctionner sur un graphique 1 minute.
* Identifier automatiquement les niveaux H/L.
* Afficher les zones FVG.
* Afficher les retests.
* Identifier les bougies englobantes.
* Placer les entrées LONG/SHORT.
* Afficher les stop-loss et take-profit.
* Respecter les horaires.
* Respecter la limite d'un trade par jour.
* Être compatible avec le Strategy Tester de TradingView.

Utiliser des méthodes qui évitent le repainting et les informations futures.

Expliquer les éventuelles différences entre les résultats Python et TradingView, notamment celles liées aux hypothèses d'exécution du simulateur.

## 22. Validation du code

Avant de présenter les résultats :

* Vérifier que le code Python s'exécute réellement.
* Tester les fonctions critiques sur des scénarios contrôlés.
* Vérifier que les signaux correspondent aux règles.
* Examiner manuellement plusieurs trades historiques.
* Vérifier les calculs de P&L et de risque.
* Identifier toute fonctionnalité non testée.

Ne prétends pas avoir compilé le Pine Script dans TradingView si tu n'y as pas réellement accès.

Si les résultats Python et TradingView diffèrent, rechercher les raisons au lieu de choisir arbitrairement les meilleurs.

---

# PARTIE 9 — RAPPORT FINAL

Je souhaite recevoir :

### A. Résumé exécutif

Une conclusion objective et directe sur les performances constatées.

### B. Résultats historiques

Des tableaux comparatifs avec toutes les statistiques.

### C. Analyse du risque

Une présentation des pertes possibles et du drawdown.

### D. Robustesse

Les résultats des tests hors échantillon et des différentes hypothèses de frais.

### E. Code source

Le code Python complet et le Pine Script v6.

### F. Données et reproductibilité

Les sources de données, les dates testées, les paramètres utilisés et les instructions permettant de reproduire les résultats.

### G. Conclusion

Classe la stratégie dans l'une de ces catégories :

1. **Avantage statistique encourageant** — résultats positifs après frais, avec validation suffisamment solide.
2. **Potentiellement intéressante, mais preuves insuffisantes** — certains résultats sont positifs, mais l'incertitude reste importante.
3. **Aucun avantage démontré** — résultats non convaincants ou non robustes.
4. **Structurellement déficitaire dans les conditions testées** — pertes persistantes après frais.
5. **Impossible à évaluer sérieusement** — données ou exécution insuffisantes.

Explique les éléments qui justifient la classification.

Ne recommande pas le passage au trading réel uniquement parce que le backtest est positif.

---

# INSTRUCTION FINALE

**Ta priorité absolue est l'exactitude, pas la rentabilité apparente.**

Je veux vérifier si cette stratégie possède réellement un avantage exploitable.

Ne cherche pas à me convaincre qu'elle fonctionne.

Ne fabrique pas de résultats.

Ne contourne pas les difficultés techniques en utilisant des données fictives ou des hypothèses irréalistes.

Si la stratégie perd de l'argent, montre-le.

Si elle semble rentable, démontre-le avec des données fiables, des frais réalistes et une validation hors échantillon.

Si tu ne peux pas exécuter une partie du travail, indique précisément ce qui a été exécuté, ce qui reste non testé et pourquoi.

**Commence par établir les règles exactes et vérifier la disponibilité des données. Ensuite, implémente le backtest Python, exécute-le sur des données réelles, valide les résultats et réalise l'implémentation TradingView. Ne remplace jamais un résultat calculé par une estimation inventée.**
