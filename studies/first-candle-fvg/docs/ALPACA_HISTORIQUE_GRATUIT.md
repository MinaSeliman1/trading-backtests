# Données gratuites Alpaca et lancement de la validation longue

La [FAQ officielle Alpaca](https://docs.alpaca.markets/us/docs/market-data-faq) indique que le SIP historique est accessible sans abonnement lorsque la fin des requêtes est antérieure aux quinze dernières minutes. Le flux SIP consolide les places américaines, alors qu'IEX n'en représente qu'une. L'acquisition réelle du 19 octobre 2026 a confirmé cet accès avec les clés du compte existant : 773 977 bougies SPY et 807 421 QQQ, du 3 janvier 2023 au 18 septembre 2026 avant filtrage régulier. Les fichiers déjà acquis permettent de refaire l'analyse hors ligne ; aucune nouvelle clé n'est requise pour les réutiliser.

## Saisie locale

La commande suivante ouvre une saisie masquée dans une console Python :

```powershell
python scripts/download_alpaca.py --prompt-credentials
```

Les deux valeurs demandées sont **API Key ID** et **API Secret**, et non les identifiants de connexion au site. Les caractères ne s'affichent pas. Ne placer aucune clé dans le chat ou dans un fichier synchronisé OneDrive. Le script garde les valeurs en mémoire pendant le téléchargement puis termine ; il ne sauvegarde ni les valeurs ni les en-têtes d'authentification.

Alpaca situe le panneau **API Keys** dans son tableau de bord. [Instructions officielles](https://alpaca.markets/learn/start-paper-trading). Le secret n'est généralement affiché qu'à la création de la clé ; si vous n'avez plus de secret, la génération ou la rotation d'une clé est une action à réaliser vous-même dans le compte, en tenant compte des applications qui utilisent déjà la clé existante. Le programme ici ne crée ni ne régénère de clé et n'appelle aucun endpoint de trading ou de compte.

Les clés peuvent aussi être fournies au processus par `APCA_API_KEY_ID` et `APCA_API_SECRET_KEY` (ou `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`) ; dans ce cas omettre `--prompt-credentials`. Aucune variable personnelle persistante n'est créée par le programme.

## Période et provenance

Les valeurs par défaut sont 2023-01-01 inclus à 2026-09-21 exclu. Cette période s'arrête avant les séances déjà examinées lors du premier backtest. Elle est définie dans `PROTOCOLE_HISTORIQUE_LONG.md` avant toute inspection des nouveaux P&L. Les règles de stratégie restent inchangées.

Le téléchargement utilise exclusivement `https://data.alpaca.markets/v2/stocks/{SPY|QQQ}/bars`, `feed=sip`, `timeframe=1Min`, `adjustment=raw`, et suit toute la pagination. Aucune substitution silencieuse par IEX. Les réponses JSON compressées, paramètres, tailles, dates et SHA-256 sont archivés. Un refus d'accès reste un refus d'accès ; aucun abonnement n'est acheté.

Statut : `data/alpaca_sip_2023_2026/job_status.json`. Le statut `awaiting_credentials` signifie qu'aucune acquisition n'a encore eu lieu. `complete` n'est écrit que lorsque SPY et QQQ ont été téléchargés et leurs manifests enregistrés. Un manifeste n'inclut aucune clé API.

## Exécution longue

Après le téléchargement, avec les paquets locaux du projet :

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) '.python_packages'
$env:MPLCONFIGDIR = Join-Path (Get-Location) '.mplconfig'
python scripts/run_long_history.py
```

Le programme contrôle d'abord le hash, le flux, les sessions et la couverture minimale. Il écrit les dates 70/30 dans `PRE_EXECUTION_SPLIT.json` avant de calculer les performances. Puis il exécute les stops A/B, les coûts préfixés, les sensibilités et le walk-forward si la couverture le permet. Ce contrôle ne relâche aucune règle de qualité pour obtenir plus de séances.

Le moteur peut exécuter un bootstrap de séances ou de blocs de cinq séances si les seuils préfixés sont atteints. Une longue période ne garantit pas assez de trades ni un avantage ; la conclusion doit se fonder sur les résultats réellement exécutés.

Cette source vise SPY/QQQ. Elle ne remplace pas une source de contrats datés ES/NQ avec une traçabilité suffisante.
