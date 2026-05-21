#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
failures = []
warnings = []

safe_script = ROOT / "scripts/actions_commit_generated_readonly_safe.py"
if not safe_script.exists():
    failures.append("missing scripts/actions_commit_generated_readonly_safe.py")
else:
    txt = safe_script.read_text(encoding="utf-8", errors="ignore")
    for token in [
        "ACTIONS-COMMIT-SCOPE-FIX-02A",
        "ensure_report_dir",
        "write_report",
        "runtime/sig_shadow/live_logs/**",
        "**/*.jsonl",
    ]:
        if token not in txt:
            failures.append(f"safe commit script missing token: {token}")
    if "REPORT_DIR.mkdir(parents=True, exist_ok=True)\n\n# Explicitly forbidden" in txt:
        warnings.append("old 02 layout marker still present; verify report dir recreation")

ui_js = ROOT / "panel/brain4/assets/brain4_ui_ops_01.js"
ui_css = ROOT / "panel/brain4/assets/brain4_ui_ops_01.css"
if not ui_js.exists():
    failures.append("missing brain4_ui_ops_01.js")
else:
    jst = ui_js.read_text(encoding="utf-8", errors="ignore")
    for token in ["BRAIN4_UI_STABILIZE_02", "removeOldUiMutations", "brain4-ui-eyebrow"]:
        if token not in jst:
            failures.append(f"UI stabilizer JS missing token: {token}")
    if "addSectionEyebrow" in jst:
        failures.append("old aggressive addSectionEyebrow still present")
if not ui_css.exists():
    failures.append("missing brain4_ui_ops_01.css")

workflow_text = ""
wf_dir = ROOT / ".github/workflows"
if wf_dir.exists():
    for wf in list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")):
        workflow_text += "\n" + wf.read_text(encoding="utf-8", errors="ignore")
if "scripts/actions_commit_generated_readonly_safe.py" not in workflow_text:
    warnings.append("workflow does not reference safe commit script; if already patched remotely, ignore only after manual check")

result = {
    "validation_name": "ACTIONS_UI_HOTFIX_02A_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "boundary": {
        "ui_only_for_panel_change": True,
        "safe_commit_scope_only": True,
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = ROOT / "proofs/actions_ui_hotfix_02a_validation_result.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
