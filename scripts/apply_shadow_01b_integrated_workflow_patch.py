#!/usr/bin/env python3
"""
Apply SHADOW-01B integrated workflow patch.

Idempotently injects the shadow pipeline into current TradingOS2 workflows.
Backups are handled by the PowerShell installer before this script is called.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

PATCH_VERSION = "SHADOW_01B_INTEGRATED_SAFE_PATCH_v1_0"
SHADOW_RUN_LINE = "          python scripts/run_sig_shadow_01b_integrated.py\n"
RUNTIME_ADDS = ["runtime/sig_signal_candidates", "runtime/sig_shadow"]

WORKFLOWS = [
    ".github/workflows/sig_live_m5_refresh_resample_brain.yml",
    ".github/workflows/sig_brain5_context_builder_brain4_panel.yml",
    ".github/workflows/sig_brain4_display_only_mobile_panel.yml",
]

INSERT_AFTER_BY_FILE = {
    ".github/workflows/sig_live_m5_refresh_resample_brain.yml": [
        "          python scripts/send_sig_brain4_event_email_alerts.py\n",
        "          python scripts/validate_sig_brain4_event_history.py\n",
        "          python scripts/run_live_m5_refresh_pipeline.py --fetch-live\n",
    ],
    ".github/workflows/sig_brain5_context_builder_brain4_panel.yml": [
        "          python scripts/validate_sig_brain5_context_builder.py\n",
    ],
    ".github/workflows/sig_brain4_display_only_mobile_panel.yml": [
        "          python scripts/validate_sig_brain4_outputs.py\n",
    ],
}

def ensure_shadow_step(text: str, path: str, report: List[dict]) -> str:
    if "python scripts/run_sig_shadow_01b_integrated.py" in text:
        report.append({"path": path, "change": "shadow_run_step", "status": "already_present"})
        return text

    lines = text.splitlines(keepends=True)
    candidates = INSERT_AFTER_BY_FILE.get(path, [])
    for needle in candidates:
        for i, line in enumerate(lines):
            if line == needle:
                lines.insert(i + 1, SHADOW_RUN_LINE)
                report.append({"path": path, "change": "shadow_run_step", "status": f"inserted_after:{needle.strip()}"})
                return "".join(lines)

    report.append({"path": path, "change": "shadow_run_step", "status": "not_inserted_anchor_missing"})
    return text

def ensure_git_add_dirs(text: str, path: str, report: List[dict]) -> str:
    lines = text.splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("git add "):
            continue
        # Only generated-output commits; avoid non-runtime setup lines.
        if "runtime/sig_brain" in stripped or "panel/brain4" in stripped or "proofs" in stripped:
            add_line = line.rstrip("\n")
            for item in RUNTIME_ADDS:
                if item not in add_line:
                    add_line += " " + item
                    changed = True
            lines[i] = add_line + ("\n" if line.endswith("\n") else "")
    report.append({"path": path, "change": "git_add_shadow_outputs", "status": "updated" if changed else "already_present_or_no_target_line"})
    return "".join(lines)

def main() -> int:
    report = []
    for wf in WORKFLOWS:
        path = Path(wf)
        if not path.exists():
            report.append({"path": wf, "status": "missing"})
            continue
        text = path.read_text(encoding="utf-8")
        text2 = ensure_shadow_step(text, wf, report)
        text3 = ensure_git_add_dirs(text2, wf, report)
        if text3 != text:
            path.write_text(text3, encoding="utf-8")
    out = Path("proofs/shadow_01b_workflow_patch_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "patch_version": PATCH_VERSION,
        "status": "APPLIED_WITH_REPORT",
        "report": report,
        "signal_authorized": False,
        "broker_execution_authorized": False,
    }, indent=2), encoding="utf-8")
    print(json.dumps({"status": "SHADOW_01B_WORKFLOW_PATCH_APPLIED", "report": report}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
