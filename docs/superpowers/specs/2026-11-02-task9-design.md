# Task 9 — Free simulation alerts

User approval: activate free push for both QQQ bots, daily life message and prompt crash/data-delay/unresolved/STOP notices, publish report; no strategy, fee, rule, ledger reset or broker order.

Approach: a separate Windows read-only watchdog (30 second loop), ntfy anonymous random topics in a new Windows credential slot and Actions Secrets, and a dedicated Actions notification workflow. Telegram requires a destination/bot not present; provider/device question is pending. ntfy is the proposed default, not an authenticated private topic: only generic technical states leave the PC. A second unguessable topic carries minimal technical health for the cloud daily message; it is never the user subscription.

The daily cloud life message is 09:20 America/New_York, including non-session days clearly labelled. During XNYS observation windows (09:10 through close+20 minutes), local process PID/engine heartbeat and read-only journals detect errors, missed logical decisions, unresolved positions and STOP. No old gaps are re-alerted. Persistent STOP/unresolved positions remain alertable outside session; normal waiting/flat and no-signal days are healthy.

A server-side dead-man message is refreshed every five minutes, expiring after twelve minutes during observation windows. Outside a window it is scheduled for the next XNYS 09:20 only if within ntfy's three-day horizon, otherwise removed. This limits free publication volume and provides an external alarm if the PC/network/watchdog dies; no instant phone delivery guarantee is claimed. Local crash check aims <=30 seconds plus delivery; stale engine threshold180 seconds; decision tolerance120 seconds on wall-clock minus16 minutes; half-days/DST use XNYS.

Durable alert outbox, deduplication and one recovery notice; a failed POST is never marked delivered. Generic fixed message templates omit credentials, subscription addresses, account identifiers, quantities and P&L. Fixed HTTPS ntfy.sh destination, no redirects; protected new configuration, no PAPER or EOD state key access. Notification failure never modifies/restarts trading bots. Cloud workflow_run reads trusted main run metadata/summary only, alerts failed replay and unresolved/risk STOP; no provider key access.

Receipt of a real test on the user's phone must be reported separately from server acceptance. User subscription remains a necessary user-side step. No paid topic reservation, service, runner or dependency purchase. No task10/11 implementation.
