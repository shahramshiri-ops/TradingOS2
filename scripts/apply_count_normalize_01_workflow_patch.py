#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
WORKFLOWS = [
    ROOT / ".github/workflows/sig_live_m5_refresh_resample_brain.yml",
    ROOT / ".github/workflows/sig_brain5_context_builder_brain4_panel.yml",
    ROOT / ".github/workflows/sig_brain4_display_only_mobile_panel.yml",
]

BLOCK = """\n      # COUNT-NORMALIZE-01 — clarify shadow count semantics (NOT_SIGNAL)\n      - name: Build COUNT-NORMALIZE-01 shadow count semantics\n        run: python scripts/run_sig_shadow_count_normalize_01.py\n"""

TOKEN = "scripts/run_sig_shadow_count_normalize_01.py"
reports = []

for wf in WORKFLOWS:
    report = {"workflow": str(wf), "exists": wf.exists(), "patched": False, "note": ""}
    if not wf.exists():
        report["note"] = "missing"
        reports.append(report)
        continue

    original = wf.read_text(encoding="utf-8", errors="ignore")
    text = original

    if TOKEN in text:
        report["note"] = "already_patched"
        reports.append(report)
        continue

    anchors = [
        "scripts/run_sig_shadow_reason_upstream_01.py",
        "scripts/run_sig_shadow_ops_01.py",
        "scripts/run_sig_shadow_diag_01.py",
    ]

    patched = False
    for anchor in anchors:
        idx = text.find(anchor)
        if idx >= 0:
            next_step = text.find("\n      - name:", idx)
            if next_step >= 0:
                text = text[:next_step] + BLOCK + text[next_step:]
            else:
                text = text.rstrip() + BLOCK + "\n"
            patched = True
            break

    if not patched:
        text = text.rstrip() + BLOCK + "\n"
        report["note"] = "appended_without_anchor_review_yaml"
    else:
        report["note"] = "patched_after_reason_or_ops_step"

    backup = wf.with_suffix(wf.suffix + ".bak_count_normalize_01")
    backup.write_text(original, encoding="utf-8")
    wf.write_text(text, encoding="utf-8")
    report["patched"] = True
    reports.append(report)

out = ROOT / "proofs/count_normalize_01_workflow_patch_result.json"
out.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "patch_name": "COUNT_NORMALIZE_01_WORKFLOW_PATCH",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "status": "APPLIED_WITH_REPORT",
    "reports": reports,
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
