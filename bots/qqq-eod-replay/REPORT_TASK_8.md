# Tâche 8 — Suivi GitHub Actions activé en simulation

Livraison du **1er novembre 2026, heure de New York**. Le replay cloud est actif et sa reprise a été vérifiée. La nouvelle cohorte commence le **2 novembre 2026** ; aucun gain prospectif n’est encore disponible à la livraison.

## Ce qui est activé

- GitHub Actions : **17:23 et 18:23 America/New_York, en semaine**, runner Ubuntu standard du dépôt public ; variable `QQQ_EOD_ENABLED=true`.
- Deux nouveaux comptes statistiques indépendants : **100 000 USD par bot**, Noise Area et ORB. Aucun ancien solde n’a été copié ou remis à zéro.
- Un collecteur Windows distinct, sans console : **18:35 et 19:35 Eastern, en semaine**, et deux minutes après ouverture de session. Il lit les journaux existants sans écrire dedans.
- Les deux moteurs Windows existants restent en **shadow/SIP différé de 16 minutes**. Le dernier contrôle les montre `Running` ; leurs tâches et paramètres n’ont pas été modifiés par cette livraison.

Le cloud traite les dates XNYS échues depuis clôture + 17 minutes, demi-séances comprises, dans l’ordre. Il rattrape jusqu’à 20 dates par compte et passage ; le suivant continue. Une date inconnue reste `unresolved`, les suivantes `pending`, jamais une performance nulle inventée. Un bot bloqué n’efface pas les preuves de l’autre.

## Antériorité et versions

| Élément | Référence figée |
|---|---|
| Stratégies et frais | `f7ed9515b97644102ef674315c6af46e6fce8988` |
| Règle numérique de tâche 7 | `6e5e36c5ab91caf964523d9f6a52a996aae5f7c2` |
| SHA-256 de `rules/v1/RULE.json` | `3d19e338d9e0c3aea0df68f230d3386d1dc5b97161f1e3120cfa4aa2f10fa19f` |
| Worker de replay validé avant la cohorte | `2286aca61f4bf3636cada8e1234709cb8beafb77` |
| Métadonnées d’activation publiées | `47f9e658afa357814986c604342ec58600e674fb` |

Les frais restent **0,0035 USD/action/côté, minimum 0,35 USD/ordre**, friction **0,01 USD/action/côté**, emprunt short **1 % annuel / 360, minimum un jour**. Les bandes, seuils et règles d’arrêt de [tâche 7](REPORT_TASK_7.md) restent inchangés. Les raffinements finaux concernent uniquement collecte, diagnostic et documentation ; le moteur économique reste verrouillé au worker indiqué ci-dessus.

## Deux ledgers séparés

| Ledger | Contenu et stockage | Portée |
|---|---|---|
| **Statistique** | `statistical.sqlite`, checkpoints cloud chiffrés ; calendrier complet de la cohorte, états inconnus/en attente et arrêts conservés | Replay du modèle publié avant les séances ; deux capitaux indépendants |
| **Opérationnel** | `runtime/operational/operational.sqlite`, vue SQL canonique `qualified_sessions` | Dernière observation réellement qualifiée par bot/date depuis le 2 novembre |

La table d’audit opérationnelle conserve les versions, les journées rejetées et les anciennes dates ; elle ne les promeut pas en séances qualifiées. Les pointeurs `observation_heads` suivent la dernière observation réelle, même si elle redevient identique à une ancienne version. La date de cohorte du journal ne peut pas être changée silencieusement.

À la livraison : **0 séance statistique et 0 séance opérationnelle de nouvelle cohorte par bot**. Treize observations bot/date antérieures sont conservées à part ; parmi elles, l’ancien sous-ensemble qualifié compte Noise 0, ORB 1. Elles ne font avancer ni les nouveaux compteurs ni les jalons 20/60.

Le [protocole](PROTOCOL.md) explique la distinction : les futurs prix sont hors-échantillon pour la **politique stratégique figée**, mais un replay après clôture ne teste pas la disponibilité intraday, la latence, la file d’ordres ou les fills d’un courtier. Le ledger opérationnel qualifié ne reconstitue pas artificiellement un portefeuille continu dans les lacunes de couverture.

Les rapprochements conservent les écarts de sens, quantité, prix, minute économique, sortie et P&L disponibles. Un diagnostic au capital live est conditionnel aux signaux/prix du replay ; il ne constitue pas un troisième compte. Les capitaux ou archives incomplets restent un contexte de comparaison, pas une conformité supposée. Les seuils décisionnels de parité restent ceux de la règle 7.

## Preuves de fonctionnement réel

1. [CI de la version du worker](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41381787764) : succès, 78 tests réussis et un test Windows ignoré sur Linux ; aller-retour réel d’un artefact synthétique chiffré réussi.
2. [Initialisation explicite](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41382235448) : succès. Checkpoint à **2026-11-02 03:19:34 UTC**, soit **1er novembre 22:19 New York**, avant la date de cohorte. Déchiffrement authentifié vérifié localement : deux comptes à 100 000 USD, zéro séance, zéro tentative de marché. Sonde SIP cloud : cinq barres QQQ raw du 30 octobre, aucun calcul de P&L ni ordre.
3. [Reprise normale, sans initialisation](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41382868100) : succès. Checkpoint à **03:25:11 UTC**, référence explicite au run d’initialisation, mêmes capitaux, zéro doublon. Déchiffrement authentifié vérifié à nouveau.
4. Collecteur natif Windows : dernier passage **03:48:18–03:51:23 UTC**, retour **0**, 13 observations archivées, résumé cloud disponible, aucune erreur. Tâche installée sur secteur, réseau requis, deux reprises espacées de cinq minutes ; prochaine échéance contrôlée : 2 novembre 18:35 Eastern.

Une exécution intermédiaire du collecteur a renvoyé `RuntimeError` lors de la lecture du résumé GitHub. Le premier diagnostic ne conservait pas le détail HTTP : **la cause précise n’est donc pas établie**. Les observations locales ont été conservées, l’état statistique cloud n’a pas été affecté, et une nouvelle lecture a réussi. Des diagnostics sans corps de réponse, une seule reprise des GET transitoires identifiés et deux reprises planifiées Windows sont désormais en place. Aucun repli silencieux sur un vieux résumé n’a été ajouté.

La suite locale finale compte **83 tests réussis, aucune erreur ni omission**, dont le test d’un emplacement Windows d’identifiants synthétique, supprimé après contrôle. Les tests de couverture traitent les demi-séances et signalent les dates absentes/non résolues ; les tests réseau distinguent erreur transitoire et refus permanent sans exposer la réponse. La revue indépendante du code n’a trouvé aucun problème important. Les preuves structurées sont dans [task8_deployment.json](validation/task8_deployment.json) et [task8_checks.json](validation/task8_checks.json) ; le [contrôle cloud du commit de livraison](https://github.com/MinaSeliman1/trading-backtests/actions/runs/41386367570) a réussi : **82 tests réussis et un test Windows ignoré sur Linux**, puis reprise normale et sauvegarde chiffrée réussies, deux comptes toujours à 100 000 USD et zéro séance avant la cohorte. Le commit de code vérifié est `1b9b5e5a820fb351029b4ad1041860e26f4c9037` ; le complément suivant ne modifie que ces preuves documentaires.

## Secrets, droits et simulation

Trois **GitHub Actions Secrets** sont configurés : `ALPACA_PAPER_KEY_ID`, `ALPACA_PAPER_SECRET_KEY`, `QQQ_EOD_STATE_KEY`. Les deux identifiants PAPER existants ont été transférés par entrée standard d’un processus GitHub CLI à destination fixe, sans valeur dans les arguments, le chat, Git ou les sorties. La clé AES-256 indépendante possède une copie protégée dans un emplacement Windows Credential Manager distinct. Aucun fichier de clés n’a été créé dans le dépôt.

**Limite de droits fournisseur :** Alpaca PAPER ne fournit pas ici un rôle natif limité à la lecture. Le programme impose la restriction : GET QQQ SIP raw/dividendes uniquement, aucun endpoint broker/compte/ordre. Le workflow a seulement `contents: read` et `actions: read`, utilise `main` et des actions épinglées. Les scripts de collecte ne lisent aucune clé Alpaca et ouvrent les bases live en SQLite `mode=ro`.

L’état cloud et les barres sont chiffrés AES-GCM avant upload ; le résumé public est dérivé et sans identifiant de compte. Une source récente absente, expirée, corrompue ou incompatible bloque la reprise au lieu de réinitialiser le capital. Les exécutions normales n’initialisent jamais à nouveau ; les anciens runs relancés ne peuvent écrire l’état.

## Limites et suite

Aucun achat, abonnement, runner payant ou budget additionnel n’a été créé. L’état chiffré est plafonné à 4 MiB par checkpoint et conservé 30 jours. Les horaires GitHub peuvent être retardés et le planificateur d’un dépôt public peut être désactivé après 60 jours sans activité ; une interruption dépassant la rétention exige une restauration contrôlée. Le cloud fonctionne sans PC ; le ledger opérationnel dépend toujours de la disponibilité du PC, du réseau et de la session Windows.

La livraison valide **l’activation et la reprise**, pas encore une séance de marché de la cohorte ni une rentabilité. Les fills restent simulés et les observations anciennes restent séparées. Les [commandes d’exploitation](DEPLOYMENT.md) précisent la reprise sans reset. **La tâche 9 (alertes push) n’est pas activée ; elle attend le prochain feu vert.**
