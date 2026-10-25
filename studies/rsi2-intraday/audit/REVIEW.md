# Revue et audit indépendants — RSI(2)

Statut : **PASS**, aucun P1/P2 ouvert sur le moteur et les exports `2026-10-24-v1` examinés.

La revue statique a détecté avant la première boucle PnL un écart P2 entre le protocole et la validité du close journalier : un volume/high invalide à la dernière minute rendait le close historique inutilisable même lorsqu’il était connu. Le parent a corrigé ce point avant l’exécution de marché et ajouté une régression. La suite contrôlée a été exécutée indépendamment : **25 tests passent**, cache pytest désactivé. Les empreintes de tous les fichiers `code_sha256` du gel correspondent au code courant examiné.

L’audit [independent_audit.py](independent_audit.py) réimplémente depuis le protocole la validité des minutes, l’agrégation 5 minutes, les récurrences Wilder RSI(2)/ATR(14), les 200 closes antérieurs cash-additifs, la recherche du premier signal, le sizing causal, les priorités stop/RSI/EOD, les fills, les marques et MAE/MFE. Il ne fait appel à aucune fonction arithmétique du moteur ou des modules d’analyse. Le loader historique sert uniquement à lire et revalider par SHA/calendrier les archives locales.

Les [preuves JSON](AUDIT_RESULTS.json) couvrent les **72 scénarios**, **78 646 lignes de transactions** et **130 224 lignes journalières** : comptes, quantités et frais refaits avec `Decimal`, chemins refaits depuis les prix minute, agrégats principaux, drawdowns minute/événements et quotidiens, exposition et exclusions. Il s’agit de lignes recouvrantes entre variantes et ALL/A/B, pas d’événements de marché indépendants.

**3 691 214 contrôles passent**, sans divergence ; écart absolu numérique maximal : **0,000000015512341633439064 USD** pour le rapprochement final des comptes flottants avec le calcul Decimal. Les tolérances financières sont de 0,000001 USD. Les signaux, quantités et motifs de sortie se rapprochent.

Les sources originales sont également échantillonnées : **480 minutes RTH × 5 champs OHLCV**, provenant de la première et dernière page de chacune des **6 acquisitions**, soit **12 pages compressées hashées**. Aucun écart avec les arrays préparés n’a été trouvé sur ces échantillons.

Le rapport final et ses principaux tableaux ont été relus : la conclusion négative sur les deux références correspond aux exports. Les limites de couverture, les comptes conditionnels, les closes historiques absents, le filtre `complete_days` connu après la séance, le recouvrement A/B/ALL et la réutilisation de B sont décrits. La borne supérieure d’occupation RTH cumulée ne doit pas être présentée comme un pic d’exposition quotidien.

Limites de cet audit : les pages sources sont échantillonnées, la complétude du fournisseur et des corporate actions n’est pas prouvée, les données restent à la minute et ne reconstruisent pas le bid/ask. La validité arithmétique ne crée ni nouvelle preuve OOS ni rentabilité attendue. Les résultats conditionnels n’attestent pas une exécution continue pendant les données absentes.

Reproduction locale depuis la racine du dépôt, avec le runtime et les dépendances de l’étude :

```powershell
$env:PYTHONPATH=(Resolve-Path '../.python_packages').Path
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Python314\python.exe' studies/rsi2-intraday/audit/independent_audit.py --results studies/rsi2-intraday/results/2026-10-24-v1
& 'C:\Python314\python.exe' -m pytest -q -p no:cacheprovider studies/rsi2-intraday/tests
```

Le script refuse de commencer le contrôle financier tant que `RUN_COMPLETE.json` est absent. Aucun ordre, secret, API réseau, bot, ancienne étude ou état Git n’a été modifié par le reviewer. Seuls les fichiers de ce répertoire `audit/` ont été créés ou modifiés.
