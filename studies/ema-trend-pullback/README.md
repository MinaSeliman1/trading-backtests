# EMA9/20 — repli puis reprise, SPY / QQQ

Étude Python intraday issue d'une recherche sur forums et GitHub. Aucun nouveau bot.

- [Recherche et limites des sources publiques](RESEARCH.md)
- [Protocole fixé avant PnL](PROTOCOL_EXECUTION.md)
- [Rapport complet](results/2026-10-26-v1/RAPPORT_FINAL.md)
- [72 scénarios A/B/ALL](results/2026-10-26-v1/comparison_all.csv)
- [Validation](VALIDATION.md)
- [Interprétation](INTERPRETATION.md)

EMA connues avant bougie, entrée open suivant, quantité au signal, risque cible1%, plafond1x, mêmes frais que les études précédentes. Cash ex-date courant, resets et chauffe60bougies après trous. B déjà explorée : aucun nouvel échantillon aveugle. Comptes conditionnels à la résolution des données, pas fills broker observés. Les deux simulations actives ne sont pas modifiées.

Python3.14 et versions de `requirements-lock.txt`. Depuis ce dossier :

```powershell
python -m pytest tests -q --basetemp .test_tmp_local
python scripts/verify_delivery.py --raw
```

Avec les archives locales requises par `ema_pullback/data.py`, reproduction vers un nouveau dossier seulement :

```powershell
python scripts/run_study.py --out results/nouvelle-execution
python audit/independent.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

L'audit reconstruit séparément les EMA par segments EWM sur closes+cash cumulatif passé, puis les décisions/fills/comptes. Il s'arrête explicitement si un cash extrême rend les états non positifs, situation vérifiée absente de cette source ETF. Son reçu est écrit dans `audit/AUDIT_RESULTS.json` : reproduire dans une autre copie de travail pour conserver les octets scellés. Le vérificateur exige aussi les preuves de tests et le manifest de la livraison. Historiques bruts et clés restent locaux.
