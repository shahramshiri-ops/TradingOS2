# PRV1M-RC1 — Active Watch Lifecycle Reclassification Patch

## Final verdict
Accepted with Caveats / Patch built; local GitHub Actions proof required.

## What it fixes
The mobile panel showed an Active Watch row as `no_completed_post_trigger_bars_available_yet` even after later H1 candles were available. This patch fixes lifecycle update cache parsing and adds strict validation so that stale reason cannot pass when refreshed cache has bars after trigger.

## Files
- `scripts/run_post_refresh_candidate_lifecycle_update.py`
- `scripts/validate_post_refresh_update_outputs.py`
- `docs/PRV1M_ACTIVE_WATCH_LIFECYCLE_FIX_FA.md`
- `proofs/PRV1M_package_build_proof.json`

## Boundary
Observation-only. No broker, order, execution, signal, buy/sell/hold, entry/stop/target, PnL, optimizer, validation verdict, adaptation decision, or production-readiness claim.
