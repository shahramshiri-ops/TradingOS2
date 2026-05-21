#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Idempotently integrate LIVE_OBSERVATION_MAX_VALUE_01 into workflows and safe commit scope."""
from __future__ import annotations

from pathlib import Path
from typing import List
import json
import re

ROOT = Path.cwd()
PATCH_VERSION = "LIVE_OBSERVATION_MAX_VALUE_01_INTEGRATION_PATCH_v1_0"

LIVE_STEP = """      # LIVE-OBSERVATION-MAX-VALUE-01 — forward evidence ledger/summaries (DISPLAY_ONLY, NOT_SIGNAL)
      - name: Build LIVE-OBSERVATION-MAX-VALUE-01 forward evidence pack
        run: |
          python scripts/build_live_observation_max_value_01.py
          python scripts/validate_live_observation_max_value_01.py

"""

DEPLOY_AFTER_PANEL_STEP = """      # LIVE-OBSERVATION-MAX-VALUE-01 — explicit static Pages deploy trigger after panel evidence update
      - name: Trigger static Pages deploy after panel build
        if: success()
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -e
          echo "Triggering Deploy TradingOS Static Pages after panel build..."
          gh workflow run "Deploy TradingOS Static Pages" --ref "${GITHUB_REF_NAME:-main}" || \
          gh workflow run "deploy_tradingos_static_pages.yml" --ref "${GITHUB_REF_NAME:-main}" || \
          gh workflow run "deploy.yml" --ref "${GITHUB_REF_NAME:-main}"

"""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_broken_generated_commit_deploy_step(text: str) -> str:
    # Removes the legacy step that references steps.commit_generated.outputs.changed when commit step has no id.
    lines = text.splitlines(keepends=True)
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "- name: Trigger static Pages deploy after generated commit" in line:
            block = "".join(lines[i:i+12])
            if "steps.commit_generated.outputs.changed" in block:
                # Skip until next step at same indentation or EOF.
                i += 1
                while i < len(lines):
                    if re.match(r"^      - name: ", lines[i]):
                        break
                    i += 1
                continue
        out.append(line)
        i += 1
    return "".join(out)


def insert_live_step_before_commit(text: str) -> str:
    if "Build LIVE-OBSERVATION-MAX-VALUE-01 forward evidence pack" in text:
        return text
    marker = "      - name: Commit generated read-only data, brain payload, and refresh status\n"
    if marker not in text:
        raise RuntimeError("Could not find commit generated step marker in workflow")
    return text.replace(marker, LIVE_STEP + marker, 1)


def ensure_panel_explicit_deploy(text: str) -> str:
    if "Trigger static Pages deploy after panel build" in text or "Trigger static Pages deploy after live refresh" in text:
        return text
    marker = "      - name: Commit generated read-only data, brain payload, and refresh status\n        run: python scripts/actions_commit_generated_readonly_safe.py\n"
    if marker in text:
        return text.replace(marker, marker + DEPLOY_AFTER_PANEL_STEP, 1)
    return text


def patch_workflow(path: Path, add_panel_deploy: bool = False) -> dict:
    before = read(path)
    after = before
    after = remove_broken_generated_commit_deploy_step(after)
    after = insert_live_step_before_commit(after)
    if add_panel_deploy:
        after = ensure_panel_explicit_deploy(after)
    changed = after != before
    if changed:
        backup = path.with_suffix(path.suffix + ".bak_live_observation_max_value_01")
        if not backup.exists():
            write(backup, before)
        write(path, after)
    return {"path": path.as_posix(), "changed": changed}


def patch_safe_commit(path: Path) -> dict:
    before = read(path)
    after = before
    additions = [
        '    "state/live_observation/*.json",',
        '    "runtime/sig_live_observation/*.json",',
        '    "panel/brain4/live_observation_*.json",',
        '    "panel/brain4/live_memory_evaluation_current.json",',
        '    "panel/brain4/live_event_ledger_current.json",',
    ]
    # Insert after panel/brain4 json line, idempotently.
    if '"state/live_observation/*.json"' not in after:
        marker = '    "panel/brain4/*.json",\n'
        if marker not in after:
            raise RuntimeError("Could not find ALLOWED_GLOBS panel/brain4 marker in safe commit script")
        after = after.replace(marker, marker + "\n".join(additions) + "\n", 1)
    changed = after != before
    if changed:
        backup = path.with_suffix(path.suffix + ".bak_live_observation_max_value_01")
        if not backup.exists():
            write(backup, before)
        write(path, after)
    return {"path": path.as_posix(), "changed": changed}


def main() -> None:
    results = []
    live_wf = ROOT / ".github" / "workflows" / "sig_live_m5_refresh_resample_brain.yml"
    panel_wf = ROOT / ".github" / "workflows" / "sig_brain4_display_only_mobile_panel.yml"
    safe_commit = ROOT / "scripts" / "actions_commit_generated_readonly_safe.py"

    if live_wf.exists():
        results.append(patch_workflow(live_wf, add_panel_deploy=False))
    else:
        results.append({"path": live_wf.as_posix(), "changed": False, "warning": "missing"})

    if panel_wf.exists():
        results.append(patch_workflow(panel_wf, add_panel_deploy=True))
    else:
        results.append({"path": panel_wf.as_posix(), "changed": False, "warning": "missing"})

    if safe_commit.exists():
        results.append(patch_safe_commit(safe_commit))
    else:
        results.append({"path": safe_commit.as_posix(), "changed": False, "warning": "missing"})

    result = {
        "status": "LIVE_OBSERVATION_MAX_VALUE_01_INTEGRATION_PATCH_OK",
        "patch_version": PATCH_VERSION,
        "results": results,
        "boundary": {
            "display_only": True,
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }
    out = ROOT / "proofs" / "live_observation_max_value_01_integration_patch_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
