#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Idempotently integrate SHADOW_CANDIDATE_UNIVERSE_01 into workflow and safe commit scope."""
from __future__ import annotations

from pathlib import Path
from typing import List
import json
import re

ROOT = Path.cwd()
PATCH_VERSION = "SHADOW_CANDIDATE_UNIVERSE_01_INTEGRATION_PATCH_v1_0"

WORKFLOW_STEP = """      # SHADOW-CANDIDATE-UNIVERSE-01 — research-only candidate bank for forward observation (NOT_SIGNAL)
      - name: Build SHADOW-CANDIDATE-UNIVERSE-01 research candidates
        run: python scripts/run_shadow_candidate_universe_01.py

"""

SAFE_GLOBS = [
    '"runtime/sig_shadow_candidate_universe/*current.json",',
    '"state/shadow_candidate_universe/*.json",',
    '"panel/brain4/shadow_candidate_universe*.json",',
]

LIVE_OBS_GLOBS = [
    '"runtime/sig_live_observation/*current.json",',
    '"state/live_observation/*.json",',
    '"panel/brain4/live_observation*.json",',
    '"panel/brain4/live_memory_evaluation*.json",',
    '"panel/brain4/live_event_ledger*.json",',
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_broken_generated_commit_deploy_step(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "- name: Trigger static Pages deploy after generated commit" in line:
            block = "".join(lines[i:i+12])
            if "steps.commit_generated.outputs.changed" in block:
                i += 1
                while i < len(lines):
                    if re.match(r"^      - name: ", lines[i]):
                        break
                    i += 1
                continue
        out.append(line)
        i += 1
    return "".join(out)


def patch_live_workflow() -> Dict[str, object]:
    wf = ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml"
    if not wf.exists():
        return {"workflow_found": False, "changed": False, "path": str(wf)}
    text = read(wf)
    original = text
    text = remove_broken_generated_commit_deploy_step(text)
    if "Build SHADOW-CANDIDATE-UNIVERSE-01 research candidates" not in text:
        marker = "      # SHADOW-DIAG-01 — near-miss/blocker/eligibility diagnostics (NOT_SIGNAL)\n"
        if marker in text:
            text = text.replace(marker, WORKFLOW_STEP + marker, 1)
        else:
            marker2 = "      - name: Commit generated read-only data, brain payload, and refresh status\n"
            if marker2 not in text:
                raise RuntimeError("Could not find workflow insertion marker")
            text = text.replace(marker2, WORKFLOW_STEP + marker2, 1)
    changed = text != original
    if changed:
        write(wf, text)
    return {"workflow_found": True, "changed": changed, "path": str(wf.relative_to(ROOT))}


def patch_safe_commit_scope() -> Dict[str, object]:
    p = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"
    if not p.exists():
        return {"safe_commit_found": False, "changed": False, "path": str(p)}
    text = read(p)
    original = text
    marker = "ALLOWED_GLOBS = ["
    if marker not in text:
        raise RuntimeError("ALLOWED_GLOBS marker not found in actions_commit_generated_readonly_safe.py")
    insert_after = '    "panel/brain4/assets/*.css",\n'
    additions = []
    for g in SAFE_GLOBS + LIVE_OBS_GLOBS:
        raw = g.strip().strip(',').strip('"')
        if raw not in text:
            additions.append("    " + g + "\n")
    if additions:
        if insert_after in text:
            text = text.replace(insert_after, insert_after + "\n" + "".join(additions), 1)
        else:
            text = text.replace(marker + "\n", marker + "\n" + "".join(additions), 1)
    changed = text != original
    if changed:
        write(p, text)
    return {"safe_commit_found": True, "changed": changed, "path": str(p.relative_to(ROOT)), "added_globs": additions}


def main() -> int:
    result = {
        "patch_version": PATCH_VERSION,
        "workflow": patch_live_workflow(),
        "safe_commit_scope": patch_safe_commit_scope(),
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }
    out = ROOT / "outputs" / "_shadow_candidate_universe_01" / "shadow_candidate_universe_01_integration_patch_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
