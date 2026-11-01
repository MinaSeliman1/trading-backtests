# Validation

- 40tests passent sur TR, gaps, décalages, moyennes/arrondis, grilles, première sélection, sizing, coûts, stop/EOD, variantes et oracles manuels.
- Oracle scalaire :8509072contrôles,84comptes,227976features,63582lignes de trades,151928lignes quotidiennes. Recouvrements entre variantes/périodes, pas autant d’observations indépendantes.
- 864contrôles agrégés et six comptes bootstrap blocs5/20 reproduits. Dates/signaux/fills ALL réconciliés avec A/B ; quantités/capitaux distincts par période.
- 10fichiers financiers/tests/runner/oracle et15dépendances gelés avant premier PnL. Protocoles conservés. Présentation/contrôles supplémentaires ajoutés ensuite, manifest final.

SourceSIP/calendrier XNYS/hashes des caches/acquisitions vérifiés avant chargement. Oracle indépendant des calculs TR/gap/scan/exécution/ledger, même fournisseur et chargeur. Cache oracle supposant les objets marché immuables pendant son exécution ; main respecte cette condition.

Pré-PnL :37tests rouges observés sur stub, fixtures OHLC rendues cohérentes, puis40tests verts avec matrice et contrôles scalaires. Revue préalable sans bloqueur. Normalisation décimale1e-8 ATR et arrondi du seuil connus avant résultats. Aucune règle changée d’après PnL.

Couverture référence ALL : SPY : no_signal=1422, eligible=1222, unknown_history=38, half_session=21, warmup=5, unknown_scan=5 ; QQQ : no_signal=1381, eligible=1277, unknown_history=26, half_session=21, warmup=5, unknown_scan=2, excluded_incomplete_day=1. Semi-séances courantes connues sans transaction ; trous d’historique ne sont pas contournés. Exclusions au zéro de chaînage, pas cash observé. Les risques et durées sont ceux du protocole, pas des garanties au tick.

[Tests](results/2026-10-31-v1/TESTS.json) · [Audit](audit/AUDIT_RESULTS.json) · [Agrégats](audit/ADDITIONAL_CHECKS.json) · [Gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json) · [Sources](WEB_SOURCE_STATUS.json).

Quatre PNG accompagnent le rapport. Réutilisation A/B et essais multiples, biais de couverture future de complete_days, no_stop à risque distinct, absence de quotes/partiels/latence et donnée révisable sont explicités. Reproduction Windows : PYTHONUTF8=1 et PYTHONDONTWRITEBYTECODE=1. Aucun bot, coffre, SQLite, tâche Windows ou paramètre actif modifié.

Le profil source hérité contient des notes de rapprochement de dividendes propres à l’étude d’origine ; elles ne transforment pas les prix de cet ATR. Ici TR et gaps utilisent les prix raw, conformément au protocole et à l’oracle.

Le vérificateur de livraison est en lecture seule. Un nouveau calcul/audit doit se faire dans une copie séparée du checkout, au même niveau et avec données locales disponibles, pour ne pas remplacer audit/AUDIT_RESULTS.json archivé. Le chemin --out de l’oracle doit rester sous le dossier de l’étude.
