# Tâche 7 — Règles d’arrêt préenregistrées

**1er novembre 2026, America/New_York.** Règles numériques figées pour QQQ Noise Area et QQQ ORB, exclusivement en simulation. Code stratégique inchangé : `f7ed9515b97644102ef674315c6af46e6fce8988`. La règle numérique est publiée au commit **`6e5e36c5ab91caf964523d9f6a52a996aae5f7c2`**, le **1er novembre à 20:33:04 New York** selon GitHub. La première date de la nouvelle population statistique est donc **le 2 novembre 2026**, enregistrée dans [REGISTRATION.json](rules/v1/REGISTRATION.json). Les séances déjà vues depuis le 21 octobre restent séparées. L’activation, les clés et l’amorçage GitHub Actions relèvent de la tâche 8 ; aucun accès aux clés ni changement des tâches live n’a eu lieu ici.

## Seuils de P&L

Chaque compte statistique commence à **100 000 USD**. Les montants représentent le P&L cumulé net, avec capitalisation, depuis ce départ. La bande p5–p95 contient 90 % des chemins bootstrap marginaux à cet horizon ; ce n’est pas une garantie de performance future.

| Bot | Séances | p5 : arrêt si résultat strictement inférieur | Médiane p50 | p95 |
|---|---:|---:|---:|---:|
| Noise Area | 20 | −4 439,17 USD | +960,52 USD | +7 947,55 USD |
| Noise Area | 60 | −6 415,07 USD | +3 297,36 USD | +15 687,09 USD |
| ORB | 20 | −3 248,33 USD | +91,93 USD | +4 622,38 USD |
| ORB | 60 | −5 376,71 USD | +654,21 USD | +8 493,66 USD |

Les contrôles p5 ont lieu **une seule fois après les 20 premières, puis les 60 premières séances résolues dans l’ordre**. Il ne s’agit ni de 20/60 trades, ni de fenêtres glissantes. Une séance complète sans trade compte ; une séance inconnue bloque la suite et n’est jamais remplacée par un zéro. Le résultat à 60 séances part toujours du capital initial, sans remise à zéro après 20.

Un arrêt reste acquis même si des prix ou un calcul ultérieur feraient remonter le P&L. Après détection de fin de journée, les nouvelles entrées de ce compte sont suspendues dès la séance suivante. Les journées post-arrêt portent explicitement `registered_risk_stop` ; elles ne sont pas présentées comme des journées où le modèle de base aurait naturellement choisi de rester liquide. Les transactions déjà calculées et les positions non résolues ne sont ni réécrites ni effacées. Aucune reprise ou modification de seuil automatique.

Les valeurs non arrondies de [RULE.json](rules/v1/RULE.json) commandent les décisions ; les centimes affichés servent à la lecture. Seule une tolérance numérique de 0,000001 USD évite une fausse inégalité due aux flottants.

## Seuil de drawdown

| Bot | Pire drawdown du backtest continu figé | Seuil strict d’arrêt : 1,5 × historique |
|---|---:|---:|
| Noise Area | 28,4854 % | **42,7281 %** |
| ORB | 14,2287 % | **21,3430 %** |

Le drawdown est la baisse depuis le plus haut capital marqué atteint, en pourcentage de ce sommet. Il utilise les marques ordonnées de clôture 1 minute et de fills des moteurs historiques, frais compris, en conservant les sommets entre séances. Il ne se limite pas aux clôtures quotidiennes ; il ne prétend pas mesurer les extrêmes intraminute inconnus. La tolérance numérique est de 1e-10 en fraction.

Le seuil Noise est large parce que la formule demandée applique 1,5 au pire historique complet, atteint en mai 2017 ; ORB atteint son pire historique en juin 2023. Ces valeurs n’ont pas été resserrées après leur découverte. Ce sont des limites expérimentales de simulation, pas une proposition de budget de risque réel. Le contrôle est de fin de journée : il n’ajoute aucune sortie intraday au modèle figé.

## Parité : déclencheur d’enquête

Une différence supérieure à **0,01 USD** sur le P&L net ou un coût, supérieure à **0,000001 USD** sur un prix ou à 1e-6 sur un indicateur numérique, ou toute différence de quantité, sens ou heure économique d’entrée/sortie déclenche une enquête. Les timestamps sont comparés en instants équivalents, indépendamment de leur présentation UTC/New York. Les changements d’empreinte de prix ORB et les conflits de source sont également signalés.

Le rapprochement utilise le diagnostic à capital comparable lorsqu’il existe. Il conserve les explications possibles : couverture manquante, reprise tardive, état initial différent, révision de prix, archive Noise incomplète. Une absence de comparaison ne vaut jamais accord. Un écart documenté ne devient pas automatiquement une preuve de bug du moteur. L’enquête suspend la validation ; elle n’autorise aucun ajustement automatique de stratégie ou de frais. Les observations antérieures à la date d’enregistrement ne reçoivent pas rétroactivement ces seuils.

## Méthode figée avant les résultats

Le [plan de calibration](rules/v1/CALIBRATION_PLAN.json) a été committé et poussé dans **`d21b3e6976ed4d7318d237e9f9998f22cfe25417` avant le calcul numérique**. Il fixe 50 000 chemins, générateur NumPy PCG64, graine 20261101, blocs mobiles non circulaires de cinq séances XNYS consécutives et horizons 20/60 sur les mêmes chemins. Aucun bloc ne franchit une journée exclue ou absente. Les rendements nets journaliers sont composés, sans appliquer les nouvelles règles d’arrêt aux chemins de calibration. Le bootstrap ne recalcule ni les quantités entières ni la volatilité sur chaque chemin synthétique : les frais et le sizing sont déjà présents dans les rendements sources, dont il rééchantillonne la distribution. Aucune longueur de bloc ou variante n’est choisie après comparaison des résultats.

Les deux moteurs historiques au SHA figé sont réexécutés depuis 100 000 USD sur **2016-01-04 à 2026-10-16**. Noise n’avait pas de fichier ALL publié à ces frais : cette base continue est dérivée du code existant, sans reset entre A et B et sans nouvelle hypothèse d’alpha. Elle ne remplace aucun ancien résultat publié. La partie A de Noise, 2 080 lignes, et l’intégralité ALL d’ORB, 2 713 lignes, ont été rapprochées des fichiers publiés avec un écart maximal inférieur à 6e-11 sur les montants et aucun écart de quantité.

Coûts conservés : commission 0,0035 USD/action/côté, minimum 0,35 USD/ordre ; friction 0,01 USD/action/côté ; emprunt short 1 % annuel/360, minimum un jour. Noise conserve le plafond 4x, les observations 14/14, les décisions 30 minutes et le signal combined. ORB conserve son risque de sizing 1 %, plafond 1x, cible 10R et stop prioritaire. Leur calibration éventuelle en tâche 1 sera une nouvelle version avec sa propre règle.

| Base | Lignes calendaires | Séances éligibles au bootstrap | Blocs valides |
|---|---:|---:|---:|
| Noise Area | 2 713 | 2 646 | 2 634 |
| ORB | 2 713 | 2 707 | 2 687 |

Noise exclut six journées de données invalides et 61 journées d’indicateurs passés indisponibles, dont le warmup initial. ORB exclut cinq journées incomplètes et une ouverture invalide. Les zéros artificiels de ces exclusions historiques ne sont pas échantillonnés. Les vrais jours sans trade restent dans la base. Les rendements et drawdowns historiques restent conditionnels à cette qualité de données ; la tâche 1 traitera séparément les suspensions, sans retoucher cette version.

Le bootstrap par blocs conserve une dépendance locale, suivant la famille de méthodes de [Künsch (1989)](https://doi.org/10.1214/aos/1176347265). Le choix fixe de cinq jours ne préserve pas tous les régimes de longue durée. Les bandes ne sont ni un intervalle de confiance du rendement moyen, ni une preuve de rentabilité, ni une couverture simultanée de tous les bots et horizons.

Avec deux contrôles p5, la fréquence bootstrap de franchir au moins l’un des deux seuils est **8,464 % pour Noise et 8,692 % pour ORB**, même lorsque les chemins sont issus de cette base. Ces fréquences n’incluent pas le critère de drawdown et ne constituent pas un calcul de risque global entre bots. Les contrôles de risque prescrits ne sont pas des tests d’alpha ; ils ne servent à promouvoir aucune stratégie ni à contourner Holm pour une nouvelle étude.

## Vérifications et publication

- [Reçu de calibration et provenance](rules/v1/calibration_receipt.json), [base Noise](rules/v1/noise_baseline_daily.csv), [base ORB](rules/v1/orb_baseline_daily.csv).
- [Second algorithme de calcul](validation/task7_second_algorithm.json) : erreur maximale sur tous les quantiles inférieure à 6e-12 USD, seuils de drawdown identiques.
- Recalcul indépendant par un autre agent : mêmes blocs et quantiles, écart nul, aucune anomalie importante trouvée.
- [Contrôle SIP réel rétrospectif](validation/task7_offline_check.json) : P&L, prix, frais et métriques de risque reproduits sans écart sur la séance contrôlée. Aucun résultat de cette séance passée ne devient prospectif.
- [Preuves finales](validation/task7_checks.json) : **71 tests locaux et 71 tests Linux réussis**, empreintes et publication GitHub avant la première date. [Run GitHub 41373059258](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41373059258), chiffrement vérifié, job statistique désactivé comme prévu.

Le chargeur vérifie le contenu Git immuable de la règle, le commit de la recette, les frais/paramètres des moteurs figés et la date de départ. Avant une future exécution active, il vérifiera aussi auprès de GitHub qu’un run sur main portant ce SHA a réellement été créé avant la première date ; un commit simplement antidaté ne suffit pas.

**État à livraison : règles publiées, activation désactivée, zéro nouvelle séance statistique exécutée.** L’ancre d’amorçage dans REGISTRATION.json engage les deux soldes virtuels initiaux, la population et les positions nulles avant les prix futurs ; elle n’est pas un runtime initialisé et ne contient aucun résultat de marché. La tâche 8 devra traiter l’amorçage et les éventuels rattrapages sans déplacer cette date pour éviter des pertes, sans reset d’un état existant et sans déclarer le replay « observé en direct ». Les deux simulations opérationnelles existantes restent séparées et inchangées.
