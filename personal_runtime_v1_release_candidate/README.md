# Personal Runtime V1 — Release Candidate

Use only the root command:

```bat
RUN_DAILY.bat
```

Optional validation only:

```bat
VALIDATE_DAILY.bat
```

Last accepted local proof: validation passed; candidate_count=4, lifecycle_count=4, final_outcome_count=3, active_tracking_count=1, new_observation_candidate_count=0.

This package is observation-only. It is not a signal, not execution, not broker access, not PnL/win-loss, not optimizer, not validation verdict, and not production readiness.

Read:

- `docs/PRV1_operator_runbook_FA.md`
- `docs/PRV1_operator_runbook_EN.md`
- `docs/PRV1_known_limits.md`
- `reports/PRV1_release_candidate_manifest.json`


## PRV1H Mobile / GitHub Pages path

For mobile/cloud use, see:

```text
docs/PRV1H_GITHUB_ACTIONS_MOBILE_SETUP_FA.md
.github/workflows/prv1_daily_runtime_mobile_panel.yml
```

The mobile cloud path runs the canonical daily runtime loop through GitHub Actions and publishes a static display-only panel to GitHub Pages. It does not create broker, execution, signal, entry/stop/target, PnL, validation verdict, or production-readiness functionality.
