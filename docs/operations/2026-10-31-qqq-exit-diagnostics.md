# Relance des deux simulations QQQ et diagnostic des sorties code 1

Le 31 octobre, les deux bots ont été relancés avec l'autorisation explicite de l'utilisateur, y compris après 09:30. **Noise Area et ORB tournent en simulation shadow, avec SIP différé de 16 minutes.** Le défaut confirmé et corrigé est l'absence de trace des exceptions fatales sous `pythonw`. La cause précise des deux anciennes sorties au code 1 reste inconnue ; aucun diagnostic OneDrive, mémoire ou trading n'est présenté comme démontré.

## Ce que les anciennes traces permettent de conclure

Les deux moteurs ont cessé d'actualiser leurs statuts vers 14:35:45, heure Toronto/New York, puis les tâches étaient `Ready`, résultat 1. Aucun STOP opérateur, aucune pause, position ou attente locale ne bloquait la reprise. Aucun nouvel événement de veille, crash Application 1000/1001 ou épuisement mémoire System 2004 n'a été trouvé dans la fenêtre contrôlée. L'historique opérationnel du Planificateur était désactivé et les logs des bots ne contenaient aucune exception finale.

Le code 1 indique un échec du processus, sans en identifier la cause. Les anciens points d'entrée sans console ne capturaient pas une exception échappant à la supervision. De plus, Noise Area absorbait un `RuntimeError` dans `main` en retournant simplement 1. Cela explique pourquoi l'erreur n'était pas exploitable après coup, sans démontrer quelle erreur a déclenché les deux arrêts. Les contrats de tests consultés simulent les tâches et n'arrêtent pas les deux tâches installées.

## Correction de la journalisation

Les deux bootstraps chargent maintenant leur moteur à l'intérieur d'un garde standard Python. Une exception fatale ou un retour non nul enregistre seulement la date UTC, le PID, le composant, le code de sortie, le type d'erreur, errno/winerror et les douze dernières positions fichier/fonction/ligne. La capture spécifique du `RuntimeError` Noise Area est conservée et ne devient pas une simple sortie générique.

Le fichier principal est `runtime/windows/last_fatal.json` du bot concerné. Si son écriture échoue, un repli se fait hors OneDrive sous `%LOCALAPPDATA%/TradingBacktests/Diagnostics/noise/last_fatal.json` ou `orb/last_fatal.json`. L'écriture est atomique ; un échec des deux destinations conserve le code d'échec original. Les messages d'exception, lignes de source, variables locales, arguments et variables d'environnement ne sont jamais sérialisés par ce garde. Les anciennes traces applicatives ne sont pas supprimées.

Le lecteur doit comparer la date et le PID à ceux du processus actuel : un ancien fichier d'échec peut rester présent après une reprise normale. Une terminaison forcée, un crash natif, un échec avant l'import du garde ou deux stockages indisponibles peuvent encore empêcher toute trace. Aucun défaut n'a été injecté dans les moteurs actifs : les essais d'erreur utilisent des fonctions simulées et des dossiers temporaires.

## Remise en marche et observations

| Événement | Noise Area | ORB |
|---|---|---|
| Première relance autorisée | 31 octobre 14:53:42 | 31 octobre 14:53:44 |
| Rechargement gracieux du diagnostic | 15:07:15 | 15:06:50 |
| PID actif vérifié | 27992 | 19944 |
| État au contrôle vers 15:11 | waiting_for_regular_session | waiting_non_session |
| Âge du statut au contrôle | 0,23 s | 1,82 s |
| Protection secteur | active, AC | active, AC |

Le rechargement a été fait samedi hors séance, comptes à plat et sans pause, par arrêt gracieux puis relance des seules commandes shadow/SIP déjà installées. Chaque arrêt gracieux a retourné 0. Seuls les drapeaux de maintenance créés atomiquement par cette opération ont été retirés, avec vérification de leur marqueur ; aucun STOP opérateur n'a été contourné et aucun processus n'a été tué.

ORB a rencontré un `PermissionError` de démarrage à 15:06:51 puis a repris automatiquement à 15:07:51 après sa temporisation de 60 secondes, avec le même PID. Cette erreur transitoire n'a pas terminé le processus et n'établit pas la cause des anciens codes 1. Au contrôle, les deux tâches sont `Running` ; le résultat 267009, soit 0x41301, correspond à une tâche encore en cours d'exécution.

## Intégrité et validation

Les lectures SQLite ont été faites en mode `ro` et `query_only`. Les empreintes de compte et configuration, nombres d'enregistrements et références avant/après sont identiques. Il n'est pas affirmé que chaque octet SQLite est inchangé : ORB enregistre normalement ses reprises opérationnelles.

| Élément conservé | Noise Area | ORB |
|---|---:|---:|
| Solde simulé USD | 98 041,4235 | 99 188,18398333332 |
| Référence prospective | 21 octobre 2026 | 26 octobre 2026 |
| Position / attente / pause | aucune | aucune |
| Séances pleinement qualifiées | 0 | 1 |

**166 tests passent : 136 Noise Area et 30 ORB.** Une intégration native du coffre Windows est désélectionnée, sans rapport avec le changement ; aucun accès au coffre par les tests ou l'assistant. Les douze cas de diagnostic couvrent confidentialité, errno/positions, repli hors OneDrive, double échec d'écriture, sortie normale, SystemExit, absence de console, RuntimeError absorbé, deux vrais bootstraps avec moteur simulé et les deux formes de `--runtime` avec dernière valeur prioritaire. Les trois derniers cas ont d'abord reproduit deux échecs, puis sont verts après correction. La revue indépendante a rejoué 20 tests diagnostic/supervision ; aucun problème important restant.

Aucune stratégie, règle d'exécution, taille, friction, commission, transaction ni référence n'a été remise à zéro. Les moteurs lisent leurs identifiants par leur mécanisme Windows normal ; l'assistant n'a ni lu ni affiché les clés et aucun ordre broker n'est envoyé.

## Prochaine séance et suivi

Le réglage secteur durable reste RTCWAKE AC1, STANDBYIDLE AC0, HIBERNATEIDLE AC0, couvercle AC0 ; les réglages batterie sont conservés. Le réveil commun reste prévu **lundi 2 novembre à 09:10 Eastern, UTC−05:00**, sans modifier les commandes ou horaires installés. Le PC doit rester branché, avec session ouverte. Une veille manuelle, un arrêt, un changement de plan, une panne réseau ou de données restent des limites de couverture.

Le suivi a été mis à jour et relu après sauvegarde : la relance du 31 n'est plus annoncée en attente. Cette autorisation ponctuelle hors créneau ne change pas la règle ordinaire du heartbeat, qui ne relance automatiquement une tâche arrêtée qu'avant 09:30 et respecte STOP, désactivation, pauses, positions et attentes. Les diagnostics d'échec peuvent être lus sans coffre ni API. Le bilan commun reste prévu après 20 séances entièrement qualifiées par bot ; aucun rattrapage n'est reclassé et aucun passage en réel n'est autorisé.

La santé observée samedi ne valide pas la ponctualité de lundi et ne constitue pas une séance de test complète. La cause historique demeure indéterminée ; la prochaine sortie Python capturable disposera désormais d'une trace exploitable.

[Preuve détaillée](../../bots/qqq-noise-area/validation/exit_diagnostics_2026-10-31.json) · [Diagnostic énergie précédent](2026-10-31-qqq-ac-wake-availability.md).
