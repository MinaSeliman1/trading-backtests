# Trading Backtests

Dépôt de recherche pour regrouper nos stratégies, leur code, les tests automatisés et les résultats réellement calculés. Chaque étude possède son propre dossier et son statut. Les conclusions restent propres aux instruments, dates et hypothèses testés.

## Registre des études

| Étude | Statut | Résultats disponibles | Conclusion |
|---|---|---|---|
| [First Candle Rule + FVG](studies/first-candle-fvg/README.md) | Terminée pour SPY/QQQ | Alpaca SIP, 2023–2026, 116 scénarios IS/OOS et walk-forward ; 41 tests automatisés | Aucun avantage démontré dans les conditions testées ; les quatre scénarios principaux perdent hors échantillon |
| [Intraday Momentum « Noise Area »](studies/intraday-momentum-noise-area/README.md) | Terminée pour SPY/QQQ | SIP 2016–16/10/2026 ; 220 scénarios ; 32 tests ; audits indépendants ; 73 figures | SPY : aucun avantage démontré ; QQQ : potentiellement intéressante, preuves insuffisantes |
| [Opening Gap Reversal](studies/opening-gap-reversal/README.md) | Backtest terminé SPY/QQQ | 54 scénarios, 20 tests, audit de 2 334 lignes ; référence v3 | QQQ : piste à suivre, preuves insuffisantes ; SPY peu convaincante |
| [Momentum de clôture](studies/closing-momentum/README.md) | Backtest terminé SPY/QQQ | 42 exécutions, 33 tests, audit de 70 934 lignes recouvrantes ; référence v2 | Principaux négatifs après coûts en A, B et ALL ; aucun bot justifié pour cette version |

L'étude FVG contient aussi l'exploration Yahoo récente (72 scénarios), clairement archivée, et l'audit des sources gratuites de futures. ES/NQ ne disposent pas d'une validation longue sur des contrats datés vérifiables.

## Bot QQQ Noise Area en simulation

[Code et lancement de la simulation QQQ](bots/qqq-noise-area/README.md), [validation](bots/qqq-noise-area/VALIDATION.md) et [preuve du replay SIP](bots/qqq-noise-area/validation/replay_2026-10-20.json). Paramètres 14/14, 30 minutes, cible 2 %, plafond 4x ; coûts conservateurs tenus dans un ledger local. 69 tests et parité antérieure sur 618 séances / 7 380 décisions.

Le [lanceur Windows sans console](bots/qqq-noise-area/BACKGROUND_WINDOWS.md) est installé avec démarrage automatique à l'ouverture de session, clés dans le coffre Windows et conservation du solde. Référence prospective à partir du 21 octobre 2026 ; suivi quotidien en jours ouvrés et bilans opérationnels définis. Les preuves de démarrage ne constituent pas des résultats de rentabilité.

Avec l'offre gratuite, le mode retenu est shadow SIP différé de 16 minutes : transactions simulées localement, sans ordre paper. L'essai IEX a été arrêté sans fill à cause de minutes manquantes incompatibles avec les règles strictes. L'adaptateur d'ordres paper reste disponible avec SIP temps réel et droits appropriés. L'[état d'activation observé](bots/qqq-noise-area/validation/activation_2026-10-20.json) distingue la livraison du code, la connexion et les transactions éventuelles.

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
