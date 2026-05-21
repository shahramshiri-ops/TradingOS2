# SHADOW-OUTCOME-01D — Freshness / Pending Completion Guard

## Purpose

01C connected outcome to live M5 data. 01D makes the outcome data trustworthy enough for future analytics.

It adds:

- Live freshness tiers:
  - LIVE_FRESH: <= 30 minutes
  - LIVE_LAGGING: 30–90 minutes
  - LIVE_STALE: 90 minutes–6 hours
  - LIVE_BROKEN: > 6 hours
- Closed-H1-only guard
- Pending carry-forward state
- Stable subject/horizon keys
- Duplicate inflation control
- Horizon completion ladder for H1+1 / H1+2 / H1+4 / H1+8

## Boundary

No signal, no PnL, no entry/stop/target, no broker/execution, no auto-learning, no rule rewrite.
