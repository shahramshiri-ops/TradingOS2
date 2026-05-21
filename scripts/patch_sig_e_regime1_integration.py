#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patch workflow and safe commit scope for SIG-E-REGIME1.

Adds market-state build/validation to the live refresh workflow and makes sure
small SIG-E current JSON outputs are eligible for safe commit.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
WORKFLOW = ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml"
SAFE_COMMIT = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"
OUT = ROOT / "outputs" / "_sig_e_regime1" / "sig_e_regime1_integration_patch_result.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_workflow() -> str:
    if not WORKFLOW.exists():
        return "WORKFLOW_MISSING_SKIPPED"
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "SIG-E-REGIME1 — market state / regime runtime layer"
    if marker in text or "build_sig_e_regime1_market_state.py" in text:
        return "ALREADY_PRESENT"

    block = (
        "      # SIG-E-REGIME1 — market state / regime runtime layer (CONTEXT_ONLY / NOT_SIGNAL)\n"
        "      - name: Build SIG-E-REGIME1 market state context\n"
        "        run: |\n"
        "          python scripts/build_sig_e_regime1_market_state.py\n"
        "          python scripts/validate_sig_e_regime1_market_state.py\n\n"
    )

    # Prefer to run after the main live refresh/Brain5/Brain4 block and before shadow candidate research.
    anchors = [
        "      # SHADOW-CANDIDATE-UNIVERSE-01 — research-only candidate bank for forward observation (NOT_SIGNAL)\n",
        "      # SHADOW-DIAG-01 — near-miss/blocker/eligibility diagnostics (NOT_SIGNAL)\n",
        "      - name: Commit generated read-only data, brain payload, and refresh status\n",
    ]
    for anchor in anchors:
        if anchor in text:
            text = text.replace(anchor, block + anchor, 1)
            WORKFLOW.write_text(text, encoding="utf-8")
            return "INSERTED_BEFORE_" + anchor.strip().split(" ")[1].replace("—", "")[:40]

    text += "\n\n" + block
    WORKFLOW.write_text(text, encoding="utf-8")
    return "APPENDED_NO_ANCHOR"


def patch_safe_commit() -> str:
    if not SAFE_COMMIT.exists():
        return "SAFE_COMMIT_MISSING_SKIPPED"
    text = SAFE_COMMIT.read_text(encoding="utf-8")
    required = [
        '    "runtime/sig_e/*current.json",',
        '    "panel/brain4/sig_e*.json",',
    ]
    if all(item in text for item in required):
        return "ALREADY_PRESENT"
    anchor = '    "panel/brain4/*.json",\n'
    insertion = "\n".join(item for item in required if item not in text) + "\n"
    if anchor not in text:
        return "ANCHOR_MISSING_SKIPPED"
    text = text.replace(anchor, anchor + insertion, 1)
    SAFE_COMMIT.write_text(text, encoding="utf-8")
    return "PATCHED"


def main() -> None:
    result = {
        "status": "PASS",
        "created_utc": now_utc(),
        "program": "SIG-E-REGIME1",
        "workflow_patch_status": patch_workflow(),
        "safe_commit_patch_status": patch_safe_commit(),
        "boundary": {
            "context_only": True,
            "signal_authorized": False,
            "trade_proposal_authorized": False,
            "entry_stop_target_authorized": False,
            "broker_execution_authorized": False,
            "auto_execution_authorized": False,
        },
    }
    write_json(OUT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
