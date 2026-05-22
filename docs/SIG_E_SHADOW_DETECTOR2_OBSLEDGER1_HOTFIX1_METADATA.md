# SIG-E Shadow Detector2 OBSLEDGER1 HOTFIX1

Fixes metadata in the Detector2 observation ledger.

Changes:
- Always writes `detector_id`.
- Always writes `source_spec_id`.
- Keeps `SESSION_NOT_MATCHED` out of near-miss counting.
- Preserves caveated observation-only boundaries.

No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.
