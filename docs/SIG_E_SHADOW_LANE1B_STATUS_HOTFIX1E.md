# SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1E

This replaces the 1D normalizer with a more robust normalizer.

Why 1D failed:
It filled `source_spec_id`, but did not reclassify the status because it only handled exact boolean fields. The runtime output still had `SESSION_NOT_MATCHED` even though overlap context was present.

What 1E changes:
- Handles boolean strings and boolean values.
- Searches nested objects for regime details.
- Treats visible `LONDON_NY_OVERLAP` context as proof that this is not a session miss.
- Reclassifies `SESSION_NOT_MATCHED` to `REGIME_NOT_MATCHED` when overlap is visible but alignment/volatility/regime failed.
- Updates workflow calls from 1D to 1E.

Boundary:
Runtime status/metadata normalization only. No setup/trigger/M15 logic change, no Lane1 change, no signal, no trade proposal, no entry/stop/target, no broker/execution.
