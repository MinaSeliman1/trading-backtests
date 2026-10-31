# Réveil manqué du 30 octobre — diagnostic et protection secteur

Le réveil Windows était correctement armé pour le30octobre, environ30secondes avant09:10locale. Le PC est entré en veille après débranchement le29octobre, puis en hibernation ; aucun réveil de séance n'est enregistré le30. La cause la mieux étayée est la disponibilité de l'alimentation pendant cette hibernation, et non un décalage de fuseau ou une stratégie de trading bloquée.

## Faits et degré de certitude

| Heure Toronto/New York | Preuve locale |
|---|---|
| 29oct13:29:36 | KernelPower105 : AcOnline=false |
| 29oct13:29:49 | KernelPower42 : veille « Button or Lid » |
| 29oct16:30:14 | KernelPower42 : passage enS4, « Hibernate from Sleep - Fixed Timeout » |
| Réveil programmé30oct09:09:30 | KernelPower107 : ProgrammedWakeTimeAc=2026-10-30T13:09:30.8822698Z ; aucune minuterie DC |
| 31oct14:00 | Retour enregistré depuis l'état basse consommation ; nouvel AcOnline=true |

RTCWAKE était déjà AC1/DC0. La tâche avait WakeToRun=true, démarrage sur batterie interdit,09:10du lundi au vendredi, ancrage local sans offset fixe. Son prochain horaire, lundi2novembre09:10−05:00, confirme le changement d'heure saisonnier. Le journal opérationnel TaskScheduler était désactivé : impossible de certifier rétrospectivement l'état exact de la prise à09:10 ou la délivrance matérielle du timer. Les événements d'alimentation ne s'enregistrent pas continuellement pendant une hibernation. On ne présente donc pas l'hypothèse batterie comme une preuve absolue contre tout problème de firmware.

Le garde de veille logiciel libérait normalement sa requête sur batterie, conformément au choix utilisateur. Une fois suspendu, il ne pouvait pas empêcher la transition en hibernation ni observer un éventuel rebranchement. Les transactions manquées ne sont pas reconstruites ou reclassées comme prospectives.

## Correction appliquée le31octobre

Le nouveau [helper](../../bots/qqq-noise-area/configure-ac-availability.ps1) rend le maintien éveillé **sur secteur indépendant des moteurs** sur le plan actif Balanced. Audit en lecture seule par défaut, application uniquement avec `-Apply`.

| Paramètre | AC avant | AC après | DC conservé |
|---|---:|---:|---:|
| RTCWAKE | 1 | 1 | 0 |
| STANDBYIDLE | 900s | 0, jamais automatiquement | 600s |
| HIBERNATEIDLE | 10800s | 0, jamais automatiquement | 10800s |

LIDACTION reste AC0/DC1 ; l'ensemble du sous-groupe boutons/couvercle a été comparé avant/après, identique. Écran, boutons, hibernation globale et réglages batterie conservés. Ce choix consomme davantage d'énergie sur secteur et reste actif même si les bots sont arrêtés. Il ne modifie pas une veille explicitement demandée par bouton/menu, un arrêt ou une coupure d'alimentation.

Sauvegarde initiale parGUID dans `bots/qqq-noise-area/runtime/windows/ac_availability_before-381b4222-f694-41f0-9685-ff5bb260df2e.json`, ignorée parGit. Appels répétés idempotents sans écraser la première sauvegarde. Un échec partiel, y compris l'impossibilité d'enregistrer la preuve finale, tente de restaurer les indices AC originaux et conserve l'erreur initiale. Les réglages DC ne sont jamais écrits.

## Vérification et intégrité financière

154tests passent :124Noise Area et30ORB. Une intégration native du Gestionnaire d'identifiants Windows, sans rapport avec ce changement, est explicitement désélectionnée ; aucun accès au coffre. Les6tests du helper utilisent un faux powercfg et couvrent lecture seule, métadonnées min/max, AC seul, sauvegarde/idempotence et retours arrière. Les18contrats du réveil conservent les protections STOP, désactivation, commande réservée, indépendance des deux bots et09:10locale aprèsDST.

La revue indépendante a reproduit l'échec d'écriture de preuve hors transaction ; un test rouge puis la correction l'ont fermé AVANT application. Six tests helper rejoués par le reviewer, aucun problème important restant.

L'action installée du réveil a été exécutée PC éveillé le31à14:32:58 : résultat0, les deux tâches reconnues `already_running`, aucune duplication ni redémarrage des tâches principales. Leurs derniers démarrages restent le28octobre08:48:02/08:47:38. États frais, protégés sur secteur et sans position ni ordre local en attente.

Les snapshots SQLite en mode lecture seule confirment soldes, empreintes de compte/configuration, nombres d'enregistrements, pauses, drapeaux STOP et références inchangés : Noise Area98041,4235USD, baseline21octobre ; ORB99188,18398333332USD, baseline26octobre. Mode exclusivement shadow/SIP différé16minutes ; aucun ordre broker, aucune lecture de clé.

[Preuve chiffrée et périmètre](../../bots/qqq-noise-area/validation/ac_availability_2026-10-31.json). Les historiques d'études et résultats précédents restent inchangés.

## Incident constaté avant autorisation de relance

Un contrôle ultérieur à14:40–14:42 a constaté que les deux tâches principales étaient passées `Ready`, résultat1, avec des statuts moteur arrêtés vers14:35:45. Aucun nouvel événement de veille ni crash applicatif1000/1001 n'a été trouvé dans la fenêtre contrôlée. Les réglages secteur sont toujours AC1/0/0 ; la cause de ces sorties de processus n'est pas établie. Les tests de scripts consultés simulent le planificateur et n'appellent pas les tâches réelles. Le succès du test éveillé à14:33 reste une preuve passée, pas une affirmation que les moteurs tournent encore.

La revue automatique d'approbation a rejeté la demande de démarrer le vérificateur de réveil pour relancer maintenant les deux tâches : la consigne conservée du suivi limite ce démarrage automatique à avant09:30. L'action rejetée n'a pas été exécutée. Une autorisation explicite de relance hors de ce créneau est demandée à l'utilisateur ; aucun autre chemin n'est utilisé pour contourner ce refus. Le réveil ordinaire déjà installé reste prévu le2novembre09:10, dans le créneau autorisé.

Les comptes sont à plat et les STOP/pauses/références ont été contrôlés sans les modifier. Une éventuelle reprise utilisera seulement les deux commandes shadow/SIP déjà installées, sans remise à zéro et sans ordre broker. **La politique secteur est corrigée et vérifiée ; la remise en marche immédiate des moteurs reste en attente d'autorisation.**

## Relance autorisée et effectuée ensuite

Après l'autorisation explicite de l'utilisateur de relancer même après09:30, les deux tâches ont repris le31octobre vers14:54 puis ont chargé les diagnostics lors d'un arrêt gracieux/rechargement vers15:07. Les contrôles suivants confirment des statuts frais et une protection secteur active, avec soldes, configurations et références conservés. Le blocage décrit ci-dessus est donc historique, résolu par cette nouvelle autorisation. La cause précise des codes1 reste indéterminée. [Rapport de reprise, tests et preuve](2026-10-31-qqq-exit-diagnostics.md).

## Prochaine observation

Le prochain réveil planifié est lundi2novembre à09:10Toronto/NewYork. Un test d'action PC éveillé ne prouve pas une sortie physique depuisS3/S4 ; aucun sommeil artificiel n'a été déclenché. La nouvelle politique évite la veille et l'hibernation automatiques sur secteur dès maintenant, mais une prise débranchée, une veille manuelle, un PC éteint ou une panne de données peut toujours interrompre la séance. Garder le PC branché avec sa session ouverte. Le suivi contrôlera la fraîcheur et les décisions effectives ; aucune garantie de ponctualité absolue ou de rentabilité.

Sources techniques primaires : [minuteries powercfg](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options), [temporisation d'hibernation aprèsS3](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/display--sleep--and-hibernate-idle-timers), [restriction batterie d'une tâche](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-disallowstartifonbatteries). Consultées le31octobre2026.
