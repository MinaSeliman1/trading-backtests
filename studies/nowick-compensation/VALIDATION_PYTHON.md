# Validation Python — Nowick / Compensation Play

Exécution de référence : `results/2026-10-24-python-v1/`. Publication autorisée explicitement par Mina après abandon de l’exécution TradingView. Le périmètre est un backtest Python sur quotes FXCM indicatives, avec les conventions du [protocole](PYTHON_PROTOCOL.md). La compilation Pine et la parité TradingView restent non vérifiées.

## Séquence et version

1. Protocole, période commune 2015–2024, deux moitiés et configurations figés avant consultation de performances Nowick.
2. Acquisition publique FXCM 1 minute : 1 579 archives reçues, 41 réponses 404, aucune erreur de téléchargement restante. Données et empreintes préparées avant calcul du PnL.
3. Tests contrôlés et revue du moteur. Le décodage pandas 3 a été corrigé pour convertir explicitement en nanosecondes avant calcul des secondes UTC. Le drawdown a été corrigé pour compter la commission dès l’entrée. Ces corrections précèdent la première exécution de marché ; aucun résultat antérieur n’a été sélectionné ou effacé.
4. Une exécution financière v1, 126 scénarios recouvrants, sans changement du moteur pendant les calculs. Snapshot initial du moteur, métriques, protocole, runner et tests. Le helper de statistiques `reference.py`, omis de la liste initiale de snapshot, est ajouté avec un fichier de provenance distinct : mêmes octets que le commit Git antérieur `599b1359c3ac1bb70cc13add581f0f29f89a7117`.
5. Revue indépendante, résultats rapprochés aux transactions, graphiques issus des exports. Deux régressions de préservation des données ajoutées après le lancement : elles concernent la reproduction d’acquisition, pas les règles ni les comptes de marché. Le téléchargeur vérifie maintenant les archives avant de préparer, puis vérifie un NPZ temporaire avant tout remplacement d’une préparation existante. Un refus préserve les preuves originales.

## Tests contrôlés

**70 tests passent** : 27 tests de référence antérieurs, 6 de décodage/qualité, 32 du moteur minute, 3 de métriques et 2 de préservation d’acquisition. La preuve fraîche et sa sortie sont dans `results/2026-10-24-python-v1/TESTS.json`.

Les fixtures vérifient notamment la causalité des pivots, l’alignement horaire de l’EMA, les horaires/DST, les neuf bougies de validité, le franchissement de limite, l’open avant les extrêmes, les deux politiques de front-run, le stop avant TP dans une minute ambiguë, l’absence de TP favorable non prouvé après fill intraminute, les commissions, les quantités et les trous de source. Elles ne contiennent aucune performance de marché.

Les deux tests de reproduction injectent une archive différente ou une préparation différente : ils reproduisaient un remplacement incorrect des données originales avant correction et vérifient désormais leur conservation. Ils utilisent un espace de test isolé, sans appel réseau et sans toucher aux historiques actifs.

## Audit indépendant

[Script reproductible](audit/independent_audit.py) et [preuve JSON](audit/independent_audit_v1.json). Le script n’importe ni `fx_engine`, ni `fx_metrics`, ni `fx_data`, ni `reference`. Il utilise Decimal/math pour les comptes et reconstruit les signaux à partir des tableaux source.

- Tous les exports : taille à risque 1 %, absence de positions superposées, PnL brut, frais, net, risque monétaire, R, soldes, PF, win rate, Wilson, série de pertes, drawdown des R fermés et drawdown des marques minute/événements. Rapprochement des annulations et du nombre de trades résolus.
- Référence ALL et `fill_first` ALL, pour chaque paire : reconstruction des bougies/pivots confirmés, direction, niveaux figés et toutes les limites acceptées, annulations, première minute de fill possible, sessions New York, validité et premier exit selon les conventions déclarées.
- Reconstruction indépendante de l’EMA 50/200 à partir des heures complètes et comparaison des features exportées, après préchauffage.
- Chronologie et validité OHLC des préparations ; échantillons de timestamps/OHLC directement dans les gzip originaux, avec empreintes. Ces échantillons prouvent la transformation des observations inspectées, pas l’exactitude des quotes FXCM.

La preuve JSON finale couvre 126 scénarios, 243 466 contrôles, zéro erreur. Elle donne les écarts numériques maximaux et les échantillons. La vérification indépendante EMA porte sur 749 481 features des trois paires, dont 692 814 bougies après 200 heures complètes de préchauffage ; les fixtures courtes ne suffisent pas à prouver ce préchauffage. Le vérificateur de publication exige l’audit final complet sans erreur ; il refuse une preuve partielle obtenue pendant que le runner calculait encore.

L’audit causal relit les ordres acceptés de ces six portefeuilles ; il n’énumère pas indépendamment tous les signaux rejetés possibles. Les autres variantes disposent des contrôles de comptes et des tests de leurs règles, pas d’une seconde implémentation intégrale de leur sélection. Une reconstruction de l’ordre des ticks à partir de OHLC reste impossible.

## Seuil et qualité

| Paire | Fermés référence ALL | Sans trou pendant la position | Pénalités de couverture |
| --- | --- | --- | --- |
| GBPUSD | 127 | 122 | 5 |
| USDJPY | 191 | 174 | 17 |
| AUDUSD | 222 | 193 | 29 |

Le seuil demandé est atteint séparément sur les trois paires, sans addition de périodes ou variantes. Aucune position finale n’est forcée fermée pour ce seuil. Les moitiés et filtres peuvent avoir moins de 100 observations ; leurs tailles sont publiées.

Le principal comprend une pénalité de couverture au pire du stop ou de l’open de reprise pour chaque position traversant une minute absente ; le montant n’est pas un fill observé. Les sorties `observed_gap`, le diagnostic des seuls trades résolus et le front-run `fill_first` sont publiés séparément. Aucune annulation ni pénalité n’est présentée comme une borne universelle du PnL.

Le fournisseur laisse des trous importants, notamment après le 13 décembre 2024. Les jours fériés sont inclus dans l’enveloppe nominale des jours ouvrés de couverture. Des quotes Ask/Bid sont croisées ; le modèle utilise Bid et 1 pip synthétique total, pas un spread réel reconstitué. Swaps, latence, file d’attente, révisions du fournisseur et divergence avec le courtier ne sont pas validés. Les taux de réussite et leur Wilson ne corrigent pas ces défauts ni la dépendance des trades.

## Intégrité et reproduction

```powershell
python -m unittest discover -s tests -v
python scripts/verify_python_publication.py
python scripts/verify_python_publication.py --raw
```

La deuxième commande fonctionne sur les fichiers publiés, sans historique complet. La troisième ajoute les SHA des 1 579 gzip et des trois préparations locales. `FILE_MANIFEST.json` couvre code, tests, audit, rapport, graphiques, sources et résultats dérivés. Les empreintes initiales du code financier sont vérifiées séparément et doivent toujours correspondre au snapshot.

La commande `python audit/independent_audit.py` exige les données locales et remplace seulement sa preuve d’audit. Ne pas relancer ce producteur sur une copie archivée destinée à garder son empreinte ; utiliser une copie de travail pour une nouvelle preuve. `run_python.py --run-id <nouvel-identifiant>` refuse un dossier existant. Le README décrit le téléchargement et les dépendances. Les versions Pine et l’ancienne tentative TradingView restent archivées avec leur statut initial.

**Conclusion dans ce périmètre : partage avec réserves de couverture et d’exécution.** Les références et les deux moitiés de chaque paire sont négatives après frais ; aucun avantage ni passage en réel n’est établi. Les audits vérifient les calculs du modèle déclaré, pas la disponibilité d’un prix chez un courtier.
