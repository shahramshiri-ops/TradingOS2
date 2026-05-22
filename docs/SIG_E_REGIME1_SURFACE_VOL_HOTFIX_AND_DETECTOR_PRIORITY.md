# SIG-E-REGIME1-SURFACE-VOL-HOTFIX + Detector Priority Fix

This patch:

1. Enriches SIG-E regime surfaces with explicit `d1_vol_bucket` / `volatility_state`.
2. Uses `UNKNOWN` when the volatility bucket is not directly available.
3. Fixes detector priority:
   - session mismatch -> `SESSION_NOT_MATCHED`
   - alignment mismatch -> `REGIME_NOT_MATCHED`
   - volatility missing -> `FIELD_MAPPING_INCOMPLETE` only if session/alignment already match
4. Preserves live-only OHLC policy.
5. Preserves all non-authority boundaries.

No signal, trade proposal, entry/stop/target, risk sizing, broker/execution, auto execution, or memory promotion.
