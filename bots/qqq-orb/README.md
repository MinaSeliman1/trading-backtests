# QQQ ORB cinq minutes — simulation locale

Simulation QQQ séparée de Noise Area. Règles figées du [backtest ORB](../../studies/opening-range-5m/README.md), risque1%, plafond causal1x, objectif10R, stop prioritaire et capital virtuel initial100000USD. Même commission0,0035/action/côté minimum0,35, friction0,01/côté et empruntSHORT1%/360. Lire le [protocole d'exécution](PROTOCOL.md) avant d'interpréter les résultats.

Uniquement **shadow / SIP différé16minutes** : prix de remplissage simulés aux barres archivées, aucun ordre paper ni réel. La classe de transport refuse toute route broker et toute méthode autre que GET QQQ SIP. Les clés PAPER déjà protégées dans le Gestionnaire d'identifiants Windows sont réutilisées en mémoire ; aucun secret n'est écrit dans ce dossier ou Git. Les données et le ledger restent sous `runtime/`, ignoré par Git.

## Installation et contrôle Windows

Depuis ce dossier :

```powershell
& C:/Python314/python.exe scripts/background_bootstrap.py --check --runtime runtime
.\install-background.ps1 -StartNow
Get-Content .\runtime\status.json
Get-Content .\runtime\windows\power_status.json
```

Tâche dédiée `TradingBacktests-QQQ-ORB-Simulation`, `pythonw.exe` sans console, ouverture de session Windows avec délai20s. La tâche ne réveille pas un PC arrêté/endormi. Sur secteur, une requête de maintien éveillé empêche la veille automatique tant que le bot tourne, y compris la nuit ; écran libre de s'éteindre, batterie/couvercle/boutons inchangés. Garder le couvercle ouvert. Les historiques, verrous, compte100000 et état sont distincts de Noise Area.

```powershell
.\stop-background.ps1
# ou arrêt avec désactivation du prochain démarrage
.\stop-background.ps1 -DisableStartup
.\start-background.ps1
```

L'arrêt n'invente pas une clôture virtuelle. Une position persistée peut se terminer à la reprise lorsque ses barres sont disponibles, même le lendemain ; la séance est alors signalée comme rattrapage. Une lacune réellement non résolue conserve position, frais et dernière marque, et bloque les nouvelles entrées jusqu'à inspection. Aucun reset de compte automatique.

L'entrée doit être observée au plus tard09:37 sur horloge logique (heure réelle09:53 avec le délai16min). Une entrée manquée est sautée, jamais reconstituée après coup comme prospective. Les barres mémorisées ne sont pas réécrites par les révisions ultérieures observées pendant la séance. Après une sortie connue, le bot cesse de télécharger/recalculer cette journée ; les révisions ultérieures à sa clôture ne sont donc pas toutes détectées.

## Bilan et tests

Définir PYTHONPATH vers les dépendances locales comme dans les autres études, puis depuis ce dossier :

```powershell
python -m orb_shadow.monitor --runtime runtime
python -m pytest -q
python scripts/verify_parity.py
```

Le monitor est en lecture seule, sans clés ni API. Il sépare le compte global, les séances entièrement observées, les trades correspondants et les lacunes. Revue opérationnelle à20séances qualifiées ; revue descriptive à60séances et50trades qualifiés fermés. Ces seuils ne prouvent pas une rentabilité et n'activent jamais le réel. Le suivi automatique Codex de Noise Area reste distinct ; ce module fournit le bilan local ORB.

La parité historique vérifie l'intégration avec le moteur figé sur les journées complètes du backtest ; elle réutilise ses fonctions de sortie et n'est ni un audit indépendant supplémentaire ni une observation prospective. Les audits indépendants du moteur historique restent publiés dans l'étude ORB. Les preuves d'activation et de parité sont sous `validation/`.
