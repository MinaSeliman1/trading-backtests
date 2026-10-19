# Statut des exécutions

| Dossier | Statut | Usage |
|---|---|---|
| `alpaca_sip_long` | Référence validée pour SPY/QQQ | 116 scénarios recalculés après la correction numérique documentée, plus de trois ans de données réelles |
| `etude_2026-10-19` | Exploration Yahoo archivée | 72 scénarios récents, avant la correction des contacts exacts au tick ; cette archive ne remplace pas la référence Alpaca |
| `source_audit_2026-10-19` | Audit de disponibilité/provenance | Sources gratuites de futures examinées ; aucun backtest long validé ES/NQ n'en est déduit |

Les résultats et manifests sont copiés sans modification. Le moteur courant correspond à la référence Alpaca. Le code historique de l'exploration Yahoo reste dans le ZIP local original ; il n'est pas présenté ici comme identique au moteur corrigé.

Les premières exécutions de développement (`yahoo_exploratory`, `yahoo_28d`) et le calcul Alpaca interrompu avant correction (`archive_alpaca_float_precision_20261019`) restent archivés localement. Ils ne sont pas ajoutés comme résultats de référence. Les différences et les inspections antérieures sont déclarées dans `alpaca_sip_long/CORRECTION_NUMERIQUE.md`.
