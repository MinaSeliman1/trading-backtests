# QQQ End-of-Day Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Task0: immutable-code SIP replay and honest live comparison, stop before external task2.
**Architecture:** Pinned source snapshot, data-only captures, causal adapters, separate transactional ledger and inactive GitHub Actions workflow.
**Tech Stack:** Python3.14,pandas/NumPy,SQLite,exchange_calendars,pytest,GitHub Actions.
**Spec:** bots/qqq-eod-replay/PREREGISTRATION.md and ENGINE_LOCK.json.

## Global Constraints
- Commit before PnL, first prospective strictly after approved stop-rule commit,100000USD each.
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
- [x] Commit/publish protocol and engine fingerprints before PnL.
### Implementation
- [x] RED schedule/snapshot/transport tests, implement source.py/schedule.py.
- [x] RED prefix/parity/cost tests, implement replay.py using frozen code.
- [x] RED ledger idempotence/unresolved tests, implement journal.py/live.py.
### Deployment
- [x] CLI/captures/retries/safe errors and synthetic tests.
- [x] Retrospective integration diagnostic, never prospective claim.
- [x] Pin sources/dependencies, publish inactive Actions workflow and verify real synthetic artifact transport.
### Delivery
- [x] Independent review, full checks, report and exact-scope publication.
- [x] Deliver task0 and wait for user green light before task7 calibration/activation and subsequent research.

User clarified Actions from task0 and rule7 on the current frozen model/costs before the new statistical start. This plan supersedes its initial Windows proposal. No new Windows replay job, no live-bot source/runtime edits. Future rule7 policy adapter and numeric bands deliberately remain outside task0.
