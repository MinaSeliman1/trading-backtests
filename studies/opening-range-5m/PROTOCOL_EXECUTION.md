# Protocole ORB 5 minutes — avant P&L

Demande : trouver une autre piste SPY/QQQ, la tester avec les mêmes frais et publier dans trading-backtests. Exécution autonome autorisée pendant l'absence de l'utilisateur. La disponibilité des historiques et les résultats des études antérieures sont connus ; aucun nouveau P&L ORB n'a été consulté.

## Signal, quantité et sorties

1. Données : caches Alpaca SIP raw validés, calendrier XNYS et précision float64. Première plage = cinq minutes 09:30 à 09:34 incluses, toutes OHLCV cohérentes et volume cumulé positif. Direction LONG si close 09:34 > open 09:30 ; SHORT si inférieur ; nul si égal par comparaison décimale. Pas de référence à une clôture précédente : le dividende ex-date ne crée pas de signal artificiel.
2. Au signal, stop connu = plus bas des cinq minutes pour LONG, plus haut pour SHORT. Le risque unitaire de taille est la distance entre close 09:34 et ce stop. `q=floor(min(capital/close_09:34, 0.01*capital/risque_unitaire))`. Capital net recomposé, actions entières, maximum théorique 1x au prix connu ; le gap d'entrée peut modifier ce levier et dépasser la perte cible.
3. Entrée supposée à l'open 09:35, plus friction adverse selon le sens. Aucun prix de 09:35 n'est utilisé pour choisir q. Le délai de publication de close 09:34 et de transmission ne garantit pas ce fill : hypothèse de backtest, pas exécution constatée. Une entrée sans open observable est exclue comme exécution non établie, sans retard inventé vers une autre minute.
4. Après fill, R de référence = distance signée entre open d'entrée et stop. Si R <=0, le stop est immédiatement marketable : sortie au même open, avec les deux commissions et frictions ; le trade n'est pas éliminé après avoir vu le gap. Sinon objectif = open d'entrée + signe*10R, sans trailing ni sortie partielle. Quantité préfixée inchangée malgré ce risque réalisé.
5. Pour chaque minute active : vérifier d'abord l'open. Un gap au-delà du stop se remplit à l'open, un gap favorable au-delà de l'objectif au niveau objectif conservateur. Ensuite comparer low/high au stop et à l'objectif, inclusivement. Si les deux sont touchés dans la même minute sans ordre observable, priorité STOP dans le principal ; sensibilité TARGET séparée à friction 0,01. Les prix exécutables appliquent ensuite la friction adverse. Aucune amélioration de cours supposée sur la cible.
6. À l'open de la dernière minute (15:59 ou 12:59), si aucune barrière déjà exécutable à cet open, liquider au marché. Ne pas utiliser high/low/close de cette dernière minute après la liquidation. Un seul aller-retour par jour, aucune réentrée ou position overnight. Les timestamps de barrières intraminute désignent une minute, pas une seconde connue.
7. Pour le drawdown minute, marquer l'entrée, les closes des minutes entièrement maintenues avant la minute de sortie, puis le capital réalisé net. Ne pas marquer le close ou les extrêmes postérieurs possibles à une sortie intraminute. MAE/MFE limitées aux barres entièrement maintenues, à l'entrée et à la référence de sortie : bornes observées partielles, pas risque tick exact. Durée d'exposition : borne supérieure d'une minute pour une sortie intraminute ; durée exacte aux opens.
8. Frais : par côté `max(0.35, q*0.0035)` ; friction 0,01 USD/action/côté, stress 0,02/0,03/0,05 ; SHORT `q*prix_entrée_après_friction*0.01/360`, un jour minimum même pour une sortie immédiate. Pas de tarif réglementaire séparé ni intérêts sur cash. Les prix après friction doivent rester positifs. Insolvabilité : arrêter les nouvelles entrées et publier l'état.

## Qualité et portée des performances

Les historiques comportent des minutes manquantes, dont certaines autour des interruptions de mars 2020 et d'autres sans suspension officielle établie. Une sonde SIP actuelle sur QQQ 02/02/2016 11:15–11:30, via les identifiants déjà protégés, n'a pas récupéré les neuf minutes absentes ; aucune nouvelle clé n'a été demandée.

Profil principal `complete_days` : uniquement séances intégrales validées. Cette sélection dépend d'une qualité connue après coup et les métriques sont **conditionnelles à cet univers historique**. Les autres séances sont publiées comme données exclues, pas comme journées où une stratégie réellement connectée aurait volontairement choisi le cash.

Sensibilité `resolved_prefix` à 0,01 : les cinq premières minutes puis l'open d'entrée doivent être observés ; examiner les barres uniquement jusqu'à la sortie. Si une minute active est absente ou invalide avant toute sortie démontrée, classer le trade/séance `unresolved_execution` : aucun fill, retour, barrière ou maintien réel ne peut être établi. Le compte conditionnel omet ces séances ; les colonnes d'exclusion et dates rendent cette imputation comptable explicite. Un trou après une sortie établie ne modifie pas le trade. Aucun trou n'est automatiquement déclaré halt, aucune bougie n'est fabriquée. Aucun rendement continu sur toutes les séances n'est revendiqué.

OHLC extrêmes provenant d'un seul fournisseur peuvent comporter des anomalies affectant les stops. Relire dans les CSV bruts des exemples extrêmes, ex-dates, demi-séances et barrières ambiguës ; cette vérification n'est pas un contrôle indépendant par un autre fournisseur. Publier comptes de barres ambiguës, gaps, données exclues, expositions et risques effectivement dépassés.

## Scénarios et évaluation

54 exécutions : deux instruments × trois périodes × neuf spécifications :

- LONG/SHORT, `complete_days`, STOP prioritaire, quatre frictions 0,01/0,02/0,03/0,05 ;
- LONG seul et SHORT seul, chacun `complete_days` à 0,01, diagnostics prédéfinis ;
- signal inversé, `complete_days` à 0,01, même règle de risque et stop à l'extrême approprié au sens : les quantités et sorties ne sont pas identiques au principal, ce n'est pas une comparaison à exposition fixée ;
- priorité TARGET sur les barres ambiguës, `complete_days` à 0,01 : sensibilité d'exécution, aucun choix après observation ;
- LONG/SHORT `resolved_prefix` à 0,01, STOP prioritaire : sensibilité de couverture, toujours conditionnelle aux exécutions résolues.

Périodes ALL/A/B identiques à README, réinitialisées à 100 000 USD. Publier toutes les exécutions, frais, P&L net, rendements/CAGR conditionnels, DD quotidiens/minute observée, succès/échecs, profit factor, LONG/SHORT, années, demi-séances, coûts, levier et perte au stop. Cash témoin non rémunéré = 0 %, sans prétendre qu'il répare une observation manquante.

Incertitude descriptive : blocs circulaires de 5 et 20 séances et années complètes, 3 000 répétitions, graine 20261020 ; années sans trade conservées. Peu de groupes annuels en B et filtrage de qualité imposent des réserves. Retirer les trois meilleurs jours est un diagnostic à rendements et tailles figés. A/B/ALL et les variantes se recouvrent ; ne pas compter les lignes comme observations indépendantes. Aucun réglage du stop, objectif, horaire ou budget après P&L.

Toute correction numérique après calcul crée un nouveau dossier avec motif ; conserver les sorties précédentes. Ne modifier ni le bot, ni ses secrets, ni les études historiques. Une performance positive conditionnelle ne suffit pas à autoriser un bot ou du réel.

Précision éditoriale après revue du 20/10/2026 : l'ablation des trois meilleurs jours conserve les autres **rendements quotidiens** et les recompose. La mention antérieure de tailles figées ne décrit pas une trajectoire à quantités originales fixes. Aucun P&L ni paramètre n'est changé ; le texte initial reste dans le gel avant exécution.
