# Repli estimé sur les séances rouges — QQQ et SPY

**Statut : Piste écartée pour un nouveau bot : les critères fixés avant les résultats ne sont pas tous satisfaits.** Références 2016–16/10/2026, après les mêmes frais : SPY -19.21 % / 1,520 trades ; QQQ -38.15 % / 1,513 trades.

Niveau = ouverture − moyenne des max(Open−Close,0) des 21 séances précédentes, jours verts à zéro. Première clôture de 5 min sous le niveau de 09:35 à 15:30 New York ; entrée au marché une minute après décision. LONG, stop niveau−ADR 14, sortie open 15:59, pas de nuit. Taille entière, risque 1 % et cible 1× calculés avant le fill ; gap/frais peuvent dépasser ces cibles.

Commission 0.0035 USD/action/côté min 0.35 USD ; friction adverse 0.01 USD/action/côté et stresses 0.02/0.03/0.05. Adaptation du signal public, pas réplication de ses ordres limites supposés remplis.

[Rapport complet et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84 comptes](results/2026-10-31-v1/comparison_all.csv) · [Protocole](PROTOCOL_EXECUTION.md) · [Recherche](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).

## Reproduction locale

Python3.14 et versions requirements-lock.txt. Archives SIP et caches locaux vérifiés nécessaires, non redistribués ; aucun appel API ni clé requis par ces scripts. Pour recalculer, utiliser une copie séparée du checkout au même niveau, disposant des mêmes archives/préparations ignorées par Git. Cela protège les preuves originales. Depuis la racine de cette copie, avec dépendances installées :

~~~powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
python -m pytest studies/adaptive-red-day-dip/tests -q -p no:cacheprovider
python studies/adaptive-red-day-dip/scripts/run_study.py --out studies/adaptive-red-day-dip/results/reproduction
~~~

Le runner refuse un dossier non vide. Dans cette copie seulement, fournir le même --out à audit/independent.py ; ce chemin doit rester SOUS studies/adaptive-red-day-dip. L’oracle écrit aussi audit/AUDIT_RESULTS.json à un emplacement fixe : ne pas le lancer sur une reproduction dans le checkout original, car il remplacerait la preuve archivée. Les scripts de statistiques et de présentation ciblent le run original par défaut ; adapter leurs chemins uniquement dans la copie pour une reproduction.

Vérification en lecture seule de la livraison originale :

~~~powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
python studies/adaptive-red-day-dip/scripts/verify_delivery.py --raw
~~~

Empreintes = intégrité des octets, pas garantie de complétude ni de fills réels. A/B réutilisées, essais multiples et couverture conditionnelle. Aucun nouveau bot ; les deux simulations QQQ sont préservées.
