# Trading Backtests

Dépôt de recherche pour regrouper nos stratégies, leur code, les tests automatisés et les résultats réellement calculés. Chaque étude possède son propre dossier et son statut. Les conclusions restent propres aux instruments, dates et hypothèses testés.

## Registre des études

| Étude | Statut | Résultats disponibles | Conclusion |
|---|---|---|---|
| [First Candle Rule + FVG](studies/first-candle-fvg/README.md) | Terminée pour SPY/QQQ | Alpaca SIP, 2023–2026, 116 scénarios IS/OOS et walk-forward ; 41 tests automatisés | Aucun avantage démontré dans les conditions testées ; les quatre scénarios principaux perdent hors échantillon |
| [Intraday Momentum « Noise Area »](studies/intraday-momentum-noise-area/README.md) | À faire | Cahier des charges enregistré ; aucun backtest exécuté | Aucune conclusion disponible |

L'étude FVG contient aussi l'exploration Yahoo récente (72 scénarios), clairement archivée, et l'audit des sources gratuites de futures. ES/NQ ne disposent pas d'une validation longue sur des contrats datés vérifiables.

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
