# Rejet des extrêmes de veille — SPY / QQQ

Hypothèse intraday distincte des cassures ORB : dépasser un extrême RTH de la veille puis clôturer de retour dans son range. Étude Python, aucun bot ajouté.

- [Recherche et sources](RESEARCH.md)
- [Protocole fixé avant résultats](PROTOCOL_EXECUTION.md)
- [Rapport complet](results/2026-10-26-v1/RAPPORT_FINAL.md)
- [72 scénarios A/B/ALL](results/2026-10-26-v1/comparison_all.csv)
- [Validation](VALIDATION.md)
- [Décision et lecture des figures](INTERPRETATION.md)

Les mêmes archives locales SIP vérifiées et frais sont réutilisés. Capital100000USD, taille au signal, plafond1x et risque cible1%, stop prioritaire dans les bougies ambiguës. Compte conditionnel aux données résolues ; B déjà explorée, aucun nouvel OOS aveugle. Aucun accès aux clés, coffre, ordres ou journaux des deux simulations actives.

Depuis ce dossier, avec les dépendances Python déjà installées :

```powershell
python -m pytest tests -q --basetemp .test_tmp_local
python scripts/verify_delivery.py --raw
```

Reproduction financière avec les données locales requises par `pdr/data.py`, vers un nouveau dossier uniquement :

```powershell
python scripts/run_study.py --out results/nouvelle-execution
python audit/independent.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

L'audit écrit son reçu dans `audit/AUDIT_RESULTS.json` : utiliser une copie de travail distincte pour reproduire sans changer la livraison scellée. `verify_delivery.py` exige les preuves de tests et le manifest de cette livraison ; il ne prétend pas valider un dossier arbitraire sans ces éléments. Les historiques bruts ne sont pas publiés ; pas de promesse de résultat garanti ou de backtest indépendant sur un autre flux.
