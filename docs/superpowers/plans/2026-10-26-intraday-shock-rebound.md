# Intraday Shock Rebound Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with independent read-only reviewer gates.

**Goal:** Research beyond forums/GitHub, select one defensible new intraday mechanism, test SPY/QQQ with unchanged costs and publish all results.

**Architecture:** New studies/intraday-shock-rebound, package shock. Causal matched-clock20session normalization of30minute negative moves, immediate5minute confirmation, next-open fixed sizing and conservative SL/TP/EOD. Reuse verified source/accounting patterns without modifying older studies. Independent deque/NumPy feature reconstruction and scalar replay.

**Tech Stack:** Python3.14, numpy/pandas, matplotlib/pytest; local verified SIP source.

**Spec:** studies/intraday-shock-rebound/PROTOCOL_EXECUTION.md and RESEARCH.md. User delegates choice and expressly expands Web research. No redundant design permission; meaningful choices documented as ours.

## Global Constraints

- Same costs, periods and source; B reused, no blind OOS claim.
- Only new study, plan and global README registry; no active bot/runtime/vault/order changes.
- No full history or keys in Git; preserve all historical study bytes.
- Fix code/protocol/scenarios before first market PnL; changes after PnL require new immutable run.

## Review Focus

- Same-clock historical20sessions and half-day calendar selection, no future quality filtering of history.
- Missing observations before first signal cannot be treated as absent signals; confirmation fetched only when needed.
- Signal-known sizing, future-open gaps, rounded SL/TP, ambiguous minutes and EOD before last wick.
- Warmup/zero variance distinct from missing history; corporate-action scale invariance of intraday returns.
- Cost stresses, unknown active fills, concentration and descriptive bootstrap; no winning variant promotion.

### Task1: Engine and synthetic validation

Create shock/engine.py,data.py,__init__.py and tests/test_engine.py. Interfaces prepare(market,cash), signal(market,feature,Config), trace and simulate follow established daily/trade exports. Tests first, observe failure, implement, then independent review without market PnL.

- [x] Write red cases for historical normalization, causality, confirmation, half-day, unknowns, fills/costs/accounting.
- [x] Implement minimal engine and validate all synthetic cases.

### Task2: Frozen execution and independent audit

Create scripts/run_study.py,report.py,verify_delivery.py and audit/features.py,independent.py. Sources/dependencies/protocols/scripts/test hashes archived before72scenarios execute once. Reviewer prefreeze checks synthetic only.

- [x] Independent prefreeze review, freeze and run72scenarios.
- [x] Independent full replay plus final numeric/report review; inspect four figures.

### Task3: Publication

Create README/VALIDATION/INTERPRETATION and source-backed full report; update root registry. Seal study-only SHA manifest; scope/staged-byte/secret/link checks, commit and push authorized repository. Verify actual remote hashes before claiming publication.

- [x] Seal/verify; stage only intended files; publish and verify remote commit.

Execution ledger:38tests;72scenarios;4276184independent replay checks,68102overlapping trade rows,130224day rows, zero divergences. Reviewer271963feature and7953aggregate checks; six bootstraps recomputed. Six references negative. No bot change. Final publication/remote state reported at delivery after verification.
