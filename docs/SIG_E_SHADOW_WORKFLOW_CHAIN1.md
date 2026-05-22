# SIG-E-SHADOW-WORKFLOW-CHAIN1

## Problem found

The uploaded workflow only had the persistence commands in comments, not actual workflow steps. It also did not run the SIG-E shadow detectors, obsledgers, or portfolio after REGIME1.

As a result:
- ARCH1 and REGIME1 were fresh.
- `shadow_portfolio_current.json` stayed stale.
- Persistence could not be proven inside GitHub Actions.

## What this patch inserts

After `Build SIG-E-REGIME1 market state context`:

```yaml
- name: Build SIG-E shadow detector portfolio and persistence chain
  run: |
    python scripts/restore_sig_e_shadow_persistence1.py
    python scripts/build_sig_e_shadow_detector1_usdjpy_london_long.py
    python scripts/validate_sig_e_shadow_detector1.py
    python scripts/build_sig_e_shadow_detector1_obsledger.py
    python scripts/validate_sig_e_shadow_detector1_obsledger.py
    python scripts/build_sig_e_shadow_detector2_usdjpy_asia_short.py
    python scripts/validate_sig_e_shadow_detector2.py
    python scripts/build_sig_e_shadow_detector2_obsledger.py
    python scripts/validate_sig_e_shadow_detector2_obsledger.py
    python scripts/build_sig_e_shadow_portfolio1.py
    python scripts/validate_sig_e_shadow_portfolio1.py
    python scripts/build_sig_e_shadow_persistence1_snapshot.py
    python scripts/validate_sig_e_shadow_persistence1.py
```

Before deploy trigger:

```yaml
- name: Commit SIG-E shadow persistence generated outputs
  run: python scripts/commit_sig_e_shadow_persistence_outputs.py
```

## Boundary

Workflow-only integration. No detector rule change. No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.
