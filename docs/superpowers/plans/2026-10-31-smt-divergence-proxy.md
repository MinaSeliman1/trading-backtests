# SMT ES/NQ Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Test incremental SMT value vs bias/time controls using authorized ES/NQ proxies at micro economics, without fake confirmation on MNQ/MES.
**Architecture:** Verified rawfile loader/calendar/rollguard; causal minute signal engine; one-contract stop/TP executor; precomputed candidate outcome grid; deterministic random portfolios; independent scalar reviews and immutable receipts.
**Tech Stack:** Python3.14, NumPy/pandas, exchange_calendars, pytest, matplotlib; no API execution.
**Spec:** studies/smt-divergence-proxy/DESIGN.md then finalPROTOCOL_EXECUTION.md beforePnL.

## Global Constraints
- Six principal variants only: H1/H2×A/B/C, levels pooled priorityLondon/pre/previous on same-minute ties.
- User approved existing continuous ES/NQ proxies, micro2USDpoint/.25tick and1.25USDside. Not actualmicrofills.
- Never use old-contract previous levels across uncertain rolls; disclose calendar exclusions, not invented exact switch dates.
- One first trade/setup per day, causal closedbar to nextopen, stopfirst dualtouch, forced11:30.
- Two controls,1000randomportfolios, H3notrade; all scenarios and invalidgeometrycounts exposed.
- No bot/runtime/task/vault/order mutation. User already authorizes publication in existing research repo.

## Review Focus
- NY/UTC/DST, previoussession/halfday data, missingbar vs knownclosure.
- Continuous roll contamination of previouslevels and SMA20, no invented contractidentity.
- Signalstate vs futurefill filters and H2samebar reclaim/cancellation.
- Counterfactual control direction or future signal leakage, especiallyC.
- RNG/multiplicity, fair exposure/target comparability and rare samples.

### Task1: source/calendar
- [x] RED tests timezone, pairedvalidity and calendarrollguards; implement smt/data.py.
- [x] Profile inputs and source evidence withoutPnL; acquire only public news calendars.

### Task2: frozen hypotheses/engine
- [x] Resolve remaining user conventions, finalize protocol and analysisgate.
- [x] RED signal/executor/control tests; implement pure functions and candidategrid.
- [x] Fresh readonly pre-PnL review, fix findings beforefreeze.

### Task3: experiment/delivery
- [x] Freeze protocols/code/source hashes; run principals, two controls,1000portfolios andH3, then discover-only leveldiagnostic.
- [ ] Independent replay/statistical checks, report/figures/proxy limits, finalreview.
- [x] Prepare final manifest verification and exact-scope guarded atomic publication procedure; the final delivery message records the actual remote-ref and clean-tree confirmation.
