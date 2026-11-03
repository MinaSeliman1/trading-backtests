# ORB : statut Windows et recuperation du 3 novembre 2026

Le blocage de la position a ete leve et la tache ORB existante relancee le 3 novembre a **11:08:54 New York**, en shadow/SIP differe de 16 minutes. Le journal historique, les parametres, les frais et l'entree du jour sont conserves. La position reste **active** selon les regles du modele : la recuperation ne constitue pas une cloture forcee. Premiere reprise effective confirmee a 11:09:53 ; controle sain a 11:10:58, statut vieux de 2,8 secondes et barres traitees jusqu'a 10:53 logique.

## Cause et chronologie

Toutes les heures ci-dessous sont en America/New_York ; les captures SIP sont horodatees UTC et converties avec la base des fuseaux.

- Entree du jour observee a 09:36:00 logique, donc dans la limite existante de 09:37.
- Windows a enregistre le passage sur batterie a 10:05:08 puis une veille « Button or Lid ». Reprise vers 10:09:13, retour sur secteur. Les protections secteur ne changent pas la politique batterie. Aucun reglage d'alimentation n'a ete modifie ici.
- Le journal est passe en `unresolved / missing_active_open`, avec seulement les barres 09:30 a 09:48 conservees. Le moteur refuse volontairement de poursuivre une position lacunaire et ne retente pas automatiquement cette phase terminale.
- Le processus est sorti avec code 1 a 10:22:59 UTC-5. La trace fatale montre `PermissionError`, errno 13, winerror 5 dans le remplacement atomique de `status.json`, puis dans le gestionnaire d'erreur qui tentait a nouveau d'ecrire ce meme statut. L'acces refuse est demontre ; le processus qui detenait le fichier n'est pas identifie. L'emplacement OneDrive ne suffit pas a lui attribuer le verrou.

## Correctif de fonctionnement

`orb_shadow/status.py` ecrit un temporaire unique, puis tente le remplacement atomique quatre fois au maximum, avec 0,55 seconde de temporisation cumulee. Une erreur d'entree/sortie persistante est journalisee avec type/errno/winerror, sans texte d'exception ni secret, et renvoie un echec de telemetrie sans interrompre la gestion de la position. Le cycle suivant retente normalement ; l'ancien statut reste intact et sa fraicheur continue d'etre surveillee. Le meme garde couvre le fichier de verification de connexion.

Seul ORB importe ce nouveau composant. Aucun changement du module partage `qqq_paper.runtime`, du processus Noise Area, de l'algorithme ORB ou du replay statistique fige. Un test natif Windows reproduit le refus de remplacement en tenant un fichier temporaire ouvert sans partage DELETE ; aucune faute n'a ete provoquee sur les journaux actifs. Un test de service complet exerce aussi les gestionnaires d'erreur de demarrage et de cycle avec une telemetrie continuellement verrouillee.

## Recuperation de la position

1. Verification de la tache ORB arretee et activee, de sa commande fixe `pythonw`/bootstrap shadow et de l'absence de STOP ; acquisition du verrou d'instance.
2. Sauvegardes SQLite coherentes via l'API backup, incluant le WAL, puis controles d'integrite. Les copies et captures restent dans `runtime/recovery/`, ignore par Git.
3. Requete historique **GET QQQ SIP, raw, 1 minute**, avec les cles PAPER deja protegees chargees uniquement en memoire. Aucun acces a une route d'ordre. Capture finale : 79 barres de 09:30 a 10:48, cutoff logique 10:49, obtenue a 11:05:37. La minute 09:49 est presente ; aucune minute n'a ete inventee ou remplie par interpolation.
4. Previsualisation de la reprise avec le moteur existant, puis application transactionnelle a 11:08:32 apres comparaison de l'empreinte exacte du compte et de la journee. Ajout de 60 barres apres le prefixe connu, **zero revision** de ce prefixe. Les memes octets CSV sont hashes et parses. Une lacune residuelle parmi les minutes deja cloturees interdit la reprise active, y compris pendant la tolerance de deux minutes du moteur live ; des barres posterieures a une sortie deja determinee ne sont pas requises.
5. L'entree reste LONG 144 actions QQQ, reference 685,54, remplissage 685,55, stop 683,18, objectif 709,14. Commission d'entree 0,504 USD deja prelevee, non prelevee une seconde fois. Le solde realise est reste 99 187,67998333332 USD pendant cette recuperation. Aucun stop/objectif atteint dans la capture ; le moteur reprend donc la gestion de la position encore ouverte.
6. Toutes les anciennes lignes des autres jours, metadonnees hors compte, transactions et evenements restent identiques. Un evenement `recovery` garde l'etat precedent et les empreintes ; les evenements d'entree et de sortie ne sont jamais remplaces. Une repetition est refusee. Controle SQLite `integrity_check=ok`, un evenement d'entree et un evenement de recuperation pour le 3 novembre.
7. Relance de la tache existante apres 09:30, expressément autorisee pour cette intervention. Le demarrage observe inclut environ 47 secondes d'initialisation ; les cycles de donnees puis le statut ont repris. Noise Area demeure actif et n'a pas ete redemarre.

La journee garde `prospective=false`, `fully_observed=false` et les notes `data_gap`, `historical_recovery`, `late_observation`, `process_restart`. Elle reste un rattrapage operationnel, sans ajouter de seance qualifiee au bilan des 20 seances. Le compteur ORB demeure a une seance qualifiee anterieure. Le ledger statistique independant conserve son propre replay de toutes les seances selon son SHA pre-enregistre.

## Invariants et verification

- Moteur historique ORB SHA256 : `0ee6f0f9e7b7f1080d444e90a055aeb4ed2dc63349cfc7ab05f66d1d4f5f1810`, identique.
- Configuration SQLite SHA256 : `1b20a825838929e755ffee97641ecef61ad60b95742ae999bcc6d10f24d853c2`, identique avant/apres.
- Frais identiques : commission 0,0035 USD/action/cote, minimum 0,35 ; friction 0,01 USD/action/cote ; emprunt short 1 %/360. Risque 1 %, plafond 1x, objectif 10R et stop prioritaire inchanges.
- Sources statistiques toujours epinglees au commit `f7ed9515b97644102ef674315c6af46e6fce8988`. Regle d'arret et moteur EOD inchanges ; ce correctif est une version d'exploitation distincte.
- **90 tests selectionnes passent** : 49 ORB, 25 alertes, 16 EOD (sources, replay, parite). Il ne s'agit pas d'une execution de tous les tests de toutes les etudes du depot.
- Revue independante effectuee avant application ; garde des lacunes recentes et lecture unique des octets hashes ajoutes. Tests directs du CLI : previsualisation sans mutation, backup avant application, recu, refus du hash altere, du STOP et d'une instance active.

[Preuves expurgees](../../bots/qqq-orb/validation/2026-11-03-status-recovery.json). Les bases sauvegardees, bougies, etats complets et recus d'application restent locaux. Aucun secret ou identifiant de compte n'est publie.

## Reprise manuelle ulterieure

Le CLI de recuperation n'effectue aucune requete reseau et ne lance aucun ordre. Il exige une position deja entree et `unresolved`, une capture SIP locale avec `data_receipt.json` (SHA256 et cutoff logique), le bot arrete, aucun STOP, et le verrou d'instance libre. La previsualisation est en lecture seule ; l'application exige l'empreinte imprimee par celle-ci et cree une nouvelle sauvegarde sans ecrasement.

```powershell
# Depuis bots/qqq-orb, dependances Python configurees
python -m orb_shadow.recovery --runtime runtime --evidence runtime/recovery/CAPTURE
# Apres inspection de la previsualisation et autorisation de reprise
python -m orb_shadow.recovery --runtime runtime --evidence runtime/recovery/CAPTURE --apply --expected-digest EMPREINTE
```

La relance utilise exclusivement la tache shadow deja installee, apres controle de sa commande et des gardes. Cette autorisation apres 09:30 ne supprime pas la regle ordinaire du suivi automatique, qui reste limite aux demarrages avant l'ouverture et ne contourne jamais un STOP.

Derniere verification avant publication : 2026-11-03 16:13:58.056482+00:00, phase active, derniere barre 2026-11-03 10:56:00-05:00, statut age de 5.49 secondes. Un seul evenement d'entree et un seul evenement de recuperation ; aucune nouvelle qualification du 3 novembre.
