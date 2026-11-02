# Tâche 0 — Replay statistique QQQ et rapprochement opérationnel

**Livraison pour validation utilisateur, 1er novembre 2026.** L’infrastructure GitHub Actions est publiée, mais le calcul statistique est volontairement désactivé : il commencera seulement après la règle d’arrêt de tâche 7 et sa validation. **Zéro séance du nouveau ledger statistique à ce stade.** Les résultats déjà vus depuis le 21 octobre restent anciens et séparés.

## Périmètre livré

| Élément | Résultat |
|---|---|
| Modèle | Noise Area et ORB au commit `f7ed9515b97644102ef674315c6af46e6fce8988`, fichiers Python hachés et extraits de Git |
| Économie | Deux comptes nouveaux de 100 000 USD, coûts figés actuels, plafonds Noise 4x / ORB 1x |
| Calendrier | XNYS, America/New_York, jours fériés, DST, demi-séances, clôture + 17 minutes |
| Planification | GitHub Actions public, 17:23 et 18:23 New York en semaine ; aucun replay Windows installé |
| Causalité | Indicateurs calculés sur préfixes fermés ; entrée selon les moteurs figés ; aucune première observation ORB à la clôture |
| Données | QQQ SIP 1 minute raw, warmup Noise antérieur, dividende ex-date, captures et empreintes immuables |
| Exhaustivité | Dates non résolues et en attente conservées ; rattrapages distingués des captures ponctuelles |
| Persistance | SQLite transactionnel, comptes indépendants, checkpoint authentifié/chiffré, reprise idempotente |
| Sécurité d’usage | GET de données autorisé exclusivement ; aucun broker/ordre, ni lecture des clés locales |
| Opérationnel | Lecteur SQLite en lecture seule, ledger distinct, sous-ensemble qualifié, comparaison des écarts disponibles |

Les détails, commandes et limites figurent dans [README.md](README.md) et [PROTOCOL.md](PROTOCOL.md). Le [pré-enregistrement](PREREGISTRATION.md) a été poussé avant les nouveaux calculs. Les commits `47cf1bf` puis `596885d` ont fixé le protocole et la clarification utilisateur avant les tests de performance synthétiques. Le workflow a été publié dans `a70df6f` avant sa première exécution cloud.

## Preuves et vérifications

Le premier [run GitHub Actions 41364142893](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41364142893) a exécuté avec succès 37 tests Linux et un vrai cycle d’upload/téléchargement/déchiffrement d’un artefact synthétique. Le job statistique y est bien désactivé. La livraison finale a ensuite réussi **55 tests locaux et 55 tests Linux** dans le [run 41369260668](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41369260668), avec un nouveau cycle de chiffrement vérifié et le job statistique toujours désactivé. Les preuves et empreintes sont consignées dans [final_checks.json](validation/final_checks.json).

Le [contrôle technique sur archive SIP](validation/offline_check.json) du 16 octobre 2026 donne : 12 décisions Noise, 2 fills, écart de P&L par rapport à l’étude publiée **0 USD** ; 1 trade ORB, écarts de prix d’entrée/sortie, commission, emprunt et P&L **0** par rapport au chemin figé. Aucun appel fournisseur ou ordre. Cette séance déjà connue ne compte jamais comme prospective.

Une collecte locale réelle a lu 13 observations bot/date anciennes sans erreur, dont **0 séance Noise qualifiée et 1 séance ORB qualifiée**. Aucun rapprochement avec un nouveau replay statistique n’existe encore. Le compagnon local est livré et testé ; son appel automatique par le suivi sera activé avec la règle 7, sans installer de replay Windows. Le fichier détaillé reste dans le runtime local ignoré par Git ; ni les bases live ni leurs comptes n’ont été modifiés. Ces nombres décrivent la couverture opérationnelle disponible, pas une nouvelle preuve de rentabilité.

Une revue indépendante a contrôlé les moteurs, les préfixes, les checkpoints et le rapprochement. Les corrections issues de cette revue préservent les frais/positions connus après un échec de données et leur provenance, empêchent le retour à un ancien checkpoint, refusent les writers dans le mauvais ordre, normalisent les heures comparées et distinguent les horloges différées. La synthèse de revue est conservée dans `validation/review.json`.

## Limites assumées

Le replay est hors-échantillon pour la **politique figée**, à partir de sa future date de départ. Il ne prouve ni ponctualité live, ni fills réalisables chez un courtier. Des barres SIP archivées peuvent être révisées. L’archive historique Noise live ne permet pas une certification de tous ses prix d’entrée. Le diagnostic à capital égal reste conditionnel aux signaux et prix du replay ; il ne remplace pas une reconstruction indépendante des entrées live.

GitHub peut retarder ses jobs. Une absence du laptop ne bloque pas le futur ledger statistique, mais retarde le rapprochement local. La persistance utilise des artefacts de rétention 30 jours, limite chiffrée 4 MiB par checkpoint ; une perte du dernier état attendu bloque la reprise sans reset silencieux. Les quotas de stockage partagés restent à vérifier à l’activation. Aucun achat ou budget payant n’a été créé.

## Décision attendue

Valider cette tâche 0, puis autoriser la **tâche 7 en priorité avant activation**. Elle calculera les bandes 20/60 séances sur le backtest courant figé, avec les mêmes coûts, fixera p5, drawdown 1,5x et le seuil de parité, et publiera sa règle avant la première date comptée. Les clés GitHub Secrets et l’initialisation viendront après cette validation technique et ce pré-enregistrement. Une future calibration des frais sera une autre version, sans réécriture de celle-ci.

Les tâches 1–5 et 9–11 ne sont pas exécutées dans cette livraison. Une partie de la tâche 8 est intégrée à l’infrastructure commune et sera documentée dans son propre rapport. Aucun nouveau bot, nouvel alpha ou passage au réel n’est lancé.
