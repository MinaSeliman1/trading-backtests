# Opening volume breakout — Implementation Plan

> Execution inline, with independent code review before market calculations and delivery.

**Goal:** Research public sources, freeze an ETF adaptation, calculate SPY/QQQ after the existing fees, publish honest results.

**Architecture:** New isolated `studies/opening-volume-breakout/`; reuse verified SIP loader and statistical functions without modifying previous studies. New causal opening-volume features, confirmed breakout, minute fills and conditional account. No new bot.

**Stack:** Python 3.14, numpy, pandas, pytest, matplotlib, local verified SIP archives.

- [x] Record source comparison and exact execution protocol before inspecting new PnL.
- [x] Write failing synthetic tests: prior-only RVOL, missing observations, next-open decisions, stop/target priorities, costs/sizing and coverage.
- [x] Implement `ovb/engine.py`, source adapter and 72-scenario runner. Independent code review, repair and retest.
- [x] Freeze source/code/dependencies and execute immutable v1. Audit fills/accounting using a separate implementation and inspect charts.
- [x] Prepare source ledger, report, tests, audit, manifest and registry. Final delivery gate: commit/push and verify that remote main matches the delivery commit.

Existing histories have already been explored; B is a chronological diagnostic, never a fresh blind holdout. Preserve all prior study bytes. Mutable global README is verified in prior manifests against its historical delivery commit, not required to stay frozen forever.
