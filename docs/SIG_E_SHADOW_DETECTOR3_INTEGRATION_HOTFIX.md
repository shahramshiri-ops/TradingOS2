# SIG-E Shadow Detector3 Integration Hotfix

Detector3 was built, but `shadow_portfolio_current.json` still showed only 2 lanes. This hotfix wires Detector3 into the rest of the live stack.

It patches:
- `scripts/build_sig_e_shadow_portfolio1.py`
- `scripts/build_sig_e_shadow_observation_report1.py`
- `scripts/restore_sig_e_shadow_persistence1.py`
- `scripts/build_sig_e_shadow_persistence1_snapshot.py`
- `.github/workflows/sig_live_m5_refresh_resample_brain.yml`
- `scripts/commit_sig_e_shadow_persistence_outputs.py`

Expected result:
- `shadow_portfolio_current.json` shows `detector_count: 3`.
- Lane3 appears as `SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15`.
- Observation report includes lane3 state.
- Persistence restore/snapshot preserves lane3 state.

Boundary: no signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution, no auto execution.
