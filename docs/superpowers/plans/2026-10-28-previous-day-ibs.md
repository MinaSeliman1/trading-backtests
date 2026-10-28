# Plan natif — IBS précédent intraday

Mandat utilisateur : chercher une autre piste, la choisir, tester SPY/QQQ mêmes coûts et publier. Approche retenue : Python local, source SIP déjà vérifiée, aucune modification des bots. Alternatives et différence avec IBS swing consignées dans RESEARCH.md ; règles détaillées dans PROTOCOL_EXECUTION.md. Base Git9561fe75125efe33a436c336c4172f433118eed5.

- [x] Rechercher publications, auteurs, forums, GitHub ; choisir IBS précédent sans RSI ni overnight.
- [x] Ajouter tests synthétiques avant moteur, constater rouge, implémenter features causales/signaux/stop/compte puis vert.
- [x] Runner72scénarios, snapshots SHA, tables, statistiques et rapport figés avant PnL ; revue ciblée.
- [x] Exécuter une fois sur archives vérifiées ; audit scalaire indépendant des historiques/sizing/fills/PnL/DD et matrice.
- [x] Examiner graphiques, comparer les exports/rapport, sceller empreintes et publier code/tests/résultats dansGitHub.

Fichiers : ibs/engine.py moteur, ibs/data.py accès source existant ; scripts/run_study.py gel et exécutions, report.py rapport/figures, verify_delivery.py intégrité ; audit/independent.py calcul séparé, matrix.py matrice ; tests/test_engine.py et test_matrix.py ; docs de recherche/protocole/validation et résultats datés.

Interfaces : Config immuable ; prepare(market,cash)->features passées ; signal(market,feature,cfg)->raison et paramètres ; simulate(...,start,end)->daily,trades,unresolved etDD. Statistiques réutilisées d'orb.analysis, dépendances archivées. Audit ne doit appeler ni prepare, ni signal, ni simulate, ni trace. Même chargeur, pas second fournisseur.

Revue à cibler : seuils inclusifs, pas de skip sur trou historique, warmup200, fills de09:31, sizing connu avant open futur, SL prioritaire et mècheEOD ignorée, coûts une seule fois, historique prix bruts et qualité ex-post, variante always_long sans preuve causale. Critères déclarés dans protocole, aucun choix après résultat.

Bilan :48tests ;72comptes ; audit scalaire3212571contrôles ; revue indépendante2538contrôles d’agrégats et2308tables, sixbootstraps, quatrefigures. Aucun code financier modifié après gel. La publication est déclarée accomplie seulement après concordance de HEAD et des références distantes.
