# Protocole First Candle Rule + FVG

Le cahier des charges fourni le 19 octobre 2026 est la référence. Objectif : mesurer un avantage après frais, sans sélectionner une variante a posteriori. Python est le moteur de référence pour l'ordre pessimiste des événements intrabougie. Pine est une implémentation de comparaison dans le simulateur TradingView.

## Conventions arrêtées avant les résultats

- Horodatage CSV au début de la minute ; fuseau obligatoire, ou timestamps ISO avec décalage. Données brutes non ajustées. Jamais de remplissage des prix.
- Calendrier XNYS pour la plage actions américaine, également utilisée pour limiter ES/NQ selon la mission. Pour les futures, un calendrier explicite fourni par l'utilisateur peut raccourcir cette plage. Les fermetures exceptionnelles CME doivent être vérifiées avec la source.
- Exclusion de toute séance incomplète, y compris au-delà des cinq premières minutes. Choix conservateur pouvant introduire un biais de sélection, journalisé. Doublons identiques supprimés ; conflits exclus via rejet de la séance.
- H/L calculés sur les cinq minutes 09:30–09:34. Premier FVG possible : minutes 09:35/36/37, connu à 09:38.
- Cassure stricte avec le corps de la deuxième bougie, telle que demandée. Tous les FVG valides coexistent ; le premier qui termine toutes les confirmations est retenu ; égalité : le plus ancien FVG, puis LONG.
- Retest sur une bougie ultérieure, intersection inclusive ; clôture du retest au plus tard 15 minutes après la clôture de formation. Confirmation sur la bougie du premier retest ou les deux suivantes. La limite des 15 minutes concerne le premier retest ; la confirmation peut terminer après ce délai.
- Confirmation clôturée strictement avant 11:00 ; exécution à l'ouverture suivante, également strictement avant 11:00. Un ordre dont le stop devient invalide au prochain open est rejeté ; recherche du prochain setup sans dépasser un trade exécuté par jour.
- A : extrême entre premier retest et confirmation inclus, plus un tick. B : bord externe du FVG plus un tick. Pas d'invalidation supplémentaire implicite du FVG.
- Entrée au marché à l'open suivant, prix arrondi au tick défavorablement. TP à 3 fois le risque réellement exécuté. TP modélisé comme un ordre au marché déclenché au niveau, afin d'appliquer le slippage défavorable sur toutes les sorties. Un ordre limite donnerait d'autres résultats.
- Si stop et TP sont possibles dans une minute, priorité au stop, sauf gap d'ouverture déjà au-delà du TP : le déclenchement connu à l'open précède le reste de la minute. Gap stop : prix open disponible ; gap TP : niveau TP, sans amélioration favorable.
- Liquidation programmée à l'ouverture de la dernière minute de la séance, avec coûts. Ce prix est disponible, contrairement à une clôture finale connue après coup. Aucune position la nuit.
- Capital distinct de 100 000 USD pour chaque instrument/scénario/segment ; risque cible estimé au passage de l'ordre plafonné à 0,5 %, intégrant perte stop, friction de sortie et commissions estimées aller-retour. Quantités entières, exposition et marge plafonnées. Taille réduite au plafond réalisable ; rejet si moins d'une unité.
- Quantité fixée à la clôture de confirmation, à partir du close connu et d'une estimation d'entrée avec friction. Aucun prix, volume, high/low/close de la minute suivante n'entre dans la taille. Le fill réel simulé à l'open suivant fixe ensuite le risque effectif et le TP à 3R ; un gap peut faire dépasser le risque cible sans redimensionnement rétroactif. `estimated_loss_at_order_usd` et `planned_loss_usd` distinguent le risque estimé au passage de l'ordre et la perte stop projetée après fill. Le rejet d'un stop devenu invalide ou d'une insuffisance de capital/exposition à l'open est une convention d'acceptation conditionnelle du simulateur imposée pour ces cas par la mission ; un vrai ordre au marché déjà envoyé pourrait avoir été exécuté et nécessiter une fermeture. La liquidité, les cotations et la latence restent à valider.
- ETF : 0,005 USD/action/côté, minimum 1 USD, plafond 1 % du nominal, plus réserve réglementaire paramétrable. Spread hypothétique 1 tick complet, ajouté pour moitié par côté avec arrondi défavorable. Disponibilité de vente à découvert supposée et explicitement non vérifiée sans fichier d'emprunt.
- Futures : commission totale hypothétique 2,50 USD/contrat/côté, à remplacer selon le courtier et l'époque. Marge initiale hypothétique ES 25 000 USD, NQ 40 000 USD, exposition maximale 10 fois le capital ; ces montants ne représentent pas un historique officiel de marge. Le mode strict exige un fichier daté de marge et un calendrier daté de contrats.
- Futures : un seul contrat brut par séance, sélection par fichier `rolls.csv` décidé avant l'open ; aucun raccordement ni calcul entre contrats. Les continus Yahoo/TradingView sont exploratoires et désactivés par défaut.
- Scénarios principaux : stops A/B et slippage 1/2/3/5 ticks. Sensibilités préfixées séparées : retest 10/20 minutes, confirmation 0/1/3 bougies suivantes, sans classement optimisé.
- Au moins 252 séances valides et 365 jours calendaires couverts pour division 70/30 par séances, comptes réinitialisés par segment. Walk-forward sans optimisation : fenêtres de développement de 252 séances, blocs de test suivants de 63 séances si au moins 504 séances. Historiques plus courts : exploratoires.
- Régime de volatilité connu au signal : amplitude de l'opening range divisée par son milieu. Seuils des tiers fixés sur la période de développement uniquement ; exploratoire sans classement si historique insuffisant.
- Bootstrap de 5 000 réplications avec graine 20261019 : séances complètes (y compris sans trade), intervalle percentile de l'espérance en R ; ce n'est pas une preuve de stationnarité. Sensibilité complémentaire en blocs de cinq séances pour autocorrélation.

## Architecture et validation

1. `fvg_backtest/data.py` : import CSV, provenance SHA-256, calendrier, qualité et contrats.
2. `fvg_backtest/engine.py` : détection séquentielle, exécution, frais, dimensionnement et courbe intraday au close de chaque minute.
3. `fvg_backtest/report.py` : statistiques, regroupements, intervalles, figures et rapport français.
4. `fvg_backtest/cli.py` : orchestration reproductible, segments et sensibilités, manifeste des versions et paramètres.
5. `scripts/download_yahoo.py` : acquisition exploratoire documentée, sans reconstruction 1 minute.
6. `tradingview/first_candle_fvg.pine` : v6, calcul sur bougies closes et différences du broker emulator explicites.
7. `tests/` : scénarios fabriqués uniquement pour vérification du code, jamais comme résultats historiques.

Ne publier aucune statistique comme résultat historique si les bougies réelles n'ont pas été acquises et exécutées. Ne revendiquer aucune compilation Pine sans exécution effective dans TradingView.
