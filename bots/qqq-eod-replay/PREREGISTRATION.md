# Pré-enregistrement : replay QQQ de fin de journée, tâche 0

Date locale : **31 octobre 2026, America/New_York**. Ce document, la demande REQUEST.md et les empreintes ENGINE_LOCK.json sont committés et publiés avant tout nouveau P&L de ce projet. Première séance statistique : **première séance XNYS strictement après la date locale du commit de la règle d’arrêt validée**, au plus tôt le2novembre2026. Activation désactivée jusque-là. Les anciens résultats ne sont ni effacés ni réévalués.

## Règles et population

Code des deux bots au commit f7ed9515b97644102ef674315c6af46e6fce8988, tous modules Python hachés. Déploiement dans une copie du paquet committé ; vérification à chaque lancement, refus d'une modification. Deux comptes nouveaux distincts de **100000USD**, sans reset/transfert des comptes live.

Noise Area : 14/14, décisions30minutes, cible2%, plafond4x, signalcombined et dividendeex-date. Utiliser Controller/Store existants en shadow. ORB : plage5minutes, risque1%, plafond1x, objectif10R, stopprioritaire ; utiliser core.advance/trade_path existants. Horloge et préfixes avancés causalement, jamais premier appelORB à la clôture qui créerait un late_start.

Coûts inchangés : commission0,0035USD/action/côté minimum0,35USD/ordre ; friction0,01USD/action/côté ; empruntshort1%/360 minimumunjour. Leur calibration relève de la tâche1. Infrastructure de suivi, sans nouvelle hypothèse d'alpha ni nouveaux témoins/Holm pour repêcher un ancien verdict. Les nouvelles études suivent les garde-fous de REQUEST.md.

## Sources et qualité

Alpaca QQQ SIP 1Min raw uniquement, dividendeex-date. Transport GET de données seulement : aucun compte/broker/ordre/POST. CoffreWindows via mécanisme existant, clés en mémoire seulement, jamais dans chat/log/Git. Métadonnées d'erreur type/code seulement, aucun texte API sensible.

UTC stocké, America/New_York et calendrierXNYS pour les fenêtres, demi-séances et DST. WarmupNoise100jours calendaires maximum, strictement avant la séance ; pas de prix du lendemain. Après clôture+17minutes, conserver première capture datée, SHA, warmup et dividende. Captures numérotées append-only ; un retry/révision ne remplace jamais un fichier ancien.

Lacunes : comportement des moteurs gelés, pas de prix inventé ni changement complete_days (tâche1 séparée). Une issue inconnue n'est ni un zéro ni un no-trade. Frais/position connus conservés, compte concerné bloqué tant que non résolu ; autre compte indépendant.

## Journal et rapprochement

Runtime séparé ignoré parGit, ledger transactionnel idempotent bot/date et verrou. Relancer ne double aucun trade/frais. Enregistrer décisions, fills/trades, coûts, P&L, capital, horloge logique ET vrai instant d'évaluation. Jamais présenter les temps internes du replay comme des observations live ponctuelles.

Séances après pré-enregistrement : première capture avant ouvertureNYSE suivante = EODponctuel ; plus tard = rattrapagepréenregistré. Comptes globaux conservés et sous-ensembles séparés sans retirer les pertes. Avant2novembre : diagnostic rétrospectif seulement, jamais prospectif.

Journaux live lus en SQLite modelectureseule. Comparaison supplémentaire avec leur capital avant séance quand connu et plat au départ : pas de comparaison de quantités issues de capitaux différents. Chaque écart est enregistré comme anomalie à qualifier : couverture/reprise, étatinitial, révisionprix ou inexpliqué. Même capital/données/code et résultats différents = bugcandidat ; absence de live = noncomparable, pas accord. Comparer les barresORB archivées ; sans archive de prixNoise complète, une révision fournisseur ne peut pas être exclue.

## Planification et revue

Exécuteur confirmé : **GitHub Actions**, dépôt public et runner standard gratuit. Déclenchements lundi-vendredi à **17:23 et18:23 America/New_York** (second passage idempotent pour reprise), timezoneIANA. Le programme recalcule les échéances réelles par calendrier après clôture+17minutes et rattrape toutes les séances manquantes. Le cron peut être retardé ou désactivé après60jours sans activité ; ce n’est pas une promesse d’exécution intraday. Secrets uniquement GitHubSecrets ; routes GETdonnées seulement. Aucun jobWindows supplémentaire, arrêt/redémarrage ou changement des deux tâches live.

Les états persistants contenant les barres et journaux seront chiffrés avant tout artefact public, avec clé distincte dans GitHubSecrets. Pas de publication d’archives brutes ni de secrets. Les rapports de synthèse ne contiennent que métriques de simulation et empreintes. Aucun transfert de clés versGitHub tant que le workflow concret n’a pas été vérifié.

La règle d’arrêt7 est calibrée sur le **backtest actuel verrouillé, même SHA et mêmes coûts**. Une calibration de coûts en tâche1 créera une nouvelle version et sa propre règle ; aucune modification de cette version. Les séances déjà vues depuis le21octobre restent hors de ce nouveau ledger statistique, rapportées à part.

Journal statistique : toutes les séances enregistrées après activation, même si rejouées tard, avec leur SHA publié avant la date de séance ; issue inconnue conservée comme telle. Journal opérationnel distinct : mesures live, sous-ensemble qualifié, sans effacer ses autres événements. Hors-échantillon pour la politique figée, pas preuve d’exploitation intraday. Premier bilan commun après20séances futures résolues parbot, avec captures ponctuelles, rattrapages et lacunes séparés. Seuil de revue, pas preuve de rentabilité ni passage au réel ; aucune sélection/retouche à partir de ces20jours.

Tests avant activation : préfixescausaux, parité moteurs/coûts, gaps/inconnus, capital, idempotence, week-end/demi-séance/DST, refus datesfutures, captures immuables, refusPOST/broker. Une séance historique peut valider techniquement l'intégration après publication de ce protocole, hors compteprospectif. Vérifier installation et prochaine échéance sans prétendre le premier lundi déjà observé.

Ajout utilisateur : **aucune activation du nouveau suivi avant résolution de la priorité et validation du pré-enregistrement d’arrêt de tâche7**. Les anciens bots continuent en simulation opérationnelle. Le début est dérivé du commit de la règle d’arrêt, pas d’une date choisie après performances. Aucun résultat antérieur à ce début n’est requalifié prospectif. Le code exécuté et ses SHA doivent être publiés avant la date de la séance. Publier le rapport de tâche0, attendre le feu vert avant tâche2 ou tâche7 selon la priorité confirmée. Les tâches1–5 et7–11 restent distinctes, chacune avec rapport et feuvert.

## Révision utilisateur avant tout P&L

GitHubActions confirmé pour tâche0 ; règle7 sur modèle/frais actuels ; première séance après son commit. La publication initiale47cf1bf n’a été suivie d’aucun calcul de P&L : seulement neuf tests de calendrier, validation de données, transport et immutabilité. Cette précision est donc intégrée avant résultats.
