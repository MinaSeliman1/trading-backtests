# Validation QQQ Noise Area paper — 20 octobre 2026

## Extension arrière-plan Windows

**69 tests passent en 15,40 secondes**, commande `python -m pytest -q --basetemp=.test_tmp_windows_release`. Deux tests de coffre Windows utilisent des valeurs factices sous une cible de test unique, supprimée après le roundtrip. Le profil restreint de l'environnement refuse l'accès au coffre ; ces tests ont donc été exécutés sous le contexte utilisateur autorisé. Aucune clé réelle n'est imprimée ou incluse dans les tests. Les scripts PowerShell ont aussi été analysés sans erreur de syntaxe.

La tâche Windows est enregistrée et active sous l'utilisateur courant, déclenchée à sa connexion avec délai de 20 secondes, `pythonw.exe`, fenêtre absente, durée d'exécution illimitée. Le premier lancement caché a été observé, puis un arrêt par drapeau et une reprise immédiate ont réussi : même solde **99 237,196 USD**, à plat, aucun ordre en attente, séquence de fills inchangée à **2**. L'ancienne console dédiée est fermée. La tâche de connexion est vérifiée, mais un redémarrage effectif du PC n'a pas été provoqué pour ce test. [Preuve sans identifiants de compte](validation/windows_background_2026-10-20.json).

Une revue indépendante a trouvé deux défauts de cette extension. Les premiers tests rouges ont reproduit une observation tardive datée avec l'horloge antérieure au téléchargement et un lancement perdu pendant l'arrêt du superviseur. La correction conserve le cutoff des données, mais date l'observation après calcul/fill ; le marqueur de clôture utilise une observation distincte après traitement. Le script attend désormais la fin de la tâche précédente avant de supprimer le drapeau, puis confirme un superviseur récent avec processus actif. Les régressions incluent l'absence de double lancement et la conservation d'un solde existant avec position virtuelle ouverte lors d'un arrêt shadow. La seconde revue ne trouve plus de blocage sur les changements corrigés.

Le module de bilan lit SQLite en lecture seule. Une référence prospective créée une seule fois débute le **21 octobre 2026**, au solde existant, sans inclure les fills du rattrapage du 20 octobre. Les séances avec décision ou clôture observée trop tard ne deviennent pas entièrement prospectives ; les manques sont signalés. Premier bilan à 20 séances complètes, bilan prolongé à 60 séances et 50 transactions fermées ; ces seuils ne prouvent pas une rentabilité. Le suivi de ce chat est programmé les jours ouvrés à 17 h, heure locale Toronto. [Exploitation et limites](BACKGROUND_WINDOWS.md).

Les preuves de replay et de la livraison antérieure ci-dessous restent datées de leur version ; le replay de marché n'a pas été réexécuté pour cette extension d'exploitation. Aucun résultat des études historiques n'est modifié.

## Périmètre effectivement exercé

**47 tests contrôlés passent en 9,20 secondes** sous Python 3.14.6, avec les dépendances figées de l'étude. Les données de ces tests ne sont pas des résultats de marché. Commande depuis ce dossier :

```powershell
python -m pytest -q --basetemp=.test_tmp_release_complete
```

Les tests couvrent le préfixe causal, les dividendes, fenêtres 14/14 et demi-séances ; le refus d'un historique incomplet avant statut opérationnel ; les commissions et emprunts, dont maintien accidentel plusieurs jours ; l'application idempotente des fills cumulés ; les limites d'hôte et la restriction paper/QQQ ; les refus et envois ambigus ; la fermeture avant retournement ; les redémarrages avec ordre partiel ou position overnight ; la clôture sans données ; la publication tardive de la dernière minute ; le refus final après expiration ; l'arrêt précoce ; le verrou tenu jusqu'à la fin du nettoyage et le contrôle de connexion sans mutation.

L'essai connecté a aussi exposé une comparaison incorrecte d'index UTC et New York. Un test rouge l'a reproduite ; le préfixe est désormais normalisé au fuseau de séance. Un test d'intégration fait traverser une réponse REST en UTC jusqu'au signal shadow et au fill net de coûts. Le diagnostic initial, sans fill, est conservé dans [startup_utc_diagnostic_2026-10-20.json](validation/startup_utc_diagnostic_2026-10-20.json).

Une revue indépendante a identifié des défauts de la première version sur ces chemins de reprise et d'interruption. Ils ont été reproduits, corrigés et couverts par des régressions. La revue finale n'a pas identifié d'autre blocage majeur ; son dernier défaut d'interruption pendant l'initialisation a ensuite été reproduit par deux tests rouges puis corrigé. La revue n'a contacté aucun compte.

Une régression supplémentaire vérifie que shadow suspend une position issue d'une séance précédente dont la clôture a été manquée, au lieu de la reporter silencieusement. La reprise historique de cette interruption demande une reconstruction séparée. Les empreintes du code livré et les commandes de validation sont dans [build_2026-10-20.json](validation/build_2026-10-20.json).

## Replay sur les vraies données archivées

Commande exécutée : `python scripts/replay_parity.py`.

| Mesure | Observation |
|---|---:|
| Source | Acquisition QQQ Alpaca SIP raw de l'étude |
| Période B | 01/05/2024–16/10/2026 |
| Séances | 618 |
| Décisions comparées | 7 380 |
| Événements de fill shadow | 1 008 |
| Transactions complètes | 504 |
| Résultat net rejoué et attendu | 54 303,22175441508 USD |
| Écart maximal de P&L quotidien | 1,15961 × 10⁻¹⁰ USD |
| Écart maximal d'indicateur | 1,36425 × 10⁻¹² |

Le replay parcourt les séances chronologiquement avec historique limité au passé et préfixe terminé. Il compare prix, bandes, VWAP, objectifs et quantités aux exports, puis le ledger au scénario **next_open, 0,01 USD/action/côté, plafond 4x**. Le décideur et les prix ne dépendent pas de la friction ; les références de décision à 0,001 et les références de quantité/P&L à 0,01 sont distinguées dans le script.

Preuve : [replay_2026-10-20.json](validation/replay_2026-10-20.json). SHA-256 du pickle QQQ : `67e5ae72288b8878777683c67343174491895b6069c41f331b13aff422e06711` ; SHA-256 du décideur historique : `ecab630d5f850c4def089739c9a13b7acd88de1361527483ff39f0f6a6765664`.

Cette preuve porte sur le calcul historique et la comptabilité shadow. Elle ne valide ni les prix des ordres Alpaca paper, ni IEX contre SIP, ni la rentabilité future. Les corrections finales des chemins d'interruption/reprise paper sont exercées par les tests dédiés, pas par le replay shadow.

## Intégrité des études existantes

`python tools/verify_snapshot.py` depuis la racine : **1 977 fichiers FVG importés, SHA-256 identiques**. Les **32 tests Noise Area** de l'étude originale passent séparément en 10,25 secondes. Aucun résultat historique n'est remplacé par le code du bot.

## Activation connectée

Le statut de connexion effectivement observé est consigné dans [activation_2026-10-20.json](validation/activation_2026-10-20.json). Aucun numéro de compte, clé ou historique complet ne sera publié. Un statut connecté n'implique pas qu'une transaction ait été exécutée.

L'essai connecté paper/IEX a téléchargé 70 séances. Parmi les 15 dernières, une seule était complète ; les autres comportaient de 1 à 32 minutes manquantes. Les règles exigent 15 clôtures précédentes de séances valides pour la volatilité. L'instance a été suspendue et arrêtée, à plat et sans fill, avant le premier créneau futur. Le statut initial `running` attestait la connexion, mais n'avait pas encore évalué ces fenêtres : un contrôle anticipé et son test de régression corrigent cette insuffisance d'observabilité. Aucune minute n'a été interpolée.

Le choix gratuit retenu est donc **shadow/SIP différé de 16 minutes**, qui utilise les mêmes données consolidées et simule localement les transactions. Ce mode ne transmet aucun ordre paper. L'exécution d'ordres paper fidèles demande un flux SIP temps réel autorisé ; elle n'est pas déclarée active sur ce compte gratuit.

Le lancement corrigé a été observé actif à 15:31 UTC : trois décisions traitées, un fill virtuel et une position locale de +252 QQQ. Il s’agit du rattrapage shadow du début de séance, pas de transactions exécutées chez Alpaca ni d’une preuve prospective de rendement. La fenêtre historique SIP des 15 séances précédentes est valide.

Les journaux futurs restent locaux et ne sont pas automatiquement ajoutés à GitHub. Les résultats prospectifs devront être publiés avec dates, coûts, manques de données et rapprochement des fills, en distinguant shadow et ordres paper.
