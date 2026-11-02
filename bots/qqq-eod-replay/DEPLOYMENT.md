# Exploitation du suivi QQQ en simulation

Le replay statistique tourne dans GitHub Actions, sur `main`, à **17:23 et 18:23 America/New_York, du lundi au vendredi**. Il traite les séances XNYS échues depuis clôture + 17 minutes et rattrape les dates non traitées, dans l’ordre. Les demi-séances et changements d’heure suivent le calendrier, sans offset UTC fixe.

La cohorte statistique commence le **2 novembre 2026**. Deux comptes virtuels distincts partent de 100 000 USD. Stratégies au SHA `f7ed9515b97644102ef674315c6af46e6fce8988`, règle au SHA `6e5e36c5ab91caf964523d9f6a52a996aae5f7c2`, worker au SHA `2286aca61f4bf3636cada8e1234709cb8beafb77`. Les frais et seuils de la tâche 7 restent identiques.

## Journaux distincts

| Journal | Stockage canonique | Population |
|---|---|---|
| Statistique | `statistical.sqlite` dans les checkpoints cloud chiffrés | Toutes les dates de la cohorte ; issues inconnues et dates en attente visibles ; suspensions de risque étiquetées |
| Opérationnel | `runtime/operational/operational.sqlite`, vue SQL `qualified_sessions` | Dernière observation qualifiée de chaque bot/date depuis le 2 novembre |
| Audit opérationnel | Table `observations`, pointeurs `observation_heads` | Versions des observations, journées refusées et anciennes dates conservées sans les promouvoir dans le ledger canonique |

Le fichier local `comparison.json` contient les écarts et la couverture. `cloud_summary.json` est seulement un cache du résumé cloud, pas un troisième compte. Les dates antérieures restent sous `legacy_observations` et `legacy_qualified_sessions`. Les anciens soldes, bases et références des deux bots Windows sont conservés.

Le collecteur local lit les bases des bots avec SQLite `mode=ro`. Il ne lit aucune clé Alpaca et n’appelle pas Alpaca. Il utilise GitHub CLI dans la session utilisateur pour lire les résumés, puis écrit exclusivement dans son runtime distinct. Un problème GitHub n’empêche pas l’archivage des observations locales ; le rapprochement reste alors indisponible, jamais déclaré conforme. Les dates statistiques absentes ou non résolues sont signalées.

## Collecteur Windows sans console

Tâche `TradingBacktests-QQQ-EOD-Operational-Ledger`, `pythonw.exe`, **18:35 et 19:35 Eastern en semaine**, et deux minutes après ouverture de session. Elle exige réseau, session ouverte et alimentation secteur ; les deux tâches de trading existantes ne sont ni remplacées ni redémarrées. Elle possède deux reprises après échec, espacées de cinq minutes. Les GET GitHub transitoires connus ont une reprise bornée, sans repli sur un résumé ancien.

Le statut local est `runtime/operational/worker_status.json`. Les diagnostics ne conservent que type, phase, code de retour et statut HTTP disponibles, sans corps de réponse ni secret.

```powershell
Get-ScheduledTask -TaskName TradingBacktests-QQQ-EOD-Operational-Ledger
Get-ScheduledTaskInfo -TaskName TradingBacktests-QQQ-EOD-Operational-Ledger
Get-Content .\runtime\operational\worker_status.json
Start-ScheduledTask -TaskName TradingBacktests-QQQ-EOD-Operational-Ledger
```

Ces commandes concernent le collecteur de lecture, pas les moteurs de trading. Les états `attention` ou `failed` demandent de lire `comparison.json` et les derniers runs GitHub ; ils ne remettent jamais un compte à zéro.

## Secrets et état cloud

Trois secrets **Actions** du dépôt : `ALPACA_PAPER_KEY_ID`, `ALPACA_PAPER_SECRET_KEY`, `QQQ_EOD_STATE_KEY`. Les valeurs PAPER proviennent de l’emplacement Windows déjà configuré. Le transfert utilise l’entrée standard de GitHub CLI, chiffrée côté client ; aucune valeur n’est passée dans les arguments, un fichier `.env`, le chat ou Git.

Une clé AES-256 indépendante protège les checkpoints. Sa copie de récupération est dans un emplacement Windows Credential Manager distinct, `TradingBacktests/QQQ/EOD/StateKey/v1`. La réexécution du programme de configuration réutilise cette clé ; elle refuse une rotation et refuse un secret distant existant si la copie locale manque. Ne pas supprimer cette copie ou remplacer le secret pour contourner une erreur de reprise.

Les clés PAPER ne sont pas un rôle fournisseur natif « données seules ». La restriction est imposée par le programme : GET QQQ SIP raw et dividendes seulement, aucun endpoint broker/compte/ordre. Le workflow accepte uniquement `main`, emploie les actions épinglées et un jeton GitHub limité à `contents: read` et `actions: read`.

L’initialisation a été faite avant la première date, puis une exécution sans initialisation a repris ce checkpoint. Les exécutions normales utilisent `initialize=false`. Pour demander une reprise normale :

```text
gh workflow run qqq-eod-replay.yml --repo MinaSeliman1/trading-backtests --ref main --raw-field initialize=false
```

Ne pas utiliser le bouton de relance d’un ancien run pour écrire l’état : son numéro de tentative est refusé. Déclencher un nouveau run. Un état récent manquant, expiré, corrompu ou incompatible bloque la reprise ; aucun retour silencieux à un ancien capital. Un run échoué ayant sauvegardé un état valide reste une source de reprise autoritative.

Pour suspendre le déclenchement récurrent : `gh variable set QQQ_EOD_ENABLED --repo MinaSeliman1/trading-backtests --body false`. Cette suspension concerne le replay, pas les deux processus Windows. Elle n’efface ni l’état ni la cohorte ; les dates seront rattrapées lors d’une reprise autorisée.

## Limites

Le replay fournit du hors-échantillon pour la stratégie figée, pas pour son exploitation intraday : il utilise des barres archivées et des fills shadow modélisés. La qualification opérationnelle mesure continuité et ponctualité du processus sur une horloge différée de 16 minutes ; elle ne prouve pas une exécution chez un courtier. Les capitaux live diffèrent des nouveaux comptes : le diagnostic à capital comparable reste conditionnel aux signaux/prix du replay.

Le cloud fonctionne sans PC allumé ni Codex ouvert. La collecte opérationnelle nécessite le PC disponible ; ses lacunes restent visibles. Les schedules GitHub peuvent être retardés, et les schedules d’un dépôt public peuvent être désactivés après 60 jours sans activité du dépôt. Les checkpoints sont limités à 4 MiB et conservés 30 jours ; une longue interruption peut exiger une restauration contrôlée. Aucun achat, runner payant ou budget additionnel n’a été créé. Les alertes push relèvent de la tâche 9, distincte de cette activation.
