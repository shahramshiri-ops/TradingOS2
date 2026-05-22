# SIG-E Shadow Detector1 HOTFIX3

This patch does three things:

1. Propagates explicit volatility fields to all relevant live context payloads:
   - `runtime/sig_e/market_state_current.json`
   - `runtime/sig_e/sig_e_regime1_market_state_current.json`
   - `panel/brain4/sig_e_market_state_current.json`
   - `runtime/sig_brain/sig_brain5_derived_context_latest.json`
   - `inputs/sig_brain4_live_context_latest.json`

2. Makes the detector prefer SIG-E market-state surfaces before Brain5/input fallback.

3. Keeps the corrected status priority:
   - session mismatch -> `SESSION_NOT_MATCHED`
   - alignment mismatch -> `REGIME_NOT_MATCHED`
   - volatility missing -> `FIELD_MAPPING_INCOMPLETE` only after session/alignment match

Still shadow/research only. No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.
