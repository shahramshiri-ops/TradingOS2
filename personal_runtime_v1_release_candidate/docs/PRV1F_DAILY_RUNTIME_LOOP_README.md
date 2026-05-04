# PRV1F-01 — One-Command End-to-End Daily Runtime Loop

## Purpose

This patch turns PRV1 into a one-command daily runtime loop.

Run:

```bat
scripts\run_daily_runtime.bat
python scripts\validate_daily_runtime_outputs.py .
```

The loop executes:

1. PRV1F preflight.
2. PRV1C staged credentialed read-only refresh.
3. PRV1D post-refresh lifecycle update.
4. PRV1E corrected candidate detection from local cache.
5. Final daily panel/status/heartbeat/proofs.

## Boundary

This is display-only personal runtime observation. It is not a signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, and not production readiness.

## Required local condition

`LFB_TWELVE_DATA_API_KEY` must already exist as a local environment variable. Do not send it in chat and do not place it in outputs.

## Outputs to send back after local run

```text
reports\daily_runtime_preflight_report.json
reports\daily_runtime_step_report.json
panel\panel_payload_after_daily_runtime.json
proofs\daily_runtime_secret_redaction_proof.json
proofs\daily_runtime_no_action_surface_proof.json
proofs\daily_runtime_boundary_proof.json
proofs\daily_runtime_local_validation_result.json
logs\last_run_status_after_daily_runtime.json
logs\runtime_heartbeat_after_daily_runtime.json
```
