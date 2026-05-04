# PRV1 Release Notes

## Release candidate status

Accepted with Caveats / Personal Runtime V1 Release Candidate Built from accepted local daily runtime proof.

## Included capabilities

- one-command daily runtime loop via `RUN_DAILY.bat`
- rate-limit-aware staged credentialed read-only refresh
- 11/11 surface refresh proof from latest local run
- post-refresh lifecycle update
- corrected cache-read candidate detection
- panel/status/proofs generation
- daily status count correction applied

## Last accepted local proof

`proofs/daily_runtime_local_validation_result.json` passed, and `proofs/daily_runtime_status_count_correction_proof.json` corrected the final status count fields.

## Not included

No broker, orders, execution, signal, buy/sell/hold, entry/stop/target, PnL, win/loss, optimizer, validation verdict, adaptation decision, production readiness, source2, or calendar/event logic.
