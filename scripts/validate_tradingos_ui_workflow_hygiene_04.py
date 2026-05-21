#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRADINGOS-UI-WORKFLOW-HYGIENE-04 validation.
Checks only repo hygiene/UI-loading/workflow boundaries. It does not run discovery,
validation, signal generation, broker/execution, or rule rewriting.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

failures = []
warnings = []

BOUNDARY = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
}

index = ROOT / "panel" / "brain4" / "index.html"
brain_js = ROOT / "panel" / "brain4" / "assets" / "brain4_panel.js"
live_wf = ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml"
panel_wf = ROOT / ".github" / "workflows" / "sig_brain4_display_only_mobile_panel.yml"
commit_script = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"

for p in [index, brain_js, live_wf, panel_wf, commit_script]:
    if not p.exists():
        failures.append(f"missing file: {p.as_posix()}")

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

idx = read(index)
js = read(brain_js)
workflow_text = read(live_wf) + "\n" + read(panel_wf)
commit_text = read(commit_script)

# Main page should not directly load debug/diagnostic panels.
for asset in [
    "shadow_unified_panel.js",
    "live_shadow_foundation_panel.js",
    "shadow_outcome_panel.js",
    "shadow_outcome_01d_panel.js",
    "brain4_ui_ops_01.js",
    "shadow_unified_panel.css",
    "live_shadow_foundation_panel.css",
    "shadow_outcome_panel.css",
    "shadow_outcome_01d_panel.css",
    "brain4_ui_ops_01.css",
]:
    if re.search(rf"<(script|link)[^>]+{re.escape(asset)}", idx):
        failures.append(f"main index directly loads debug asset: {asset}")

for token in [
    "SIG-BRAIN-OPS22_MINIMAL_SURFACE_DEBUG_GATED_v1_0",
    "DEBUG_PANEL_ASSETS",
    "debugPanelsEnabled",
    "loadDebugPanelAssets",
    "?debug=1",
]:
    if token not in js and token != "?debug=1":
        failures.append(f"brain4_panel.js missing token: {token}")

if "debug" not in js or "diagnostics" not in js:
    failures.append("brain4_panel.js does not expose debug/diagnostics query gating")

# Workflow stale-output references must be gone.
if "steps.commit_generated.outputs.changed" in workflow_text:
    failures.append("stale steps.commit_generated.outputs.changed dependency remains in workflow")

for needle in [
    "Trigger static Pages deploy after live refresh",
    "Trigger static Pages deploy after panel build",
    "gh workflow run \"Deploy TradingOS Static Pages\"",
]:
    if needle not in workflow_text:
        failures.append(f"workflow missing explicit deploy trigger evidence: {needle}")

# Safe commit scope should include small freshness reports and runtime brain JSON, while still forbidding raw data/logs.
for glob in [
    '"runtime/sig_brain/*.json"',
    '"data/live_m5/incremental/*.json"',
    '"data/live_m5/reports/*.json"',
]:
    if glob not in commit_text:
        failures.append(f"safe commit script missing allowed glob: {glob}")

for forbidden in [
    '"runtime/sig_shadow/live_logs/**"',
    '"runtime/sig_shadow/price_bridge_h1/**"',
    '"outputs/**"',
    '"proofs/**"',
    '"data/live_m5/**/*.csv"',
    '"data/**/*.csv.gz"',
    '"**/*.jsonl"',
]:
    if forbidden not in commit_text:
        failures.append(f"safe commit script missing forbidden guard: {forbidden}")

if "ACTIONS_COMMIT_SCOPE_FIX_02B_UI_WORKFLOW_HYGIENE_04" not in commit_text:
    warnings.append("safe commit script hotfix version token not found; behavior may still be OK but versioning is unclear")

result = {
    "validation_name": "TRADINGOS_UI_WORKFLOW_HYGIENE_04_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "checks": {
        "main_surface_debug_assets_directly_loaded": False if not any("directly loads debug asset" in f for f in failures) else True,
        "debug_query_gating_required": True,
        "workflow_stale_commit_generated_dependency_allowed": False,
        "safe_commit_raw_data_allowed": False,
    },
    "boundary": BOUNDARY,
}

out = PROOFS / "tradingos_ui_workflow_hygiene_04_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
