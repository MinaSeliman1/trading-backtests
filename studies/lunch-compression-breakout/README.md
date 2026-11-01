# Compression de midi, cassure après 13 h — QQQ et SPY

**Statut : Piste écartée pour un nouveau bot : les critères fixés avant les résultats ne sont pas tous satisfaits.** Références 2016–16/10/2026 après mêmes frais : SPY +1.59 % / 78 trades ; QQQ +0.47 % / 97 trades.

Range midi 11:30–12:30 strictement inférieur à 30 % du range matin 09:30–11:30. Première nouvelle traversée au-dessus du highMidi après 13:00 jusqu’à 14:30, clôture 5 min et volume/minute supérieur à la moyenne du midi. Une candidate consommée même si son volume échoue. Achat au marché une minute après décision ; stop milieu du midi, sortie 15:59 au plus tard. LONG, risque 1 % et objectif 1× avant fill/frais ; ces cibles peuvent être dépassées par un gap.

Commission 0.0035 USD/action/côté min 0.35 USD ; friction adverse 0.01 USD/action/côté, stresses 0.02/0.03/0.05. Une formalisation mécanique inspirée d’un article, pas une réplication certifiée. A/B déjà réutilisées, portefeuille conditionnel à la couverture, aucun nouvel OOS aveugle.

[Rapport et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84 comptes](results/2026-10-31-v1/comparison_all.csv) · [Protocole](PROTOCOL_EXECUTION.md) · [Recherche](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).

## Reproduction locale

Python3.14 et versions requirements-lock.txt. Archives SIP et préparations locales vérifiées nécessaires, ignorées par Git et non redistribuées. Aucun API/clé/ordre. Recalcul dans une copie séparée du checkout au même niveau, avec mêmes archives/préparations disponibles ; cela protège les preuves originales. Depuis la racine de cette copie, dépendances installées :

~~~powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
python -m pytest studies/lunch-compression-breakout/tests -q -p no:cacheprovider
python studies/lunch-compression-breakout/scripts/run_study.py --out studies/lunch-compression-breakout/results/reproduction
~~~

Le runner refuse un dossier non vide. Dans la copie seulement, donner le même --out à audit/independent.py ; il doit rester SOUS studies/lunch-compression-breakout. L’oracle écrit audit/AUDIT_RESULTS.json à une position fixe : ne pas lancer une reproduction dans le checkout original, car cette preuve serait remplacée. Les scripts de statistiques et de présentation ciblent le run archivé ; adapter leurs chemins dans la copie avant emploi sur une reproduction.

Vérification en lecture seule de la livraison originale :

~~~powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
python studies/lunch-compression-breakout/scripts/verify_delivery.py --raw
~~~

Empreintes = intégrité des octets, pas certification de complétude ou de fills réels. Aucun nouveau bot ; les deux simulations existantes sont préservées.
