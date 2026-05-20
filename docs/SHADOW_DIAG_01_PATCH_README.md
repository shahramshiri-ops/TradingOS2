# SHADOW-DIAG-01 — Near-Miss / Blocker / Eligibility Diagnostic Hardening

## Purpose

This patch turns raw `near_miss_count` into explainable diagnostics.

It answers:

- Which memory was near-miss?
- Why did it not become a shadow candidate?
- Was it out-of-core?
- Was it expired or invalidated?
- Was it blocked by candidate intake policy?
- Was it one step from candidate?
- Which stage failed most often?

## Outputs

- `runtime/sig_shadow/near_miss_detail_ledger_current.json`
- `runtime/sig_shadow/blocker_reason_breakdown_current.json`
- `runtime/sig_shadow/eligibility_diagnostic_current.json`
- `runtime/sig_shadow/shadow_near_miss_summary_current.json`
- `panel/brain4/shadow_near_miss_summary_current.json`
- `proofs/sig_shadow_diag_01_validation_result.json`

## Boundary

This patch is diagnostic only:

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE

## Important interpretation

A near-miss is not a trading opportunity. It is a diagnostic record explaining why a market state did not become a complete shadow candidate.
