# First Candle Rule + Fair Value Gap

Étude quantitative reproductible, en français. **SPY/QQQ ont maintenant un historique Alpaca SIP de plus de trois ans : 930/931 séances complètes, découpage IS/OOS 70/30 et walk-forward. Les quatre scénarios principaux perdent hors échantillon ; catégorie 3, aucun avantage démontré.** ES/NQ n'ont pas encore de validation longue sur des contrats datés vérifiables.

Ouvrir [le rapport long de référence](results/alpaca_sip_long/RAPPORT_FINAL.md), [le protocole](docs/PROTOCOLE.md), [les sources gratuites examinées](docs/RECHERCHE_SOURCES_GRATUITES.md) et [le statut TradingView](tradingview/README.md). L'[étude Yahoo récente](results/etude_2026-10-19/RAPPORT_FINAL.md) reste une exploration archivée antérieure à la correction numérique des contacts au tick.

L'[acquisition Alpaca SIP](docs/ALPACA_HISTORIQUE_GRATUIT.md) est terminée : 773 977 bougies SPY et 807 421 QQQ, du 3 janvier 2023 au 18 septembre 2026 avant filtrage régulier. 116 scénarios ont été calculés ; 872 lignes principales IS/OOS sont rapprochées indépendamment des bougies et les pages brutes sont archivées. Les fichiers acquis permettent de tout recalculer sans clé ni réseau. La [correction numérique et l'historique de validation](results/alpaca_sip_long/CORRECTION_NUMERIQUE.md) sont déclarés.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) '.python_packages'
$env:MPLCONFIGDIR = Join-Path (Get-Location) '.mplconfig'
python scripts/run_long_history.py --out results/reproduction_alpaca
python scripts/audit_long_history.py --results results/reproduction_alpaca
python scripts/render_long_figures.py --results results/reproduction_alpaca
```

## Installation et exécution

Exécution vérifiée avec Python 3.14 sous Windows. Dans un environnement Python normal :

```powershell
python -m venv .venv_local
.\.venv_local\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pytest -q --basetemp=.test_tmp_local
python -m fvg_backtest --data SPY=chemin/SPY_1m.csv --data QQQ=chemin/QQQ_1m.csv --sensitivity --out results/mes_donnees
```

Les paquets de cette exécution sont déjà installés dans `.python_packages`, avec Python 3.14 Windows. Pour les réutiliser :

```powershell
.\run.ps1 --data SPY=data/yahoo_28d/SPY_1m.csv --data QQQ=data/yahoo_28d/QQQ_1m.csv --data ES=data/yahoo_contracts/ES_1m.csv --data NQ=data/yahoo_contracts/NQ_1m.csv --rolls data/yahoo_contracts/rolls.csv --sensitivity --out results/reproduction
```

Pour exécuter les tests avec cette installation locale :

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) '.python_packages'
$env:MPLCONFIGDIR = Join-Path (Get-Location) '.mplconfig'
python -m pytest -q --basetemp=.test_tmp_local
```

`requirements-lock.txt` fige les versions réellement utilisées. Les données brutes, leur transformation et les SHA-256 sont conservés. Les fichiers produits ne nécessitent pas de télécharger à nouveau des cotations. Les données Yahoo récentes peuvent disparaître de la fenêtre d'accès ; les fichiers archivés permettent la reproduction locale.

## CSV externes et TradingView

```csv
timestamp,open,high,low,close,volume
2025-01-02T09:30:00-05:00,100,101,99,100.5,10000
```

Cet extrait illustre le **format** uniquement ; ce ne sont pas des prix historiques à backtester. Un fichier réel doit contenir toutes les minutes de chaque séance retenue. Horodatage de début de minute par défaut ; `--timestamp-at close` pour un fournisseur qui horodate au close. Timestamps ISO avec fuseau, ou epoch UNIX s/ms. Si les timestamps sont naïfs, fournir `--timezone America/New_York` ou le fuseau réel de la source. Le programme reconnaît notamment `time,open,high,low,close,volume` d'un export TradingView et ignore ses colonnes de plots supplémentaires. Vérifier le fuseau de l'export, ses ajustements et son flux de marché.

Ne pas utiliser de données ajustées pour dividendes/splits sans les identifier et analyser leur effet. Ne pas reconstruire des minutes à partir de bougies 5 minutes. Les barres de fin/début mal alignées et les séances manquantes sont journalisées, sans interpolation.

Futures : ajouter `contract`, avec une échéance explicite. Si plusieurs contrats figurent dans le CSV, fournir `--rolls` :

```csv
effective_date,instrument,contract
2025-09-01,ES,ESZ25
2025-12-11,ES,ESH26
```

Les dates ci-dessus illustrent le **format**, pas une recommandation de rollover. Fournir un calendrier défini avant les signaux : dates fixes préannoncées ou décisions basées uniquement sur les volumes de séances précédentes. Le contrat choisi est fixe toute la séance. Aucun prix n'est raccordé entre deux contrats.

Avec `--margins` : `effective_date,instrument,margin_per_unit`, valeurs historiques USD par contrat. Avec `--calendar` : `date,open,close`, ouvertures/clôtures ISO avec fuseau. Ce calendrier remplace XNYS puis est borné à 09:30–16:00 NY. Pour les futures, il doit représenter l'intersection du calendrier cash américain et des ouvertures CME réelles. `--strict-futures` impose marge et calendrier explicites. Sans ces archives, les futures conservent des hypothèses de marge/calendrier documentées.

`--allow-continuous` permet une **exploration explicitement non validée** d'un continu ; ce mode ne sert pas dans l'étude finale livrée.

## Paramètres et résultats

Les stops A/B et le slippage 1/2/3/5 sont comparés automatiquement, sans sélection du meilleur. `--sensitivity` ajoute séparément retest 10/20 minutes et confirmation 0/1/3 bougies suivantes. Aucun paramètre n'est appris sur l'OOS. `--config configuration.json` accepte les clés du dataclass `Config` pour des hypothèses de coûts, capital et liquidité déclarées avant exécution. Les paramètres du protocole principal restent 15 minutes / 2 bougies / 3R / 0,5 % / 100 000 USD.

Le moteur divise 70/30 chronologiquement lorsque la couverture atteint au moins 365 jours et 252 séances valides. Avec au moins 504 séances, il ajoute des blocs walk-forward sans optimisation : 252 séances de développement, 63 séances suivantes de test, dernier bloc conservé s'il a au moins 30 séances. Les comptes de chaque segment sont réinitialisés pour une comparaison autonome ; ne pas additionner leurs rendements.

Chaque scénario produit un journal de trades, rejets, courbe de capital aux closes 1 minute, résultats quotidiens/mensuels, regroupements LONG/SHORT/heure/volatilité, statistiques JSON et une figure à quatre panneaux. Le manifeste global contient sources, versions et hashes du code. Le drawdown ne représente pas une mesure tick par tick.

La durée des sorties intrabougie est une borne à une minute près. Les timestamps de sortie désignent le début du bar où le niveau a été atteint ; leur ordre exact à l'intérieur du bar est inconnu. Les timestamps de formation, retest et signal désignent les closes qui rendent ces informations disponibles.

## Acquérir à nouveau l'échantillon récent

```powershell
python scripts/download_yahoo.py --symbols SPY QQQ --start 2026-09-21 --end 2026-10-19 --out data/yahoo_28d
python scripts/download_yahoo.py --symbols ESZ26.CME NQZ26.CME --start 2026-09-21 --end 2026-10-19 --out data/yahoo_contracts
python scripts/prepare_yahoo_futures.py
```

Ces commandes ne fonctionneront que tant que le fournisseur conserve ces minutes. `prepare_yahoo_futures.py` est volontairement propre à cet échantillon et à ses contrats décembre 2026. Pour un autre historique, fournir directement les CSV et le calendrier de contrats appropriés.

Après l'exécution finale, `python scripts/audit_historical_trades.py` rapproche indépendamment les trades des scénarios principaux avec les OHLC réels. Il ne valide pas la chronologie subminute, absente des données.
