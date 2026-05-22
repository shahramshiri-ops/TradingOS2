# SIG-E-SHADOW-PERSIST1-WORKFLOW-HOTFIX

## Why this patch exists

`Select-String` returned no output, so the workflow still does not run the persistence restore/snapshot/validate scripts.

That means the local persistence logic works, but GitHub Actions will not persist history unless the workflow explicitly calls those scripts.

## What this patch does

It patches:

`.github/workflows/sig_live_m5_refresh_resample_brain.yml`

and adds:

```yaml
- name: Restore SIG-E shadow persistence 1
  run: python scripts/restore_sig_e_shadow_persistence1.py

- name: Build SIG-E shadow persistence 1 snapshot
  run: python scripts/build_sig_e_shadow_persistence1_snapshot.py

- name: Validate SIG-E shadow persistence 1
  run: python scripts/validate_sig_e_shadow_persistence1.py
```

Restore is inserted before obsledger builds. Snapshot/validate are inserted after portfolio/ledger outputs.

## Boundaries

Workflow-only patch. No detector rule change. No signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.
