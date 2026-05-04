# PRV1C-01 — Rate-Limit-Aware Staged Refresh Orchestrator

Created at UTC: 2026-05-04T12:09:02Z

## Purpose

PRV1C fixes the PRV1B full-refresh weakness: the prior full run attempted all 11 surfaces too quickly and the provider blocked the last XAUUSD surfaces due to the observed per-minute credit limit.

PRV1C changes the refresh model from full-blast to staged:

```text
batch 1: EURUSD D1/H1/M15/M5
wait
batch 2: USDJPY D1/H1/M15/M5
wait
batch 3: XAUUSD D1/H1/M15
retry failed surfaces only
```

## Run plan-only first

```bat
cd personal_runtime_v1
scriptsun_staged_refresh_plan_only.bat
```

## Run staged refresh

```bat
cd personal_runtime_v1
scriptsun_staged_credentialed_refresh.bat
python scriptsalidate_staged_refresh_outputs.py .
```

The script reads only this local environment variable:

```text
LFB_TWELVE_DATA_API_KEY
```

Do not send `.env`, API keys, tokens, or secrets back to ChatGPT.

## Files to send back for review

```text
reports\staged_refresh_plan.json
reports\staged_provider_fetch_report.json
reports\staged_cache_update_report.json
reports\staged_row_level_ledger_refresh_report.json
panel\panel_payload_after_staged_credentialed_refresh.json
proofs\staged_secret_redaction_proof.json
proofs\staged_no_action_surface_proof.json
proofs\staged_refresh_boundary_proof.json
proofs\staged_refresh_local_validation_result.json
logs\last_run_status_after_staged_refresh.json
logsuntime_heartbeat_after_staged_refresh.json
```

## Boundaries

This is read-only cache refresh only. It is not a signal engine, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL/win-loss, not optimizer, not validation verdict, not adaptation decision, and not production readiness.
