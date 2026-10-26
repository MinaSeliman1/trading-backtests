# EMA trend pullback — Implementation Plan

**Goal:** Research forums/GitHub, test a distinct EMA9/20 continuation hypothesis on SPY/QQQ at unchanged costs, publish all outcomes.

**Architecture:** New `studies/ema-trend-pullback/`, package `ema_pullback`, source/statistical adapters reused without changing legacy files or bots. Causal recursive EMA engine; separate EWM-segment audit. Python3.14, numpy/pandas/matplotlib/pytest. Inline implementation, independent reviewer.

**Spec:** New study's RESEARCH.md and PROTOCOL_EXECUTION.md. User delegates hypothesis choice; do not stop for a redundant design approval. Alternatives: EMA pullback, frequent VWAP reversal, Dual Thrust. First selected for a different entry mechanism and testable definitions, not external headline returns.

**Files:** `ema_pullback/engine.py`, `data.py`, tests, scripts/run_study.py, report.py, verify_delivery.py, audit/independent.py. Documentation, frozen exports, figures and manifests in the new study. Global README registry only legacy edit.

**Review focus:** prebar indicators and no future warmup; cash-scale changes; unknown segments; fixed sizing across next-open gaps; ambiguous SL/TP and account attribution. All need synthetic checks before PnL.

- [x] Failing tests: EMA recurrence/seed/cash/reset and causal snapshots; first signal and boundaries; costs/fills/coverage/compounding.
- [x] Implement minimal engine and pipeline; independently review before results.
- [x] Freeze protocol/code/dependencies/source hashes.
- [x] Complete72fixed scenarios once and preserve exports.
- [x] Separate audit of every decision, fill and account; inspect tables/figures, write validation and seal.
- [x] Prepare scoped commit/publication.

Actual push and remote hash confirmation are the final operations and will be reported in the user response.
