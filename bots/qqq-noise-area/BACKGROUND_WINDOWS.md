# QQQ en arrière-plan sous Windows

Lanceur prévu pour **shadow / SIP différé de 16 minutes** uniquement. Les transactions et les frais restent dans le journal local : aucun ordre n'est envoyé à Alpaca. Les paramètres de Noise Area et le capital déjà présent dans SQLite sont conservés.

## Démarrage et dépendances

La tâche `TradingBacktests-QQQ-NoiseArea-Simulation` lance `pythonw.exe` à l'ouverture de la session Windows de l'utilisateur qui l'installe, avec un délai de 20 secondes. Elle utilise les droits ordinaires de cet utilisateur, sans mot de passe Windows enregistré. Elle ne démarre pas avant connexion et ne réveille pas un PC arrêté ou en veille. La fermeture de Codex ou du navigateur n'arrête pas le bot.

Le PC doit rester éveillé et connecté pendant les séances. Le lanceur réessaie une initialisation qui échoue toutes les 60 secondes ; les erreurs API en cours d'exécution sont réévaluées par le moteur. Une pause du journal reste une pause : aucune reconstruction de transactions manquées ni remise à zéro des protections n'est automatique.

Le dossier du dépôt, Python et ses dépendances doivent rester au même endroit. Les chemins absolus enregistrés dans la tâche sont propres à la machine ; un déplacement nécessite de réinstaller la tâche depuis le nouveau dossier. Une seule instance peut posséder le verrou du journal.

## Configuration initiale

Depuis ce dossier sous PowerShell :

```powershell
.\configure-windows.ps1
.\install-background.ps1
.\start-background.ps1
```

La configuration demande les clés **PAPER**, masque leur saisie et vérifie le compte et l'accès SIP avec des requêtes GET avant enregistrement. Windows Credential Manager les protège pour cet utilisateur sur ce PC. Les clés n'apparaissent ni dans les arguments de la tâche, ni dans un fichier de configuration du bot, ni dans Git. Le programme les lit en mémoire ; ce coffre ne protège pas contre un programme malveillant exécuté sous le même utilisateur Windows.

Le stockage persiste après les connexions suivantes sur ce PC. Pour renouveler les clés, arrêter la simulation, relancer `configure-windows.ps1`, puis reprendre. Une révocation chez Alpaca invalide naturellement les clés enregistrées.

## Contrôle, arrêt et reprise

```powershell
# Lire l'état du moteur et du superviseur ; aucun secret
Get-Content .\runtime\shadow-sip\status.json
Get-Content .\runtime\windows\status.json
Get-ScheduledTask -TaskName TradingBacktests-QQQ-NoiseArea-Simulation

# Arrêt demandé au moteur, sans ordre Alpaca et sans suppression du journal
.\stop-background.ps1

# Même arrêt et désactivation du prochain démarrage automatique
.\stop-background.ps1 -DisableStartup

# Enlever le drapeau d'arrêt, réactiver la tâche et relancer
.\start-background.ps1
```

L'arrêt prend effet après le cycle API en cours. Vérifier `state: stopped` dans `runtime/windows/status.json`. Un drapeau `runtime/STOP_SHADOW.flag` laissé en place maintient l'arrêt, même après une nouvelle connexion ; utiliser le script de reprise pour l'enlever. Éviter un arrêt pendant une position virtuelle ouverte : une clôture manquée entraînera une suspension à la séance suivante, qui demande une inspection du journal.

Les fichiers `runtime/windows/` contiennent les logs rotatifs (2 Mo, cinq sauvegardes), les preuves d'installation et le bilan local. SQLite et les exports existants restent dans `runtime/shadow-sip/`. Tout `runtime/` est ignoré par Git ; aucune sauvegarde des clés n'y est créée.

## Suivi prospectif

La référence est créée une fois, à partir de la prochaine séance NYSE suivant l'installation, sans remettre le solde à 100 000 USD :

```powershell
python -m qqq_paper.monitor --runtime runtime --initialize
python -m qqq_paper.monitor --runtime runtime
```

Le bilan lit SQLite en lecture seule, sans API et sans clé. Une séance complète exige toutes les décisions prévues, à plat après clôture, sans pause, et des observations dans les deux minutes du créneau et de la clôture sur l'horloge logique différée de 16 minutes. Un rattrapage tardif reste identifié comme tel. Les transactions des séances incomplètes sont conservées dans le journal et le résultat global ; elles ne sont pas comptées comme observations entièrement prospectives.

Premier bilan opérationnel après **20 séances entièrement prospectives**. Bilan prolongé après **60 séances et 50 transactions fermées** sur ces séances. Un arrêt, un statut périmé ou une couverture manquante est à examiner plus tôt. Ces seuils permettent une revue ; ils ne prouvent pas un avantage statistique ou une rentabilité future, et les fills demeurent des simulations aux prix archivés.

Le suivi Codex est distinct de la tâche Windows : le bot fonctionne sans Codex ouvert, tandis que les contrôles planifiés nécessitent que l'environnement local du suivi puisse s'exécuter. Il faut conserver le PC disponible pour recevoir un contrôle à l'heure prévue.

## Sources techniques

[CredWriteW et contexte utilisateur](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew), [persistance des identifiants Windows](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw), [paramètres de tâche Windows](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset?view=windowsserver2025-ps). Consultés le 20 octobre 2026.
