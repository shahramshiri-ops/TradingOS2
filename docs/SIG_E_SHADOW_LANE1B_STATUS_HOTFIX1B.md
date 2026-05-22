# SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1B

This fixes the failed previous hotfix.

Why the previous patch failed:
- The detector patch was inserted successfully.
- The original validator file did not contain the expected `result = {` marker, so validator patching failed.

What this robust patch does:
- Completes/keeps the detector status normalizer.
- Does not edit the original validator.
- Adds a separate hotfix validator:
  `scripts/validate_sig_e_shadow_lane1b_status_hotfix1_extra.py`

Expected correction:
- If `session_ok=true` but `alignment_ok=false` or `vol_ok=false`, Lane1B reports:
  `REGIME_NOT_MATCHED`
  not `SESSION_NOT_MATCHED`.
- `source_spec_id` is not null.

Boundary:
Status/metadata only. No setup/trigger/M15 logic change, no Lane1 change, no signal, no trade proposal, no entry/stop/target, no broker/execution.
