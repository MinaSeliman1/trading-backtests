# Tâche 9 — Alertes gratuites pour les deux simulations QQQ

Livraison du **2 novembre 2026, heure de New York**. Le watchdog Windows, les sujets ntfy et le workflow GitHub sont activés et vérifiés. Les preuves couvrent l’envoi réel, le rappel externe et la reprise de la boîte d’envoi cloud. **La réception sur téléphone reste à confirmer par l’utilisateur**, distinctement de l’acceptation par le serveur.

Code de livraison vérifié : `f78a980800b5a49377d55c4087d0288f6eaeb4a9`. Les compléments suivants ne modifient que les preuves et la documentation.

## Ce qui est installé

- Tâche cachée `TradingBacktests-QQQ-Simulation-Alerts`, processus distinct des deux moteurs, contrôle toutes les30secondes hors temps réseau. Démarrage au logon+10secondes, à09:05en semaine, reprise horaire et trois reprises sur échec espacées d’une minute. Le contrôle natif montre `Running`, statuts frais, aucun incident actif ni envoi en attente.
- **Message de vie quotidien : déclenchement GitHub à09:20 America/New_York**, y compris les jours sans séance, indiqués comme tels. Le message distingue contrôle technique récent sain, attention, non vérifié et hors séance ; il ne prétend pas qu’un téléphone a reçu le message.
- Alertes locales sur STOP, processus arrêté, statut ancien, erreur moteur/journal, configuration inattendue, décision absente ou tardive, données insuffisantes et position/ordre simulé non résolu.
- Alertes cloud après achèvement du replay : échec, résumé indisponible, dates non résolues et STOP statistique de la règle7. Les notifications ne changent pas cette règle et ne déverrouillent aucun STOP.

## Horloges et délais réels

PID, fraîcheur du statut, configuration, erreurs de lecture, pauses et positions non résolues sont surveillés aussi hors séance. Un bot arrêté ne devient pas sain simplement parce que la fenêtre d’observation vient de fermer.

Les créneaux suivent le calendrier XNYS, ses demi-séances et **America/New_York**, sans offset UTC fixe. Noise Area : horloge réelle moins16minutes, décisions de10:00à15:30logiques selon durée de séance, tolérance120secondes. ORB : prise en charge avant09:37logique, ou absence de signal conforme ; les démarrages tardifs et lacunes restent des incidents.

Un arrêt de processus connu peut être détecté au prochain passage nominal de30secondes ; un statut trop ancien est signalé après180secondes. L’appel réseau, le téléphone et GitHub ajoutent leur propre délai : **aucune garantie de livraison instantanée**. Le statut Noise n’expose pas chaque horodatage de barre : les erreurs moteur et les créneaux permettent de constater une indisponibilité, mais ne certifient pas minute par minute tout le flux.

## PC éteint, veille ou réseau coupé

Le PC ne peut pas envoyer un push pendant sa propre panne. Un rappel ntfy côté serveur est donc repoussé toutes les5minutes pendant la fenêtre09:10–clôture+20minutes, avec échéance à12minutes, plafonnée près de la fermeture. Si le PC, le réseau ou le watchdog cesse de répondre, ntfy livre ce rappel indépendamment de Codex et du PC.

Hors fenêtre, le prochain XNYS09:20 est armé lorsqu’il se trouve à moins de3jours. Au-delà de cette limite du service, le rappel est retiré ; le contrôle quotidien cloud constate ensuite un reçu absent. Le message distingue cette absence d’une panne démontrée d’un bot. La session Windows ouverte reste nécessaire au processus local.

## Déduplication, reprise et arrêt volontaire

La boîte d’envoi locale, dans son propre runtime, conserve les événements avant envoi. Un événement n’est acquitté qu’après acceptation ntfy. Un incident inchangé reste silencieux ; un contrôle positif peut notifier un retour sain. L’expiration d’une anomalie historique liée au calendrier n’annonce pas sa résolution.

Le cloud restaure sa propre boîte d’envoi depuis un petit artefact Actions : un STOP ou état non résolu persistant n’est pas republié à chaque run. Les événements sont sérialisés par `queue:max`,100en attente maximum. Les artefacts de notification, conservés30jours et validés à256KiB maximum en lecture, contiennent seulement codes techniques et dates, **aucun état économique ni adresse ntfy**.

Le plafond local est30alertes/jour UTC ; les événements restants attendent. Les rappels et reçus techniques sont espacés pour rester sous la limite gratuite nominale en fonctionnement normal. Une réponse réseau ambiguë peut encore entraîner un doublon ; une interruption au-delà de la rétention nécessite une revue du suivi, jamais une remise à zéro d’un ledger de trading.

Le fichier `runtime/STOP_ALERTS.flag` arrête uniquement ce notificateur et retire son rappel externe. Il ne touche pas aux deux simulations. Leur STOP de trading n’est jamais contourné.

## Secrets, confidentialité et gratuité

Deux sujets distincts de192bits aléatoires : abonnement utilisateur et reçu technique cloud. Ils sont protégés dans un nouvel emplacement Windows CredentialManager et dans **`QQQ_ALERT_TOPIC` / `QQQ_HEALTH_TOPIC`**, GitHub Actions Secrets. Le notificateur ne lit ni les clés PAPER ni la clé chiffrant le ledger statistique. Les transferts Secrets passent par stdin, sans valeur dans arguments, chat, Git ou logs.

Les sujets gratuits ntfy.sh ne sont pas des canaux privés authentifiés : **quiconque connaît l’adresse peut lire et publier**. Elle reste hors du dépôt et des messages. Aucun identifiant de compte, solde, P&L, quantité, clé, URL d’abonnement ou trace brute n’est envoyé. Le transport refuse les redirections et vise uniquement HTTPS ntfy.sh. [Publication et sujets ntfy](https://docs.ntfy.sh/publish/).

Le service gratuit annonce250messages/jour et une conservation habituelle12heures ; le projet n’ajoute aucun abonnement, budget ou runner payant. Les restrictions mobiles et quotas peuvent retarder ou empêcher une livraison. Sur Android, activer Instant delivery ; sur iPhone, autoriser les notifications et vérifier le test réel. [Application mobile](https://docs.ntfy.sh/subscribe/phone/), [limites du service](https://docs.ntfy.sh/publish/#limitations).

## Validation

- **108 tests locaux réussis**, aucune erreur ni omission :25pour les alertes et83pour le suivi EOD existant, y compris deux tests de coffres Windows sur emplacements synthétiques isolés et nettoyés.
- Trois constats de revue indépendante ont été reproduits avant correction : fausse guérison à la fermeture, répétition des STOP cloud, dépendances QR imposées. Les tests couvrent leur correction, le démarrage sans PYTHONPATH hérité, les erreurs de lecture, les demi-séances, le changement d’heure, l’absence normale de signal et la persistance des notifications non livrées.
- **Test ntfy réel accepté**, remplacement d’un rappel programmé et annulation acceptés. Le reçu technique a été relu depuis le serveur. La première lecture immédiate a devancé l’écriture asynchrone du cache ; le contrôle borné suivant l’a retrouvé en0,71seconde. C’est une visibilité du cache, pas une preuve de réception mobile. [Cache asynchrone documenté](https://docs.ntfy.sh/config/#message-cache).
- [CI du code publié](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41393672249) : **24 tests réussis, un test Windows ignoré sur Linux**. [TEST cloud](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41393814871) : un message TEST accepté et boîte d’envoi sauvegardée. [Reprise EOD normale](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41393817769) réussie, puis [déclenchement automatique des alertes](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41393961301) réussi : état des notifications restauré depuis le run TEST, zéro message d’incident indu car le résumé est sain, zéro envoi en attente.
- Les deux tâches originales sont toujours `Running`. Aucun ancien moteur, coût, seuil, pause, compte, transaction ou référence prospective n’a été modifié. Le SHA-256 de la règle7 reste `3d19e338d9e0c3aea0df68f230d3386d1dc5b97161f1e3120cfa4aa2f10fa19f`.

Preuves sans secret : [task9_deployment.json](validation/task9_deployment.json). [Commandes et procédure](README.md). La fenêtre locale affiche le sujet copiable et un QR facultatif. Installer ntfy, s’abonner, envoyer le TEST puis confirmer sa réception dans cette fenêtre ou dans le chat, sans transmettre l’adresse.

**Point restant côté utilisateur : réception sur téléphone non confirmée à la rédaction.** L’acceptation serveur et le fonctionnement des émetteurs sont contrôlés séparément ; aucun test simulé n’est présenté comme une livraison mobile réelle. Aucune tâche10ou11 n’est lancée.
