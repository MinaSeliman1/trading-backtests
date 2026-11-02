# Alertes gratuites QQQ — simulation uniquement

Voir [le rapport de tâche 9](REPORT_TASK_9.md) pour les preuves et le statut réel de réception. Les stratégies, coûts, règles d’arrêt, comptes et processus de trading existants ne sont pas modifiés.

## Fonctionnement

Un watchdog Windows distinct lit les statuts et SQLite en `mode=ro`, toutes les30secondes. Il contrôle PID/statut/configuration/STOP/positions non résolues en permanence ; les échéances de trading suivent XNYS, demi-séances et America/New_York. Les décisions Noise sont jugées sur wall-clock−16minutes avec tolérance120secondes ; ORB exige la prise en charge avant09:37logique ou un non-trade conforme. Les erreurs de lecture restent des erreurs, jamais un état sain. Les lacunes anciennes ne deviennent pas prospectives.

Les messages techniques sont génériques : aucun compte, solde, P&L, quantité, clé, adresse d’abonnement ou trace d’exception. Un incident inchangé ne répète pas ses notifications ; le retour sain d’un défaut effectivement résolu peut notifier une fois. L’expiration d’une échéance historique n’annonce pas de guérison.

La boîte d’envoi locale conserve les événements avant l’envoi et les acquitte seulement après acceptation par ntfy. Les alertes locales ont un plafond30par jour UTC ; les événements restants attendent. Une réponse réseau ambiguë peut produire un doublon, aucun système distant n’offrant ici une garantie exactly-once. Les erreurs ne stoppent, ne lancent ni ne liquident aucun bot.

## Relais externe et cloud

Pendant09:10 à clôture+20minutes XNYS, un rappel ntfy est repoussé toutes les5minutes, avec échéance à12minutes (plafonnée près de la fin de fenêtre). S’il n’est plus repoussé, ntfy alerte même si le PC/réseau/watchdog est indisponible. Hors fenêtre, le prochain XNYS09:20 est armé s’il est à moins de3jours ; au-delà, le rappel est retiré et le contrôle quotidien cloud reprend la détection. Un démarrage/reprise demande le PC et une session Windows ouverte.

Le workflow cloud déclenche **un message de vie quotidien à09:20 NewYork**, jours sans séance explicitement indiqués. Il lit seulement le reçu technique récent, jamais le laptop directement. Le temps d’attente GitHub et la livraison mobile peuvent retarder ce message. Les achèvements du replay EOD déclenchent aussi le contrôle d’échec, de date non résolue et de STOP statistique.

La boîte d’envoi cloud séparée est conservée dans de petits artefacts Actions30jours, restaurés avant envoi pour dédupliquer les incidents persistants. Aucun état économique n’est stocké dans cette boîte. Les runs sont sérialisés par `queue:max` (100en attente maximum). Une longue interruption hors rétention exige une revue de l’état des notifications, sans toucher aux ledgers de trading.

## Abonnement et confidentialité

ntfy.sh gratuit : deux sujets aléatoires de192bits, un pour les alertes, un pour le contrôle technique cloud. Les adresses sont dans un emplacement Windows CredentialManager propre au notificateur et dans `QQQ_ALERT_TOPIC`/`QQQ_HEALTH_TOPIC` de GitHub Actions Secrets. Le notificateur n’a besoin ni des clés PAPER ni de la clé chiffrant le ledger statistique.

Les sujets gratuits ne sont pas des canaux privés authentifiés : quiconque connaît leur adresse peut lire/publier. Garder cette adresse hors du chat/Git et n’envoyer que les messages génériques prévus. Le serveur conserve normalement les messages12heures. Les limitations gratuites et la livraison mobile n’autorisent aucune promesse de disponibilité absolue. [Documentation ntfy](https://docs.ntfy.sh/publish/).

Ouvrir la fenêtre locale : `C:\Python314\pythonw.exe scripts/show_subscription.py`. Installer ntfy sur le téléphone, ajouter le serveur `https://ntfy.sh` et le sujet affiché, autoriser les notifications puis envoyer le TEST. Sur Android, activer Instant delivery. Le QR est facultatif ; le sujet copiable fonctionne sans qrcode/Pillow. Le bouton de réception doit être cliqué par l’utilisateur après réception réelle, jamais par un outil automatisé. Accepter côté serveur n’est pas prouver la réception sur téléphone.

## Commandes locales

```powershell
C:\Python314\python.exe scripts/watch.py --check
Get-ScheduledTask -TaskName TradingBacktests-QQQ-Simulation-Alerts
Get-Content runtime/status.json
Start-ScheduledTask -TaskName TradingBacktests-QQQ-Simulation-Alerts
```

Le diagnostic `--check` ne lit aucun coffre. Pour arrêter seulement les notifications locales, créer `runtime/STOP_ALERTS.flag` ; cela retire le rappel externe mais ne touche pas aux moteurs. Ne pas contourner un STOP de trading pour tester les alertes. Le redémarrage du notificateur ne supprime pas ce flag.

La tâche cachée démarre au logon, à09:05en semaine et possède un contrôle horaire/reprises limités. Elle est autorisée sur batterie pour pouvoir signaler la perte du secteur, sans empêcher la veille batterie. Les politiques d’alimentation des bots restent inchangées.

## Vérification

```text
python -m pip install -r bots/qqq-alerts/requirements.txt
python -m pytest bots/qqq-alerts/tests -q -p no:cacheprovider
```

Les tests utilisent des fixtures SQLite et sujets synthétiques, sans réseau ni identifiant réel. Le test natif de coffre Windows emploie un emplacement isolé supprimé ensuite. Le code cloud ne consomme que le workflow EOD de `main` du dépôt attendu, refuse les forks/autres branches et filtre les champs du résumé avant de construire les messages.
