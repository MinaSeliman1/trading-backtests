# SMT proxy ES/NQ — conception avant PnL

Demande utilisateur : H1 continuation, H2 retournement, trois biais A/B/C, H3 association de volatilité. Dernières décisions utilisateur : utiliser ES/NQ existants comme proxy avec valeur MNQ2USD/point et commission1.25USD/côté ; six variantes principales, niveaux regroupés, priorité Londres/prémarché/veille uniquement simultanéité ; objectif H1 = premier niveau de cette liste au-delà de l’entrée dans le sens choisi, règle identique aux témoins. Diagnostics par niveau seulement en découverte APRÈS principal, sans sélection de variante.

## Données, sans PnL encore
Archives longues alfordlabs/BARS : ES2025-06-20/2026-10-09, NQ2024-08-04/2026-10-08. Entête America/New_York sur dates naïves ; localiser avec zoneinfo, ambigu/nonexistent=raise, convertir UTC pour rapprochement. Doublons constatés0, offsets−04/−05 présents ; Londres/prémarché inclus. SHA256 des originaux vérifiés contre acquisition existante. Documentation : continu frontmonth non ajusté, pas d’échéance à chaque minute. Source amont/roll exact non authentifiables. Pas de prétention à des prix MNQ/MES identiques, utilisateur autorise ce proxy seulement.

Le jeu Yahoo séparé comporte ESZ26.CME/NQZ26.CME datés sur quelques semaines. Pas substitué silencieusement aux longs continus, pas de bootstrap d’une année à partir de ce fragment.

## Protection des raccords, à figer avant calcul
Pas de nouveau choix du contrat avec volume futur. Sur les fichiers continus existants, exclusion calendaire prudente des dates du1er de chaque mois trimestriel jusqu’à la première séance NYSE suivant le troisième vendredi, et des jours dont le niveau de veille serait dans cette zone. Pour A, les20closes doivent rester hors des zones de raccord incertain. Ce sont des fenêtres POSSIBLES, pas des dates de changement identifiées ; publier leur nombre et leurs dates. Impossible de certifier chaque raccord sans contrats datés ; cette limite reste un garde-fou de phaseproxy et n’est pas effacée par la réussite statistique.

## Conventions opérationnelles proposées avant PnL
- Une unité de NQ évaluée comme1MNQ, 2USD/point ; ES sert seulement au signal, aucune jambe ES tradée.
- Horaires NY fixes. Fenêtres Londres04:00–07:00, prémarché07:00–09:30, précédent cashRTH09:30–closeNYSE (16h ou13h demi-séance). Pas de joursNYSEfermés ; compte les exclusions plutôt que traiter les jours fériés comme des données manquantes. Agrégats journaliers de biais sur ce même RTH.
- Entrée réelle de09:32 à11:00 incluse, signal clos minute précédente. Aucun filtre fondé sur le fill futur sans compter ses coûts ; convention H1 acceptée : objectif et RR filtrés sur dernièreclose connue ; gaps ultérieurs conservés.
- Balayage1tick=.25point. Divergence = ES premier balayage du niveau dans la séance, NQ sans balayage équivalent depuis09:30, y compris la bougie signal. Une touche exactement au niveau n’est pas un balayage1tick.
- H2 attend reclôture ES du bon côté du niveau, même bougie possible si elle rejette déjà ; annuler si NQ balaye à son tour avant confirmation. Premier setup consommé, pas de recherche d’un deuxième plus flatteur. Sens concurrents simultanés au même niveau sans ordre intraminute connu : invalider l’ambiguïté.
- Biais A : closeNQ veille vs moyenne20RTHcloses finissant veille ; B : closeveille vsopenveille ; égalité=neutre. C : pas de filtre, directionSMT ; témoinsC avec pièce long/short par jour, graine commune20261031 ; sensSMT futur seulement diagnostic contrefactuel non tradable.
- Coût principal2ticks AU TOTAL par roundtrip (1tick/côté), donc3.50USD/contrat avec commissions. Le script TradingView cité parle de slippage2, qui est une convention par fill différente ; publier aussi un stress4ticksRT, sans changer les six stratégies.
- H3 : indicateur primaire balayageLondon par au moins un des deux indices entre07:00 et09:30 exclue ; plageNQ09:30–11:00 exclue enpoints etbps. Association, pas causalité ni rentabilité.

## Témoins, statistique et validation
Témoin biais-seul09:32 et1000tirages de minute entre09:32/11:00 ; une seule entrée/jour/portefeuille simulé. Stop et TP du modèle identiques. Géométries impossibles/exclusions comptées, pas de nouveau tirage caché. Comparer moyennes nettes/jour, netR/trade, couverture et nombres de trades ; le PnL total de nombres de trades différents ne suffit pas. Ajouter un diagnostic de placebo aux mêmes minutes/biais entre dates pour isoler l’effet de timing (pas nouvelle stratégie ni choix de gagnant). A/B chronologiques fixes sur chevauchement, découverte2025-06-20/2026-02-27, validation2026-03-02/2026-10-08 ; jamais qualifiée d’OOSaveugle garanti dans ce dépôt réutilisé. Résultat de découverte ne change aucune règle de validation. Les tests par niveau restent diagnostic découverte uniquement.

Protocole final et seuils statistiques doivent être gelés après les précisions utilisateur maintenant reçues, avant toute performance. Aucun ordre broker, coffre, tâche Windows ou runtime de bot modifié.
