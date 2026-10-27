# Turn-of-month intraday — Implementation Plan

**Goal:** Research calendar hypothesis on forums/GitHub, test SPY/QQQ at unchanged fees, publish every result without touching active bots.

**Architecture:** New study `studies/turn-of-month-intraday/`, package `tom`. Full-month XNYS labels, pure signal, frozen next-open sizing, optional1%stop, noTP/EOD. Existing source/statistic adapters remain unchanged. Separate monthly-calendar scalar audit. Python3.14, pandas/numpy/matplotlib/pytest.

**Spec:** New study RESEARCH.md and PROTOCOL_EXECUTION.md. User delegates research choice. Alternatives: calendar, relative-strength pair, Dual Thrust. Calendar selected as different mechanism, not because of its external headline returns. No extra permission needed for authorized research/publication.

**Files:** tom/engine.py,data.py,statistics.py; tests; scripts/run_study.py,report.py,verify_delivery.py; audit/independent.py. New docs, dated frozen results and figures. Only legacy edit: global README registry.

**Review:** calendar truncation/holidays/half-days and A/B boundaries, signal-known sizing, no-stop virtual risk, gaps/unknowns/last-bar ordering, controls and monthly clustering.

- [x] Red tests for calendar labels, truncation, signal/fills/costs and controls/statistics.
- [x] Implement and independently review before first market PnL.
- [x] Freeze72scenarios/code/dependencies/source/calendar hashes and execute once.
- [x] Replay independently, inspect report/figures, seal and verify.
- [x] Prepare scoped commit; actual push and remote confirmation reported at delivery.

Execution evidence:30tests;72scenarios;2992740independent replay checks, zero divergences;17862final-review checks;371sealed study fingerprints. Six references positive, but both ALL monthly-contrast IC95 include zero: predefined candidate criterion fails. No bot change. Final publication status is reported in the delivery after remote verification.
