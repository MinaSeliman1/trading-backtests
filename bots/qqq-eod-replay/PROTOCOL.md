# Journaux statistique et opérationnel

Le protocole autoritatif préenregistré est [PREREGISTRATION.md](PREREGISTRATION.md), les empreintes [ENGINE_LOCK.json](ENGINE_LOCK.json).

Le ledger **statistique** rejoue toutes les séances à partir de la première séance après le commit de la règle d’arrêt validée, avec le code/SHA publiés avant chaque date. Une donnée indisponible reste nonrésolue ; le rattrapage n’efface pas les pertes. Les coûts et politiques sont identiques au modèle figé. Les séances déjà vues depuis le21octobre sont séparées.

Ce ledger est hors-échantillon **pour la politique de trading figée** : les prix de ces dates n’étaient pas disponibles lors du préenregistrement, et aucune règle n’est choisie après leurs résultats. Le replay des préfixes n’utilise jamais une bougie future pour décider. Il reste une simulation sur barres archivées, éventuellement révisées, pas une validation de fills réels.

Le ledger **opérationnel** décrit le processus intraday existant. Ses séances qualifiées indiquent ponctualité, continuité et absence de lacunes selon ses critères ; les événements nonqualifiés restent conservés dans ses journaux. Un replay calculé après la clôture ne prouve ni disponibilité intraday, ni latence réseau, ni exécution chez le courtier : il n’est pas hors-échantillon pour cette exploitation.

Comparer les deux nécessite même capital initial de séance, code et prix ; toute différence est documentée et classée, non effacée. Les archives/live sont lus en lecture seule. GitHubActions est la cible d’exécution indépendante du laptop ; les barres et états dans les artefacts publics sont chiffrés et les clés restent dans GitHubSecrets.

**Activation de tâche 8 effectuée**, cohorte du 2 novembre 2026. Une nouvelle version des coûts imposera un nouveau préenregistrement et sa propre règle d’arrêt.

La tâche7 a publié [les règles d’arrêt](REPORT_TASK_7.md), figées dans rules/v1/RULE.json. La première date suit strictement le commit numérique et figure dans rules/v1/REGISTRATION.json. Les états prospectifs incluent désormais les marques de risque compatibles avec l’historique. Activation, secrets et amorçage ont été vérifiés en tâche 8 ; aucun seuil de cette nouvelle cohorte ne s’applique rétroactivement aux comptes opérationnels anciens.

## Activation de tâche8

Le suivi statistique est actif à partir de la cohorte du 2 novembre 2026, indépendant du laptop. Voir DEPLOYMENT.md et REPORT_TASK_8.md. Les SHA stratégiques et la règle7 restent inchangés ; le worker validé de déploiement est `2286aca61f4bf3636cada8e1234709cb8beafb77`, publié avant cette date. Le ledger opérationnel canonique est une vue des dernières observations qualifiées, filtrée sur cette même cohorte ; rejets et anciennes observations restent archivés à part. Il ne constitue pas un portefeuille continu observé lorsque la couverture est lacunaire. Le replay est hors-échantillon pour la politique figée car les prix futurs n’étaient pas disponibles lors de sa publication ; il ne teste pas la disponibilité réseau intraday, la file d’ordres ni les fills du courtier.
