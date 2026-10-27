# Choc baissier puis rebond — SPY / QQQ

Nouvelle hypothèse intraday : achat après baisse30minutes anormale par rapport aux20séances passées à même heure, puis confirmation5minutes. Stop sous le creux, cible2R, sortie le jour même. Aucun RSI, VWAP, maintien overnight ou trading de paire. Deux comptes indépendants, mêmes historiques/frais ; aucun bot modifié.

ALL2016–16octobre2026 : SPY−22,02%/1290trades, QQQ−28,69%/1319trades après frais ; A et B également négatives. Critères fixés avant PnL non satisfaits : piste archivée dans cette formalisation, sans promouvoir les trois sensibilités positives isolées.

- [Recherche Web élargie et limites des sources](RESEARCH.md)
- [Règles et critères fixés avant PnL](PROTOCOL_EXECUTION.md)
- [Rapport complet](results/2026-10-26-v1/RAPPORT_FINAL.md)
- [72scénarios](results/2026-10-26-v1/comparison_all.csv)
- [Validation](VALIDATION.md)
- [Interprétation](INTERPRETATION.md)

Capital100000USD, risque cible1%, plafond causal1x ; commissions/friction/emprunt identiques aux études précédentes. B déjà explorée, comptes conditionnels aux données résolues : aucun nouveau OOS aveugle. Une anomalie NBBO/event-time publiée ne prouve pas la rentabilité de cette adaptation minute.

Six exports de premières décisions distinctes : référence, seuil1,5, seuil2,5, sans confirmation, sans z et miroir SHORT. Coûts, RR et qualité prefix réutilisent les mêmes décisions avant les contrôles de qualité/exécution ; pas de duplication artificielle de ces features.

Python3.14, dépendances dans requirements-lock.txt. Depuis ce dossier :

```powershell
python -m pytest tests -q --basetemp .test_tmp_local
python scripts/verify_delivery.py --raw
```

Reproduction avec archives locales exigées par shock/data.py, dans une copie de travail distincte et un nouveau dossier de résultats :

```powershell
python scripts/run_study.py --out results/nouvelle-execution
python audit/independent.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

L'audit écrit audit/AUDIT_RESULTS.json ; ne pas écraser le reçu de la livraison scellée. Le vérificateur exige aussi preuves de tests et manifest de cette livraison. Historiques complets, clés et runtime restent locaux. Code/tests/rapport/audit/dépendances sont archivés avant premier PnL ; toute correction financière ultérieure exige une nouvelle version conservant l'ancienne.
