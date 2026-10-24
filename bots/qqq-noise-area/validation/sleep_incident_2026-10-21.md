# Décisions Noise Area retardées le 21 octobre 2026

Diagnostic commencé le 23 octobre ; correctif préparé le 23 et déployé le 24 octobre 2026. Toutes les heures ci-dessous sont en heure de New York/Toronto, UTC−4 ce jour-là.

Le journal conserve les douze décisions comme traitées, mais seulement **quatre à l'heure**. Le défaut porte sur la couverture prospective ; il ne s'agit pas de huit décisions définitivement absentes. Le mode reste shadow / SIP différé de 16 minutes, sans ordre chez Alpaca.

## Preuves concordantes

| Observation | Heure réelle |
|---|---|
| Décision logique de 10:00 observée | 10:17:01,556 |
| Décision logique de 10:30 observée | 10:47:03,825 |
| Événement Windows Kernel-Power 42 : entrée en veille, motif « Button or Lid » | 10:55:52 |
| Événement Windows Kernel-Power 42 : passage de veille en hibernation | 13:56:07 |
| Retour d'état basse consommation, Power-Troubleshooter 1 | 15:11:10,329 |
| Huit décisions logiques de 11:00 à 14:30 rattrapées | 15:11:50,818 à 15:11:51,423 |
| Décision logique de 15:00 observée | 15:17:07,823 |
| Décision logique de 15:30 observée | 15:47:07,478 |

Le champ `observed_at` du journal est l'heure UTC réelle **moins 16 minutes** : il mesure le retard sur l'horloge logique SIP. Le tableau remet ces observations en heure réelle. Le seuil prospectif demeure 120 secondes après l'horaire logique ; les quatre observations à l'heure ont un retard de 61 à 68 secondes, notamment parce que l'open de la minute de référence doit déjà avoir été reçu. Pour 11:00, le retard logique dépasse 3 h 55 min.

La mise en veille explique la longue interruption : aucune tâche Python ne peut traiter les créneaux lorsque Windows dort. Les erreurs de connexion près des reprises sont consignées, mais les journaux ne démontrent pas une panne réseau continue expliquant à elle seule ces huit retards. L'événement « Button or Lid » ne permet pas de distinguer précisément un appui sur un bouton d'une fermeture du couvercle.

La copie cohérente de SQLite, les événements Windows et l'extraction des horaires sont conservés uniquement dans le dossier ignoré `runtime/diagnostics/2026-10-23-timing/`. Cette publication contient les constats utiles, sans identifiant de compte ni clés.

## Correction retenue

L'utilisateur choisit d'empêcher uniquement la veille automatique et de laisser le couvercle ouvert. Le superviseur caché détient une requête Windows `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` sur secteur, y compris la nuit pour que la prochaine séance reste accessible. Un thread indépendant des appels réseau vérifie l'alimentation toutes les 15 secondes. La requête est libérée sur batterie, à la demande d'arrêt et à la sortie du superviseur, sur le même thread qui l'a acquise. L'écran reste libre de s'éteindre.

Aucun réglage permanent de veille, de couvercle, de bouton ou de batterie n'est modifié. La protection ne contourne pas une veille explicite et ne réveille pas une machine déjà endormie ou arrêtée. Un PC branché, déjà allumé et au couvercle ouvert reste nécessaire.

Le bilan local signale désormais les créneaux retardés, le retard maximal, l'état de la protection et un statut invalide, absent après installation, périmé ou en erreur. La protection et les diagnostics ne changent ni les signaux, ni les frais, ni les quantités, ni les fills ; les rattrapages shadow restent identifiés dans le résultat global et exclus des séances entièrement prospectives.

## Validation

Les tests reproduisent les huit rattrapages et l'échec de la protection nocturne avant correctif, puis vérifient l'alimentation AC/batterie/inconnue, l'indépendance des attentes API, la libération sur arrêt, le même thread pour acquisition/libération, les erreurs récupérables, les limites de calendrier et les statuts de suivi invalides. La preuve de déploiement et le résultat de la suite complète sont enregistrés dans [sleep_fix_2026-10-24.json](sleep_fix_2026-10-24.json).

La référence prospective du 21 octobre et les écritures existantes sont conservées. La séance du 21 octobre reste incomplète. Le correctif nécessite l'observation de prochaines séances pour confirmer la couverture ; il ne prouve aucun avantage financier.

Source technique : [Microsoft — SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
