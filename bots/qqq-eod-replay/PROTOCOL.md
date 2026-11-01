# Journaux statistique et opérationnel

Le protocole autoritatif préenregistré est [PREREGISTRATION.md](PREREGISTRATION.md), les empreintes [ENGINE_LOCK.json](ENGINE_LOCK.json).

Le ledger **statistique** rejoue toutes les séances à partir de la première séance après le commit de la règle d’arrêt validée, avec le code/SHA publiés avant chaque date. Une donnée indisponible reste nonrésolue ; le rattrapage n’efface pas les pertes. Les coûts et politiques sont identiques au modèle figé. Les séances déjà vues depuis le21octobre sont séparées.

Ce ledger est hors-échantillon **pour la politique de trading figée** : les prix de ces dates n’étaient pas disponibles lors du préenregistrement, et aucune règle n’est choisie après leurs résultats. Le replay des préfixes n’utilise jamais une bougie future pour décider. Il reste une simulation sur barres archivées, éventuellement révisées, pas une validation de fills réels.

Le ledger **opérationnel** décrit le processus intraday existant. Ses séances qualifiées indiquent ponctualité, continuité et absence de lacunes selon ses critères ; les événements nonqualifiés restent conservés dans ses journaux. Un replay calculé après la clôture ne prouve ni disponibilité intraday, ni latence réseau, ni exécution chez le courtier : il n’est pas hors-échantillon pour cette exploitation.

Comparer les deux nécessite même capital initial de séance, code et prix ; toute différence est documentée et classée, non effacée. Les archives/live sont lus en lecture seule. GitHubActions est la cible d’exécution indépendante du laptop ; les barres et états dans les artefacts publics sont chiffrés et les clés restent dans GitHubSecrets.

**Activation actuellement désactivée**, en attente de la livraison/validation de tâche0 puis de la règle7. Une nouvelle version des coûts imposera un nouveau préenregistrement et sa propre règle d’arrêt.
