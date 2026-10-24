# Noise Area Windows sleep fix

> Implementation: native in this session; regression tests followed by an independent review.

**Goal:** prevent automatic sleep while the hidden simulation runs plugged in, and diagnose future coverage gaps without changing trades or strategy parameters.

**Evidence and scope:** the preserved October 21 journal records timely decisions at 10:00, 10:30, 15:00 and 15:30 logical New York time. All eight intervening decisions were replayed at approximately 15:11:50 actual time. Windows reports sleep at 10:55:52 (Button or Lid), hibernation at 13:56 and wake at 15:11:10. The user explicitly chooses automatic sleep prevention only and will leave the lid open. No lid, power-button, battery, sleep-plan or trading-parameter changes.

**Design:** a separate thread owned by the existing hidden supervisor holds a Windows system execution request only on AC, for the supervisor's lifetime. It releases the request on battery and on shutdown. Keeping it overnight avoids automatic sleep preventing the next morning's protection from starting; no wake timer or permanent power-plan changes are needed. Display sleep remains allowed. Independent polling keeps this protection alive during data/API waits. A separate ignored status file records power protection and loop interruptions without credentials. The read-only monitor reports protection failures and timings on incomplete sessions. Its alert window uses real NYSE session open minus 15 minutes through close plus 20 minutes, including the SIP delay. Original session records remain immutable.

**Files:** new `qqq_paper/power.py` and `tests/test_power.py`; modify `qqq_paper/background.py`, `qqq_paper/monitor.py`, monitor/background tests and `BACKGROUND_WINDOWS.md`; add a sanitized incident report and verification evidence under `validation/`.

## Checks

- [x] Snapshot SQLite using the read-only source and back up safe Windows power events under ignored runtime diagnostics.
- [x] Regression tests first: AC activation and overnight retention; battery/unknown AC release; calendar alert windows; same-thread cleanup; operator stop; error recovery; monitor diagnosis from immutable decision timestamps.
- [x] Minimal implementation, full bot tests (96 passed) and independent code review (no remaining findings).
- [x] Controlled restart of the existing shadow/SIP task on October 24; no reset, no pause clearing, no broker orders; existing ledger and prospective baseline fingerprints unchanged.
- [x] Fresh engine heartbeat and successful native Windows request verified; sanitized evidence saved in `bots/qqq-noise-area/validation/sleep_fix_2026-10-24.json`. Administrator-only `powercfg /requests` inspection was unavailable and no machine sleep was induced.

Delivery includes only this fix and its documentation; unrelated ORB/NR7 work remains outside the commit.

**Limit:** no execution request prevents explicit sleep, lid-triggered sleep, shutdown, a lost network or loss of AC. The October 21 day remains incomplete and October 22 missing; successful future coverage must be observed, never imputed.
