# Protocole Python figé avant performances — 24 octobre 2026

Autorisation explicite de Mina : remplacer le contrôle TradingView indisponible par un backtest Python sur GBPUSD, USDJPY, AUDUSD, mêmes règles et1pip de frais, au moins100trades fermés distincts par paire, publier code/résultats/rapport dans trading-backtests. Aucun ordre broker ni modification des bots QQQ.

## Données et période

Archives gratuites officielles FXCM `https://candledata.fxcorporate.com/m1/{pair}/{year}/{week}.csv.gz`, bid/ask OHLC à1minute, timestamps UTC selon FXCM. Acquisition des semaines48–53 de2014 pour amorçage,1–53 de2015–2024,1–4 de2025 pour laisser sortir les positions2024 sans clôture forcée. Les404, réponses vides, erreurs et SHA256 de chaque réponse utile sont conservés ; une404 n'est pas assimilée silencieusement à un jour fermé.

ALL = entrées du01/01/2015 00:00UTC au01/01/2025 exclu. A =2015–2019, B =2020–2024, bornes chronologiques fixes. Capital initial100000 dans la devise de cotation par simulation indépendante (USD ou JPY), pas100000USD sur USDJPY. B est une validation chronologique de règles fixées par l'utilisateur, pas une promesse de données restées inconnues de toute recherche antérieure. Aucun résultat Nowick de marché n'a été consulté à la rédaction de ce fichier.

Dukascopy renvoie429 avec un lien vers sa migration S3 Requester Pays ; cette voie facturée n'est pas utilisée. FXCM a été retenu après vérification de disponibilité de semaines isolées, sans calcul de performance. HistData a aussi été sondé sans acquisition. Ne pas mélanger les fournisseurs pour combler des trous.

## Signaux

Bougies15m UTC construites exclusivement à partir des Bid OHLC1m. Un signal exige15minutes valides ; les pivots5/5 ne se confirment que sur11bougies complètes et consécutives. En cas d'égalité, le pivot est le dernier extrême de sa fenêtre (égalité à gauche permise, à droite interdite), choix explicite non certifié par un compilateur Pine. Les pivots déjà confirmés restent utilisables ; SL et taille sont figés au signal.

Structure principale : dernier pivot haut ET bas au-dessus des précédents, inverse pour vente. EMA50/2001h en sensibilité, calculée seulement sur des heures complètes, au moins200heures de chauffe, aucune valeur de l'heure en cours. Entrées02:00incluse–08:00exclue America/New_York, DST IANA, ordre posé après clôture du signal, au plus une position/limite. Nowick sans tolérance, ouverture=low pour achat /open=high pour vente et corps de bon sens. Limite ouverture,9bougies suivantes, SL dernier pivot opposé plus3pips, distance5–30pips incluse, TP1R. Risque de prix1% du solde disponible au signal, unités entières arrondies vers le bas, plafond de marge100x ; pertes nettes non plafonnées à1%.

Swing, S/R et Double sont testés individuellement ON contre la référence OFF, conventions identiques à MISSION.md. Sensibilités EMA1h, milieu de corps,1.5R/2R, front-runOFF et coûts2/3pips fixées avant résultats. News manuel implémentable mais non évalué sans calendrier daté fourni/archivé ; ne pas inventer les exclusions.

## Exécution minute et frais

Prix en ticks entiers : .00001 GBPUSD/AUDUSD, .001 USDJPY ;1pip=10ticks pour les trois. La limite exige une pénétration de10ticks dans le sens du retest ; elle est remplie à la limite prévue sans amélioration de prix. Comme la déclaration Pine d'origine, le TP limite exige également10ticks de dépassement ; son prix de fill reste le TP. Un stop touché s'exécute au stop, ou à l'open de reprise si ce prix est pire. Aucun break-even, fermeture de session ou sortie discrétionnaire.

Le modèle principal représente le coût total par une commission synthétique1pip aller-retour, moitié à l'entrée/moitié à la sortie. Il utilise la série Bid comme série de prix commune, comme un backtest graphique ; les spreads Ask-Bid ne sont pas ajoutés une deuxième fois. **Ce n'est pas un backtest d'exécution bid/ask réelle.** FXCM qualifie ses prix d'indicatifs. Les Ask sont conservés pour contrôle de qualité ; swaps/financement ne sont pas inclus dans le coût demandé. Les positions overnight et leur durée sont signalées.

Un ordre en attente est annulé dès un front-run connu avant fill, une sortie d'horaire ou un trou minute. Si front-run et pénétration se produisent dans la même minute et que l'open ne résout pas l'ordre : principal `cancel_first` = annulation, sensibilité `fill_first` = retest d'abord. **Annuler un trade ambigu n'est pas une borne de PnL garantie** ; publier les deux portefeuilles indépendants et les comptes d'ambiguïtés. L'open connu est traité avant les extrêmes. Une position déjà ouverte dont SL et TP sont touchés dans la même minute sort au SL. Un fill intraminute ne peut profiter d'un TP par la seule mèche de cette minute : seule une clôture au-delà du TP+pénétration prouve le retour après le fill ; sinon l'exécution attend la minute suivante. Si le fill est connu à l'open, le TP de la minute peut être exécuté, après priorité au SL.

## Couverture et comptes

Bid OHLC non finis, non positifs ou incohérents invalidés, jamais forward-fill. Doublons identiques dédupliqués avec compte ; doublons conflictuels refusés. Les minutes absentes/incohérentes empêchent la formation de signaux concernés et annulent les limites. **Une position ouverte traversant un trou n'est pas supprimée de l'échantillon** : au premier open valide de reprise, pénalité de couverture au pire du SL ou de cet open, avec frais complets ; résultat étiqueté `coverage_gap_stop`, ni fill observé ni borne universelle d'un gap inconnu. Publier nombre, contribution et poids de ces pénalités. Si elles dominent une conclusion, refuser une rentabilité établie.

Après la fin des entrées, SL/TP restent actifs sur le reste de l'historique acquis. Une position toujours ouverte est affichée et valorisée séparément, jamais forcée fermée pour atteindre100trades. Les nombres de trades exigés sont des transactions distinctes fermées de la référence ALL par paire, pas la somme de scénarios recouvrants. Si100n'est pas atteint, étendre la période commune selon la disponibilité avant toute modification de paramètres, ou déclarer explicitement l'objectif non atteint.

Métriques : PnL net, frais, WR/Wilson95%, PF monétaire, espéranceR et sommeR, série de pertes, DD de la courbe des R fermés ; DD% complémentaire sur marques observées de clôture1m et événements de fill, pas un drawdown tick exact. A/B simulées indépendamment avec mêmes paramètres et historique antérieur conservé pour les indicateurs. Export de chaque trade, erreurs/couverture, configurations et empreintes du code. Audit indépendant des comptes et des signaux/fills à partir des archives originales ; aucun résultat TradingView revendiqué.

Sources : [FXCM MarketData officiel](https://github.com/fxcm/MarketData), [exemple officiel pandas](https://github.com/fxcm/MarketData/blob/master/CandleData/CandleData%28pandas%29.py), [modèle Pine](tradingview/nowick_compensation_usd.pine).
