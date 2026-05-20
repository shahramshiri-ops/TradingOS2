#!/usr/bin/env python3
"""Idempotently inject SHADOW-READY-01 after SHADOW-01B in current workflows."""
from __future__ import annotations
import json
from pathlib import Path

PATCH_VERSION = "SHADOW_READY_01_REPO_PATCH_v1_0"
WORKFLOWS = [
    ".github/workflows/sig_live_m5_refresh_resample_brain.yml",
    ".github/workflows/sig_brain5_context_builder_brain4_panel.yml",
    ".github/workflows/sig_brain4_display_only_mobile_panel.yml",
]
READY_LINE = "          python scripts/run_sig_shadow_ready_01.py\n"
AFTER_LINE = "          python scripts/run_sig_shadow_01b_integrated.py\n"
OUTPUT_ADDS = ["runtime/sig_shadow", "panel/brain4", "proofs"]

def ensure_ready_step(text: str, wf: str, report: list) -> str:
    if "python scripts/run_sig_shadow_ready_01.py" in text:
        report.append({"path": wf, "change": "ready_run_step", "status": "already_present"})
        return text
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line == AFTER_LINE:
            lines.insert(i + 1, READY_LINE)
            report.append({"path": wf, "change": "ready_run_step", "status": "inserted_after_shadow01b"})
            return "".join(lines)
    # fallback anchors if SHADOW-01B line was not present for some reason
    anchors = [
        "          python scripts/validate_sig_brain5_context_builder.py\n",
        "          python scripts/validate_sig_brain4_outputs.py\n",
        "          python scripts/validate_sig_brain4_event_history.py\n",
    ]
    for anchor in anchors:
        for i, line in enumerate(lines):
            if line == anchor:
                lines.insert(i + 1, READY_LINE)
                report.append({"path": wf, "change": "ready_run_step", "status": f"inserted_after_fallback:{anchor.strip()}"})
                return "".join(lines)
    report.append({"path": wf, "change": "ready_run_step", "status": "not_inserted_anchor_missing"})
    return text

def ensure_git_add(text: str, wf: str, report: list) -> str:
    lines = text.splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("git add "):
            continue
        if any(x in stripped for x in ["runtime/sig_brain", "runtime/sig_shadow", "panel/brain4", "proofs"]):
            add_line = line.rstrip("\n")
            for item in OUTPUT_ADDS:
                if item not in add_line:
                    add_line += " " + item
                    changed = True
            lines[i] = add_line + ("\n" if line.endswith("\n") else "")
    report.append({"path": wf, "change": "git_add_ready_outputs", "status": "updated" if changed else "already_present_or_no_target_line"})
    return "".join(lines)

def main() -> int:
    report = []
    for wf in WORKFLOWS:
        path = Path(wf)
        if not path.exists():
            report.append({"path": wf, "status": "missing"})
            continue
        old = path.read_text(encoding="utf-8")
        new = ensure_git_add(ensure_ready_step(old, wf, report), wf, report)
        if new != old:
            path.write_text(new, encoding="utf-8")
    out = Path("proofs/shadow_ready_01_workflow_patch_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"patch_version": PATCH_VERSION, "status": "APPLIED_WITH_REPORT", "report": report, "signal_authorized": False, "broker_execution_authorized": False, "auto_learning_authorized": False}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
