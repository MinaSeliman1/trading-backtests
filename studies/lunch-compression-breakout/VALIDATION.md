# Validation

51 tests passent : compression/égalité, niveaux fixes, nouveau croisement, premier échec volume, unités1/5/15min, fenêtres/cutoff, taille/frais/gaps/unknowns, ledger et configurations exportées. WR/PF/Sharpe indéfinis testés sans les confondre avec zéro.

Oracle complet : 7177660 contrôles, 84 comptes, 227976 lignes de caractéristiques, 5474 lignes de trades, 151928 lignes quotidiennes. Recouvrements entre variantes/périodes, pas observations indépendantes. 864 contrôles agrégés et six références bootstrap blocs5/20 reproduites.

Gel avant premier PnL : 10 fichiers code/tests/runner/oracle/vérification, 15 dépendances et deux protocoles conservés avec texte. Présentation après gel et manifest final distinct. Les notes héritées de dividendes ne changent pas les prix bruts de ce test.

Revue pré-PnL lunch_pre_review :47tests puis51tests après corrections,112comptes synthétiques/20850comparaisons supplémentaires avant les derniers guards statistiques. Défaut Config-only stop_enabled absent des lignes exportées corrigé (stop toujours actif), avec régression RED puis GREEN. Audit agrégé renforcé sur zéro-trade/all-winning/variance nulle et manquants, quatre tests RED puis GREEN. Test de matrice charge le runner par chemin exact pour éviter un namespace scripts d’une ancienne étude. Aucune règle changée après PnL.

SPY : not_compressed=2373, no_signal=170, eligible=78, volume_filtered=65, half_session=21, unknown_context=6. Trades résolus du 2016-02-03 au 2026-07-06.

QQQ : not_compressed=2219, no_signal=242, volume_filtered=129, eligible=97, half_session=21, unknown_context=5. Trades résolus du 2016-02-03 au 2026-10-15.

Source/calendrier/caches/acquisitions vérifiés, même chargeur et fournisseur pour l’oracle. Aucun deuxième fournisseur, quote/partiel/latence réelle. Cache de l’oracle retient les marchés pour empêcher réemploi d’identité ; ils doivent rester immuables pendant main. Couverture conditionnelle explicite, exclusions au zéro de chaînage, pas cash observé.

[Tests](results/2026-10-31-v1/TESTS.json) · [Oracle](audit/AUDIT_RESULTS.json) · [Agrégats](audit/ADDITIONAL_CHECKS.json) · [Gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json) · [Sources](WEB_SOURCE_STATUS.json). Quatre figures inspectées avant publication ; reproduction dans copie séparée, --out sous l’étude et audit fixe protégé, détails README. verify_delivery.py --raw vérifie la livraison originale en lecture seule. Aucun bot, coffre, tâche Windows, SQLite ou paramètre actif modifié.
