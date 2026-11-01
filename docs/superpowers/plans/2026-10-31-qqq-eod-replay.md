# QQQ End-of-Day Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Task0: immutable-code SIP replay and honest live comparison, stop before external task2.
**Architecture:** Pinned source snapshot, data-only captures, causal adapters, separate transactional ledger and Windows scheduled launcher.
**Tech Stack:** Python3.14,pandas/NumPy,SQLite,exchange_calendars,pytest,TaskScheduler.
**Spec:** bots/qqq-eod-replay/PREREGISTRATION.md and ENGINE_LOCK.json.

## Global Constraints
- Commit before PnL, first prospective2026-11-02,100000USD each.
- Noise4x/ORB1x, original fees/signals; no live journal/task mutations.
- QQQ SIP GET only; no secret output/order routes.
- Unknown outcome never cash; backfill not intraday observation.

## Review Focus
- Causal prefixes and ORB late_start avoidance.
- Unresolved data/account continuity; no loss omission.
- Actual capture vs logicalclock, DST/half-days.
- Capital/state/revision differences in live comparison.
- Immutable deployment, idempotent catchup, read-only SQLite.

### Source registration
- [ ] Commit/publish protocol and engine fingerprints before PnL.
### Implementation
- [ ] RED schedule/snapshot/transport tests, implement source.py/schedule.py.
- [ ] RED prefix/parity/cost tests, implement replay.py using frozen code.
- [ ] RED ledger idempotence/unresolved tests, implement journal.py/live.py.
### Deployment
- [ ] CLI/captures/retries/safe errors and synthetic tests.
- [ ] Retrospective integration diagnostic, never prospective claim.
- [ ] Pin deployed code, install distinct Windows task and verify.
### Delivery
- [ ] Independent review, full checks, report and exact-scope publication.
- [ ] Wait for user green light before external task2.
