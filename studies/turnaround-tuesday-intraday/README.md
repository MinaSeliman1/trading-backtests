# Turnaround Tuesday intraday — SPY et QQQ

**Statut : positif historiquement, insuffisamment étayé pour un nouveau bot.** Acheter le mardi après un lundi baissier, entrer09:31 et sortir le jour même avec stopADR14. Adaptation propre sans nuit, distincte des versions publiées overnight.

| ETF | Trades ALL | Net cumulé | CAGR | Profit factor | DD observé |
|---|---:|---:|---:|---:|---:|
| SPY | 196 | +11,91 % | 1,05 % | 1,287 | 7,66 % |
| QQQ | 187 | +13,01 % | 1,14 % | 1,268 | 10,76 % |

Du4janvier2016 au16octobre2026, deux comptes initiaux séparés100000USD, risque cible1%, plafond causal1x. Le rendement est conditionnel aux données résolues ; les deux périodes A/B ont déjà été explorées, donc aucun OOS aveugle. B ne compte que41/42trades ; SPY B devient négatif sans ses3meilleurs jours. Borne basse IC95 de moyenne quotidienne sous zéro pour les deux : le critère fixé avant résultats échoue, aucun nouveau bot.

- [Rapport complet et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md)
- [84scénarios](results/2026-10-31-v1/comparison_all.csv) et [critères](results/2026-10-31-v1/SCREENING.json)
- [Recherche et différences avec les règles externes](RESEARCH.md), [état des sources](WEB_SOURCE_STATUS.json)
- [Protocole avant PnL](PROTOCOL_EXECUTION.md), [gel SHA](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json)
- [Validation et limites](VALIDATION.md), [interprétation](INTERPRETATION.md)

Même commission0,0035USD/action/côté, minimum0,35 ; friction0,01USD/action/côté, stress0,02/0,03/0,05. LONG seulement donc emprunt nul. Les quantités sont décidées avant le fill ; les gaps peuvent dépasser la cible de risque. Frais et paramètres des bots Noise Area/ORB conservés, aucun moteur ajouté.

## Reproduire

Python3.14 et dépendances dans requirements-lock.txt. Les archives SIP complètes restent locales et leurs hashes sont contrôlés avant tout calcul ; pas de clé ou API requise pour cette étude. Le dépôt seul ne distribue pas l’historique sous licence.

Pour une nouvelle exécution, utiliser une copie ou un worktree séparé pour préserver les preuves scellées de cette livraison. Le runner refuse un dossier de résultats déjà rempli ; les scripts d’audit y génèrent une preuve propre à leur exécution. Ne pas écraser la livraison de référence.

```powershell
python -m pytest tests -q -p no:cacheprovider
python scripts/run_study.py --out results/nouvelle_execution
python audit/independent.py --out results/nouvelle_execution
python audit/additional.py --out results/nouvelle_execution
python scripts/report.py --out results/nouvelle_execution
```

`python scripts/verify_delivery.py --raw` vérifie la livraison de référence, les empreintes et la source locale. Le rapport Markdown final a reçu une correction éditoriale sur l’ablation top3 après génération : seule la prose finale change, calculs et générateur initial restent figés. Voir VALIDATION.md. Aucun résultat TradingView, fill broker ou avantage prospectif n’est revendiqué.
