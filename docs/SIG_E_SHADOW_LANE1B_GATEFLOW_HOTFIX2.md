# SIG-E-SHADOW-LANE1B-GATEFLOW-HOTFIX2

Problem:
Lane1B showed `REGIME` check as passed, but the detector terminal status remained at an earlier gate (`SESSION_NOT_MATCHED` / later normalized to `REGIME_NOT_MATCHED`). That means the label was corrected but the actual detector gateflow did not continue to OHLC/data/setup/trigger/M15.

This patch adds a post-build gateflow repair:

- If regime is not passed, it keeps the correct early gate.
- If regime is passed, it continues to live OHLC source discovery.
- Then it evaluates:
  - live OHLC availability
  - H1/M15 history sufficiency
  - H1 lower-rejection range-expansion setup
  - next H1 bullish close trigger
  - M15 bullish close confirmation
  - diagnostic shadow match

Expected statuses after regime pass:
- `LIVE_OHLC_SOURCE_MISSING`
- `LIVE_H1_HISTORY_INSUFFICIENT`
- `LIVE_M15_HISTORY_INSUFFICIENT`
- `SETUP_NOT_FORMED`
- `H1_TRIGGER_WAIT`
- `H1_TRIGGER_NOT_CONFIRMED`
- `M15_TRIGGER_WAIT`
- `DIAGNOSTIC_SHADOW_MATCH_CONFIRMED`

Boundary:
Diagnostic-only lane. No Lane1 change. No signal. No trade proposal. No entry/stop/target. No risk sizing. No broker/execution. No auto execution.
