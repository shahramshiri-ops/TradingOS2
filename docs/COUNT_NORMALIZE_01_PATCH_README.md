# COUNT-NORMALIZE-01 / SHADOW-SEMANTICS-01

## Purpose

This patch fixes the confusing interpretation of `near-miss`.

It separates:

- Candidate count
- Diagnostic record count
- Unique market near-miss event count
- Unique memory count
- Blocker diagnostic records
- Eligibility / lifecycle records
- Instrumentation gaps
- Active watch count

## Why

`near-miss = 11` was misleading. It could look like 11 market opportunities,
while in reality it was mostly diagnostic records.

## Outputs

- `runtime/sig_shadow/shadow_count_semantics_current.json`
- `panel/brain4/shadow_count_semantics_current.json`
- `proofs/sig_shadow_count_normalize_01_validation_result.json`

The unified panel is also updated to read `shadow_count_semantics_current.json`.

## Boundary

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
