# SHADOW-PANEL-02 — OPS Diagnostics Panel Integration

Adds a visible operational diagnostics card to the Brain4 panel.

It reads:

- `panel/brain4/shadow_ops_status_current.json`

It displays:

- Health PASS/WARN/FAIL
- Last-run candidate / near-miss / high near-miss / blocked
- Core-eligible vs extended-only active watches
- Top near-miss reasons
- Top failed stages
- Daily / weekly / cohort rollups
- Review queue count

Boundary:

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
