# Saisonnalité au même créneau — QQQ et SPY

**Piste écartée dans cette formalisation : les références sont perdantes après les mêmes frais.** Recherche Web académique, dépôts d’auteurs et discussions, puis règles et code publiés avant le premier calcul de marché au commit `28a4a77f45102319ae8a38b45065b2d081c72933`.

| ETF | Trades ALL | Résultat net | Drawdown observé |
|---|---:|---:|---:|
| SPY | 1 857 | −23,20 % (−23 204,48 USD) | 23,90 % |
| QQQ | 1 887 | −20,02 % (−20 018,65 USD) | 20,56 % |

Période : 4 janvier 2016–16 octobre 2026 ; capital initial de 100 000 USD par compte. A et B sont aussi négatives pour chaque ETF. Les périodes ont déjà été utilisées dans d’autres recherches : B n’est pas une nouvelle validation aveugle. Performances conditionnelles à la couverture ; les journées inconnues ne constituent pas du cash observé.

La règle estime la direction du rendement d’un créneau sur les 40 séances précédentes, puis traite son premier signal pendant 30 minutes au maximum. L’article source étudie des portefeuilles transversaux d’actions : cette règle par ETF et ses stops sont notre adaptation. Commissions max(0,35 USD ; 0,0035 USD/action) par côté, friction adverse de 0,01 USD/action/côté et emprunt SHORT de 1 %/360, minimum un jour ; mêmes frais que les études précédentes.

[Rapport final et figures](results/2026-11-04-v1/RAPPORT_FINAL.md) · [96 comparaisons](results/2026-11-04-v1/comparison_all.csv) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md) · [Recherche et sources](RESEARCH.md) · [Protocole figé](PROTOCOL_EXECUTION.md).

## Reproduire

Python 3.14 et versions de `requirements-lock.txt`, dans un environnement distinct ou avec le PYTHONPATH local existant. Les caches SIP vérifiés et leurs archives sources sont nécessaires ; ils restent locaux sous licence. Le code ne télécharge rien et n’accède à aucune clé.

```powershell
python -m pytest studies/time-of-day-momentum/tests -q --junitxml=studies/time-of-day-momentum/runtime/preflight-tests.xml
python studies/time-of-day-momentum/scripts/run_study.py --out studies/time-of-day-momentum/results/nouvelle_execution
python studies/time-of-day-momentum/audit/independent.py --out studies/time-of-day-momentum/results/nouvelle_execution
python studies/time-of-day-momentum/scripts/additional_checks.py --out studies/time-of-day-momentum/results/nouvelle_execution
python studies/time-of-day-momentum/scripts/report.py --out studies/time-of-day-momentum/results/nouvelle_execution
python studies/time-of-day-momentum/scripts/verify_delivery.py --out studies/time-of-day-momentum/results/nouvelle_execution --seal
python studies/time-of-day-momentum/scripts/verify_delivery.py --out studies/time-of-day-momentum/results/nouvelle_execution
```

Le runner refuse un répertoire d’exécution déjà rempli. Les scripts de présentation et de contrôle des exports sont ajoutés après calcul, séparément du code financier figé. Le manifest de livraison couvre les deux catégories. Aucun nouveau bot installé ; les simulations Noise Area et ORB conservent leurs journaux et paramètres.
