# Bilan final du 3 novembre 2026 : Noise Area et ORB QQQ

**Noise Area : −292,60 USD nets, séance complète qualifiée. ORB : +10,51 USD nets, séance de rattrapage. Les deux positions sont fermées.**

Ce rapport décrit les **journaux opérationnels locaux shadow/SIP différé de 16 minutes**. Il est séparé du ledger statistique indépendant qui rejoue les stratégies préenregistrées sur GitHub Actions. Une transaction récupérée après une panne reste dans le résultat global mais ne devient pas une observation opérationnelle entièrement prospective.

Date de marché : **3 novembre 2026, America/New_York**. Les copies ont été capturées le 4 novembre à 05:00:28 UTC, soit le 4 novembre à 00:00:28 à New York, après la fin de la séance du 3. Tous les résultats ci-dessous sont filtrés jusqu'au 3 novembre inclus. Aucun résultat du 4 novembre n'est inclus.

## Résultat de la journée après frais

| Mesure en USD | Noise Area | ORB |
|---|---:|---:|
| Trades fermés | 1 | 1 |
| Commissions aller-retour | 1,225 | 1,008 |
| Friction / glissement simulé aller-retour | 3,500 | 2,880 |
| Emprunt short | 0,000 | 0,000 |
| **Total des coûts inclus** | **4,725** | **3,888** |
| **Résultat net réalisé** | **−292,60** | **+10,51** |
| Qualification opérationnelle | **Complète et ponctuelle** | **Rattrapage, non qualifiée** |

Les coûts sont déjà intégrés aux résultats nets ; ils ne doivent pas être retranchés une seconde fois. Les coûts sont montrés à trois décimales pour conserver les fractions de cent de la commission ; les P&L sont arrondis au centime. Aucun gain latent ne subsiste.

Noise Area a simulé un aller-retour LONG de 175 actions, créneau d'entrée 11:00 et créneau de fermeture 11:30 sur l'horloge logique. Prix simulés d'entrée/sortie : 688,115 / 686,450 USD. La différence de prix après friction produit −291,375 USD, puis 1,225 USD de commission donne **−292,600 USD**. Les prix et horaires de remplissage sont simulés à partir des barres archivées, et ne constituent pas des exécutions broker.

ORB a conservé l'entrée d'origine LONG de 144 actions, prix simulé 685,55 USD, puis a fermé selon la règle de fin de séance à **15:59 New York**, prix simulé 685,63 USD. Le mouvement de référence produit +14,400 USD ; friction 2,880 et commission 1,008 donnent **+10,512 USD**, soit **+10,51 USD**. Aucun stop ou objectif n'a été déplacé.

## Séance complète et rattrapage

**Noise Area** : les 12 décisions prévues de 10:00 à 15:30 ont toutes été traitées dans la tolérance de 120 secondes. Les retards logiques observés vont de 60,79 à 66,82 secondes. Le marqueur de fin enregistre 12/12 décisions ponctuelles, clôture observée dans le délai, `fully_prospective=true`. Le 3 novembre est sa **première séance entièrement prospective** depuis la référence du 21 octobre. Le résultat de cette séance qualifiée est −292,60 USD.

**ORB** : l'entrée initiale avait été observée à 09:36 logique, dans le délai existant de 09:37. La veille sur batterie et la lacune qui ont suivi, puis la récupération historique et le redémarrage, laissent les notes `data_gap`, `historical_recovery`, `late_observation`, `process_restart`. La position a bien été résolue et fermée, mais `fully_observed=false` demeure. Le +10,51 USD appartient donc au **rattrapage**. [Incident, correctif et reprise auditée](2026-11-03-orb-status-and-position-recovery.md).

Une séance terminée avec des observations manquantes ou tardives n'est pas assimilée à une séance complète qualifiée. Les séances totalement manquantes ne sont pas traitées comme des séances observées sans trade.

## Cumul des comptes opérationnels jusqu'au 3 novembre inclus

| Sous-ensemble après frais, USD | Noise Area | ORB |
|---|---:|---:|
| Séances entièrement qualifiées | **−292,60** : 1 séance, 1 trade | **−145,87** : 1 séance, 1 trade |
| Rattrapages / séances non qualifiées avec trades | **−1 304,18** : 8 trades | **−655,44** : 2 trades |
| **Total net comptabilisé** | **−1 596,78** : 9 trades | **−801,30** : 3 trades |
| Capital de référence | 99 237,196 | 100 000,000 |
| Solde final | 97 640,420823 | 99 198,695983 |
| Rendement du compte depuis sa référence | −1,61 % | −0,80 % |
| Total des coûts déjà intégrés | 55,15 | 14,16 |

Noise Area conserve sa référence existante du **21 octobre** et son solde réel du journal à cette date, 99 237,196 USD ; les opérations antérieures, correspondant aux deux premiers fills, ne sont pas réintégrées dans ce cumul. ORB conserve son compte séparé de 100 000 USD et sa référence du **26 octobre**. Aucun compteur ou solde n'a été réinitialisé.

Pour ORB, la séance qualifiée est celle du 28 octobre (−145,866 USD) ; les rattrapages sont ceux du 29 octobre (−665,9500167 USD) et du 3 novembre (+10,512 USD). Les deux cumuls restent négatifs après frais. Les expositions diffèrent : plafond Noise Area 4x et ORB 1x ; les seuls rendements bruts ne suffisent pas à classer les stratégies.

## Méthode de vérification et sources

Les deux bases actives ont été ouvertes avec `mode=ro`, puis copiées par l'API SQLite backup, WAL compris. Les copies ont passé `PRAGMA integrity_check` et tous les calculs ont été réalisés dessus en lecture seule. Les bases complètes restent dans un dossier `runtime/` ignoré par Git ; les empreintes des snapshots sont publiées sans chemin personnel, identifiant de compte ni clé.

Pour Noise Area, les fills sont joints aux ordres, filtrés depuis la date de référence et après `baseline_fill_seq=2`. Le net est la somme `realized − commission − borrow`, la friction étant déjà incluse aux prix simulés. Pour ORB, les `net_pnl` des trades fermés sont additionnés. Chaque sous-ensemble a été rapproché du solde final ; la somme qualifiée + non qualifiée égale le total à une tolérance numérique de 0,0000001 USD.

La ventilation se fait par **séance** : un trade pris ponctuellement dans une journée lacunaire ne rend pas cette journée complète. Le CSV comprend les seules dates avec fills/trades enregistrés ; les dates absentes ne doivent pas être interprétées comme des séances observées sans transaction.

- [Agrégats, décisions et preuves JSON](validation/2026-11-03-qqq-final-balance.json)
- [Ventilation quotidienne CSV](validation/2026-11-03-qqq-final-daily.csv)
- [Règles de qualification et d'exécution ORB](../../bots/qqq-orb/PROTOCOL.md)
- [Référence et suivi Noise Area](../../bots/qqq-noise-area/BACKGROUND_WINDOWS.md)
- [Distinction des ledgers statistique et opérationnel](../../bots/qqq-eod-replay/PROTOCOL.md)

## Poursuite des simulations et prochain bilan

Les deux tâches Windows ont été contrôlées actives, activées au démarrage, sans position ouverte. Le réveil commun reste programmé à **09:10 Eastern** les jours de semaine ; son dernier passage du 3 novembre a retourné 0 et sa prochaine échéance contrôlée est le **4 novembre à 09:10**. Ce rapport n'a modifié ni moteur, ni règle, ni paramètre, ni coût, ni journal. La surveillance conserve les contrôles de fraîcheur, données manquantes, pauses, STOP et ponctualité ; une tâche déclarée active ne suffit pas à prouver que ses décisions arrivent à l'heure.

Le contrôle de fin de soirée a trouvé le PC sur batterie, hors séance. Pour les prochaines séances, le PC doit être **branché sur secteur, session utilisateur ouverte, réseau disponible**. Le couvercle fermé reste autorisé sur secteur. Les politiques batterie et les veilles explicites conservent leurs limites ; aucune nouvelle politique Windows n'a été appliquée pour produire ce bilan.

Le suivi existant revient **une seule fois quand chacun des deux bots atteint 20 séances boursières terminées et entièrement qualifiées**. À la fin du 3 novembre, ils en comptent **1 chacun**. Les rattrapages et les 20 trades éventuels ne remplacent pas ces 20 séances. Les pannes et retards significatifs restent signalés sans attendre ce seuil ; les contrôles sains restent silencieux. La revue prolongée Noise Area à au moins 60 séances qualifiées et 50 trades correspondants demeure prévue.

Ces observations shadow et ce très petit échantillon ne démontrent pas une rentabilité. Aucune activation en réel n'est autorisée par ce bilan.
