# QQQ Windows Background Implementation Plan

> **For agentic workers:** execute inline with superpowers:executing-plans; final independent code review before publication. The user explicitly authorized installation and automatic startup in simulation.

**Goal:** simulation QQQ sans console, démarrage à la connexion Windows, clés protégées et suivi de l'expérience.

**Architecture:** tâche sous l'utilisateur courant → pythonw → lanceur shadow/SIP fixe → moteur existant ; Credential Manager pour les secrets, SQLite existant pour l'état.

**Tech Stack:** Python 3.14.6, API Windows WinCred via ctypes, PowerShell ScheduledTasks, dépendances de l'étude existante.

**Spec:** bots/qqq-noise-area/WINDOWS_BACKGROUND_DESIGN.md.

## Global Constraints

- Simulation shadow/SIP uniquement dans le lanceur caché ; aucun ordre Alpaca.
- Aucun secret dans fichiers, arguments, journaux, Git ou suivi Codex.
- Conservation de l'état et du capital, une instance, pas de redémarrage du PC pour tester.
- Windows courant après connexion ; aucun mot de passe administrateur et aucune modification globale de mise en veille.

## Review Focus

- API Credential Manager : allocation/libération mémoire, mauvais utilisateur, refus ou secret invalide.
- Arrêt par fichier : aucun chemin de clôture ou d'ordre paper et verrou libéré.
- Démarrage sans réseau : reprise bornée dans le temps et logs limités, pas de boucle agressive.
- Redémarrage ou double lancement : conserver SQLite et éviter un second moteur.
- Suivi : ne pas confondre replay initial et observations prospectives ; ne pas conclure une rentabilité avec un simple nombre de jours.

## Tâches

1. [x] Tests rouges du vault et du lanceur ; implémentation et roundtrip Windows avec identifiants factices uniques supprimés après le test.
2. [x] Saisie masquée et scripts de tâche Windows ; tests du CLI/arrêt ; revue indépendante, deux défauts reproduits et corrigés, seconde revue sans blocage.
3. [x] Configuration réelle avec les clés fournies dans la fenêtre dédiée, enregistrement et lancement de la tâche, transition depuis la console à état conservé ; preuve de statut frais et absence de fenêtre. Arrêt/reprise observés sans reset du solde.
4. [x] Suivi quotidien lié à ce chat, seuils opérationnels définis, pas d'ordre ni lecture des secrets ; nouvelle hypothèse documentée sans résultats inventés.
5. [x] Documentation et tests finaux : 69 tests, syntaxe PowerShell et 1 977 empreintes historiques conservées ; tâche et suivi installés. Code, preuve sans secrets et protocole de la prochaine piste préparés pour publication dans le même commit.
