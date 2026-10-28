# QQQ en arrière-plan sous Windows

Lanceur prévu pour **shadow / SIP différé de 16 minutes** uniquement. Les transactions et les frais restent dans le journal local : aucun ordre n'est envoyé à Alpaca. Les paramètres de Noise Area et le capital déjà présent dans SQLite sont conservés.

## Démarrage et dépendances

La tâche principale `TradingBacktests-QQQ-NoiseArea-Simulation` lance `pythonw.exe` à l'ouverture de la session Windows de l'utilisateur qui l'installe, avec un délai de 20 secondes. Elle utilise les droits ordinaires de cet utilisateur, sans mot de passe Windows enregistré. Elle ne démarre pas avant connexion et ne réveille pas elle-même le PC. La fermeture de Codex ou du navigateur n'arrête pas le bot. Le réveil avant séance est assuré par la tâche distincte décrite ci-dessous.

Le PC doit rester éveillé et connecté pendant les séances. Le lanceur réessaie une initialisation qui échoue toutes les 60 secondes ; les erreurs API en cours d'exécution sont réévaluées par le moteur. Une pause du journal reste une pause : aucune reconstruction de transactions manquées ni remise à zéro des protections n'est automatique.

Depuis le correctif du **24 octobre 2026**, le superviseur empêche la **veille automatique sur secteur** avec une requête Windows `ES_SYSTEM_REQUIRED`. Un thread indépendant la maintient même pendant une attente API et la libère sur batterie, lors d'une demande d'arrêt ou à la sortie. La vérification d'alimentation s'effectue toutes les 15 secondes. La protection reste active la nuit lorsque le bot tourne sur secteur : sinon une mise en veille nocturne empêcherait le code de se réveiller pour protéger la séance suivante. L'écran peut s'éteindre normalement ; aucun réglage permanent du plan d'alimentation n'est changé.

Conformément au choix de l'utilisateur, **le couvercle et les boutons de veille ne sont pas modifiés**. Garder le PC branché et le couvercle ouvert. Une veille explicite en séance, une fermeture du couvercle, un arrêt, une panne réseau ou une perte d'alimentation peuvent encore interrompre la couverture. Le garde de veille ne peut pas réveiller son propre processus suspendu. Voir les diagnostics des [huit retards du21octobre](validation/sleep_incident_2026-10-21.md) et des [quatre retards du26octobre](validation/morning_wake_2026-10-26.md).

## Réveil avant séance ajouté le26octobre2026

La tâche courte `TradingBacktests-QQQ-NoiseArea-Simulation-Wakeup` est distincte du moteur qui tourne longtemps : celui-ci peut rester marqué Running pendant une hibernation. Du lundi au vendredi à **09:10 heure de Toronto/New York**, Windows demande un réveil de veille/hibernation, sur secteur. La session utilisateur doit déjà être ouverte, éventuellement verrouillée ; aucun mot de passe n'est stocké. L'installateur exige le fuseau Windows Eastern Standard Time pour conserver l'heure locale et les changements saisonniers.

L'action cachée `wake-before-session.ps1` vérifie la commande exacte du simulateur. Si sa tâche tourne déjà, elle ne la duplique pas. Si elle est arrêtée, elle demande son démarrage ; si le drapeau STOP existe ou la tâche principale est désactivée, elle respecte cet arrêt. Elle ne lit ni coffre ni SQLite, ne fait aucune requête API et ne modifie aucune pause ou transaction. Une demande de démarrage n'est pas une preuve de fraîcheur du moteur : le monitor conserve ce contrôle séparé.

L'installation passe les **minuteries de réveil sur secteur** du mode « important uniquement » à « activé », sinon la nouvelle tâche ordinaire ne pourrait pas réveiller Windows. Ce réglage du plan actif peut aussi autoriser les autres minuteries ordinaires déjà installées. Les minuteries sur batterie restent désactivées ; les délais de veille/hibernation, l'écran, les boutons et le couvercle sont inchangés. L'ancien réglage est conservé dans `runtime/windows/wake_policy_before.json`.

Le réveil ne met pas sous tension un PC éteint et ne garantit rien sur batterie, sans session ouverte ou sans prise en charge matérielle. Aucun sommeil artificiel n'est provoqué pour le tester : installation, paramètres et action éveillée sont vérifiés ; le premier réveil réel reste une observation future. Le démarrage manqué peut être rattrapé lorsque Windows redevient disponible, sans reclasser les décisions tardives comme prospectives.

Le dossier du dépôt, Python et ses dépendances doivent rester au même endroit. Les chemins absolus enregistrés dans la tâche sont propres à la machine ; un déplacement nécessite de réinstaller la tâche depuis le nouveau dossier. Une seule instance peut posséder le verrou du journal.

## Configuration initiale

Depuis ce dossier sous PowerShell :

```powershell
.\configure-windows.ps1
.\install-background.ps1
.\install-wakeup.ps1 -EnableAcWakeTimers
.\start-background.ps1
```

La configuration demande les clés **PAPER**, masque leur saisie et vérifie le compte et l'accès SIP avec des requêtes GET avant enregistrement. Windows Credential Manager les protège pour cet utilisateur sur ce PC. Les clés n'apparaissent ni dans les arguments de la tâche, ni dans un fichier de configuration du bot, ni dans Git. Le programme les lit en mémoire ; ce coffre ne protège pas contre un programme malveillant exécuté sous le même utilisateur Windows.

Le stockage persiste après les connexions suivantes sur ce PC. Pour renouveler les clés, arrêter la simulation, relancer `configure-windows.ps1`, puis reprendre. Une révocation chez Alpaca invalide naturellement les clés enregistrées.

## Contrôle, arrêt et reprise

```powershell
# Lire l'état du moteur et du superviseur ; aucun secret
Get-Content .\runtime\shadow-sip\status.json
Get-Content .\runtime\windows\status.json
Get-Content .\runtime\windows\power_status.json
Get-ScheduledTask -TaskName TradingBacktests-QQQ-NoiseArea-Simulation
Get-ScheduledTask -TaskName TradingBacktests-QQQ-NoiseArea-Simulation-Wakeup
Get-Content .\runtime\windows\wake_status.json

# Arrêt demandé au moteur, sans ordre Alpaca et sans suppression du journal
.\stop-background.ps1

# Même arrêt et désactivation du prochain démarrage automatique
.\stop-background.ps1 -DisableStartup

# Enlever le drapeau d'arrêt, réactiver la tâche et relancer
.\start-background.ps1
```

L'arrêt prend effet après le cycle API en cours. Vérifier `state: stopped` dans `runtime/windows/status.json`. Un drapeau `runtime/STOP_SHADOW.flag` laissé en place maintient l'arrêt, même après une nouvelle connexion ; utiliser le script de reprise pour l'enlever. Éviter un arrêt pendant une position virtuelle ouverte : une clôture manquée entraînera une suspension à la séance suivante, qui demande une inspection du journal.

Un arrêt du bot ne supprime pas la minuterie de réveil : son action respectera le STOP. Pour supprimer aussi le réveil du PC, désactiver séparément la tâche `...-Wakeup` avec `Disable-ScheduledTask`. Pour restaurer la politique précédente, lire `runtime/windows/wake_policy_before.json` et rétablir seulement sa valeur AC RTCWAKE sur le plan qui y est enregistré ; aucune remise à zéro globale de l'alimentation n'est nécessaire.

Les fichiers `runtime/windows/` contiennent les logs rotatifs (2 Mo, cinq sauvegardes), les preuves d'installation et le bilan local. SQLite et les exports existants restent dans `runtime/shadow-sip/`. Tout `runtime/` est ignoré par Git ; aucune sauvegarde des clés n'y est créée.

## Suivi prospectif

La référence est créée une fois, à partir de la prochaine séance NYSE suivant l'installation, sans remettre le solde à 100 000 USD :

```powershell
python -m qqq_paper.monitor --runtime runtime --initialize
python -m qqq_paper.monitor --runtime runtime
```

Le bilan lit SQLite en lecture seule, sans API et sans clé. Une séance complète exige toutes les décisions prévues, à plat après clôture, sans pause, et des observations dans les deux minutes du créneau et de la clôture sur l'horloge logique différée de 16 minutes. Un rattrapage tardif reste identifié comme tel. Les transactions des séances incomplètes sont conservées dans le journal et le résultat global ; elles ne sont pas comptées comme observations entièrement prospectives.

Le bilan expose aussi `coverage_details` : décisions à l'heure, retards, premiers et derniers créneaux retardés et retard maximal, calculés à partir des observations enregistrées. `power_protection` indique la requête de maintien éveillé et les interruptions du thread. Un statut périmé, absent après installation, invalide ou en erreur déclenche une alerte ; une alimentation sur batterie pendant une séance est signalée. Ces diagnostics ne reclassent pas une séance manquante ou rattrapée comme prospective.

Premier bilan opérationnel après **20 séances entièrement prospectives**. Bilan prolongé après **60 séances et 50 transactions fermées** sur ces séances. Un arrêt, un statut périmé ou une couverture manquante est à examiner plus tôt. Ces seuils permettent une revue ; ils ne prouvent pas un avantage statistique ou une rentabilité future, et les fills demeurent des simulations aux prix archivés.

Le suivi Codex est distinct de la tâche Windows : le bot fonctionne sans Codex ouvert, tandis que les contrôles planifiés nécessitent que l'environnement local du suivi puisse s'exécuter. Il faut conserver le PC disponible pour recevoir un contrôle à l'heure prévue.

## Sources techniques

[CredWriteW et contexte utilisateur](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew), [persistance des identifiants Windows](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw), [paramètres de tâche Windows](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset?view=windowsserver2025-ps). Consultés le 20 octobre 2026.

[SetThreadExecutionState et ses limites face à la veille explicite](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate), [GetSystemPowerStatus](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getsystempowerstatus). Consultés le 23 octobre 2026.

[WakeToRun et sortie de veille/hibernation](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-waketorun), [powercfg et réglage AC distinct du DC](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options). Consultés le26octobre2026.


## Contrôle commun du28octobre2026

Le même réveil09:10 contrôle maintenant les **deux** tâches fixes Noise Area et ORB, indépendamment. `wake_status.json` conserve un résultat `bots.noise` et `bots.orb` ; STOP/désactivation restent propres à chacun. Le contrôle valide aussi le dossier de travail et ne redémarre pas un moteur actif. Le passage automatique du28à09:10 a réussi. [Incident, correction et limites matérielles](../../docs/operations/2026-10-28-qqq-startup-and-coverage.md).
