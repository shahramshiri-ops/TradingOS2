#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patch workflow and safe commit scope for SIG-E-ARCH1.

Adds static contract validation to the live refresh workflow and allows the small
SIG-E status JSON payloads to be committed by the safe commit script.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
WORKFLOW = ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml"
SAFE_COMMIT = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"
OUT = ROOT / "outputs" / "_sig_e_arch1" / "sig_e_arch1_integration_patch_result.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_workflow() -> str:
    if not WORKFLOW.exists():
        return "WORKFLOW_MISSING_SKIPPED"
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "SIG-E-ARCH1 — target E architecture contract validation"
    if marker in text:
        return "ALREADY_PRESENT"
    anchor = "      - name: Run read-only M5 refresh + internal resampling + brain payload + refresh status\n"
    block = (
        "      # SIG-E-ARCH1 — target E architecture contract validation (NOT_SIGNAL / NO_EXECUTION)\n"
        "      - name: Validate SIG-E-ARCH1 decision architecture contracts\n"
        "        run: |\n"
        "          python scripts/build_sig_e_arch1_status.py\n"
        "          python scripts/validate_sig_e_arch1_contracts.py\n\n"
    )
    if anchor not in text:
        text += "\n\n" + block
        status = "APPENDED_NO_ANCHOR"
    else:
        text = text.replace(anchor, block + anchor, 1)
        status = "INSERTED_BEFORE_REFRESH_PIPELINE"
    WORKFLOW.write_text(text, encoding="utf-8")
    return status


def patch_safe_commit() -> str:
    if not SAFE_COMMIT.exists():
        return "SAFE_COMMIT_MISSING_SKIPPED"
    text = SAFE_COMMIT.read_text(encoding="utf-8")
    items = [
        '    "runtime/sig_e/*current.json",',
        '    "panel/brain4/sig_e*.json",',
    ]
    changed = False
    insertion = "\n".join(items) + "\n"
    if all(item in text for item in items):
        return "ALREADY_PRESENT"
    anchor = '    "panel/brain4/*.json",\n'
    if anchor in text:
        text = text.replace(anchor, anchor + insertion, 1)
        changed = True
    else:
        # Conservative fallback: do not risk corrupting the safe commit script.
        return "ANCHOR_MISSING_SKIPPED"
    SAFE_COMMIT.write_text(text, encoding="utf-8")
    return "PATCHED" if changed else "UNCHANGED"


def main() -> None:
    result = {
        "status": "PASS",
        "created_utc": now_utc(),
        "program": "SIG-E-ARCH1",
        "workflow_patch_status": patch_workflow(),
        "safe_commit_patch_status": patch_safe_commit(),
        "boundary": {
            "not_signal": True,
            "no_entry_stop_target": True,
            "no_broker_execution": True,
            "manual_review_required_for_future_trade_plan": True,
        },
    }
    write_json(OUT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
