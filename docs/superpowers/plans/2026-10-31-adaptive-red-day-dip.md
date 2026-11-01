# Adaptive Red-Day Dip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Test a distinct causal SPY/QQQ intraday dip hypothesis and publish actual results with unchanged costs.
**Architecture:** Dedicated dip engine plus existing verified source/statistics adapters, independent scalar oracle and immutable pre-execution snapshots. No bot or archive mutation.
**Tech Stack:** Python3.14, NumPy, pandas, pytest, matplotlib.
**Spec:** studies/adaptive-red-day-dip/PROTOCOL_EXECUTION.md

## Global Constraints
- 21 prior complete sessions, mean max(Open-Close,0), ADR14, confirmed5min, delayedmarketentry1min, noTP, stop/EOD.
- commission max(.35,.0035*q)/side, friction .01/side; variants fixed beforePnL, 84accounts.
- Two existing bots shadow only and untouched; no credentials/API/orders/tasks changes.
- Historical B reused, conditional coverage and repeated-search bias disclosed.

## Review Focus
- Current afternoon must not alter past estimator or first setup.
- Missing history cannot be skipped; unknown active path cannot invent exit.
- First candidate below stop cannot be replaced by a nicer later one.
- Same-minute stop and terminal-wick ordering, gap risk and causal size.
- Public source's mean includes zero green days; no red-subset/low substitution.

### Task1: engine
Files dip/engine.py, tests/test_engine.py. Interfaces history(m,c), select(m,i,c,h=None), prepare(m,c), trace(m,f,c), simulate(m,features,c,start,end).
- [x] Write failing estimator test, run pytest and retain observed RED.
- [x] Implement estimator/scan and reuse own tested ledger with new feature fields.
- [x] Add boundary, causality, coverage, risk/cost/exit tests and scalar parity fixture.
- [x] Run pytest, then fresh read-only pre-PnL code review; fix blockers before execution.

### Task2: frozen study
Files scripts/run_study.py, audit/independent.py, scripts/additional_checks.py.
- [x] Freeze exact14variants, protocols, source/dependency/code fingerprints before firstPnL.
- [x] Run84accounts and capture real pytest evidence.
- [x] Independently replay all features/fills/ledgers; reproduce statistics and uncertainty.

### Task3: delivery
Files report generator, report/figures, README, interpretation, validation, verify_delivery.py, rootREADME.
- [x] Present all scenarios, cost stresses, A/B and concentration; no posthoc winning model promotion.
- [x] Fresh final read-only review, final tests, seal manifest, verify raw sources.
- [x] Check exact staged scope, commit and guarded atomic push to branch and main; verify remoteHEAD and clean tree.


## Pre-PnL development evidence
Observed RED: initial pytest collection failed because dip.engine did not yet exist. The initial fixture put its one red day at index1, which would remain inside the last window; moved it to index0 to test exact boundary inclusion/exclusion. Three reused execution tests initially touched their manual stop through the new signal fixture's later lows; corrected synthetic held lows, not the strategy. No market PnL consulted during these corrections.

Pre-PnL review dip_pre_review:42tests pass, no blocking financial/lookahead finding. P3: red2 initially scanned farther than its stated two preceding sessions and could reject a setup due to an older unknown session. Corrected engine and independent oracle to inspect two days, field explicitly capped2; regression added. Added exact ADR14 boundary and scalar gap/unresolved fixtures. All corrections made before first historical PnL. Other fixture corrections made OHLC rows coherent and used a sufficiently large synthetic gap to exercise actual leverage overflow.

Ruling: user already authorized GitHub publication, so no additional approval gate at the end. One final atomic commit preserves the complete reproducible study as a reviewable unit. Final presentation scripts are created after the pre-PnL financial freeze and do not change simulation rules.

84accounts completed;46tests recorded in TESTS.json. Independent aggregate/uncertainty checks passed:864numbers and6bootstrapaccounts. Presentation-only syntax issue in generated PowerShell example quoting corrected; all10frozenfinancialfiles and15dependencies remain byte-identical. Scalar full replay still running; no final verdict published until it passes.


## Closeout verification
Full scalar replay passed:9175504checks,79080overlappingtrade rows,151928daily rows; 864additionalnumericchecks and6bootstrapaccounts. Fresh final reviewer:46tests; all10code/15dependency/2protocol/463exporthashes andsnapshots match;5656independent numericchecks;8tables/343cells;36bootstrapendpoints includingannualclusters;116local links;4figures inspected. No unresolved finding. Presentation exposure label clarified and common sensitivity X scale used. Root observed bothbots fresh in shadow/SIP weekend waiting states, without modifying them.

Publication is performed after this closeout using sealed manifest, exact staged set, base/remote guards and atomic push. Its final commit/ref verification is recorded in the tool transcript rather than embedded self-referentially into its own commit. No financial rules or frozen artifacts changed after firstPnL.
