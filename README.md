# Trading Backtests

Dépôt de recherche pour regrouper nos stratégies, leur code, les tests automatisés et les résultats réellement calculés. Chaque étude possède son propre dossier et son statut. Les conclusions restent propres aux instruments, dates et hypothèses testés.

## Registre des études

| Étude | Statut | Résultats disponibles | Conclusion |
|---|---|---|---|
| [Repli EMA9/20 puis reprise](studies/ema-trend-pullback/README.md) | Backtest terminé SPY/QQQ ; piste écartée | Recherche forums/GitHub ;72scénarios figés ;31tests ; replay EWM séparé et4figures | Références A/B/ALL négatives après les mêmes frais ; aucun nouveau bot |
| [Rejet des extrêmes de veille](studies/previous-day-rejection/README.md) | Backtest terminé SPY/QQQ ; piste écartée | Recherche GitHub ;72scénarios figés ;32tests ; replay séparé et4figures | Références A/B/ALL négatives après les mêmes frais ; aucun nouveau bot |
| [ORB confirmé + volume relatif](studies/opening-volume-breakout/README.md) | Backtest terminé SPY/QQQ | Recherche13sources publiques ;72scénarios ;29tests ; audit séparé et4figures | QQQ historiquement positif mais fragile en A ; SPY négatif ; aucune modification des bots |
| [First Candle Rule + FVG](studies/first-candle-fvg/README.md) | Terminée pour SPY/QQQ | Alpaca SIP, 2023–2026, 116 scénarios IS/OOS et walk-forward ; 41 tests automatisés | Aucun avantage démontré dans les conditions testées ; les quatre scénarios principaux perdent hors échantillon |
| [Intraday Momentum « Noise Area »](studies/intraday-momentum-noise-area/README.md) | Terminée pour SPY/QQQ | SIP 2016–16/10/2026 ; 220 scénarios ; 32 tests ; audits indépendants ; 73 figures | SPY : aucun avantage démontré ; QQQ : potentiellement intéressante, preuves insuffisantes |
| [Opening Gap Reversal](studies/opening-gap-reversal/README.md) | Backtest terminé SPY/QQQ | 54 scénarios, 20 tests, audit de 2 334 lignes ; référence v3 | QQQ : piste à suivre, preuves insuffisantes ; SPY peu convaincante |
| [Momentum de clôture](studies/closing-momentum/README.md) | Backtest terminé SPY/QQQ | 42 exécutions, 33 tests, audit de 70 934 lignes recouvrantes ; référence v2 | Principaux négatifs après coûts en A, B et ALL ; aucun bot justifié pour cette version |
| [ORB cinq minutes](studies/opening-range-5m/README.md) | Backtest terminé ; simulation locale QQQ active | 54 scénarios, 42 tests historiques ; [bot séparé](bots/qqq-orb/README.md), 29 tests et parité 2 707 séances | QQQ exploratoire positif mais fragile ; observation shadow lancée le24/10, aucun avantage prospectif encore établi |
| [Retour VWAP après première heure](studies/vwap-reversion/README.md) | Backtest terminé SPY/QQQ | 48 scénarios, 46 tests, 428 pages brutes vérifiées, audit de 12 586 lignes recouvrantes | Principaux négatifs en A/B/ALL après coûts ; archivée, aucun nouveau bot |
| [Compression NR7 puis cassure](studies/nr7-breakout/README.md) | Backtest terminé SPY/QQQ | 48 scénarios, 16 tests, audit indépendant Decimal et échantillons des acquisitions brutes | B principale négative SPY/QQQ ; gains ALL faibles et sensibles aux coûts ; aucun bot NR7 |
| [Nowick / Compensation Play Forex](studies/nowick-compensation/README.md) | Backtest Python terminé sur trois paires ; Pine non compilé | 126 scénarios, 70 tests, archives FXCM 1 min 2015–2024 ; au moins 100 trades résolus par paire | Abandonnée pour un bot ; références et moitiés négatives après 1 pip ; pénalités de couverture explicites |
| [RSI(2) retour à la moyenne intraday](studies/rsi2-intraday/README.md) | Abandonnée ; archive conservée | 72scénarios,25tests, audit indépendant sur78646lignes recouvrantes ; SIP2016–16/10/2026 | Références A/B/ALL négatives après frais ; aucun nouveau bot |

L'étude FVG contient aussi l'exploration Yahoo récente (72 scénarios), clairement archivée, et l'audit des sources gratuites de futures. ES/NQ ne disposent pas d'une validation longue sur des contrats datés vérifiables.

## Pistes actuellement suivies

Nouvelle recherche du26octobre : [repli EMA9/20 puis reprise](studies/ema-trend-pullback/results/2026-10-26-v1/RAPPORT_FINAL.md), avec [sources forums/GitHub et différences de règles](studies/ema-trend-pullback/RESEARCH.md). ALL2016–16/10/2026 après les mêmes frais : **SPY−8,61%/1929trades, QQQ−18,72%/1909trades** ; A et B négatives sur les deux ETF. [Interprétation](studies/ema-trend-pullback/INTERPRETATION.md) : coûts supérieurs au gain de prix brut, variantes positives isolées non promues, aucun nouveau bot. Les deux simulations existantes restent inchangées.

Nouvelle étude du26octobre : [rejet des extrêmes de veille](studies/previous-day-rejection/results/2026-10-26-v1/RAPPORT_FINAL.md), réintégration5min puis entrée open suivant, stop mèche et cible2R. ALL2016–16/10/2026 : **SPY−8,88%/929trades, QQQ−19,16%/998trades** après les mêmes frais ; A et B réutilisée négatives sur les deux ETF. [Décision et limites](studies/previous-day-rejection/INTERPRETATION.md) : piste écartée dans cette formalisation, sans promouvoir la variante QQQ1R positive seulement en B. Les deux simulations existantes restent inchangées.

[Bilan du24octobre : pistes et état des bots](docs/research/2026-10-24-pistes-et-bots.md). Noise Area QQQ reste la piste historique prioritaire ; ORB QQQ la seconde, plus fragile. Les deux moteurs sont actifs en simulation locale shadow/SIP différé16minutes. Aucune séance entièrement qualifiée pour Noise Area depuis la référence21octobre ; première séance ORB prévue26octobre. Aucun avantage prospectif ni bot SPY validé.

La nouvelle [étude ORB confirmé + volume relatif](studies/opening-volume-breakout/results/2026-10-24-v1/RAPPORT_FINAL.md), issue d'une [recherche sur forums, GitHub et publications](studies/opening-volume-breakout/RESEARCH.md), donne ALL QQQ+44,75%/915trades et SPY−5,04%/899trades après les mêmes frais. [Interprétation](studies/opening-volume-breakout/INTERPRETATION.md) : QQQ candidat historique, B réutilisée+29,75%, mais A sensible aux coûts/concentration ; le volume n'améliore pas tous les critères.72scénarios,29tests, audit séparé ; aucun nouveau bot. RSI est abandonnée et ses fichiers restent archivés.

## Consulter le backtest Nowick Forex

[Rapport complet](studies/nowick-compensation/results/2026-10-24-python-v1/RAPPORT_FINAL.md), [126 comparaisons](studies/nowick-compensation/results/2026-10-24-python-v1/comparison_all.csv), [validation et audit](studies/nowick-compensation/VALIDATION_PYTHON.md). Python sur Bid FXCM 1 minute, signaux 15 minutes et règles figées, risque 1 %, coût synthétique 1 pip aller-retour. Entrées nominales 2015–2024 : GBPUSD **−23,77 %**, USDJPY **−30,26 %**, AUDUSD **−52,48 %** ; 127/191/222 trades fermés, dont 122/174/193 sans trou pendant la position. Les deux moitiés sont négatives sur chaque paire.

La source comporte des interruptions, notamment après le 13 décembre 2024 : ces performances incluent des pénalités de couverture et ne représentent pas dix ans de fills certifiés. Les trades sans trou restent perdants en diagnostic comptable. Les sensibilités de frais, filtres, tendance et exécution sont publiées sans choix après résultats. Aucun résultat TradingView, aucune compilation Pine ni aucun nouveau bot Forex ne sont revendiqués.

## Bot QQQ Noise Area en simulation

[Code et lancement de la simulation QQQ](bots/qqq-noise-area/README.md), [validation](bots/qqq-noise-area/VALIDATION.md) et [preuve du replay SIP](bots/qqq-noise-area/validation/replay_2026-10-20.json). Paramètres 14/14, 30 minutes, cible 2 %, plafond 4x ; coûts conservateurs tenus dans un ledger local. 96 tests au correctif du24/10 et parité antérieure sur 618 séances / 7 380 décisions.

Le [lanceur Windows sans console](bots/qqq-noise-area/BACKGROUND_WINDOWS.md) est installé avec démarrage automatique à l'ouverture de session, clés dans le coffre Windows et conservation du solde. Référence prospective à partir du 21 octobre 2026 ; suivi quotidien en jours ouvrés et bilans opérationnels définis. Les preuves de démarrage ne constituent pas des résultats de rentabilité.

Correctif du26octobre : [les quatre retards matinaux](bots/qqq-noise-area/validation/morning_wake_2026-10-26.md) venaient d'une hibernation prolongée jusqu'à12:11. Réveil distinct à09:10Toronto/NewYork du lundi au vendredi sur secteur, puis contrôle de la tâche shadow existante ; arrêts volontaires respectés, batterie/couvercle et journal conservés.103tests passent, dont le maintien de09:10locale après changement d'heure ; une intégration native du coffre sans rapport avec ce correctif est écartée après refus d'accès du bac à sable. Paramètres et action éveillée vérifiés ; premier réveil matériel encore à observer.

Avec l'offre gratuite, le mode retenu est shadow SIP différé de 16 minutes : transactions simulées localement, sans ordre paper. L'essai IEX a été arrêté sans fill à cause de minutes manquantes incompatibles avec les règles strictes. L'adaptateur d'ordres paper reste disponible avec SIP temps réel et droits appropriés. L'[état d'activation observé](bots/qqq-noise-area/validation/activation_2026-10-20.json) distingue la livraison du code, la connexion et les transactions éventuelles.

## Bot ORB QQQ en simulation

[Code, commandes et limites](bots/qqq-orb/README.md), [preuve d'activation du24octobre](bots/qqq-orb/validation/activation_2026-10-24.json), [parité historique](bots/qqq-orb/validation/historical_parity_2026-10-24.json). Tâche Windows cachée `TradingBacktests-QQQ-ORB-Simulation`, au logon, runtime100000USD propre et premières observations éligibles le26octobre2026. Règles ORB figées : première plage5minutes, risque1%, plafond causal1x, objectif10R, stop prioritaire ; mêmes frais. Le transport autorise seulement GET QQQ SIP, aucun ordre broker. 29tests passent ; 2707séances et2688trades reproduisent le moteur historique gelé.

Le démarrage est une preuve opérationnelle ; aucun trade prospectif n'est encore revendiqué. La parité partage le helper historique et n'est pas un nouvel audit indépendant. Sur secteur, les deux superviseurs peuvent maintenir leurs propres requêtes contre la veille automatique ; garder le couvercle ouvert. Noise Area conserve son compte, ses règles et son suivi distincts.

## Nouvelle piste NR7

[Rapport complet](studies/nr7-breakout/results/2026-10-24/RAPPORT_FINAL.md), [48comparaisons](studies/nr7-breakout/results/2026-10-24/comparison_all.csv), [validation](studies/nr7-breakout/VALIDATION.md). Compression stricte de la veille sur7séances, première clôture hors range, entrée open suivant, stop opposé/EOD ; risque1% et plafond causal1x. Mêmes commissions, emprunt et frictions.

ALL2016–16/10/2026 : SPY **+9,60%**, QQQ **+3,74%** après coûts ; B réutilisée01/05/2024–16/10/2026 : **−3,41% /−0,93%**, 106/94trades. B n'est pas un nouvel OOS aveugle. QQQ2020-03-09 est exclue du principal et demeure non résolue en prefix : l'égalité de leurs résultats ne prouve pas la robustesse de la couverture. Aucune variante choisie après observation et aucun bot NR7 installé.

## Consulter le retour VWAP après première heure

[Rapport complet](studies/vwap-reversion/results/2026-10-20/RAPPORT_FINAL.md), [48 comparaisons](studies/vwap-reversion/results/2026-10-20/comparison_all.csv), [validation](studies/vwap-reversion/VALIDATION.md). Mêmes frais, risque cible1 %, plafond causal1x ; vrai champ VWAP minute des archives SIP. ALL : SPY **−9,64 %**, QQQ **−15,79 %** ; B réutilisée : **−0,33 % /−0,87 %**, 107 /129 trades. Comptes historiques conditionnels à la couverture, sans nouveau OOS aveugle ; aucune variante retenue après observation.

## Consulter les résultats ORB cinq minutes

[Rapport complet](studies/opening-range-5m/results/2026-10-20/RAPPORT_FINAL.md), [54 comparaisons](studies/opening-range-5m/results/2026-10-20/comparison_all.csv), [validation](studies/opening-range-5m/VALIDATION.md). Mêmes frais, risque cible 1 %, plafond causal 1x. B réutilisée du 01/05/2024 au 16/10/2026 : QQQ **+7,76 %**, SPY **−0,84 %**, 615 trades chacun ; ALL : **+50,93 % /+1,40 %**. Comptes historiques conditionnels à la qualité des données, filtre connu après coup ; aucune validation aveugle ni performance continue sur journées exclues. QQQ B sans ses trois meilleurs jours devient négatif ; ces statistiques ne qualifient pas un bot pour le réel. La simulation distincte sert à observer de nouvelles séances.

[Décision ORB QQQ et prochaine validation recommandée](docs/research/2026-10-20-orb-qqq-decision.md) : note historique du20octobre, antérieure à la simulation distincte activée le24octobre. Conserver les règles, observer de nouvelles séances et mesurer les coûts/fills ; la mise en simulation ne démontre pas la rentabilité.

## Consulter les résultats du momentum de clôture

[Rapport complet](studies/closing-momentum/results/2026-10-20-v2/RAPPORT_FINAL.md), [42 comparaisons](studies/closing-momentum/results/2026-10-20-v2/comparison_all.csv), [validation](studies/closing-momentum/VALIDATION.md). B exploratoire réutilisée : SPY **−3,39 % /616 trades**, QQQ **−3,70 % /618 trades** à cible 1x, coûts inclus. ALL : **−34,72 % /−35,19 %**. La variante QQQ LONG seule positive en B reste négative sur ALL et sous le témoin LONG de B ; aucun changement du bot Noise Area.

## Consulter les résultats Gap Reversal

[Rapport complet](studies/opening-gap-reversal/results/2026-10-20-v3/RAPPORT_FINAL.md), [comparaison des 54 scénarios](studies/opening-gap-reversal/results/2026-10-20-v3/comparison_all.csv), [validation et corrections](studies/opening-gap-reversal/VALIDATION.md). B exploratoire : QQQ +8,47 % /18 trades, SPY +1,32 % /11 trades, cible 1x et coûts inclus. La stratégie ne remplace pas le bot Noise Area.

## Consulter les résultats Noise Area

- [Rapport complet et réponses aux dix questions](studies/intraday-momentum-noise-area/results/2026-10-19/RAPPORT_FINAL.md)
- [Validation, audits et limites](studies/intraday-momentum-noise-area/results/2026-10-19/VALIDATION.md)
- [Comparaison des 220 scénarios](studies/intraday-momentum-noise-area/results/2026-10-19/comparison_all.csv)
- [Quinze transactions historiques détaillées](studies/intraday-momentum-noise-area/results/2026-10-19/EXAMEN_MANUEL.md)
- [Code, tests et instructions de reproduction](studies/intraday-momentum-noise-area/README.md)
- [Note d'ajout au dépôt](studies/intraday-momentum-noise-area/PUBLICATION_GITHUB.md)

## Consulter les résultats FVG

- [Rapport final de référence](studies/first-candle-fvg/results/alpaca_sip_long/RAPPORT_FINAL.md)
- [Validation et audit des 872 lignes de trades principales](studies/first-candle-fvg/results/alpaca_sip_long/VALIDATION.md)
- [Comparaison des 116 scénarios](studies/first-candle-fvg/results/alpaca_sip_long/comparison_all.csv)
- [Correction numérique documentée](studies/first-candle-fvg/results/alpaca_sip_long/CORRECTION_NUMERIQUE.md)
- [Code Pine et statut de la validation TradingView](studies/first-candle-fvg/tradingview/README.md)

Les résultats ont été calculés avant leur ajout à GitHub. Ce dépôt conserve les fichiers originaux et leurs empreintes ; il ne présente pas l'import comme une nouvelle exécution du backtest. Les manifests historiques peuvent contenir les chemins absolus de la machine d'origine.

## Installation et tests

Python 3.14 a été utilisé pour l'étude FVG. Depuis la racine du dépôt, dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r studies/first-candle-fvg/requirements-lock.txt
Set-Location studies/first-candle-fvg
python -m pytest -q --basetemp=.test_tmp_local
```

Les tests automatisés utilisent des scénarios contrôlés et ne nécessitent ni compte Alpaca ni téléchargement. Ces données de test ne servent jamais aux résultats de marché.

Vérifier l'intégrité des fichiers de l'étude importée, sans dépendance externe :

```powershell
python tools/verify_snapshot.py
```

## Données et futures études

Les historiques minute complets et les clés API restent locaux. Le dépôt conserve les résultats dérivés, les extraits d'audit, la provenance et les scripts d'acquisition. Voir [les instructions pour les données](studies/first-candle-fvg/data/README.md).

Pour ajouter un prochain test, suivre [CONTRIBUTING.md](CONTRIBUTING.md) et [le modèle d'étude](templates/STUDY.md). Ajouter les nouvelles exécutions dans un dossier daté, avec leurs paramètres et leur statut, puis mettre à jour le registre ci-dessus.
