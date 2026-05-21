# REASON-UPSTREAM-01 / DIAG-02

## Purpose

This patch improves near-miss reason quality.

It replaces vague `UNKNOWN_NEAR_MISS_REASON` with:

- exact structural reasons where possible
- inferred reasons with confidence
- explicit instrumentation-gap reasons where upstream did not emit enough detail

## Key outputs

- `runtime/sig_shadow/near_miss_reason_source_current.json`
- `runtime/sig_shadow/near_miss_reason_quality_current.json`
- `runtime/sig_shadow/near_miss_reason_enriched_current.json`
- `proofs/sig_shadow_reason_upstream_01_validation_result.json`

It also updates:

- `runtime/sig_shadow/shadow_ops_status_current.json`
- `panel/brain4/shadow_ops_status_current.json`

so the unified panel can show better top reasons.

## Boundary

Diagnostic only:

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
