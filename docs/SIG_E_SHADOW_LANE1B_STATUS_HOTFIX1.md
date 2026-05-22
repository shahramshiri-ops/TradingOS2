# SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1

Fixes a status-label inconsistency in Lane1B.

Observed issue:
- `session_bucket = LONDON_NY_OVERLAP`
- `session_ok = true`
- `alignment_ok = false`
- `vol_ok = true`

but detector emitted:
- `detector_status = SESSION_NOT_MATCHED`
- `status_reason = session_not_london_ny_overlap`

Correct status:
- `detector_status = REGIME_NOT_MATCHED`
- `status_reason = overlap_long_diagnostic_regime_not_matched`

Also fixes:
- `source_spec_id` must not be null.

Boundary:
This patch only normalizes status/metadata and validation invariants. It does not change setup, trigger, M15 confirmation, shadow-match logic, Lane1, portfolio semantics, signal authority, trade proposal authority, or broker/execution.
