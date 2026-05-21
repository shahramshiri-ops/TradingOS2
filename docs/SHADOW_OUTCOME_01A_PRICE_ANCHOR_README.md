# SHADOW-OUTCOME-01A — Price Anchor Patch

## Purpose

`SHADOW-OUTCOME-01` installed correctly, but subjects may be `NOT_OBSERVABLE_RUNTIME_TIMESTAMP_ONLY`
when shadow logs do not carry price-bar anchors.

This patch fixes that by:

1. Inferring instrument from `memory_id` when `instrument` is missing.
2. Using the latest closed H1 bar at or before runtime `created_utc` as a conservative context-derived anchor.
3. Explicitly labelling such anchors as:

```text
CONTEXT_DERIVED_LATEST_CLOSED_H1_BAR
LATEST_CLOSED_H1_BAR_AT_OR_BEFORE_RUNTIME_CREATED_UTC
```

## Boundary

Still not a signal:

- No PnL
- No entry
- No stop
- No target
- No buy/sell
- No broker/execution
- No auto-learning
- No rule rewrite
