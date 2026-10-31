# Momentum matinal normalisé par la variation — SPY et QQQ

**Backtest terminé : piste écartée pour un nouveau bot.** Référence ALL2016–16octobre2026 après les mêmes frais : SPY+1.74% /273trades ; QQQ+11.55% /230trades. CAGR0.16% /1.02%. Comptes conditionnels à la couverture,252matinées de warmup, A/B déjà réutilisées.

Score matinal L/racine(somme des retours2min au carré), supérieur au q90 des seuls matins passés admissibles. Décision10:30NY, achat10:31open, sortie15:59open, notionnel causal1x, **sans stop**. Deux comptes100000USD indépendants, pas de nuit.

Commission0.0035USD/action/côté minimum0.35, friction adverse0.01USD/action/côté, stresses0.02/0.03/0.05. Emprunt LONG0. Aucun paramètre des bots modifié.

[Rapport complet et4figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84comptes](results/2026-10-31-v1/comparison_all.csv) · [Protocole figé](PROTOCOL_EXECUTION.md) · [Recherche Web lisible](RESEARCH_READABLE.md) · [Original gelé](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).

## Reproduction locale

Python3.14 et versions de requirements-lock.txt. Les archives SIP vérifiées du dépôt de travail local sont nécessaires ; données brutes et clés ne sont pas redistribuées sur GitHub. Aucun appel API ni ordre broker.

Depuis la racine du dépôt, dépendances installées. Sous Windows, activer UTF-8 est nécessaire pour lire les preuves JSON accentuées ; conserver ces variables pendant la session :

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest studies/morning-variation-momentum/tests -q -p no:cacheprovider
python studies/morning-variation-momentum/scripts/run_study.py --out CHEMIN_VIDE
~~~

Le runner refuse un dossier non vide. Pour auditer une exécution alternative, fournir le même --out à audit/independent.py ; présentation et contrôles additionnels visent par défaut le run archivé. Vérifier la livraison archivée :

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/morning-variation-momentum/scripts/verify_delivery.py --raw
~~~

Les hashes vérifient les octets, sans garantir la complétude fournisseur ou les fills réels. Les simulations Noise Area et ORB restent indépendantes de cette étude.
