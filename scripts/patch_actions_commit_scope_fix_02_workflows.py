#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patch workflows to use ACTIONS-COMMIT-SCOPE-FIX-02 safe commit script.

It replaces broad generated commit steps with:
  python scripts/actions_commit_generated_readonly_safe.py

No PyYAML required.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
WORKFLOW_DIR = ROOT / ".github" / "workflows"
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

SAFE_SCRIPT = "scripts/actions_commit_generated_readonly_safe.py"
TARGET_STEP_KEYWORDS = [
    "Commit generated read-only data",
    "Commit generated display-only payload",
    "Commit generated",
    "commit generated",
]

SAFE_STEP_NAME = "Commit generated read-only data, brain payload, and refresh status"


def now_utc() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def is_step_start(line: str) -> bool:
    return re.match(r"^\s*-\s+name\s*:", line) is not None


def step_name(line: str) -> str:
    return line.split(":", 1)[1].strip().strip("\"'")


def replace_commit_steps(text: str) -> tuple[str, list[dict]]:
    lines = text.splitlines()
    out = []
    i = 0
    reports = []

    while i < len(lines):
        line = lines[i]
        if is_step_start(line):
            name = step_name(line)
            if any(k in name for k in TARGET_STEP_KEYWORDS):
                indent = line_indent(line)
                # Identify end of this step: next step at same or lower indent.
                j = i + 1
                while j < len(lines):
                    if is_step_start(lines[j]) and line_indent(lines[j]) <= indent:
                        break
                    j += 1

                step_indent = " " * indent
                child_indent = " " * (indent + 2)
                new_step = [
                    f"{step_indent}- name: {SAFE_STEP_NAME}",
                    f"{child_indent}run: python {SAFE_SCRIPT}",
                ]
                out.extend(new_step)
                reports.append({
                    "old_step_name": name,
                    "start_line": i + 1,
                    "end_line": j,
                    "replacement": "safe_commit_script",
                })
                i = j
                continue

        out.append(line)
        i += 1

    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), reports


def patch_workflows() -> dict:
    result = {
        "patch_name": "ACTIONS_COMMIT_SCOPE_FIX_02_WORKFLOW_PATCH",
        "created_utc": now_utc(),
        "workflow_dir_exists": WORKFLOW_DIR.exists(),
        "patched_workflows": [],
        "warnings": [],
    }

    if not WORKFLOW_DIR.exists():
        result["warnings"].append(".github/workflows not found")
        return result

    for wf in sorted(list(WORKFLOW_DIR.glob("*.yml")) + list(WORKFLOW_DIR.glob("*.yaml"))):
        original = wf.read_text(encoding="utf-8", errors="ignore")
        if SAFE_SCRIPT in original:
            result["patched_workflows"].append({
                "workflow": str(wf).replace("\\", "/"),
                "status": "already_patched",
                "replaced_steps": [],
            })
            continue

        patched, reports = replace_commit_steps(original)
        if reports:
            backup = wf.with_suffix(wf.suffix + ".bak_actions_commit_scope_fix_02")
            backup.write_text(original, encoding="utf-8")
            wf.write_text(patched, encoding="utf-8")
            result["patched_workflows"].append({
                "workflow": str(wf).replace("\\", "/"),
                "status": "patched",
                "replaced_steps": reports,
            })

    if not any(x["status"] in {"patched", "already_patched"} for x in result["patched_workflows"]):
        result["warnings"].append("No generated commit step was found. Manual workflow review may be needed.")

    return result


def main() -> None:
    result = patch_workflows()
    out = PROOFS / "actions_commit_scope_fix_02_workflow_patch_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
