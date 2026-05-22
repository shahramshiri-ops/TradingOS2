# SIG-E-SHADOW-PERSIST1

## Purpose

This patch makes the SIG-E live shadow ledgers useful across multiple GitHub Actions runs.

It fixes two problems:

1. **State restore:** before building observation ledgers, it tries to restore previous ledger state from the deployed GitHub Pages persistence mirror.
2. **Run-level append:** observation ledgers now append by `observation_run_id`, not only by `detector_run_id`, so repeated refreshes are still counted even when the detector status does not change.

## Added files

- `scripts/restore_sig_e_shadow_persistence1.py`
- `scripts/build_sig_e_shadow_persistence1_snapshot.py`
- `scripts/validate_sig_e_shadow_persistence1.py`

## Patched files

- `scripts/build_sig_e_shadow_detector1_obsledger.py`
- `scripts/build_sig_e_shadow_detector2_obsledger.py`

## Persistence mirror

The snapshot is written under:

- `panel/brain4/persist/sig_e_shadow_detector_observation/...`
- `panel/brain4/persist/sig_e_shadow_detector/...`
- `panel/brain4/persist/sig_e_shadow_detector2/...`
- `panel/brain4/persist/sig_e_shadow_persistence_manifest.json`

## Boundaries

Observation/persistence only. No signal, trade proposal, entry/stop/target, risk sizing, broker/execution, auto execution, memory promotion, or rule rewrite.
