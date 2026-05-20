#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
WORKFLOWS = [
    ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml",
    ROOT / ".github" / "workflows" / "sig_brain5_context_builder_brain4_panel.yml",
    ROOT / ".github" / "workflows" / "sig_brain4_display_only_mobile_panel.yml",
]

BLOCK = """\n      # SHADOW-DIAG-01 — near-miss/blocker/eligibility diagnostics (NOT_SIGNAL)\n      - name: Build SHADOW-DIAG-01 diagnostics\n        run: python scripts/run_sig_shadow_diag_01.py\n"""

TOKEN = "scripts/run_sig_shadow_diag_01.py"

reports = []
for wf in WORKFLOWS:
    item = {"workflow": str(wf), "exists": wf.exists(), "patched": False, "note": ""}
    if not wf.exists():
        item["note"] = "missing"
        reports.append(item)
        continue

    text = wf.read_text(encoding="utf-8", errors="ignore")
    if TOKEN in text:
        item["note"] = "already_patched"
        reports.append(item)
        continue

    # Best anchor: after SHADOW-READY-01, otherwise after SHADOW-01B, otherwise before validation/deploy if possible.
    anchors = [
        "scripts/run_sig_shadow_ready_01.py",
        "scripts/validate_sig_shadow_ready_01_outputs.py",
        "scripts/run_sig_shadow_01b_integrated.py",
        "scripts/validate_sig_shadow_01b_integrated_outputs.py",
    ]

    patched = False
    for anchor in anchors:
        idx = text.find(anchor)
        if idx >= 0:
            # Insert after the YAML step block containing this anchor. We approximate by next "\n      - name:".
            next_step = text.find("\n      - name:", idx)
            if next_step >= 0:
                text = text[:next_step] + BLOCK + text[next_step:]
            else:
                text = text.rstrip() + BLOCK + "\n"
            patched = True
            break

    if not patched:
        # Append near end as a safe best-effort. This may need review if workflow shape is unusual.
        text = text.rstrip() + BLOCK + "\n"
        item["note"] = "appended_without_anchor_review_yaml"
    else:
        item["note"] = "patched_after_existing_shadow_step"

    backup = wf.with_suffix(wf.suffix + ".bak_shadow_diag_01")
    backup.write_text(wf.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    wf.write_text(text, encoding="utf-8")
    item["patched"] = True
    reports.append(item)

out = ROOT / "proofs" / "shadow_diag_01_workflow_patch_result.json"
out.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "patch_name": "SHADOW_DIAG_01_WORKFLOW_PATCH",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "status": "APPLIED_WITH_REPORT",
    "reports": reports,
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
