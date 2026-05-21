#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
WF_DIR = ROOT / ".github" / "workflows"
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

failures = []
warnings = []
checked = []

if not WF_DIR.exists():
    failures.append("missing .github/workflows")
else:
    live_wfs = []
    for wf in sorted(list(WF_DIR.glob("*.yml")) + list(WF_DIR.glob("*.yaml"))):
        txt = wf.read_text(encoding="utf-8", errors="ignore")
        low = txt.lower()
        name = wf.name.lower()
        if "sig live m5 refresh" in low or "live-m5-refresh" in low or "live_m5_refresh" in name or "sig_live_m5_refresh" in name:
            live_wfs.append(wf)

    if not live_wfs:
        failures.append("no live M5 refresh workflow found")
    for wf in live_wfs:
        txt = wf.read_text(encoding="utf-8", errors="ignore")
        item = {
            "workflow": str(wf).replace("\\", "/"),
            "has_deploy_link_token": "ACTIONS-DEPLOY-LINK-03" in txt,
            "has_gh_workflow_run": "gh workflow run" in txt,
            "has_actions_write": bool(re.search(r"(?m)^\s*actions\s*:\s*write\s*$", txt)),
        }
        checked.append(item)
        if not item["has_deploy_link_token"]:
            failures.append(f"{wf} missing ACTIONS-DEPLOY-LINK-03 token")
        if not item["has_gh_workflow_run"]:
            failures.append(f"{wf} missing gh workflow run deploy trigger")
        if not item["has_actions_write"]:
            warnings.append(f"{wf} may need permissions: actions: write for workflow dispatch")

result = {
    "validation_name": "ACTIONS_DEPLOY_LINK_03_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "checked_workflows": checked,
    "boundary": {
        "workflow_dispatch_only": True,
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = PROOFS / "actions_deploy_link_03_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
