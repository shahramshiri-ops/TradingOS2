# SHADOW-OUTCOME-01 — Shadow Outcome Observer

## Purpose

Observe what happened after shadow objects, without creating a trade.

Subjects:

- Shadow candidates
- Setup shadow records
- Trigger shadow records
- Blocker shadow records
- Diagnostic records

Horizons:

- H1+1
- H1+2
- H1+4
- H1+8

## What it measures

Path-only observations:

- horizon close delta
- MFE-like high excursion
- MAE-like low excursion
- directional favorable/adverse/flat if direction is known

## What it does NOT do

- No PnL
- No entry
- No stop
- No target
- No buy/sell
- No position size
- No broker/execution
- No auto-learning
- No rule rewrite

## Outputs

- `runtime/sig_shadow/shadow_outcome_observation_ledger_current.json`
- `runtime/sig_shadow/shadow_outcome_status_current.json`
- `panel/brain4/shadow_outcome_status_current.json`
- `runtime/sig_shadow/live_logs/YYYY-MM-DD/outcome_observation_log_YYYY-MM-DD.jsonl`
- `proofs/sig_shadow_outcome_01_validation_result.json`
