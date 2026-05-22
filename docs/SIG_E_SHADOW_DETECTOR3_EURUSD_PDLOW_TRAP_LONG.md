# SIG-E-SHADOW-DETECTOR3 — EURUSD Prior-Day-Low Trap Long

Adds Lane 3:

`EURUSD / London or London-NY overlap / Prior-day-low failed breakdown reclaim / Long / H1+M15`

This is live shadow observation only, not a signal.

Detector:
- Regime: EURUSD H1 context, London/overlap, long-supportive or H4/H1 aligned-up context
- Reference: prior UTC-day low computed from live H1 rows
- Setup: previous H1 sweeps below prior-day low and closes back above it with lower-rejection structure
- Trigger: next H1 bullish close above prior-day low
- M15 confirm: bullish M15 close above prior-day low inside trigger H1
- Observation horizon: H12

Boundaries:
No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution, no auto execution.
