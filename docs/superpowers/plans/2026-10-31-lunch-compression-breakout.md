# Lunch Compression Breakout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Test distinct midday compression/afternoon breakout SPY/QQQ and publish all results at unchanged fees.
**Architecture:** Dedicated lunch engine; existing verified source/statistics adapters and own execution ledger; independent scalar context/scan/replay; immutable pre-PnL snapshot.
**Tech Stack:** Python3.14, NumPy, pandas, pytest, matplotlib.
**Spec:** studies/lunch-compression-breakout/PROTOCOL_EXECUTION.md

## Global Constraints
- morning0:120, lunch120:180, compression<.3, freshclosecross after210 through300, volume>lunchmean, midpointstop, delayedmarket+1min, EOD389.
- One long/day, risk1%, target1x beforefill, .0035/share min.35 commission/side and .01 adversefriction/side.
- 84fixedaccounts, reusedA/B, conditionalcoverage; never modify bots/runtime/tasks/vault/orders or previous studies.
- User delegated strategy choice and GitHub publication; no new design/approval question needed.

## Review Focus
- Post-lunch highs/lows cannot change fixed levels or earlier signal.
- A close already above at13h is not a fresh cross.
- First fresh cross without volume consumes day; equality boundaries fail.
- Same units for minute volume across1/5/15bars and extended lunch.
- Unknown scan/held path, stopgap, terminalwicks and prefill size cannot become optimistic.

### Task1: engine and tests
Files lunch/engine.py, tests/test_engine.py. Interfaces context(m,i,c), select(m,i,c), prepare(m,c), trace(m,f,c), simulate(m,fs,c,start,end).
- [x] Write failing compression/cross test; observe RED before implementation.
- [x] Implement context and fixed scan, reuse own ledger; boundary/causality/volume/quantity/fees/gap/unknown tests.
- [x] Build independent scalar oracle and synthetic parity; run tests then fresh readonly pre-PnL review.

### Task2: frozen computations
Files scripts/run_study.py, audit/independent.py, scripts/additional_checks.py.
- [x] Freeze protocols/code/source/dependencies and exact14variants before any historical PnL.
- [x] Run84accounts, record actual tests, full scalar reconciliation and independent statistical/CIchecks.

### Task3: delivery
Files report/docs generators, README, validation, interpretation, fourfigures, rootREADME and finalmanifest.
- [x] Present actual results A/B/ALL, everyvariant, costs, concentration and caveats; no posthoc promotion.
- [x] Fresh final readonly review and source/hash verification, inspect figures and seal manifest.
- [x] Verify exactstagedscope, commit and guardedatomicpush to branch/main, verifyremoteHEAD and cleantree.


## Development evidence before PnL
Initial RED observed: no lunch.engine module. Initial signal fixture passed after implementation. Expanded40tests passed; matrix test exposed namespace collision with another study's scripts.run_study loaded by the source-adapter path. Test now loads the intended runner by exactfile path, avoiding false verification of another matrix. Production runner imports its lunch package explicitly. No historical PnL consulted.

Additional RED beforePnL: scalar replay from exported configuration lacked the Config-only stop_enabled property. Removed this unnecessary condition from both ledgers: stops are always active in this study. Added exported-record replay regression, then47tests expected.

Pre-PnL reviewer also identified that old aggregate audit assumed trades/losses/nonzerovariance. Four observedREDtests added for zero-trade/all-winning/mixed accounts and missing-stat parity. Added independent guarded WR/PF/Sharpe and strict missing-only comparisons; execution rules unchanged, all51tests expected beforefreeze.

Full84accounts completed without changing rules. Scalar replay passed7177660checks/5474overlappingtrades/151928dailyrows; independent864numericchecks and6bootstrapaccounts passed. Financial10files remain unchanged sincefreeze. ReferenceALL has78SPY/97QQQtrades, belowpredeclared100; no parameter loosened afterPnL. Finalreview/seal/publication remain to complete.


## Closeout
Fresh finalreview lunch_final_review:51tests,10code/15dependencies/2protocols/463exporthashes match;84matrix/summaryconfigs checked;screen recomputed;25local links;raw/cache/calendarprofile and4PNG checked. No financial blocker. P3 ambiguous doubling label fixed in reportgenerator and output to friction doubled (not commission), verified by root. Root inspected4figures and read both fresh shadow/SIP waiting statuses without mutation.

Final seal/exactstage/commit/guardedatomicpush and remote clean verification are executed after this closeout. Their finalref evidence is kept in the tool transcript rather than self-referentially embedded into the same commit. All10frozenfinancialfiles unchanged since firstPnL.
