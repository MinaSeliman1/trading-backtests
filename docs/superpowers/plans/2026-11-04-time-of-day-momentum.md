# Time-of-Day Momentum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test a previously untested time-of-day continuation hypothesis on QQQ/SPY with unchanged costs, causal controls and complete publication.
**Architecture:** Reuse only the verified local market loader/statistical helpers; add a self-contained seasonal feature/trace/account engine, scalar audit and reports. No edits to running bots.
**Tech Stack:** Python3.14, NumPy, pandas, exchange_calendars, pytest, matplotlib, local SIP cache.
**Spec:** studies/time-of-day-momentum/PROTOCOL_EXECUTION.md and RESEARCH.md.

## Global Constraints
- Fixed hypothesis, all96accounts, source hashes and code committed before first market P&L; no rule tuning after returns.
- Same costs, 100000USD independent accounts, 1x causal cap and1% risk target. Source period/cuts from existing loader, reused B disclosed.
- No API/keys, no bot changes, no overwrite of previous executions. Public results exclude raw data and credentials.
- Read-only data validation, no fill interpolation, stop/gap and partial coverage explicit.

## Review Focus
- Future-day and future-current-bar mutations cannot change an earlier candidate, quantity or stop.
- A missing earlier historical clock cannot silently promote a later candidate.
- Stops on entry/scheduled exit and missing bars do not invent fills or double count costs.
- Controls are fixed before the session; paired comparison is on common admissible resolved days.
- Monte Carlo capital is fixed, distinct from compounded trading accounts; Holm only covers this study.

### Task1: causal features, trade engine and controls
- [ ] Write synthetic failing tests for historical shifts, candidate chronology, unknown history, half days and stop/cost accounting.
- [ ] Implement seasonal/engine.py, data.py and analysis.py with verified loader delegation.
- [ ] Add independent scalar audit and randomized synthetic comparisons; run tests.
- [ ] Review code/protocol, freeze code/dependencies/protocols and commit BEFORE market P&L.

### Task2: execution and validation
- [ ] Run16variants x2ETF x3periods on verified local SIP history; export all daily/trade/unresolved/features/quality rows.
- [ ] Bootstrap, paired controls/Holm, random-clock panel1000, concentration, stress and full scalar reference parity.
- [ ] Fix only demonstrated coding errors with explicit new execution/receipt, never tune a rule after returns.

### Task3: report and publication
- [ ] Generate tables and standalone figures, source/limitations/interpretation, reproducible commands and delivery hashes.
- [ ] Verify row counts, money reconciliation, audit, file links, immutable result manifest and absence of secrets/raw data.
- [ ] Check existing simulations read-only; publish code/results/report in trading-backtests and keep the20-session follow-up.


## Execution ledger before market P&L
- Research chose same-clock return persistence, distinct from existing breakout/reversion studies; user delegated strategy selection and implementation. No design approval pause added to this already-authorized research workflow.
- TDD: missing engine, missing statistics and missing freeze guards failed as expected; core suite reached44pass before synthetic full-run test.
- Ruling: treat sigma<=1e-12 as numerical zero, frozen before any market P&L; avoid false infinite-score signals from floating-point residues.
- Review corrections before P&L: modeled exit friction included in MAE; missing-aware weighted calendar bootstrap for the economic gate and paired differences; both-trading100-date requirement; current/snapshot/dependency/source-profile binding; execution directory restricted under the study.
- The study uses an isolated new directory on codex/time-of-day-momentum in the shared checkout because the existing working folder hosts running bots and verified local caches. Only new-study files, plan and later README are in scope; no bot/runtime reset or shared model edit.
