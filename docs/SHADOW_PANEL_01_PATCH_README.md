# SHADOW-PANEL-01 — Panel Shadow Status Card

This patch adds a panel-safe Shadow status card to `panel/brain4`.

## What it does

It displays:

- Shadow readiness status
- Shadow candidate count
- Near-miss count
- High near-miss count
- Blocked count
- Observation count
- Cohort id
- Boundary flags

## What it does not do

- No signal
- No buy/sell
- No entry/stop/target
- No position sizing
- No broker/execution
- No auto-learning
- No rule rewrite

## Files added

- `panel/brain4/assets/shadow_panel_status.js`
- `panel/brain4/assets/shadow_panel_status.css`
- `scripts/validate_shadow_panel_01_install.py`

## Files patched

- `panel/brain4/index.html`

The installer creates a backup:

- `panel/brain4/index.html.bak_shadow_panel_01`
