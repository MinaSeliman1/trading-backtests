# Nowick / Compensation Play — mission du 24 octobre 2026

Implémenter la formalisation fournie par Mina, sans prétendre certifier une méthode originale de Bard FX : GBPUSD, USDJPY et AUDUSD séparément, chandeliers ordinaires 15 minutes, nouvelles entrées de 02:00 incluse à 08:00 exclue America/New_York.

Structure : deux derniers pivots hauts ET bas confirmés, longueur gauche/droite 5 ; ou EMA50/EMA200 de la dernière heure terminée, request.security lookahead_off. Nowick haussière close>open, open-low<=tolérance ticks ; inverse baissière. Limite à l'ouverture ou milieu du corps, durée 9 bougies suivantes. Annulation front-run optionnelle, pénétration de limite par défaut 1 pip. SL dernier pivot opposé connu, buffer 3 pips, distance entre 5 et 30 pips inclus. TP 1R, autres tests 1.5R et 2R. Risque de prix cible 1% du capital courant, une position et un ordre d'entrée maximum. Pas de break-even ni clôture discrétionnaire.

Filtres indépendants : extrême de 10 bougies, pivots S/R récents entre entrée et cible, deuxième Nowick même sens distante de 2–4 bougies, exclusions news manuelles. Pip .01 JPY, .0001 autrement. Coût de base total 1 pip aller-retour ; affichages des niveaux, statistiques nettes, R et Wilson95%.

## Choix fixés avant toute performance FX

- Un ordre en attente conserve ses niveaux et sa taille ; aucun remplacement par une nouvelle bougie. Un ordre ne survit pas à la fin de la fenêtre ou au début d'une exclusion news. SL/TP d'une position restent actifs hors fenêtre et après la fin du test.
- Les news sont des fenêtres datées au format YYYY-MM-DD@HHMM-HHMM, séparées par des points-virgules, dans le fuseau choisi. Les chevauchements interdisent la bougie entière de 15 minutes, même si les horaires saisis ne sont pas alignés. Pas de calendrier automatique ni de filtrage rétrospectif des mauvaises journées.
- Double Nowick : le premier signal admissible gagne ; le second signal de même sens 2–4 bougies après un premier ordre accepté est ignoré, même si le premier a déjà été fermé/annulé. L'écart de 1 bougie n'est pas assimilé au filtre demandé.
- S/R récent = pivot confirmé depuis au plus 100 bougies (paramètre), sans suppression silencieuse des niveaux traversés. Stop et pivots sont figés lors du signal, jamais déplacés vers un pivot futur.
- Comptabilité native en devise de cotation (currency.NONE) : USD pour GBPUSD/AUDUSD, JPY pour USDJPY. Deux fichiers identiques sauf commission par unité et garde sur devise : .00005 USD par côté ou .005 JPY par côté, soit 1 pip total pour pointvalue=1. Les Propriétés permettent commission, slippage et pénétration ; ce ne sont pas des inputs() dynamiques supportés par strategy(). Garde sur pointvalue=1 et compte dans la devise de cotation.
- Pénétration native 10 ticks par défaut, soit 1 pip sur les flux 5/3 décimales ; régler les Propriétés pour les flux 4/2 décimales. L'hypothèse native s'applique aussi au TP limite. Le seuil de pénétration est une exigence de remplissage, pas une deuxième commission.
- Marge 1% (plafond mécanique 100x), taille arrondie vers le bas au mincontract ; cible de risque 1% hors frais. Les pertes peuvent dépasser 1% après coûts/gaps. Aucun sizing à partir du futur.
- Bougies 15m uniquement, calcul à clôture, aucun recalcul au fill ni à chaque tick, aucune exécution sur la clôture du signal. EMA1h figée exclusivement à une clôture 15m coïncidant avec la clôture 1h demandée, jamais pendant l'heure ouverte.
- Limitation native : un ordre limite peut être rempli avant que le script annule un front-run à clôture. Le front-run et le SL/TP dans une même bougie peuvent être indécidables. Conserver le résultat natif, marquer ces trades, et montrer séparément un stress où tout trade ambigu est plafonné à une perte de -1R moins sa commission (ou sa perte réelle si pire). Ce stress n'est ni une reconstruction du véritable ordre des ticks ni une borne mathématique en présence de gaps/slippage inconnus. Il ne modifie pas le capital ni les ordres natifs et n'est pas une seconde simulation de portefeuille.
- Drawdown en R = drawdown de la somme des R des trades fermés ; distinct du drawdown intratrade du Strategy Tester. PF du tableau en monnaie, espérance en R ; commissions natives comptées une seule fois. Wilson sur gains strictement nets positifs / tous trades fermés, sans indépendance statistique garantie.

## Statut initial

Aucune donnée FX ni performance de cette méthode n'a été examinée. Les historiques Alpaca existants sont des ETF, pas ces paires. Séparer explicitement tests contrôlés, compilation Pine et backtest marché. Ne pas fabriquer de résultats si TradingView ou l'historique requis n'est pas accessible.
