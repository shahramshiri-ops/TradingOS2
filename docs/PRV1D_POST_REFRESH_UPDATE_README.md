# PRV1D-01 — Post-Refresh Candidate / Lifecycle Update Orchestrator

This patch adds a bounded post-refresh update layer after PRV1C staged refresh.

## What it does

1. Reads PRV1C staged refresh reports.
2. Reads local Twelve Data cache snapshots.
3. Preserves exact SOT02 candidate registry.
4. Updates existing active SOT02 lifecycle rows when the required local cache is available.
5. Rebuilds post-refresh ledger files and panel payload.
6. Writes boundary, no-secret, no-action-surface and validation proofs.

## What it does not do

- It does not create new candidate detection.
- It does not create signals.
- It does not create buy/sell/hold.
- It does not create entry/stop/target.
- It does not create broker/order/execution/PnL/win-loss.
- It does not create validation verdict, adaptation decision or production-readiness claim.

New candidate detection is intentionally not fabricated. PRV1D updates existing exact SOT02 lifecycle rows only.

## Run

```bat
cd personal_runtime_v1
scriptsun_post_refresh_candidate_lifecycle_update.bat
python scriptsalidate_post_refresh_update_outputs.py .
```

## Files to send back

```text
reports\post_refresh_update_plan.json
reports\post_refresh_candidate_detection_report.json
reports\post_refresh_lifecycle_update_report.json
reports\post_refresh_outcome_observation_report.json
ledger\candidate_observation_ledger_v1_post_refresh.json
panel\panel_payload_after_post_refresh_update.json
proofs\post_refresh_secret_redaction_proof.json
proofs\post_refresh_no_action_surface_proof.json
proofs\post_refresh_update_boundary_proof.json
proofs\post_refresh_update_local_validation_result.json
logs\last_run_status_after_post_refresh_update.json
logsuntime_heartbeat_after_post_refresh_update.json
```
