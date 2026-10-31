# Bollinger : réintégration intraday — QQQ et SPY

**Piste écartée pour un nouveau bot.** Référence du 4 janvier 2016 au 16 octobre 2026 après frais : SPY -19.61 % / 1637 trades ; QQQ -18.32 % / 1608 trades. Les références A et B sont également négatives. A/B déjà réutilisées, comptes conditionnels à la couverture.

Barres5min20/2 réinitialisées chaque séance, première réintégration de bande basse entre11:15 et14:30 New York. LONG une minute après décision, stop sous les deux bougies de setup, TP à la moyenne figée. Sizing1 % avec plafond notionnel1× avant frais, aucune nuit.

Commission0.0035USD/action/côté, minimum0.35USD, plus friction adverse0.01USD/action/côté. Stress0.02/0.03/0.05. Aucun nouvel indicateur ou paramètre des bots existants modifié.

[Rapport complet et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84 comptes](results/2026-10-31-v1/comparison_all.csv) · [Règles figées](PROTOCOL_EXECUTION.md) · [Recherche Web](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).

## Reproduction locale

Python3.14 et versions de requirements-lock.txt. Archives SIP locales vérifiées nécessaires ; données brutes et clés non redistribuées sur GitHub. Aucun appel API ou ordre broker.

Depuis la racine du dépôt, dépendances installées. Sous Windows, conserver UTF-8 pendant la session pour lire les preuves JSON accentuées :

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest studies/bollinger-reentry/tests -q -p no:cacheprovider
python studies/bollinger-reentry/scripts/run_study.py --out CHEMIN_VIDE
~~~

Le runner refuse un dossier non vide. L’oracle accepte le même --out pour une exécution alternative ; présentation et contrôles supplémentaires visent le run archivé par défaut.

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/bollinger-reentry/scripts/verify_delivery.py --raw
~~~

Les empreintes vérifient les octets, sans certifier la complétude fournisseur ou les fills réels. Les simulations Noise Area et ORB restent indépendantes de cette étude.
