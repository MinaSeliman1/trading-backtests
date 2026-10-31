# Valeur relative intraday QQQ/SPY

**Statut : piste écartée dans cette formalisation.** Acheter l'ETF relativement faible et vendre l'autre après une divergence inhabituelle ; retour à la moyenne attendu le même jour. Il s'agit d'UN portefeuille avec DEUX jambes, pas de deux comptes ETF indépendants.

| Période | Paires fermées | Résultat net | CAGR | Profit factor | DD observé |
|---|---:|---:|---:|---:|---:|
| ALL | 539 | −14,24 % | −1,41 % | 0,525 | 14,34 % |
| A | 411 | −12,24 % | −1,56 % | 0,491 | 12,34 % |
| B | 128 | −2,26 % | −0,93 % | 0,663 | 3,23 % |

ALL : 4 janvier 2016–16 octobre 2026 ; A jusqu'au 30 avril 2024 ; B à partir du 1 mai 2024. Comptes initiaux distincts de 100000 USD selon la période. Les deux historiques ont déjà servi à de nombreuses recherches : aucun nouvel hors-échantillon aveugle. Performance conditionnelle aux données résolues, pas compte continu observé sur les exclusions.

Les 42 comptes sont négatifs. Les mouvements bruts de prix de la référence perdent déjà 8786,18 USD avec les quantités de sa trajectoire ; frictions 3491,52, commissions 1271,40 et emprunt 688,94 portent la perte à 14238,04 USD. Cette attribution ne remplace pas un compte sans frais recalculé. Aucun nouveau bot n'est installé ; Noise Area et ORB restent inchangés en simulation.

- [Rapport complet et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md)
- [42 scénarios](results/2026-10-31-v1/comparison_all.csv) et [critères avant résultats](results/2026-10-31-v1/SCREENING.json)
- [Recherche et différences avec les sources](RESEARCH.md), [état des accès et empreintes GitHub](WEB_SOURCE_STATUS.json)
- [Protocole](PROTOCOL_EXECUTION.md), [gel financier](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json)
- [Interprétation](INTERPRETATION.md), [validation](VALIDATION.md)

Règles : retours logarithmiques intraday normalisés à l'open, moyenne/écart-type du même créneau sur 20 séances passées, entrée entre 2 et 3 écarts-types, objectif moyenne/stop 3 fixés à la décision. Opens suivant des closes observés ; stop close-based, EOD et une paire/jour. Dollar-neutralité approximative, pas neutralité bêta ni cointégration garantie. Gross cap causal 1x, proxy de risque cible 1 % sans garantie de perte maximale.

Mêmes frais par jambe : 0,0035 USD/action/côté, minimum 0,35 pour chacun des quatre ordres ; friction 0,01 USD/action/côté ; emprunt SHORT 1 % annuel/360, minimum un jour. Les coûts et les profits de short ne sont pas comptés deux fois. Les fills atomiques de deux jambes et la disponibilité de l'emprunt demeurent des hypothèses.

## Reproduire

Python 3.14, dépendances dans requirements-lock.txt. Archives SIP complètes conservées localement et vérifiées par SHA ; pas de clé ni API requise. Le dépôt ne redistribue pas ces archives sous licence. Utiliser une copie ou un worktree séparé pour une autre exécution, afin de préserver les preuves scellées. Le runner refuse un dossier de résultats déjà rempli ; les preuves d'audit sont propres à leur exécution.

```powershell
python -m pytest tests -q -p no:cacheprovider
python scripts/run_study.py --out results/nouvelle_execution
python audit/independent.py --out results/nouvelle_execution
python audit/statistics_check.py --out results/nouvelle_execution
python scripts/report.py --out results/nouvelle_execution
```

`python scripts/verify_delivery.py --raw` contrôle la livraison de référence et les sources brutes locales. Les sources financières/tests/oracle ont été figées avant PnL ; le script de présentation et le contrôle statistique supplémentaire sont ajoutés après les exports, puis scellés au manifest final. Aucun résultat TradingView, fill broker ou avantage prospectif revendiqué.
