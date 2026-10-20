# Intraday Momentum « Noise Area » — étude exécutée

**220 scénarios réellement exécutés**, 4 258 678 lignes minute Alpaca SIP contrôlées, historique régulier du 4 janvier 2016 au **16 octobre 2026**, premier jour éligible le 26 janvier. Étude ajoutée au dépôt `trading-backtests` le 20 octobre 2026 ; [provenance de la publication](PUBLICATION_GITHUB.md).

**Conclusion : SPY catégorie 3, aucun avantage démontré ; QQQ catégorie 2, potentiellement intéressante mais preuves insuffisantes.** En B (1er mai 2024–16 octobre 2026), prochain open et coûts de référence, la cible 4x donne +8,61 % sur SPY et +59,41 % sur QQQ. La concentration des gains, l'incertitude après révision de l'article et les coûts empêchent d'en déduire une validation pour le réel.

- [Rapport complet et réponses aux dix questions](results/2026-10-19/RAPPORT_FINAL.md)
- [Comparaison des 220 scénarios](results/2026-10-19/comparison_all.csv)
- [Validation et limites](results/2026-10-19/VALIDATION.md)
- [Quinze transactions historiques détaillées](results/2026-10-19/EXAMEN_MANUEL.md)
- [Protocole préexécution](docs/PROTOCOLE.md) et [mission reçue](MISSION.md)
- [Pine v6, preuve de compilation et limites](tradingview/README.md)

## Installation

Python **3.14.6** a été utilisé. Depuis ce dossier dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pytest -q --basetemp=.test_tmp_local
```

Les 32 tests utilisent des petites séries contrôlées sans API. Ces séries ne servent jamais aux résultats de marché. `requirements-lock.txt` fige l'environnement réellement installé ; `requirements.txt` contient les dépendances directes.

## Acquisition et préparation

Les [instructions de données](data/README.md) expliquent les acquisitions et les fichiers exclus de Git. `$studyWorkspace` désigne le dossier qui contient les trois sous-dossiers d'acquisition. Sur cette machine, il s'agit du dossier **Trading**, trois niveaux au-dessus de cette étude.

```powershell
$studyWorkspace = (Resolve-Path ../../..).Path
python scripts/download_public_sources.py --workspace $studyWorkspace
python scripts/resolve_dividends.py --workspace $studyWorkspace
python scripts/prepare_data.py --workspace $studyWorkspace --out data/prepared
```

Une nouvelle requête peut retourner des données révisées ; seules les empreintes des fichiers archivés établissent une reproduction exacte. Ne charger les caches pickle que depuis cette acquisition de confiance.

## Relancer l'étude et les audits

Utiliser un **nouveau dossier** pour chaque exécution : le moteur refuse d'écraser des résultats existants. L'exécution des 220 scénarios a pris environ 684 secondes ; l'audit indépendant prend plusieurs minutes supplémentaires.

```powershell
$studyResults = 'results/nouvelle_execution'
python scripts/run_study.py --workspace $studyWorkspace --out $studyResults
python scripts/audit_study.py --results $studyResults --prepared data/prepared
python scripts/audit_intraday_risk.py --results $studyResults --prepared data/prepared
python scripts/uncertainty_checks.py --results $studyResults
python scripts/compare_spy_passive.py --results $studyResults
python scripts/render_figures.py --results $studyResults
python scripts/write_report.py --workspace $studyWorkspace --results $studyResults --prepared data/prepared
```

`write_report.py` ne rejoue pas les signaux. Le jeu livré possède aussi une reproduction complète de la préparation dans `data/prepared_reproduction`, aux six hashes identiques. Cette vérification est propre à la livraison datée ; une nouvelle étude doit refaire sa propre validation. La preuve de compilation TradingView concerne le script livré et n'est pas créée par une relance Python.

## Organisation et limites

`noise_area/` contient qualité, indicateurs, moteur et statistiques ; `scripts/` contient acquisition, orchestration et audits. Chaque scénario dispose de trades, d'un compte quotidien et d'un résumé ; les 32 principaux ont aussi les décisions, regroupements et graphiques. B dispose de 1 000 contrôles de direction et 5 000 bootstrap par blocs de jours.

A finit le 30 avril 2024 ; B commence le 1er mai demandé ; C commence après la mise en ligne initiale, le 15 mai 2024 ; D commence après la révision consultée, le 23 septembre 2025. Le papier initial n'a pas été obtenu séparément : B n'est donc pas un hors-échantillon incontestable de la révision. Les comptes et périodes se recouvrent et ne s'additionnent pas.

Les cibles 1x/4x ne sont pas des plafonds d'exposition imposés en cours de position. Aucun appel de marge ni emprunt refusé n'est simulé. Les interruptions de marché de mars 2020 entraînent des exclusions selon la règle de grille complète, ce qui limite la reproduction de A. Le Pine a été compilé, mais son historique accessible ne permettait aucun backtest annuel ni contrôle de parité avec Python.
