# SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1D

This patch changes strategy: instead of trying to patch the unknown internals of the Lane1B builder, it adds a stable post-build normalizer.

Why:
The earlier detector patch was present but not actually affecting the runtime output. This means the build script path being executed is not using the inserted call as expected.

What this patch does:
- Adds `scripts/normalize_sig_e_shadow_lane1b_status_hotfix1d.py`
- Runs it after `build_sig_e_shadow_detector1b_overlap_diagnostic.py`
- Runs a dedicated validator after normalization
- Patches the workflow so the normalizer runs every refresh

Expected correction:
- `source_spec_id` is filled.
- If `session_ok=true` but `alignment_ok=false` or `vol_ok=false`, Lane1B becomes `REGIME_NOT_MATCHED`, not `SESSION_NOT_MATCHED`.

Boundary:
Runtime status/metadata normalization only. No setup/trigger/M15 logic change, no Lane1 change, no signal, no trade proposal, no entry/stop/target, no broker/execution.
