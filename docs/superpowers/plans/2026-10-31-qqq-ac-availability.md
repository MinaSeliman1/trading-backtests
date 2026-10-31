# Correction disponibilité secteur des deux simulations QQQ

Mandat : diagnostiquer le réveil manqué du30octobre et renforcer la disponibilité sur secteur, toujours shadow SIP16minutes. Base3c285e4e12ce200cac1e33dee94808dae7174e43. Choix natif déjà demandé par le contexte : correctif local et vérification, aucune réinitialisation financière.

Preuve : débranchement29/10à13:29:36, veille bouton/couvercle13:29:49, puisS4à16:30. KernelPower107 annonce ProgrammedWakeTimeAc30/10à13:09:30Z, ProgrammedWakeTimeDc absent ; prochainAcOnline=true31/10à14:00. Historique TaskScheduler désactivé. Minuterie secteur correctement armée ; batterie et/ou disponibilité matérielle constituent la limite, pas un décalage de fuseau. L'état exact de la prise pendant le sommeil n'est pas observable rétrospectivement.

Correction ciblée : nouveau configure-ac-availability.ps1, audit par défaut, -Apply explicite. Plan actif uniquement, RTCWAKE AC1, STANDBYIDLE AC0, HIBERNATEIDLE AC0. Lire les deux derniers indices de chaque requête, après les bornes numériques ; sauvegarde initiale parGUID, idempotence, rollback AC si échec partiel. Aucun changement DC, écran, couvercle, boutons, tâche principale, clé, SQLite ou paramètres.

- [x] Diagnostiquer événements, configuration, limites et disponibilité matérielle.
- [x] Tests rouges puis verts : AC seul, lecture seule, parsing métadonnées, idempotence/sauvegarde, échec lecture, rollback.
- [x] Revue ciblée et suites NoiseArea/ORB pertinentes ; conserver preuves de soldes/config/références.
- [x] Appliquer sur plan actif sans arrêter les moteurs ; vérifier AC/DC, lid0/1, tâche09:10Eastern et fraîcheur des deux.
- [x] Documenter cause/certitude/limites et publier correctif ; suivi prochain réveil réel sans le présenter comme déjà observé.

Une configuration et une action exécutée PC éveillé ne prouvent pas un réveil matériel depuisS3/S4. Aucun sommeil artificiel déclenché ; le premier créneau futur reste à observer. Sur secteur le PC ne se mettra plus automatiquement en veille/hibernation même si un superviseur manque ; une veille manuelle, arrêt, batterie ou panne réseau peut encore interrompre la couverture.

Résultat : politique native AC1/0/0 appliquée, DC0/600/10800 inchangés ;154tests ; revue proof-write red/green ; tâche awake résultat0 ; snapshots financiers identiques. Publication déclarée seulement après concordance de HEAD et des références distantes.

État final complémentaire : deux tâchesReady/code1 à14:42, cause nonétablie, politiqueACtoujoursvérifiée. Demande de relance native rejetée automatiquement hors fenêtreavant09:30 ; aucune relance exécutée. Demander autorisation explicite hors fenêtre ; ne pas présenter les moteurs comme actifs au rendu final.
