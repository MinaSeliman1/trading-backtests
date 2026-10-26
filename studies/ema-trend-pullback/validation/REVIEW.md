# Revue séparée avant performance

26 octobre 2026. Agent de revue `ema_pullback_review`, lecture seule, sans données de PnL de marché, bots, runtime, clés, coffre ou écriture Git.

Portée : protocole et moteur EMA9/20, états avant bougie, cash/pentes dans une échelle commune, chauffe60barres et resets, premier signal et inconnus, sizing avant open, gaps/SLTP, frais et comptes, scripts de gel/rapport/vérification et audit EWM indépendant.

Le contrôle cash a été étendu à tous les états conservés (pas seulement le plus récent), avec test rouge puis vert avant PnL. L'audit arrête explicitement les cas cash non positifs hors périmètre de sa reconstruction ; leur absence doit être vérifiée sur la source utilisée. Le marqueur de chauffe initiale de l'audit a aussi été corrigé avant PnL, puis comparé au moteur sur trajectoires entières avec cash et lacunes.

31tests synthétiques passent, également relancés par le reviewer. Neuf parcours d'audit simulés entièrement en mémoire passent : LONG, SHORT miroir, sens filtré, entrée absente, trou actif, bougie candidate inconnue, historique indicateur inconnu, filtre journée complète, prefix résolu avant un trou ultérieur.

Conclusion : aucun problème matériel restant pour les72scénarios prédéfinis ; prêt à figer avant le premier PnL. Cette revue ne certifie ni un second flux ni une rentabilité prospective. Les empreintes exactes du code sont dans PRE_EXECUTION_PROTOCOL.json et ses snapshots.

## Revue finale du rapport

Après calcul, même reviewer en lecture seule :63contrôles de cohérence passent. Les6tableaux du rapport concordent avec matrice, couverture, concentration et bootstrap ; années/mois/directions rapprochés avec les6références. Les comptes sources et les3scénarios positifs isolés concordent. Aucun problème matériel de résultat ou de conclusion ; aucune variante promue et aucun PnL recalculé. Le replay intégral séparé reste la preuve de cohérence financière à attendre avant livraison.
