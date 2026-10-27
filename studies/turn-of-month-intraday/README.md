# Turn of Month intraday — SPY / QQQ

LONG09:35 les dernières/premières séances du mois, stop1%, aucun TP et sortie le jour même. Hypothèse calendaire, sans signal technique ni maintien overnight. Aucun nouveau bot.

ALL2016–16octobre2026 après les mêmes frais : SPY+31,33%/516trades, QQQ+31,64%/518trades (CAGR2,56%/2,58%). Les six références A/B/ALL sont positives, mais les deux IC95 du contraste mensuel TOM−autres comprennent zéro : le critère prédéfini ne passe pas. QQQ A devient négatif à friction doublée. Résultat historique conditionnel, pas validation prospective.

- [Recherche forums/GitHub et limites des sources](RESEARCH.md)
- [Protocole fixé avant PnL](PROTOCOL_EXECUTION.md)
- [Rapport complet](results/2026-10-26-v1/RAPPORT_FINAL.md)
- [72comparaisons](results/2026-10-26-v1/comparison_all.csv)
- [Validation](VALIDATION.md)
- [Interprétation](INTERPRETATION.md)

SIP historique et frais inchangés, capital100000USD, sizing causal1x/risque cible1%. Calendrier sur mois entiers, contrôles autres/tous jours et contraste mensuel. Compte conditionnel aux données résolues ; B déjà explorée, aucun nouveau OOS aveugle. Les deux simulations QQQ restent inchangées.

Python3.14, dépendances fixées dans requirements-lock.txt. Depuis ce dossier :

```powershell
python -m pytest tests -q --basetemp .test_tmp_local
python scripts/verify_delivery.py --raw
```

Reproduction avec les archives locales requises par tom/data.py, nouveau dossier obligatoire :

```powershell
python scripts/run_study.py --out results/nouvelle-execution
python audit/independent.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

Le reçu d'audit est écrit dans audit/AUDIT_RESULTS.json : reproduire dans une copie de travail distincte pour conserver la livraison scellée. Le vérificateur exige les preuves de tests et le manifest de la livraison. Historiques complets, clés et runtime ne sont pas publiés. Les rendements de la littérature daily/overnight ne sont pas ceux de cette adaptation intraday.
