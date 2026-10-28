# QQQ — démarrage ORB et absence du27octobre2026

Diagnostic et correction du28octobre, heure Toronto/NewYork. Les deux moteurs restent en simulation locale shadow/SIP différé16minutes. [Preuve de contrôle](../../bots/qqq-orb/validation/startup_recovery_2026-10-28.json).

## Causes constatées

- ORB : premier probe historique SIP échoué au démarrage à08:11:32, puis reprise automatique déjà réussie à08:12:42 grâce au retry existant de60secondes. Ce n'était plus un blocage persistant. L'ancien transport ramenait DNS/TLS/timeout/erreur réseau à ConnectionError ; sa cause réseau précise passée n'est pas récupérable. Aucun indice de clé invalide HTTP401/403 dans cette observation.
- Absence commune le27 : veille Windows le26à21:07:45, motif Button or Lid, alors que les deux protections signalaient sur batterie. Hibernation le27à00:08:17, puis aucun réveil enregistré pendant sa séance. Redémarrage le28à07:57 avec Kernel-Power41 et EventLog6008 signalant un arrêt non propre. Les logs établissent une indisponibilité du PC ; ils ne prouvent pas pourquoi matériellement cet arrêt a eu lieu.
- Minuteries secteur activées, batterie désactivées conformément au choix utilisateur. La tâche09:10n'a pas tourné le27 ; son dernier passage restait le26. L'historique détaillé du Planificateur n'était pas activé. Ne pas attribuer cet échec à un défaut exact de firmware non démontré.
- Lacune logicielle distincte : l'action de réveil vérifiait seulement la tâche Noise Area ; ORB arrêté n'aurait pas été relancé par ce contrôle.

## Corrections installées

Le contrôle09:10 vérifie maintenant chaque tâche fixe Noise Area et ORB séparément : exécutable, arguments et dossier de travail exacts. Il démarre une tâche arrêtée, conserve une tâche active sans doublon, respecte STOP et tâche désactivée. Un arrêt ou une erreur sur l'un ne supprime pas le contrôle de l'autre. Le statut ignoré parGit donne le résultat pour chaque bot. La tâche Windows, sa minuterie secteur et son horaire Eastern sans offset fixe restent les mêmes.

Le transport conserve un code réseau fermé et sans texte externe : dns, tls, timeout, connection_refused/reset, network_unreachable, redirect_refused ou network_unknown. Il reste compatible ConnectionError ; aucune route, aucun timeout ou retry de trading modifié. ORB écrit checking_connection pendant le probe, puis un diagnostic sans clé en cas d'échec ; le monitor expose ce code. Le retry existant de60secondes est conservé et testé jusqu'à récupération.

## Vérifications et chargement

15 régressions attendues observées avant correction :14 cas API/réveil et1 reprise ORB. Après correction : **119tests Noise Area et30tests ORB passent**. Revue séparée sans blocage :29tests API/réveil et6tests service/monitor passent. Les essais utilisent faux transports, identifiants factices et Planificateur simulé.

Rechargement gracieux avant séance, uniquement après vérification des deux comptes plats, absence d'ordre en attente, de pause et de STOP opérateur. ORB redemandé à08:47:38, Noise Area à08:48:02 ; les deux nouvelles instances étaient fraîches à09:23. Aucun processus tué. Soldes, empreintes des comptes et configurations, compteurs, références21/26octobre et baseline Noise identiques avant/après. Aucun journal réinitialisé, aucune séance manquée requalifiée.

Le passage automatique réel de09:10:00 finit avec code0 et un statut à09:10:08 : les deux tâches déjà actives. Prochaine échéance29octobre09:10. Les deux protections secteur sont actives. Cela vérifie l'action quand le PC est éveillé, pas un réveil matériel depuis hibernation. Les moteurs et règles financières figés sont inchangés.

## Conditions pour les prochaines séances

PC branché, session ouverte et couvercle ouvert avant09:10, comme prévu. La protection empêche seulement la veille automatique sur secteur. Aucun changement du couvercle, des boutons, de la batterie ou du BIOS. Une extinction, une veille explicite ou l'absence d'alimentation peut encore empêcher les observations ; aucun code local ne garantit de faire tourner un PC indisponible. Le suivi conserve le seuil commun20séances réellement qualifiées ; le27reste manquant.

[Limite de SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate), [réveils Windows](https://learn.microsoft.com/en-us/windows/win32/power/system-wake-up-events), [raisons URLError](https://docs.python.org/3/library/urllib.error.html), documentation primaire consultée le28octobre2026.
