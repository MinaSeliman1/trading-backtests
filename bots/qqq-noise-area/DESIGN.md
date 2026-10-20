# Bot QQQ Noise Area en simulation — conception du 20 octobre 2026

Demande : créer un bot de simulation Alpaca avec les paramètres figés de l'étude, coûts conservateurs, puis ajouter le code à trading-backtests. L'historique scientifique existant reste intact.

## Périmètre retenu

QQQ uniquement ; 14 observations passées à la même minute, volatilité de 14 rendements passés ddof=1, cible 2 % et plafond cible 4x, quantité entière fixée par séance, décisions toutes les 30 minutes depuis 09:30, stop bande/VWAP combiné, retournement après confirmation de fermeture, liquidation pendant la dernière minute régulière. Calendrier XNYS et comparaison avec l'horloge du courtier. Capital virtuel initial 100 000 USD, recomposé après coûts.

Trois approches ont été considérées : simple réexécution historique (insuffisante pour suivre les ordres), paper IEX gratuit (données différentes du backtest), paper SIP temps réel (même famille de données, sous réserve des droits du compte). La livraison retient un moteur commun avec **shadow SIP différé gratuit** par défaut, et un adaptateur **ordres Alpaca paper** qui exige explicitement un flux frais. IEX est un choix explicite, journalisé comme expérience distincte ; aucun remplacement silencieux de SIP.

Les coûts sont tenus dans un compte local séparé des résultats bruts du courtier : 0,0035 USD/action/côté, minimum 0,35 USD/ordre, buffer adverse supplémentaire de 0,01 USD/action/côté et emprunt SHORT supposé 1 % annuel, minimum un jour/360 par trade. Le spread peut déjà être présent dans le fill paper ; le cent ajouté est un stress conservateur, pas une mesure observée. Aucun abonnement ni transaction réelle n'est autorisé par ce bot ; endpoint de trading fixé à paper-api.alpaca.markets.

## Composants

- `qqq_paper/strategy.py` : calcul causal sur historique terminé et préfixe courant ; réutilisation du décideur figé de l'étude, contrôle de son hash.
- `qqq_paper/alpaca.py` : requêtes HTTP Market Data et compte paper seulement, refus des redirections, erreurs expurgées et pagination.
- `qqq_paper/ledger.py` : SQLite transactionnel, intentions persistées avant envoi, application idempotente des fills cumulés et frais par ordre, journaux.
- `qqq_paper/runner.py` : progression shadow/paper, rapprochement du compte, ordres séparés fermeture/ouverture, reprise prudente, fermeture prioritaire.
- `qqq_paper/__main__.py` : contrôle de connexion, boucle locale, secrets en mémoire, statut et arrêt.

## Exécution et limites

SIP différé : rejouer les décisions une fois les bougies disponibles, sans envoyer d'ordre. Paper : envoyer après réception de la minute terminée dans une fenêtre bornée de 20 secondes ; un fill réel simulé ne garantit pas l'open exact du backtest. Aucun rattrapage d'entrée tardive. Un trou détecté dans la séance suspend les nouvelles entrées et entraîne une tentative de fermeture ; contrairement au backtest, aucune connaissance d'une minute future manquante.

Un timeout d'envoi ne provoque aucun nouvel ordre aveugle : rechercher le client_order_id déjà persisté. Une position ou un ordre externe, un écart de quantité, une clé de compte différente ou un résultat d'ordre incertain suspend les nouvelles entrées. Les remplissages partiels sont comptabilisés sans duplication ; la fermeture de fin de séance reste prioritaire, et tout ordre non résolu est explicite dans le statut. Les données manquantes, le réseau et l'arrêt de l'ordinateur peuvent empêcher une fermeture : aucune garantie d'absence d'overnight n'est annoncée en fonctionnement réel.

Une seule instance par dossier d'état, compte paper dédié et initialement plat. Aucun service de démarrage automatique, aucune persistance des clés. L'activation connectée dépend des clés paper et des droits de flux, actuellement non présents dans l'environnement. Le code et les essais hors ligne peuvent être terminés avant cette activation.

### Décision après essai connecté

Le 20 octobre, le compte gratuit a permis la connexion paper et l'acquisition IEX, mais 14 des 15 dernières séances IEX avaient des minutes manquantes. Ce flux ne permet donc pas d'appliquer le filtre strict sans changer les règles. L'instance IEX a été suspendue puis arrêtée, sans fill et sans position. Le lancement gratuit retenu est finalement **shadow/SIP différé de 16 minutes**, sans ordre au courtier ; le contrôle d'historique rejette maintenant ces données incomplètes avant d'afficher un état opérationnel. Les ordres paper/SIP restent disponibles pour un compte disposant du flux temps réel. Aucun abonnement n'a été souscrit.

## Validation

Tests contrôlés d'abord, puis parité sur les acquisitions QQQ réelles archivées : indicateurs, horaires et objectifs de position contre les exports figés. Tests de coûts, fills partiels, restart, timeout ambigu, refus de l'endpoint réel, données périmées, demi-séances et clôture. Une revue indépendante précède la publication. Un contrôle de connexion ne vaut pas validation de marché ; les dates et fonctionnalités réellement exercées seront distinguées.
