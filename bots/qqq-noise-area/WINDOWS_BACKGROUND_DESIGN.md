# Simulation QQQ sans console — 20 octobre 2026

Demande explicite : exécution sans console, démarrage automatique à l'allumage du PC, simulation uniquement, suivi ultérieur. L'installation retenue démarre à l'ouverture de la session Windows courante, sans compte administrateur ou mot de passe Windows ajouté. Aucun fonctionnement avant connexion de l'utilisateur n'est prétendu.

## Choix

Tâche Windows sous l'utilisateur courant, pythonw.exe et lancement fixe shadow/SIP différé de 16 minutes. Aucun argument de choix de compte réel ou de passage en paper dans ce lanceur. Le compte net, les paramètres, coûts et journaux actuels sont conservés. Le bot ne dépend pas de cette conversation pour tourner ; le PC doit rester éveillé et connecté pour traiter les données.

Les clés PAPER sont saisies masquées une dernière fois et enregistrées dans Windows Credential Manager, identifiant générique de cette application, persistance limitée à ce PC et à l'utilisateur. Elles ne sont ni dans les arguments de la tâche, ni un fichier de configuration, ni les logs ou Git. Le lanceur les lit seulement en mémoire. Une clé refusée par l'endpoint paper n'est pas enregistrée.

## Composants

- `qqq_paper/windows_vault.py` : API Windows CredWrite/CredRead/CredDelete, validation et erreurs sans secrets.
- `qqq_paper/windows_setup.py` : saisie et vérification en lecture seule du compte paper et de l'historique SIP, puis stockage Windows.
- `qqq_paper/background.py` : lanceur shadow/SIP fixe, verrou d'instance, logs rotatifs, reprise après erreur de démarrage et arrêt par drapeau local.
- `scripts/background_bootstrap.py` : dépendances locales et entrée pythonw sans console.
- Scripts PowerShell : configuration, installation, lancement et arrêt de la tâche, sans clé dans les commandes.
- Extension CLI limitée : identifiants transmis directement en mémoire et arrêt par fichier autorisé en shadow seulement. Les chemins d'ordres paper existants ne changent pas.

## Exploitation et suivi

Après vérification des tests et de la tâche, arrêter l'ancienne console uniquement après contrôle de la position virtuelle et du journal ; une seule instance utilise la base. Tester lancement caché, fraîcheur du statut et arrêt/reprise sans recréer le capital. Ne pas redémarrer réellement le PC pour le test ; vérifier le déclencheur et déclarer ce premier boot non observé.

Une interruption qui laisse une position shadow de la séance précédente reste suspendue pour reconstruction ; le démarrage automatique ne modifie pas les transactions manquées. La surveillance le signalera.

Le suivi Codex lit les états et SQLite en lecture seule, sans lire les clés ni envoyer d'ordre. Référence prospective séparée à partir de la séance suivant l'installation, en conservant le solde existant. Premier bilan opérationnel après 20 séances complètes ; bilan prolongé après 60 séances complètes et 50 transactions fermées. Ces seuils ne garantissent pas une preuve de rentabilité. Signaler plus tôt un état bloqué, un arrêt ou des données manquantes ; rester silencieux sans changement exploitable.
