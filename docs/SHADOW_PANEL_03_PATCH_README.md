# SHADOW-PANEL-03 — Unified Shadow Card

This patch merges the two previous Shadow cards into one clean card.

It reads:

- `shadow_panel_status_current.json`
- `shadow_ops_status_current.json`

It removes these old script/style references from `panel/brain4/index.html`:

- `assets/shadow_panel_status.js`
- `assets/shadow_panel_status.css`
- `assets/shadow_ops_panel.js`
- `assets/shadow_ops_panel.css`

It adds:

- `assets/shadow_unified_panel.js`
- `assets/shadow_unified_panel.css`

Boundary:

- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
