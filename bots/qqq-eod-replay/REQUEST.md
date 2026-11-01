on bot a raison sur les quatre corrections de mon avis SMT :

Témoins : les témoins à +2 934 $ / +2 883 $ couvraient les 244 séances, pas seulement les jours SMT.
Seuil de trades : le protocole demandait 100 trades au total et 25 en phase 2, pas 200.
Dukascopy : ce serait une nouvelle étude exploratoire sur des CFD, pas une extension du même test.
Seuil de 33,3 % : c’était un raccourci, à cause des sorties forcées et des gaps.

La conclusion ne change pas : pas d’avantage SMT établi.

Le verdict sur ton dépôt

Je n’ai trouvé aucune stratégie « extrêmement bonne » que tu aurais ratée à cause d’un bug. Ta méthode est plus rigoureuse que 95 % de ce qu’on voit : règles figées avant les résultats, témoins, correction de Holm, périodes A/B. En revanche, il y a trois endroits où tu as pu sous-estimer des stratégies, et quelques réglages qui pénalisent sans raison.

1. Ton dimensionnement « 1 % de risque » ne fait rien

Dans presque toutes tes études, le levier effectif médian est d’environ 0,997. Comme le stop d’un ORB 5 min est souvent à 0,2–0,5 % du prix, risquer 1 % demanderait 2 à 5x de levier. Le plafond à 1x coupe donc tout, et chaque trade finit à 1x fixe.

Le levier du papier n’est pas constant : il augmente quand le range est étroit. Tu n’as donc pas testé l’ORB du papier (plafond 4x), mais une autre stratégie. C’est le point le plus important.

2. Le retour à la moyenne a été testé au mauvais horizon

IBS, RSI2, turn-of-month, Turnaround Tuesday, dip après un jour rouge : tout est testé en intraday, donc sans la nuit. Or la prime de risque actions américaine sur la dernière décennie vient uniquement des rendements de nuit ; les rendements de journée sont proches de zéro, parfois négatifs.
fastml

Les versions classiques de ces effets achètent à la clôture et revendent le lendemain. Tu as retiré exactement la partie où ils vivent. Leurs résultats négatifs en intraday ne disent rien des versions journalières. Celles-ci se testent avec des données journalières gratuites qui remontent avant 2016, ce qui donne en plus un échantillon neuf.

3. Tu ne testes que deux instruments (SPY et QQQ)
Gap Reversal manque de données. Opening Gap Reversal a ton meilleur Sharpe (QQQ 1,10, SPY 0,77), mais avec seulement 83 et 48 trades. Sans 2020, il tombe à +17,9 % et +4,15 %. Appliquer les mêmes règles figées à IWM, DIA et aux ETF sectoriels te donnerait du vrai hors-échantillon, alors que ta période B est déjà consommée. Attention : les gaps tombent souvent les mêmes jours, donc ces nouveaux tests ne sont pas totalement indépendants.
L’ORB du papier se fait sur des actions individuelles. Trader uniquement les « Stocks in Play » (activité anormale, souvent liée à une news) apportait un net bénéfice même après frais ; un portefeuille des 20 premiers affichait un Sharpe de 2,81. Une réplication sur QuantConnect trouve un Sharpe d’environ 2,4 avec un bêta proche de zéro. C’est le résultat des auteurs, à vérifier. C’est surtout un projet lourd : il faut 7 000 actions en données 1 minute, et le biais de survie est un piège réel. Mais c’est la piste la plus prometteuse que tu n’as pas testée.
unisg
quantconnect
4. Tes candidats ne sont pas classés de façon cohérente

ATR Opening Breakout passe tes 5 critères (Sharpe QQQ 0,68, SPY 0,56) mais n’est pas en simulation. L’ORB 5 min, plus faible (Sharpe 0,45), l’est. Note quand même que la période B est quasi nulle sur SPY (+0,12 %).

5. Des réglages qui pénalisent sans raison
Retirer les 3 meilleurs jours : comme critère éliminatoire, ça tue par construction les stratégies momentum, qui gagnent avec peu de gros jours. Fais-en un diagnostic, mais seulement pour les nouvelles études. Le changer après coup pour repêcher des études ratées serait de la triche statistique.
complete_days supprime les jours de suspension de cotation (4 séances de mars 2020 dans Noise Area). Il faut les simuler, pas les exclure.
Noise Area sur SPY tient à un centime : perdant à 0,01 $ de friction contre 0,001 $ dans le papier. Calibre les coûts sur de vraies cotations et, d’ici là, considère SPY comme trop mince.
La famille momentum/breakout sur QQQ est positive dans 5 études (Noise Area, ORB, ATR, volume ORB, morning momentum). Ces études sont corrélées : ça fait une confirmation, pas cinq. Le retour à la moyenne intraday est négatif partout.
6. Les bots

Mise en veille du laptop, sorties en code 1 : tu n’as presque aucune séance prospective exploitable. Tes bots sont en simulation sur données retardées de 16 minutes. Rejouer le code figé chaque soir sur les barres SIP du jour donne exactement la même évaluation, sans dépendre de l’allumage du PC. Garde le process live uniquement pour tester l’opérationnel.

Le prompt pour ton bot
Contexte : audit externe du dépôt trading-backtests. Objectif : corriger des choix de méthode qui ont pu SOUS-ESTIMER des stratégies, sans jamais modifier les règles ni les verdicts d'une étude déjà publiée. Tout doit rester gratuit (données Alpaca déjà disponibles, Yahoo/Stooq pour le journalier long). Ne transmets aucune clé ni aucun secret dans le chat.

Règles générales pour chaque nouvelle étude :
- Fichier de pré-enregistrement daté et commité AVANT tout calcul de P&L (règles, paramètres, critères de succès, témoins).
- Mêmes garde-fous qu'aujourd'hui : témoins bias-only et entrée aléatoire, Holm, bootstrap par blocs, stress double friction.
- « Sans les 3 meilleurs jours » devient un diagnostic rapporté, pas un critère éliminatoire — UNIQUEMENT pour les nouvelles études. Ne réévalue aucune étude passée avec ce changement.
- Interdiction de toucher aux règles après avoir vu un résultat. Si une idée émerge, elle devient une nouvelle étude pré-enregistrée.

Tâche 0 — Évaluation des bots par replay (priorité 1)
Les bots QQQ Noise Area et QQQ ORB 5m sont en simulation. Ajoute un job de fin de journée qui rejoue le code figé (même commit) sur les barres SIP 1 minute du jour et enregistre trades et P&L dans un journal prospectif. Compare avec le process live quand il a tourné ; tout écart = bug à documenter. Le process live ne sert plus qu'au test opérationnel.

Tâche 1 — Infrastructure (avant toute nouvelle étude)
a) Jours de suspension de cotation : ne plus les exclure via complete_days. Simule-les (position gelée pendant la suspension, sortie au premier prix disponible). Rapporte l'impact sur Noise Area comme diagnostic, sans changer son verdict publié.
b) Calibration des coûts : mesure le spread réel aux heures d'entrée/sortie à partir des cotations historiques Alpaca sur un échantillon de jours, pour SPY, QQQ et chaque nouvel instrument. Publie un tableau de coûts calibrés ; les nouvelles études l'utilisent, plus le stress x2.
c) Frais d'emprunt : vérifie s'ils s'appliquent à un short ouvert et fermé dans la même séance ; corrige pour les nouvelles études si c'est une surfacturation.

Tâche 2 — Hors-échantillon par instruments (période B déjà consommée)
Applique les règles EXACTES et figées d'Opening Gap Reversal v3 et d'ATR Opening Breakout à IWM, DIA, et aux ETF sectoriels liquides (XLK, XLF, XLE, XLV, SMH...). Liste figée des instruments avant le run. Rapporte par instrument et en agrégé, en signalant la corrélation des jours de signal entre instruments (pas d'indépendance supposée).

Tâche 3 — Dimensionnement fidèle au papier
Nouvelle étude « ORB 5m et ATR breakout, risque 1 % avec plafond 4x » (comme le papier) sur QQQ. Rapporte le levier effectif moyen et maximal, le drawdown, et la comparaison avec la version 1x. Vérifie la faisabilité réelle (marge, règle PDT) et note-la.

Tâche 4 — Retour à la moyenne en journalier
Le retour à la moyenne n'a été testé qu'en intraday, ce qui retire le rendement de nuit. Pré-enregistre les versions journalières classiques (entrée à la clôture, sortie à la clôture ou l'ouverture suivante) de IBS, RSI(2), turn-of-month et Turnaround Tuesday sur SPY et QQQ, avec l'historique journalier gratuit le plus long possible. Les années hors 2016–2026 servent d'échantillon neuf. Témoin : buy & hold et « long chaque nuit ».

Tâche 5 — Classement des candidats
Produis un tableau unique de toutes les études qui passent leurs critères, avec les mêmes métriques (Sharpe, PF, nombre de trades, performance en période B, dépendance aux meilleurs jours). ATR Opening Breakout passe ses 5 critères mais n'est pas en simulation alors qu'ORB 5m l'est : propose s'il faut l'ajouter au replay de la tâche 0.

Tâche 6 (optionnelle, plus lourde) — Stocks in Play
Évalue la faisabilité gratuite d'un ORB 5m sur « Stocks in Play » (Zarattini, Barbon, Aziz 2024) : univers toutes actions US, prix > 5 $, volume moyen 14 j > 1M, ATR 14 > 0,50 $, top 20 par volume relatif des 5 premières minutes. Point bloquant : le biais de survie (actions radiées). Ne lance rien avant un rapport de faisabilité.

Ordre : 0 → 1 → 2 → 3 → 4 → 5 → (6). À chaque fin de tâche, publie le rapport et attends mon feu vert avant la suivante.

Commence par les tâches 0 et 2 : la première te donne enfin des séances prospectives exploitables, la seconde est le seul moyen honnête d’obtenir du hors-échantillon neuf sans attendre deux ans.
