# Cassure ATR autour de l’ouverture — QQQ et SPY

**Statut : candidat historique, sans nouveau bot automatique.** Du 4 janvier 2016 au 16 octobre 2026, référence après mêmes frais : SPY +34.51 % / 1 222 trades ; QQQ +46.38 % / 1 277 trades. Annualisé 2.79 % /3.60 %, DD minute observé 6.75 % /8.92 %.

Niveau = ouverture +0.33×moyenne des 5 True Ranges antérieurs, version arithmétique et non Wilder. Premier close de 5 min au-dessus entre 09:35 et 15:30 New York, entrée une minute après décision. LONG seulement, stop fixe vers ouverture, sortie 15:59 au plus tard. Sizing 1 % et plafond causal 1× avant frais ; aucune nuit.

Commission0.0035USD/action/côté min0.35USD et friction adverse0.01USD/action/côté ; stresses0.02/0.03/0.05. Nos délais, taille et sélection LONG diffèrent matériellement des systèmes externes à stop-orders et côtés multiples.

[Rapport complet et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84comptes](results/2026-10-31-v1/comparison_all.csv) · [Protocole figé](PROTOCOL_EXECUTION.md) · [Sources](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).

## Reproduction locale

Python3.14 et versions de requirements-lock.txt, archives SIP locales vérifiées nécessaires. Données brutes et clés non redistribuées sur GitHub. Aucun appel API ou ordre broker.

Pour recalculer, utiliser une copie indépendante du checkout au même niveau que le dépôt original, avec les mêmes archives/préparations locales vérifiées. Cela conserve les chemins d’acquisition et protège les preuves originales. Depuis la racine de CETTE COPIE, dépendances installées, activer UTF-8 :

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest studies/atr-opening-breakout/tests -q -p no:cacheprovider
python studies/atr-opening-breakout/scripts/run_study.py --out studies/atr-opening-breakout/results/reproduction
~~~

Le runner refuse un dossier non vide. Dans cette copie seulement, fournir le même --out à audit/independent.py, avec un dossier SOUS studies/atr-opening-breakout. L’oracle écrit aussi audit/AUDIT_RESULTS.json à un emplacement fixe : le lancer sur une reproduction dans le checkout original remplacerait cette preuve archivée. Ne pas le faire. Les scripts de présentation/contrôles supplémentaires ciblent le run archivé par défaut et doivent être adaptés dans la copie avant emploi sur une reproduction.

La commande suivante vérifie en lecture seule la livraison originale ; elle peut s’exécuter depuis le checkout original sans recalculer ni remplacer ses preuves :

~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/atr-opening-breakout/scripts/verify_delivery.py --raw
~~~

Les empreintes vérifient les octets, sans garantir complétude fournisseur ou fills réels. A/B déjà réutilisées, portefeuille conditionnel à la couverture. Les deux bots Noise Area et ORB ne sont pas modifiés.

Période B : SPY +0.12 % (PF 1.003), friction doublée -0.76 %. Sans les trois meilleurs jours de B : SPY -5.22 %, QQQ -1.96 %. Les IC95 blocs20 B comprennent zéro sur les deux ETF ; la robustesse récente n’est pas démontrée.
