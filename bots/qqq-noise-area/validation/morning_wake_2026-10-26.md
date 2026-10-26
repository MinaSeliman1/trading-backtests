# Quatre décisions tardives du26octobre2026

## Cause établie

Windows Power-Troubleshooter, événement1 à12:11:24Toronto : début du sommeil **25octobre01:02:37**, réveil **26octobre12:11:21**. L'événement Kernel-General1 précise une resynchronisation de l'horloge avec le RTC au réveil ; ce n'est pas une erreur UTC du bot. Le dimanche01:03, Kernel-Power42 signale le passage de sommeil à hibernation. Le garde indépendant enregistre **126545secondes sans observation**, puis réacquiert la protection secteur lundi12:12:46.

Les décisions logiques10:00,10:30,11:00,11:30 sont toutes observées autour de11:59:19 logique, soit12:15:19 au mur avec SIP différé16minutes. Retards respectifs :119min19s,89min19s,59min19s,29min19s. Le chargement historique et la reprise API après réveil expliquent les quelques minutes entre12:11 et12:15, sans expliquer les heures de sommeil antérieures. Les huit décisions suivantes ont été observées à l'heure selon la tolérance existante.

Les veilles « bouton ou couvercle » de15:51/15:52 constituent un autre événement de fin d'après-midi, pas la cause des quatre retards du matin. Aucune cause physique initiale du sommeil du dimanche n'est attribuée au-delà des événements disponibles ; le passage batterie enregistré ne prouve pas à lui seul l'action utilisateur.

## Pourquoi le correctif précédent ne suffisait pas

Le correctif du24octobre empêchait la veille automatique **pendant que le processus tournait sur secteur**. Il relâche volontairement sa requête sur batterie. Un processus suspendu ne peut pas demander son propre réveil. La tâche d'origine n'avait qu'un déclencheur au logon et WakeToRun=false. Les minuteries AC étaient limitées aux réveils importants, DC désactivées. Le moteur pouvait rester Running dans le planificateur tout en étant suspendu.

## Correctif ciblé

Tâche Windows courte et distincte, lundi–vendredi09:10Toronto/NewYork, WakeToRun=true, exécution cachée et limitée à l'utilisateur déjà connecté. Elle vérifie la tâche shadow/SIP existante et la démarre seulement si nécessaire ; STOP ou tâche désactivée restent respectés. Aucun accès aux clés ou au journal par ce contrôle. Minuteries ordinaires AC activées, DC et tous les autres réglages d'alimentation conservés. Les minuteries d'autres tâches ordinaires peuvent aussi être autorisées par cette option Windows globale.

Le moteur, ses paramètres, ses coûts, son solde, les décisions existantes et la référence du21octobre restent conservés. Aucun rechargement du moteur n'est requis pour installer ce réveil externe. Les observations tardives demeurent des rattrapages, pas des séances qualifiées.

## Validation

Voir [preuve de livraison](morning_wake_2026-10-26.json) pour tests, revue, tâche réelle, politique AC/DC et empreintes du journal avant/après. Tests PowerShell avec planificateur simulé avant déploiement ; aucun ordre, aucune mise en veille réelle imposée, aucune remise à zéro de SQLite. Une invocation éveillée du contrôle ne prouve pas un réveil matériel futur.

Le PC doit rester branché avant09:10, avec session Windows ouverte et couvercle ouvert. Le réveil ne démarre pas un PC éteint et ne garantit pas la disponibilité sur batterie. Les arrêts manuels et les interruptions réseau pendant la séance restent possibles. La prochaine séance doit confirmer l'absence de retard ; aucun bilan de rentabilité n'est déduit de ce correctif.

Revue du changement d'heure : le déclencheur produit initialement par PowerShell portait un décalage fixe. Deux tests saisonniers ont reproduit ce défaut avant correction. La tâche finalement installée utilise StartBoundary sans décalage, ce qui suit les règles locales Eastern et maintient09:10 après changement d'heure.103tests passent, dont8pour le réveil. Un test d'intégration du coffre sur une cible factice jetable a rencontré un refus Windows5 dans le bac à sable ; il est exclu du dernier passage, sans relancer d'accès aux véritables clés. L'énumération native powercfg/waketimers exige des droits administrateur non demandés davantage ; les paramètres réels, le XML et la prochaine échéance ont été vérifiés directement.

[Sémantique Microsoft de StartBoundary et DST](https://learn.microsoft.com/en-us/windows/win32/api/taskschd/nf-taskschd-itrigger-get_startboundary).
