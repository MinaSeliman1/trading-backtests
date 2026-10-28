# IBS de la veille, rebond intraday — SPY et QQQ

**Statut : adaptation intraday écartée pour un nouveau bot.** Hypothèse issue d'une recherche élargie sur le Web : acheter après une séance clôturée dans les 20 % inférieurs de son amplitude. Cette adaptation entre à 9 h 31 et sort le jour même ; elle ne reproduit pas les stratégies IBS swing ou close-to-close publiées.

| ETF | Trades ALL | Net cumulé | CAGR | Profit factor | DD observé |
|---|---:|---:|---:|---:|---:|
| SPY | 463 | -5,70 % | -0,54 % | 0.951 | 16,31 % |
| QQQ | 463 | 13,15 % | 1,15 % | 1.094 | 10,02 % |

Période complète du 4 janvier 2016 au 16 octobre 2026. Deux comptes initiaux de 100000 USD distincts, risque cible 1 %, plafond causal 1x. DD observé aux frais d'entrée, closes minute détenus et sorties, sans reconstruction de tous les ticks. Comptes conditionnels aux données résolues. B du 1 mai 2024 au 16 octobre 2026 a déjà été explorée : aucun nouveau hors-échantillon aveugle.

- [Rapport complet et quatre figures](results/2026-10-28-v1/RAPPORT_FINAL.md)
- [72 scénarios réellement calculés](results/2026-10-28-v1/comparison_all.csv)
- [Interprétation et décision](INTERPRETATION.md)
- [Recherche, alternatives et sources primaires/forums/GitHub](RESEARCH.md)
- [Règles avant PnL](PROTOCOL_EXECUTION.md) et [gel SHA du code](results/2026-10-28-v1/PRE_EXECUTION_PROTOCOL.json)
- [Tests et validation](VALIDATION.md)

IBS calculé uniquement sur la veille ; ADR14 sur les 14 séances précédentes consécutives, sans sauter un trou. Stop fixe au prix de sizing moins ADR14 ; ni TP ni nuit détenue. Commission 0,0035 USD/action/côté minimum 0,35, friction 0,01 USD/action/côté ; variantes SHORT avec emprunt 1 % annuel/360 minimum un jour. Stress de coûts et sensibilités fixés avant calcul. Aucun nouveau bot n'est installé.

## Reproduire

Python 3.14 et versions dans requirements-lock.txt. Archives SIP et préparations locales vérifiées par SHA, exclues de Git : le dépôt seul ne fournit pas un historique sous licence. Aucun accès API nécessaire pour ce calcul. Choisir un nouveau dossier de résultats au sein de cette étude ; ne jamais écraser une exécution.

```powershell
python -m pytest tests -q -p no:cacheprovider --basetemp .test_tmp_local
python scripts/run_study.py --out results/nouvelle_execution
python audit/independent.py --out results/nouvelle_execution
python scripts/report.py --out results/nouvelle_execution
```

`python scripts/verify_delivery.py --raw` vérifie la livraison de référence, les empreintes et la source locale. Pour sceller une nouvelle livraison, conserver également la preuve du passage des tests et les documents de validation propres à cette exécution. Les résultats ne représentent pas un portefeuille observé sans interruption ni une preuve de fills broker.
