#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ACTIONS-DEPLOY-LINK-03

Problem:
- Before repo hygiene, live refresh often committed generated payloads.
- That commit/push automatically triggered the static Pages deploy workflow.
- After safe commit scope, some refresh runs may produce no commit/push.
- Therefore Deploy TradingOS Static Pages is no longer guaranteed to run after every successful live refresh.

Fix:
- Patch the live refresh workflow to explicitly trigger the deploy workflow after the refresh pipeline/safe commit step.
- Do not depend on whether a new commit was created.
- Keep raw logs and huge generated files out of git.

Boundary:
- Workflow dispatch only.
- NOT_SIGNAL / NO_EXECUTION / NO_RULE_REWRITE.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT = Path.cwd()
WF_DIR = ROOT / ".github" / "workflows"
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

PATCH_ID = "ACTIONS_DEPLOY_LINK_03_v1_0"
SAFE_COMMIT_TOKEN = "scripts/actions_commit_generated_readonly_safe.py"
DEPLOY_STEP_TOKEN = "ACTIONS-DEPLOY-LINK-03"

DEPLOY_STEP = """
      # ACTIONS-DEPLOY-LINK-03 — explicit static Pages deploy trigger after live refresh
      - name: Trigger static Pages deploy after live refresh
        if: success()
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -e
          echo "Triggering Deploy TradingOS Static Pages after live refresh..."
          gh workflow run "Deploy TradingOS Static Pages" --ref "${GITHUB_REF_NAME:-main}" || \\
          gh workflow run "deploy_tradingos_static_pages.yml" --ref "${GITHUB_REF_NAME:-main}" || \\
          gh workflow run "deploy.yml" --ref "${GITHUB_REF_NAME:-main}"
"""

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def find_live_workflows() -> list[Path]:
    out = []
    if not WF_DIR.exists():
        return out
    for wf in sorted(list(WF_DIR.glob("*.yml")) + list(WF_DIR.glob("*.yaml"))):
        txt = wf.read_text(encoding="utf-8", errors="ignore")
        low = txt.lower()
        name = wf.name.lower()
        if "sig live m5 refresh" in low or "live-m5-refresh" in low or "live_m5_refresh" in name or "sig_live_m5_refresh" in name:
            out.append(wf)
    return out

def ensure_actions_permission(text: str) -> tuple[str, bool]:
    if re.search(r"(?m)^\s*actions\s*:\s*write\s*$", text):
        return text, False

    lines = text.splitlines()

    for i, line in enumerate(lines):
        if re.match(r"^permissions\s*:\s*$", line):
            j = i + 1
            insert_at = j
            while j < len(lines):
                if lines[j] and not lines[j].startswith(" "):
                    break
                insert_at = j + 1
                j += 1
            lines.insert(insert_at, "  actions: write")
            return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True

    for i, line in enumerate(lines):
        if re.match(r"^jobs\s*:\s*$", line):
            block = ["permissions:", "  contents: write", "  actions: write"]
            lines[i:i] = block + [""]
            return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True

    return text, False

def patch_workflow(wf: Path) -> dict:
    original = wf.read_text(encoding="utf-8", errors="ignore")
    report = {
        "workflow": str(wf).replace("\\", "/"),
        "status": "not_patched",
        "permission_patched": False,
        "deploy_step_inserted": False,
        "reason": "",
    }

    if DEPLOY_STEP_TOKEN in original:
        patched, perm = ensure_actions_permission(original)
        if patched != original:
            wf.with_suffix(wf.suffix + ".bak_actions_deploy_link_03_permissions").write_text(original, encoding="utf-8")
            wf.write_text(patched, encoding="utf-8")
            report["status"] = "already_had_deploy_step_permissions_updated"
            report["permission_patched"] = perm
        else:
            report["status"] = "already_patched"
        return report

    text, perm = ensure_actions_permission(original)
    report["permission_patched"] = perm

    insert_pos = -1

    safe_idx = text.find(SAFE_COMMIT_TOKEN)
    if safe_idx >= 0:
        next_step = text.find("\n      - name:", safe_idx)
        insert_pos = next_step if next_step >= 0 else len(text)

    if insert_pos < 0:
        for phrase in [
            "Commit generated read-only data",
            "Commit generated display-only payload",
            "Commit generated",
        ]:
            idx = text.find(phrase)
            if idx >= 0:
                next_step = text.find("\n      - name:", idx)
                insert_pos = next_step if next_step >= 0 else len(text)
                break

    if insert_pos < 0:
        insert_pos = len(text)
        report["reason"] = "safe_commit_anchor_not_found_appended"

    patched = text[:insert_pos] + DEPLOY_STEP + text[insert_pos:]

    backup = wf.with_suffix(wf.suffix + ".bak_actions_deploy_link_03")
    backup.write_text(original, encoding="utf-8")
    wf.write_text(patched, encoding="utf-8")

    report["status"] = "patched"
    report["deploy_step_inserted"] = True
    return report

def main() -> None:
    workflows = find_live_workflows()
    reports = []
    warnings = []

    if not workflows:
        warnings.append("No live M5 refresh workflow found by name/content. Manual workflow review needed.")
    else:
        for wf in workflows:
            reports.append(patch_workflow(wf))

    result = {
        "patch_id": PATCH_ID,
        "created_utc": now_utc(),
        "status": "APPLIED_WITH_REPORT",
        "live_workflow_count": len(workflows),
        "reports": reports,
        "warnings": warnings,
        "boundary": {
            "workflow_dispatch_only": True,
            "signal_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    out = PROOFS / "actions_deploy_link_03_workflow_patch_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
