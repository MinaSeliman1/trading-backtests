# Opening Range Retest Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; independent read-only review gates before first PnL and publication.

**Goal:** Research a new reproducible intraday SPY/QQQ hypothesis broadly, run unchanged fees, publish actual code/results/report.

**Architecture:** studies/opening-range-retest, package retest. Fixed15minute range, first confirmed5minute breakout, first later touch within6bars must hold and confirm. Next-open sizing, conservative SL/TP/EOD and verified existing account/source patterns. Separate pandas aggregation plus scalar state/account replay. No older study edits.

**Tech Stack:** Python3.14, numpy/pandas/matplotlib/pytest; verified SIP source.

**Spec:** studies/opening-range-retest/RESEARCH.md and PROTOCOL_EXECUTION.md. User delegates choice and publication; no redundant design approval.

## Global Constraints

- Same source, costs and periods; reused B, no blind OOS claim.
- New study/plan and root README only; no bots/runtime/vault/order/automation changes.
- No full history or secrets in Git; old scientific files immutable.
- Freeze all financial and report code before first market PnL; correction needs new immutable run.

## Review Focus

- First breakout and first touch only; no same-bar retest or later winner selection.
- Exact deadlines/cutoff, failed first touch terminal, unknown needed bar vs irrelevant later gap.
- Signal-known sizing and outward rounding, actual-entry target, bad gaps/ambiguous minute/EOD ordering.
- Direction variants don't search for a second first breakout; half-days and degenerate range.
- Costs, conditional coverage, comparator exposure confounding, bootstrap and no winning variant promotion.

### Task1 — Engine, tests and separate aggregation

Create retest/engine.py,data.py,__init__.py; tests/test_engine.py; audit/bars.py. Interfaces prepare/signal/trace/simulate use existing daily/trade schema with new range/state metadata.

- [x] Write failing state/timing/missing/fill/account cases, implement, pass synthetic suite.

### Task2 — Frozen execution and review

Create scripts/run_study.py,report.py,verify_delivery.py and audit/independent.py.12variants×2ETF×3periods. Freeze code/dependencies/source/protocols; audit independently.

- [x] Prefreeze reviewer and synthetic audit/report smoke; freeze and execute once.
- [x] Replay all72scenarios, review actual tables/criteria/figures.

### Task3 — Delivery

Create README/VALIDATION/INTERPRETATION and sealed dated outputs, update root registry. Scope/secret/link/hash/index checks, authorized commit/push, remote verification.

- [x] Seal and verify exact inventory.
- [ ] Publish only intended files and confirm remote commit (final Git handoff).


## Reprise et décisions du28octobre

Ruling: reprendre le protocole du26 sans modifier ses signaux ni ses coûts ; sortie datée results/2026-10-28-v1 car aucun PnL marché n'avait été exécuté. La correction des bots est publiée séparément au4687634 et reste hors de cette étude.

Ruling: corriger avant gel la liaison matrice/protocole et résumé/scénario demandée par la revue indépendante ; tests rouges explicites contre répétition d'une ligne, dérive de configuration/date et résumé divergent. Coût si absent :72lignes auraient pu masquer un scénario omis.

Les règles, les12variantes et le seed20261026 restent ceux du protocole initial ; les nouvelles sources sont contextuelles, sans import de rendement.


## Exécution et revue

Gel28octobre19:28:27UTC,12fichiers propres et12dépendances.72scénarios en172,05secondes,42tests. Audit séparé3032271contrôles,30612trades et130224jours recouvrants ; revue CSV15187contrôles, six bootstraps reproduits, quatre figures inspectées. Aucun changement après gel.

Ruling: ne pas promouvoir QQQ B positif ou SHORTseul ALL positif ; les critères restent ceux déclarés avant PnL, quatre sur cinq échouent. Le contrôle sans retest change exposition, stop et sizing et ne prouve pas une causalité.

Ruling: pour le point mineur du manifest, contrôler l’ensemble exact des fichiers avant staging et publication ; aucun fichier hors du manifest de l’étude ne doit être ajouté, hormis le manifest lui-même, le plan et le registre global.


Ruling: le scellement révèle un UnboundLocalError non financier dans le vérificateur gelé. Conserver le fichier initial intact et livrer verify_delivery_v2.py, correctif d'une seule ligne d'import avec empreintes et explication explicites. Ne pas relancer ni retoucher les résultats, car aucune règle ni statistique n'est concernée.

Scellement vérifié :377empreintes,378fichiers de l’étude manifest compris ;42tests,72scénarios,raw=True. Revue du correctif de livraison2 : suppression exacte d’un seul importsys local ; empreintes des12fichiers gelés,12dépendances et290exports d’audit inchangées.
