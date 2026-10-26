# ORB confirmé + volume relatif d'ouverture

**Backtest terminé ; QQQ intéressant historiquement, SPY non convaincant.** Après les mêmes frais ETF, référence ALL2016–16/10/2026 : QQQ+44,75%/915trades, SPY−5,04%/899trades. QQQ A+11,54%, B+29,75%, mais A devient négative sans ses trois meilleurs jours et avec friction0,03/côté. B réutilisée, pas nouveau test aveugle.

- [Rapport complet,72scénarios et4figures](results/2026-10-24-v1/RAPPORT_FINAL.md)
- [Interprétation et décision par ETF](INTERPRETATION.md)
- [Recherche sur13sources : publications, forums et GitHub](RESEARCH.md)
- [Règles figées avant performances](PROTOCOL_EXECUTION.md)
- [Comparaisons complètes](results/2026-10-24-v1/comparison_all.csv)
- [Tests, revue, audit et empreintes](VALIDATION.md)

Extension de l'ORB existant : attendre une clôture minute au-delà du range5min dans la direction initiale, puis entrer à l'open suivant ; RVOL≥1 calculé sur les14fenêtres d'ouverture précédentes. Stop extrême opposé, TP10R/EOD, une entrée par séance avant11:30NY, risque cible1% et plafond causal1x.

Frais communs : commission0,0035USD/action/côté minimum0,35, friction0,01/côté, emprunt SHORT1%annuel/360 minimum1jour. Compte100000USD séparé par scénario. Le cadre actions Stocks in Play motive le filtre, sans reproduire son univers ou ses rendements.

QQQ sans filtre de volume gagne davantage sur ALL (+54,71%) avec plus de trades et de drawdown ; le filtre réduit l'activité et le DD observé, sans supériorité universelle démontrée. Aucune variante promue après résultats. Aucun bot nouveau ni modification des deux simulations existantes.

## Reproduction

Depuis ce dossier, Python3.14 et dépendances requirements-lock.txt :

```powershell
python -m pip install -r requirements-lock.txt
python -m pytest -q -p no:cacheprovider
python scripts/verify_delivery.py
python scripts/verify_delivery.py --raw
```

Pour un nouveau calcul, utiliser une copie de travail distincte afin de conserver le dossier scellé et sa preuve d'audit. Depuis le dossier de l'étude dans cette copie :

```powershell
$studyRun = Join-Path -Path (Get-Location).Path -ChildPath 'results/nouvelle-execution'
python scripts/run_study.py --out $studyRun
python audit/independent.py --out $studyRun
python scripts/report.py --out $studyRun
```

Le runner refuse l'écrasement d'une exécution. La vérification standard fonctionne sans historiques ; --raw/runner/audit nécessitent les archives et préparations SIP locales des études précédentes, non publiées pour leur volume. Aucune requête broker, aucune clé demandée par ces scripts. Le dépôt conserve les empreintes et snapshots des modules partagés.

Pour une nouvelle livraison complète dans cette copie, enregistrer TESTS.json et les preuves de revue, puis sceller avec `python scripts/verify_delivery.py --out $studyRun --seal`. Les chemins --out doivent être absolus. L'audit exporte un fichier lié aux SHA de l'exécution mais réécrit le chemin partagé audit/AUDIT_RESULTS.json : conserver séparément la preuve de chaque run. Un recalcul dans le dossier livré modifierait sa preuve scellée ; le clone séparé préserve la livraison originale. Le manifest final de cette étude ne fige pas le README global évolutif.

Les journées/trades inconnus sont omis du compte conditionnel ; les zéros comptables d'exclusion ne sont pas des rendements observés. Une fenêtre de volume antérieure manquante n'est jamais remplacée par une séance plus ancienne. Les métriques portent sur cette couverture, sans validation prospective ni garantie de fills.
