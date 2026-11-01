# Pré-enregistrement : replay QQQ de fin de journée, tâche 0

Date locale : **31 octobre 2026, America/New_York**. Ce document, la demande REQUEST.md et les empreintes ENGINE_LOCK.json sont committés et publiés avant tout nouveau P&L de ce projet. Première séance future : **2 novembre 2026**. Les anciens résultats ne sont ni effacés ni réévalués.

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

Exécuteur séparé : choix GitHub Actions ou job Windows en attente de la précision demandée après ajout de la tâche8. Échéances calculées par calendrierNewYork : après clôture+17minutes, rattrapage de toutes les séances nontraitées, verrou et relances. GitHubActions standard dans dépôtpublic est l’option gratuite demandée pour la cible finale ; retards de cron possibles. Un job local dépend du PC/session/réseau. Aucun arrêt/redémarrage ou modification des deux tâches live. Le paquet final et son calendrier seront committés avant activation, sans modifier les règles de trading.

Journal statistique : toutes les séances enregistrées après activation, même si rejouées tard, avec leur SHA publié avant la date de séance ; issue inconnue conservée comme telle. Journal opérationnel distinct : mesures live, sous-ensemble qualifié, sans effacer ses autres événements. Hors-échantillon pour la politique figée, pas preuve d’exploitation intraday. Premier bilan commun après20séances futures résolues parbot, avec captures ponctuelles, rattrapages et lacunes séparés. Seuil de revue, pas preuve de rentabilité ni passage au réel ; aucune sélection/retouche à partir de ces20jours.

Tests avant activation : préfixescausaux, parité moteurs/coûts, gaps/inconnus, capital, idempotence, week-end/demi-séance/DST, refus datesfutures, captures immuables, refusPOST/broker. Une séance historique peut valider techniquement l'intégration après publication de ce protocole, hors compteprospectif. Vérifier installation et prochaine échéance sans prétendre le premier lundi déjà observé.

Ajout utilisateur : **aucune activation du nouveau suivi avant résolution de la priorité et validation du pré-enregistrement d’arrêt de tâche7**. Les anciens bots continuent en simulation opérationnelle. Le 2novembre est la première date possible, pas une promesse d’activation ; une activation plus tardive commence à une séance future fixée avant son ouverture, sans requalifier le passé. Publier le rapport de tâche0, attendre le feu vert avant tâche2 ou tâche7 selon la priorité confirmée. Les tâches1–5 et7–11 restent distinctes, chacune avec rapport et feuvert.
