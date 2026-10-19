# Plan d'exécution

1. Vérifier les données : TradingView visible mais non connecté au premier contrôle ; IBKR réclame une réauthentification ; Yahoo réservé à l'exploration récente. Documenter les sources officielles et les restrictions observées.
2. Écrire puis exécuter les tests des invariants de temps, du FVG strict, du retest, des stops, des gaps et du dimensionnement. Les fixtures sont explicitement artificielles.
3. Implémenter import/calendriers et moteur causal ; vérifier DST, séances écourtées, minutes manquantes et contrats.
4. Ajouter statistiques, bootstrap, segments 70/30, walk-forward sans optimisation, sensibilités préfixées, graphiques et journaux.
5. Exécuter sur toutes les vraies données effectivement accessibles, garder fichiers bruts et hashes ; examiner des trades et rapprocher les calculs.
6. Implémenter Pine v6 ; compiler et exécuter seulement si l'accès TradingView le permet, sinon indiquer précisément le statut.
7. Vérifier le programme, générer un rapport des résultats réellement observés, des fonctionnalités non testées et des limites.

Revue attentive : ordre des événements sur la minute d'entrée ; gap qui rend le stop invalide ; aucun OHLC futur dans le calcul de quantité ; contrats d'échéances mélangées ; unités dollar/point/tick ; périodes sans trade conservées dans les métriques.
