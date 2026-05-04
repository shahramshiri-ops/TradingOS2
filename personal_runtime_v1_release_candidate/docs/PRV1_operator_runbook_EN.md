# PRV1 Operator Runbook — Release Candidate

## Main command

From the release-candidate folder, run:

```bat
RUN_DAILY.bat
```

This runs:

1. preflight
2. staged credentialed refresh
3. cache validation
4. post-refresh lifecycle update
5. candidate detection from local cache
6. final panel/status/proofs

## Main outputs

- `panel/panel_payload_after_daily_runtime.json`
- `panel/index_daily_runtime.html`
- `logs/last_run_status_after_daily_runtime.json`
- `logs/runtime_heartbeat_after_daily_runtime.json`
- `proofs/daily_runtime_local_validation_result.json`

## Last accepted local proof summary

- candidate_count: 4
- lifecycle_count: 4
- final_outcome_count: 3
- active_tracking_count: 1
- new_observation_candidate_count: 0

## Boundaries

This is display-only runtime observation. It is not a signal, trade recommendation, buy/sell/hold instruction, entry/stop/target, broker/order/execution system, PnL/win-loss system, optimizer, validation verdict, adaptation decision, or production-readiness claim.

Do not share `.env`, API keys, tokens, or secrets. The credential must remain local as `LFB_TWELVE_DATA_API_KEY`.
