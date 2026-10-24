# Nowick / Compensation Play — Pine v6

**Statut : code et tests contrôlés livrés ; rentabilité non évaluée.** Aucune performance de marché GBPUSD/USDJPY/AUDUSD n'a été calculée. La compilation et l'exécution Pine restent à confirmer dans TradingView. Les 27 tests Python ne compilent pas le Pine et ne constituent pas un backtest FX.

La méthode testable est la formalisation donnée par Mina le24octobre2026, conservée dans [MISSION.md](MISSION.md). Aucun document original Bard FX n'a été fourni ; aucune conformité à une autre version de sa méthode n'est revendiquée. Les deux bots QQQ existants ne sont pas concernés.

## Code complet

- **GBPUSD et AUDUSD** : [nowick_compensation_usd.pine](tradingview/nowick_compensation_usd.pine).
- **USDJPY** : [nowick_compensation_jpy.pine](tradingview/nowick_compensation_jpy.pine).

Les règles et la taille du pip sont communes. La seconde version est générée par [build_variants.py](scripts/build_variants.py) : seuls l'en-tête, le titre, la commission en devise de cotation et la garde de devise diffèrent. Pine exige des constantes dans la déclaration de ces coûts ; leur valeur monétaire exacte ne peut pas être choisie avec un input dynamique selon la paire. Les Propriétés de la stratégie restent modifiables.

## Installation pour débutant

1. Ouvrir TradingView puis **Supercharts / Graphique**. Choisir un symbole Forex parmi `OANDA:GBPUSD`, `OANDA:AUDUSD`, `OANDA:USDJPY`, si ces flux sont disponibles. Conserver le même fournisseur pour les comparaisons.
2. Choisir **15 minutes**, et le type **Bougies / Candles ordinaires**. Le script refuse les autres unités et les bougies synthétiques.
3. Ouvrir le fichier `.pine` adapté ci-dessus, sélectionner tout et copier son contenu. Dans TradingView, ouvrir **Pine Editor**, créer une nouvelle stratégie vierge, sélectionner tout et coller. Le fichier commence par `//@version=6` et contient `strategy(...)`.
4. Cliquer **Enregistrer**, nommer le script, puis **Ajouter au graphique**. Il n'est pas nécessaire de connecter un courtier, un compte paper ou des clés API. Si le compilateur affiche une erreur, conserver le message et la ligne : la validation Pine n'est pas encore acquise dans cette livraison.
5. Ouvrir la roue dentée de la stratégie, onglet **Paramètres / Inputs**. Conserver d'abord Structure, pivots5, 02:00–08:00, America/New_York, tolérance0, entrée Ouverture, validité9, front-run activé, SL3/5/30pips, objectif1R ; quatre filtres désactivés. Le fuseau du graphique peut être différent : le calcul utilise le fuseau renseigné dans le script.
6. Choisir les **dates des nouvelles entrées**. Le défaut est01/01/2016–24/10/2026 UTC : cela ne télécharge pas cette période si le graphique ne possède pas ces données. Les sorties SL/TP continuent après la date de fin ; un trade encore ouvert reste exclu des statistiques de trades fermés.
7. Dans **Propriétés**, vérifier les frais, la devise et les options ci-dessous. Désactiver les recalculs à chaque tick et après remplissage ; laisser l'exécution sur clôture désactivée. Le Bar Magnifier est demandé ; s'il est indisponible dans le forfait, le désactiver et signaler cette dégradation de validation dans l'export.
8. Ouvrir **Rapport de stratégie / Strategy Tester**. Lire le tableau natif et le stress séparément, relever le nombre de trades et les dates réellement couvertes, puis exporter la liste des transactions et les métriques si le forfait le permet. Sauvegarder les réglages et un relevé du tableau. Répéter sur chaque paire, sans fusionner les résultats comme s'il s'agissait d'un portefeuille simulé.

## Frais et unités : à vérifier avant toute lecture des gains

La devise du compte doit rester **Default / devise du symbole** (`currency.NONE`), avec `syminfo.pointvalue=1`. Ainsi la taille représente des unités de devise de base et les commissions sont exprimées dans la devise de cotation. Le script refuse une configuration incompatible plutôt que d'afficher un risque erroné.

| Paire | Fichier | Compte | Commission cash par unité, par côté | Coût aller-retour de base |
|---|---|---|---:|---:|
| GBPUSD | USD | USD | 0,00005 | 0,0001 = 1pip |
| AUDUSD | USD | USD | 0,00005 | 0,0001 = 1pip |
| USDJPY | JPY | JPY | 0,005 | 0,01 = 1pip |

Choisir **Cash par contrat / cash per contract**, pas cash par ordre ni pourcentage. Les noms de l'interface peuvent varier. Le capital initial par défaut est100000 dans la devise du compte : **100000JPY pour USDJPY**, pas100000USD. Pour comparer des montants similaires, ajuster le capital JPY avec un taux documenté ; les métriques en R restent celles de chaque simulation. Ne pas changer le compte JPY en USD sans adapter explicitement le modèle de coûts et de conversion.

Le slippage par défaut est **0 tick** : le pip de commission représente déjà le coût total de base demandé. On peut augmenter la commission pour simuler2ou3pips, ou ajouter un slippage en ticks comme test supplémentaire. TradingView applique le slippage natif aux ordres market/stop, pas uniformément aux limites : un slippage de10ticks ajouté ici ne signifie pas «1pip aller-retour sur chaque trade». Ce modèle ne reproduit pas un spread bid/ask variable, les swaps overnight, ni des minimums de commission de courtier.

**Vérification des limites** : le défaut natif est10ticks, soit1pip sur un flux GBPUSD/AUDUSD à5décimales ou USDJPY à3décimales. Sur un flux à4/2décimales, choisir1tick. La formule est `ceil(pip / mintick)` ; le tableau affiche la valeur recommandée, **pas une lecture des Propriétés réellement appliquées**. Vérifier le champ «Verify price for limit orders / Vérifier le prix des ordres limites» et, si présent, le mode d'exécution des limites. Cette exigence s'applique également au TP limite. La pénétration exigée n'est pas une commission supplémentaire : elle élimine les simples contacts mais ne débite pas un autre pip du compte.

Risque de prix = `floor((equity * 0.01 / distanceSL) / mincontract) * mincontract`, pointvalue1. Taille figée au signal, une position/limite à la fois, marge1% (plafond100x). Si l'arrondi ou la marge empêche un ordre, le risque effectif peut être plus faible. Les frais, gaps et slippages peuvent porter une perte au-delà de1% ; aucun risque net plafonné n'est garanti. La marge du courtier réel peut différer. Une liquidation ou plusieurs clôtures inattendues dans une même bougie font refuser le journal par la garde du script.

## Règles et conventions vérifiables

Les paramètres principaux suivent la mission. Les pivots sont utilisés sur leur bougie de confirmation,5barres après l'extrême ; les marqueurs Nowick ne sont jamais décalés vers le passé. L'EMA1h utilise `lookahead_off`, mais surtout n'est mémorisée qu'à une clôture15m coïncidant avec la clôture1h renvoyée. Aucune valeur de l'heure en cours ne décide du signal. La variante EMA attend au moins200barres1h et refuse une valeur horaire trop ancienne. La comparaison historique/temps réel/rechargement reste une vérification pratique à réaliser.

Une Nowick clôturée à02:00 peut autoriser une entrée à02:00, même si sa formation commence à01:45. L'ordre posé à la clôture du signal reste actif pendant les9bougies suivantes incluses, avec annulation à la clôture de la neuvième s'il n'est pas rempli. Il est annulé avant la bougie hors session, hors dates ou chevauchant une news. Aucun nouveau signal ne remplace une limite encore active. Un nouveau signal après annulation est possible. Les sorties ne sont pas restreintes à02:00–08:00.

Le stop est figé au dernier pivot confirmé connu au signal,3pips au-delà. Le TP est calculé à partir de la limite prévue et du SL ; les niveaux arrondis au tick peuvent modifier légèrement le ratio, avec arrondi du TP vers un profit plus faible. Le risque R enregistré est le risque prévu au signal, pas un risque recalculé favorablement après une amélioration de prix. Les fills différents du prix prévu sont comptés parmi les ambiguïtés.

Swing compare l'ouverture de la Nowick aux extrêmes low/high des10barres incluant celle du signal. S/R parcourt les pivots opposés confirmés depuis100barres au plus, paramétrable, strictement entre entrée et TP. Double Nowick conserve le premier ordre accepté, ignore le second de même sens à2–4barres ; l'écart de1barre n'est pas bloqué par ce filtre. Ces précisions sont des choix de formalisation, pas des règles attribuées à Bard FX.

News : activer le filtre et saisir par exemple `2026-10-28@0245-0315;2026-10-30@0745-0800`. **Ces dates/heures illustrent seulement le format, pas un vrai calendrier de publications.** Tout chevauchement interdit la bougie entière ; saisir les dates réelles à partir d'un calendrier archivé avant le test. Plages du même jour, pas de passage minuit, pas de point-virgule final. Au maximum100plages, en fuseau sélectionné. Une position existante n'est jamais fermée à cause des news.

## Ce qui reste approximatif, même avec un code mécanique

Un script de graphique15m calculé à clôture ne peut pas annuler rétrospectivement une limite remplie pendant la bougie. Si front-run et retest se produisent dans la même bougie, leur ordre exact est parfois inconnu. **Le front-run natif est donc une approximation à clôture, pas l'application certifiée de cette règle à chaque tick.** De même, le moteur choisit une séquence intrabougie pour les TP/SL ; le script n'impose pas systématiquement «stop d'abord». Bar Magnifier réduit certaines incertitudes avec des données plus fines, sans rendre le code de cancellation exécutable à chaque tick historique.

Le tableau montre deux colonnes :

- **Natif net** : les ordres et le capital du Strategy Tester. Le PnL provient du delta de `strategy.netprofit` à la clôture du trade : aucune deuxième soustraction des commissions.
- **Stress ambiguïté** : mêmes trades et tailles natifs ; tout trade présentant un front-run sur la bougie du fill, un SL et TP touchés dans la même bougie, ou un prix de fill différent de la limite prévue, reçoit au plus `-risque initial - commission`, en conservant la perte native si elle est pire. Les autres trades gardent leur résultat natif.

Le stress peut pénaliser une bougie dont l'ordre réel aurait été valide ; il peut compter une perte là où le vrai front-run aurait annulé tout trade. **Ce n'est pas un second portefeuille, une reconstruction tick, ni une borne universelle en présence de gaps/slippage inconnus.** Le Strategy Tester continue à utiliser le capital natif. Une stratégie à peine positive dans le natif et négative dans le stress ne fournit pas un avantage suffisamment établi. La version strictement conforme au front-run intrabar demanderait un historique bid/ask ou tick et un moteur externe ; ne pas attribuer cette propriété au script15m.

Une garde refuse tout nouveau fill sur une bougie suivant un trou de données, même si son heure serait admissible : un ordre ne peut ainsi survivre silencieusement à une frontière de séance pendant le trou. S'il n'est pas rempli sur cette première bougie de reprise, il est annulé à sa clôture. La garde refuse également les fills dans une bougie hors fenêtre, hors dates ou chevauchant des news. Le code ne corrige pas cette transaction a posteriori. Un historique discontinu peut donc arrêter l'exécution au lieu de produire un résultat flatteur.

Profit factor = somme des PnL positifs nets / valeur absolue des PnL négatifs nets, en monnaie. Espérance = moyenne des PnL nets divisés par le risque initial prévu de chaque trade. Drawdown R = baisse maximale de la somme des R **fermés**, distincte du drawdown intratrade en monnaie/% du Strategy Tester. Un zéro net casse la série de pertes. Le Wilson95% est binomial et ne corrige pas la dépendance entre trades ou paires.

## Win rate minimal

Pour un stop deS pips, objectif de bR et coût total fixe c pips : gain net `b-c/S` R, perte nette `-1-c/S` R. À l'équilibre :

`p_min = (1 + c/S) / (1 + b)`.

| Stop | Coût total | Objectif | Win rate d'équilibre |
|---:|---:|---:|---:|
| 5pips | 1pip | 1R | 60,00% |
| 10pips | 1pip | 1R | 55,00% |
| 20pips | 1pip | 1R | 52,50% |
| 30pips | 1pip | 1R | 51,67% |

Il faut être **au-dessus**, pas seulement à ce seuil. Avec des stops différents, c/S varie : utiliser la moyenne empirique des coûts en R pour la série, ou mieux vérifier directement une espérance nette positive. Des gaps, arrondis, slippages asymétriques et fills améliorés changent le seuil simple. Un win rate de50% à1:1 est perdant après ces coûts. Ce calcul n'est pas une estimation du win rate de la méthode.

## Plan de test fixé avant résultats

1. Figer le fournisseur, les données bid/mid/ask, période et fuseau. Référence : Structure5, ouverture, TTL9, front-runON, 3/5/30pips,1R,1% prix,1pip coût et1pip pénétration, quatre filtresOFF. Noter marge et disponibilité du Bar Magnifier. Répertorier les paramètres avant de voir les performances.
2. Obtenir **au moins100trades fermés par paire** pour la référence, idéalement100par moitié et par variante comparée. Si un filtre laisse moins de100, l'indiquer et étendre la période pour **toutes** les variantes selon une règle fixée à l'avance ; ne pas relâcher les filtres pour atteindre un résultat positif.100trades demeure un petit échantillon.
3. Scinder la période en deux moitiés **chronologiques de durée égale**, mêmes bornes pour les paires si leur couverture le permet. Tester A et B séparément avec historique antérieur conservé pour chauffer les pivots/EMA. Les positions sont affectées à la moitié selon leur date d'entrée ; laisser SL/TP se terminer après la borne et signaler les chevauchements. Ni split selon le nombre de trades ni remise à zéro artificielle des indicateurs.
4. Tester un facteur à la fois : SwingON vs OFF, S/RON vs OFF, DoubleON vs OFF, NewsON vs OFF (calendrier daté figé). Laisser tous les autres réglages à la référence. Puis examiner une combinaison de filtres choisie à l'avance. Ne pas comparer16combinaisons pour ne publier que la meilleure.
5. Sensibilités supplémentaires identifiées comme telles : EMA50/2001h, entrée50%corps, objectif1.5R/2R, front-runOFF et coûts2/3pips. Ne pas confondre la rentabilité d'une variante choisie après observation avec celle de la référence. Pour une variante retenue après A, B ne reste hors échantillon que si elle n'a jamais été regardée pour la choisir ; sinon réserver une troisième période future.
6. Pour chaque paire, moitié et variante : trades, dates réelles, coût, PnL net, WR et Wilson, PF, espéranceR, plus longue série de pertes, DDferméR et DDintratrade%, nombre de trades ambigus, natif/stress, position ouverte finale et concentration par mois/direction. Rapprocher toutes les transactions exportées et les statistiques. Vérifier un échantillon de signaux, pivots à leur date de confirmation, expirations, annulations et fills au contact/sans pénétration.
7. Ne retenir une piste qu'avec une espérance nette suffisamment robuste sur les trois paires et les deux moitiés, une faible dépendance aux trades ambigus et aux quelques meilleurs gains, et une tenue aux coûts plus sévères. Puis geler le script et observer une nouvelle période en simulation, sans passage automatique en réel. Un désaccord entre paires est un résultat à publier, pas une paire à supprimer.

À50gains/100trades, Wilson95% est environ40,38–59,62% :100trades ne prouve pas une rentabilité à un seuil de55%. Les résultats de plusieurs variantes ne sont pas des réplications indépendantes.

## Sources officielles et limites de preuve

- [Stratégies Pine : moteur, limites, Bar Magnifier, monnaie et coûts](https://www.tradingview.com/pine-script-docs/concepts/strategies/).
- [Propriétés des stratégies](https://www.tradingview.com/support/solutions/43000628599-strategy-properties/).
- [Données de plusieurs unités et repainting](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/).
- [Risque fixe et marge](https://www.tradingview.com/pine-script-docs/faq/strategies/).
- [Limites des historiques intraday](https://www.tradingview.com/support/solutions/43000480679-historical-intraday-data-bars-and-limits-explained/).
- [PnL net : somme des transactions fermées](https://www.tradingview.com/support/solutions/43000681684-net-p-l/).

Les historiques intraday varient selon le forfait ; régler une date de début ancienne n'étend pas la couverture. Le Forex est décentralisé : le flux choisi peut créer ou supprimer une Nowick sans mèche que le courtier ne voit pas. Une limite touchée/pénétrée n'assure ni liquidité, ni priorité dans la file, ni fill réel. Les positions peuvent passer la nuit, avec swap non modélisé. Le stress ne répare pas ces données manquantes.

## Reproduction locale

Depuis ce dossier : `python -m unittest discover -s tests -v` ; sur cette machine, Python3.14 et `PYTHONPATH` vers le dossier local `.python_packages` fournissent tzdata sous Windows. Seul tzdata est nécessaire aux scénarios horaires si le système ne dispose pas d'IANA. `python scripts/build_variants.py` régénère le fichier JPY. Les fixtures ne téléchargent rien et ne contiennent aucun résultat Forex.
