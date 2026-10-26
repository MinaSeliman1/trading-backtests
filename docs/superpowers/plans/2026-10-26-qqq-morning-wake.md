# QQQ morning wake repair — Implementation Plan

**Goal:** Wake the sleeping/hibernating PC before the next session, on AC, without changing trading rules or ledger.

**Evidence:** Windows Power-Troubleshooter event1 records sleep2026-10-25T05:02:37Z and wake2026-10-26T16:11:21Z. Independent worker saw a126545second observation gap. Four logical slots10:00–11:30 were processed around11:59logical/12:15wall. Original task only triggers at logon and WakeToRun=false. AC wake timers=2(important only), DC=0(disabled).

**Design:** Separate hidden weekday09:10Toronto/NewYork task with WakeToRun; action only checks/starts the existing fixed shadow SIP task. Separate task is necessary because the long-running task can remain Running through hibernation. Enable ordinary AC wake timers on the active plan, preserve DC/lid/buttons and sleep durations. Keep interactive-user scope, no password. Respect STOP flag and disabled original task; never enable, kill, clear flags, read vault or open SQLite in wake checker. Never send orders.

**Files:** `bots/qqq-noise-area/wake-before-session.ps1`, `install-wakeup.ps1`, tests/test_wakeup.py, BACKGROUND_WINDOWS.md, validation/morning_wake_2026-10-26.*.

**Verification:** Failing PowerShell fixture tests then minimal implementation; existing bot suite. Independent review before deployment. Inspect real Windows task XML, AC/DC policy before/after, manually invoke checker against already-running task, verify ledger table/config/baseline fingerprints unchanged read-only. Do not induce sleep or claim an actual future wake. Store local task/policy backup in ignored runtime/windows. Read-only monitor after deployment. Publish code/proof to trading-backtests.

Limits: no power-on from shutdown, no wake guarantee without AC, user Windows session must be logged in (may be locked), local timezone must match Eastern rules. An explicit daytime sleep can still interrupt the run. Historical catch-up remains incomplete, never relabelled prospective.

Completed26Oct: eight new fixture tests, independent review with no P1/P2,103 regression tests passed/one unrelated native vault test deselected after sandbox access error. Separate wake task installed, manual checker succeeded with already_running, next execution27Oct09:10Eastern. Local StartBoundary explicitly has no offset to follow DST, verified with both seasonal offsets. Full power plan diff shows only AC RTCWAKE2→1; DC0 retained. Ledger/config/baseline/table hashes unchanged. No actual sleep/wake induced. Final delivery gate: publish and compare GitHub commit.
