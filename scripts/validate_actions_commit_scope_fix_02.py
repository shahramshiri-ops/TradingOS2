#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
WORKFLOWS = ROOT / ".github" / "workflows"

failures = []
warnings = []

safe_script = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"
if not safe_script.exists():
    failures.append("missing scripts/actions_commit_generated_readonly_safe.py")

workflow_text = ""
workflow_files = []
if WORKFLOWS.exists():
    for wf in sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml"))):
        txt = wf.read_text(encoding="utf-8", errors="ignore")
        workflow_files.append(str(wf).replace("\\", "/"))
        workflow_text += "\n# FILE " + str(wf) + "\n" + txt
else:
    failures.append("missing .github/workflows")

if "scripts/actions_commit_generated_readonly_safe.py" not in workflow_text:
    failures.append("no workflow references actions_commit_generated_readonly_safe.py")

# Strong guard: no workflow should explicitly git-add live_logs / outputs zip / price bridge.
for bad in [
    "runtime/sig_shadow/live_logs",
    "outcome_observation_log_",
    "runtime/sig_shadow/price_bridge_h1",
]:
    if bad in workflow_text:
        warnings.append(f"workflow text still mentions generated raw path: {bad}")

# Fail only for obvious broad add in a generated commit step nearby.
for m in re.finditer(r"(?is)(Commit generated.{0,900})", workflow_text):
    chunk = m.group(1)
    if "actions_commit_generated_readonly_safe.py" not in chunk and re.search(r"git\s+add\s+(-A|\.)", chunk):
        failures.append("broad git add remains in a Commit generated step")

gitignore = ROOT / ".gitignore"
if gitignore.exists():
    gi = gitignore.read_text(encoding="utf-8", errors="ignore")
    for token in ["runtime/sig_shadow/live_logs/", "runtime/sig_shadow/price_bridge_h1/", "outputs/", "*.zip"]:
        if token not in gi:
            warnings.append(f".gitignore missing token: {token}")
else:
    warnings.append(".gitignore missing")

result = {
    "validation_name": "ACTIONS_COMMIT_SCOPE_FIX_02_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "workflow_files_checked": workflow_files,
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

PROOFS.mkdir(parents=True, exist_ok=True)
out = PROOFS / "actions_commit_scope_fix_02_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
