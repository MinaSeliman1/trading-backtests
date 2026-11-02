# Replay QQQ de fin de journée

**Tâche 8 : suivi GitHub Actions actif, exclusivement en simulation, cohorte au 2 novembre 2026.** Voir le [rapport d’activation](REPORT_TASK_8.md), les [commandes d’exploitation](DEPLOYMENT.md) et la [règle d’arrêt figée](REPORT_TASK_7.md). Aucun résultat ancien ne devient prospectif. Les deux processus Windows existants restent des simulations opérationnelles shadow/SIP différé de 16 minutes.

Voir [le rapport](REPORT_TASK_0.md), [le pré-enregistrement](PREREGISTRATION.md), [le protocole](PROTOCOL.md) et [les empreintes](ENGINE_LOCK.json). Le code stratégique est celui de `f7ed9515b97644102ef674315c6af46e6fce8988`, extrait depuis Git et vérifié avant import. Les adaptateurs ne modifient aucun ancien moteur, coût, signal ou journal.

## Fonctionnement

Le [workflow](../../.github/workflows/qqq-eod-replay.yml) s’exécute sur runner Ubuntu standard du dépôt public à 17:23 et 18:23, America/New_York, du lundi au vendredi. Il recalcule les véritables séances XNYS, clôtures anticipées et changements d’heure, puis traite les dates échues depuis clôture + 17 minutes. Deux comptes virtuels distincts commencent à 100 000 USD. Le second passage est idempotent. Un maximum de 20 dates par compte et passage borne le temps de travail ; le prochain passage poursuit le rattrapage.

Noise Area reçoit ses préfixes fermés, ses 100 jours de warmup maximum et le dividende ex-date. ORB commence après la plage des cinq premières minutes, puis reçoit les minutes fermées successivement : commencer directement à la clôture créerait un faux démarrage tardif. Les frais figés sont 0,0035 USD/action/côté, minimum 0,35 USD/ordre, friction 0,01 USD/action/côté, emprunt short 1 %/360 avec minimum un jour. La tâche 1 pourra créer une autre version ; elle ne change pas celle-ci.

Les jours inconnus restent `unresolved`, les jours suivants bloqués `pending`, jamais des zéros. Les positions, frais et preuves déjà connus restent conservés après un échec API ou de warmup. L’autre bot peut continuer indépendamment. Une première capture avant l’ouverture XNYS suivante est `timely_eod`, sinon `catchup`. Ces catégories décrivent le replay, pas une observation intraday réelle.

Chaque capture est immuable et possède une empreinte ; les blobs identiques sont dédupliqués. L’état SQLite fermé et les barres sont compressés et chiffrés AES-GCM avant upload. Chaque checkpoint est lié à sa génération, au code, aux dépendances, à la règle et au run GitHub. Un checkpoint récent absent, expiré, incohérent ou corrompu bloque la reprise : aucun repli silencieux sur un ancien capital. Les runs échoués ayant sauvegardé un état valide restent autoritatifs. Un ancien run relancé ne peut écrire : utiliser un nouveau `workflow_dispatch`.

Les états ont une limite de 4 MiB chiffrés et une rétention de 30 jours. Deux checkpoints quotidiens plafonnent leur contribution à environ 240 MiB sur 30 jours, hors synthèses, essais et autres projets. Une interruption dépassant la rétention exige une restauration contrôlée depuis une sauvegarde vérifiée ; aucune remise à zéro automatique. Le projet ne crée ni abonnement, ni runner payant, ni budget supplémentaire. Les quotas de stockage partagés du compte restent une limite à surveiller. [Tarification GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Activation et reprise

La tâche 7 a publié les bandes numériques et la politique d’arrêt avant la cohorte. Le fichier `activation.json` référence sa règle, sa génération, le worker validé et la première séance du 2 novembre 2026. Les deux verrous d’activation sont actifs et les trois secrets Actions configurés. L’initialisation explicite a réussi le 1er novembre à 22:19 New York ; une exécution normale a ensuite repris son checkpoint, sans reset ni doublon.

Les lancements suivants utilisent exclusivement la reprise. Une fois la première date passée, le programme refuse une initialisation manquante ou une remise à zéro. Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour les commandes et la restriction GET imposée au programme, les identifiants PAPER n’étant pas un rôle fournisseur natif « données seules ».

## Rapprochement local

GitHub ne lit pas les bases du laptop. Le compagnon `scripts/collect_live.py --github` lit celles-ci en SQLite `mode=ro`, sans coffre ni API Alpaca, et écrit uniquement `runtime/operational/operational.sqlite` et `comparison.json`. La tâche Windows de collecte en lecture seule appelle ce compagnon à 18:35 et 19:35 Eastern en semaine, ainsi qu’à l’ouverture de session avec délai de 2 minutes ; elle fonctionne sans Codex. Il ne lance aucun job de trading et ne déploie pas de replay Windows.

Après activation, il télécharge par `gh` la synthèse dérivée du dernier run actif, vérifie son origine et refuse un résumé ancien en remplacement d’un résumé attendu manquant. Avant activation, aucune lecture GitHub n’est nécessaire. Un fichier local peut aussi être fourni avec `--summary fichier.json`.

Le rapport conserve les observations non qualifiées et présente séparément le sous-ensemble qualifié. Pour Noise, il recalcule également la ponctualité de chaque décision sur l’horloge logique différée, tolérance 2 minutes. Pour ORB, il compare l’empreinte du préfixe de barres effectivement utilisé, archivé par le moteur. Les indicateurs, sens, quantités, prix, heures économiques, motifs de sortie et P&L disponibles sont rapprochés.

Les comptes live ont leurs soldes propres. Un diagnostic économique supplémentaire recalcule le sizing, l’arrondi et les frais au capital live, **conditionnellement aux signaux et aux prix de référence du replay**. Il ne constitue ni un nouveau compte statistique, ni une reconstruction indépendante des indicateurs sur les données live. Noise n’archivait pas tous ses anciens prix intraday : une parité complète des entrées ne peut donc pas être certifiée. Toute différence reste documentée ; capital différent ou archive incomplète n’est pas une preuve de bug du moteur. La tolérance numérique de comparaison de 1e-6 sert à décrire les écarts ; les seuils décisionnels d’enquête/arrêt sont figés dans la règle de tâche 7.

## Reproduire les vérifications

Dans un environnement Python dédié avec `requirements.txt` installé :

```text
python -m pytest bots/qqq-eod-replay/tests -q -p no:cacheprovider
python bots/qqq-eod-replay/scripts/run_replay.py --mode status
python bots/qqq-eod-replay/scripts/collect_live.py --github
```

Le contrôle optionnel `scripts/offline_check.py --output fichier.json` exige l’archive SIP locale existante dont le SHA est figé avant désérialisation. Il vérifie la dernière séance historique contre le P&L publié Noise et le chemin d’exécution ORB figé. Il reste rétrospectif et ne contacte aucun fournisseur. Les tests CI utilisent des données synthétiques publiques ; les archives privées et bases actives ne sont jamais requises.

Le test cloud `scripts/cloud_smoke.py` utilise une clé et un contenu **synthétiques publics** pour vérifier réellement upload, téléchargement et authentification du chiffrement. Ce n’est pas un replay de marché ni un test de clé Alpaca.

Les schedules GitHub peuvent être retardés et sont désactivables après 60 jours d’inactivité du dépôt public. Le replay rattrape les dates, mais ne garantit pas la disponibilité du laptop ou des fills intraday. [Documentation des schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [support des fuseaux horaires](https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates/), [SIP historique Alpaca](https://docs.alpaca.markets/us/docs/market-data-faq).
