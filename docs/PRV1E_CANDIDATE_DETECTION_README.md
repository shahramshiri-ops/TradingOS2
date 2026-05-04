# PRV1E — Local Candidate Detection Rule Engine Sprint

Created at UTC: 2026-05-04T12:46:57Z

## Purpose

PRV1E adds a bounded, cache-based observation candidate detector after PRV1C/PRV1D.

It reads refreshed local provider cache and existing SOT02 registry/lifecycle state, then proposes new observation candidate rows if the accepted range-breakout rule is met.

## What it is not

It is not a signal engine, not trading advice, not buy/sell/hold, not entry/stop/target, not execution, not PnL/win-loss, not optimizer, not validation verdict, not production readiness.

## Required local precondition

Run PRV1C staged refresh first, then PRV1D post-refresh update. PRV1E expects provider cache files under:

```text
data/provider_cache/twelve_data/
```

## How to run

```bat
cd personal_runtime_v1
scriptsun_candidate_detection_rule_engine.bat
python scriptsalidate_candidate_detection_outputs.py .
```

## Files to send back

```text
reports\candidate_detection_report.json
reports\candidate_registry_update_report.json
reports\candidate_lifecycle_seed_report.json
ledger\candidate_lifecycle_rows_v1_after_candidate_detection.json
ledgerctive_tracking_rows_v1_after_candidate_detection.json
ledger\outcome_observation_rows_v1_after_candidate_detection.json
ledger\candidate_evidence_index_v1_after_candidate_detection.json
state\prv1e_candidate_detection\candidate_detection_new_rows_v1.json
panel\panel_payload_after_candidate_detection.json
proofs\candidate_detection_secret_redaction_proof.json
proofs\candidate_detection_no_action_surface_proof.json
proofs\candidate_detection_boundary_proof.json
proofs\candidate_detection_local_validation_result.json
logs\last_run_status_after_candidate_detection.json
logsuntime_heartbeat_after_candidate_detection.json
```

Do not send `.env`, API keys, tokens, or credentials.
