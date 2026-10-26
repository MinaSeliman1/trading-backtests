# Previous-day rejection — Implementation Plan

**Goal:** Test a new prior-day failed-breakout hypothesis on SPY/QQQ, same verified SIP sources and fees, publish all results.

**Architecture:** New `studies/previous-day-rejection/`, pure signal/execution engine, reuse source loader and statistical helpers without editing archives. No runtime or bot access. Use inline execution with separate reviewer before PnL and publication.

**Spec:** PROTOCOL_EXECUTION.md and RESEARCH.md in new study.

- [x] Freeze source reasoning and exact rules before market PnL.
- [x] Failing synthetic tests for prior-only range, dividends, half-days, 5m rejection/next-open, window boundaries, unknown bars, rounded stop/target, costs and accounts.
- [x] Implement engine, runner, report, independent audit and verifier. Review, repair, retest before financial loop.
- [x] Freeze code/dependencies/data profile; execute72fixed scenarios and audit all decisions/fills/accounts.
- [x] Inspect standalone figures, seal study and update registry.

Delivery: commit/push and remote hash verification are the final operations; their actual outcome is reported in the final user response.

Legacy studies and bots remain byte-identical. B is reused exploratory chronology, not a fresh blind holdout. Do not choose a winning parameter after inspecting PnL.
