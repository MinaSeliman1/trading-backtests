# Reproduire et contrôler

Le rapport est un test proxy indépendant en Python, pas un résultat TradingView. Aucune API, clé, connexion broker ni action sur les bots n’est nécessaire.

## Environnement

Python 3.14 ; versions exactes dans [requirements-lock.txt](requirements-lock.txt) et [audit/environment.json](audit/environment.json). Installer dans un environnement dédié :

```powershell
python -m pip install -r requirements-lock.txt
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests -q -p no:cacheprovider
```

Commandes lancées depuis le dossier de cette étude. L’environnement local de l’expérience emploie C:/Python314/python.exe avec PYTHONPATH pointant vers le dossier .python_packages de Trading. La version de Python et de NumPy/Pandas du gel est aussi inscrite dans FREEZE.json.

## Vérifications accessibles depuis GitHub seul

```powershell
python audit/reconcile.py
python scripts/verify_delivery.py
```

La réconciliation utilise les grilles de plans/remplissages candidates et les 1 000 tirages par date publiés. Elle reconstruit les 36 000 portefeuilles/périodes et les bootstraps/Holm sans importer le moteur de trading ni les statistiques de production. Elle ne remplace pas la vérification de la fidélité des données de marché.

`verify_delivery.py` vérifie les empreintes de tous les fichiers livrés, les sources publiques figées, les reçus de calcul et les 6 décisions. `--raw` ajoute la vérification des archives privées à leur emplacement d’origine. Les fichiers de reçus sont modifiés lorsqu’on relance une vérification ; pour un contrôle strict du paquet publié, lancer d’abord verify_delivery.py ou travailler sur une copie. Aucune réinitialisation d’un bot n’intervient.

## Recalcul des signaux depuis les archives privées

Nécessite les fichiers originaux, non redistribués :

- ES_1m_raw.csv.gz et son .provenance.json ;
- NQ_1m_raw.csv.gz et son .provenance.json ;
- README.md et catalog.json du répertoire BARS.

Les SHA attendus sont dans [FREEZE.json](FREEZE.json), avec les chemins de l’expérience d’origine. Un téléchargement différent n’est pas silencieusement accepté. Les sources amont historiques et le raccord exact ne sont pas authentifiés ; la possession de ces archives ne certifie pas leurs contrats.

À l’emplacement d’origine, `python audit/verify.py` contrôle l’ensemble des plans candidats, les signaux principaux et H3 par un oracle sans import du moteur/context/statistiques. Le chargement utilise le module de données commun : les tests de fuseau et les contrôles OHLC sont complémentaires, pas un second fournisseur de prix.

Pour déplacer les archives, conserver les empreintes gelées et utiliser le petit adaptateur, sans éditer les règles :

```powershell
python scripts/replay_portable.py --raw-root 'C:/mes-archives/BARS' --output 'C:/temp/smt-replay'
```

Ce programme refuse de remplacer results/ ou une sortie non vide, compare les archives déplacées aux mêmes SHA et appelle le moteur figé. Les CSV numériques sont déterministes avec les versions fixées ; le timestamp du reçu diffère. Il faut comparer leurs SHA à results/run_receipt.json. Le recalcul inclut frais principal/stress, six variantes, 1 000 témoins, diagnostics et H3. Les dates de raccord exactes restent inconnues : ne pas substituer un autre continu avec d’autres raccords.

Le programme `scripts/run.py --freeze` a été exécuté **une fois avant résultats**, puis `--run`. Ne pas regeler après lecture des performances et présenter cela comme un test préalable. Les programmes de rapport/vérification ajoutés après calcul sont couverts par le manifeste final ; ils n’altèrent pas le code figé.

## Lire les sorties

- quality.csv : dates éligibles et toutes exclusions ; levels.csv : niveaux par indice.
- candidate_grid_1/2.csv : tous les plans possibles aux heures déclarées, principal/stress. Ce ne sont pas autant de trades de la stratégie.
- daily_comparisons.csv : six séries principales et témoins sur les mêmes dates, y compris sans ordre.
- ledger_1/2_H1/H2_A/B/C.csv : trades SMT et biais seul, avec ecart_ouverture et R réel ; un trade/jour au maximum par politique.
- control_draws.csv + candidate grids : reconstruction de chaque entrée aléatoire ; random_portfolios.csv : agrégats des 1 000 portefeuilles.
- contrasts.csv, gates.json : intervalles et critères préfixés ; diagnostics.json : annonces, exclusions, placebos, contrefactuel C non tradable.
- discovery_level_diagnostic.csv : niveaux séparés seulement sur découverte, objectifs H1 communs conservés ; pas de sélection de gagnant.
- h3_daily/summary.csv : association de volatilité sans trade.

Les R indéfinis à risque zéro seraient comptés en USD et séparément : netR est la somme des R définis, meanR leur moyenne, et leur nombre est explicite. Aucun trade à risque nul dans les stratégies principales de cette exécution ; cette hypothèse est vérifiée par les critères.
