# SIG-E-PANEL-OPS6B — Tabbed Shadow Research Console

This patch upgrades the SIG-E/Brain4 panel from a single-page cockpit into a professional tabbed research console.

Tabs:
- Cockpit
- Memories
- Live Shadow
- Lanes
- History
- Diagnostics

Purpose:
- Keep the main page clean.
- Keep memory/debug/diagnostic material available without crowding the cockpit.
- Translate raw labels into readable language.
- Preserve the strict boundary: display only, shadow research only, not signal, no entry/stop/target, no broker/execution.

Data payloads attempted:
- `shadow_portfolio_current.json`
- `shadow_coverage1_current.json`
- `shadow_observation_report1_current.json`
- legacy `shadow_panel_status_current.json`
- legacy `shadow_ops_status_current.json`
- `sig_e_shadow_persistence_status_current.json`

No detector, memory, portfolio, signal, or execution logic is changed.
