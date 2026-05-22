# SIG-E-SHADOW-PERSIST1 workflow note

The prior patch could not auto-insert restore/snapshot steps because the workflow names did not match expected patterns.

If GitHub Actions still does not run persistence scripts automatically, add these steps manually in `.github/workflows/sig_live_m5_refresh_resample_brain.yml`.

Recommended position:
1. Restore step: after live context/build steps and before shadow detector obsledgers.
2. Snapshot/validate steps: after `build_sig_e_shadow_portfolio1.py` and `validate_sig_e_shadow_portfolio1.py`.

Steps:

```yaml
      - name: Restore SIG-E shadow persistence 1
        run: python scripts/restore_sig_e_shadow_persistence1.py

      - name: Build SIG-E shadow persistence 1 snapshot
        run: python scripts/build_sig_e_shadow_persistence1_snapshot.py

      - name: Validate SIG-E shadow persistence 1
        run: python scripts/validate_sig_e_shadow_persistence1.py
```

Local application disables network restore automatically. GitHub Actions can still use remote restore.
