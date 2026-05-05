# PRV1N Final Delivery Pack

## Verdict
Accepted with Caveats / Active Watch Truth Patch Built; GitHub Actions Proof Required.

## Files
- scripts/run_post_refresh_candidate_lifecycle_update.py
- scripts/validate_post_refresh_update_outputs.py
- docs/PRV1N_ACTIVE_WATCH_TRUTH_FIX_FA.md
- proofs/PRV1N_package_build_proof.json

## Install
Copy these files into the root of the TradingOS2 repo, commit, push, and run the PRV1 Daily Runtime Mobile Panel workflow.

## Expected proof
After workflow run, inspect:
- reports/post_refresh_lifecycle_update_report.json
- reports/active_watch_truth_debug_report.json
- proofs/post_refresh_update_local_validation_result.json
- public/status_public.json
- public/market_state_public.json

The stale Active Watch reason must not remain if post-trigger bars exist.
