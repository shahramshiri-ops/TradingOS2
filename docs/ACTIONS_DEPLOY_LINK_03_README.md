# ACTIONS-DEPLOY-LINK-03 — Explicit Deploy Trigger After Live Refresh

## Problem

Before safe commit hygiene, the live refresh workflow often created a generated commit. That commit triggered:

```text
Deploy TradingOS Static Pages
```

After safe commit scope, a refresh can complete successfully with no commit. In that case the deploy workflow may not run, so the panel can stay stale even though the live refresh ran.

## Fix

Patch the live refresh workflow to explicitly dispatch the static Pages deploy workflow after a successful refresh:

```yaml
gh workflow run "Deploy TradingOS Static Pages" --ref "${GITHUB_REF_NAME:-main}"
```

Fallbacks try common workflow filenames.

## Boundary

This is workflow orchestration only:

- no signal
- no buy/sell
- no entry/stop/target
- no broker/execution
- no auto-learning
- no rule rewrite
