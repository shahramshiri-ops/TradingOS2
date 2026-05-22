# SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1C

Fixes the syntax error in Hotfix1B.

Previous issue:
`patch_sig_e_shadow_lane1b_status_hotfix1b.py` failed with:

`NORMALIZER =` / `SyntaxError: invalid syntax`

This 1C version avoids nested triple-quote string generation entirely and builds the inserted normalizer from a list of safe single-line strings.

Expected correction:
- `source_spec_id` is not null.
- If `session_ok=true` but `alignment_ok=false` or `vol_ok=false`, Lane1B reports `REGIME_NOT_MATCHED`, not `SESSION_NOT_MATCHED`.

Boundary:
Status/metadata only. No setup/trigger/M15 logic change, no Lane1 change, no signal, no trade proposal, no entry/stop/target, no broker/execution.
