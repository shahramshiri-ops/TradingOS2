#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ACTIONS-COMMIT-SCOPE-FIX-02B / TRADINGOS-UI-WORKFLOW-HYGIENE-04

Hotfix for ACTIONS-COMMIT-SCOPE-FIX-02 plus UI/Workflow Hygiene 04 freshness sync.

Fixes:
1. 02 deleted outputs/** before trying to write:
   outputs/_actions_commit_scope_fix_02/actions_commit_scope_fix_02_result.json
   causing FileNotFoundError.
2. Keeps the safe commit scope: never stage raw live logs, jsonl, zip, outputs, proofs, price bridge, or live CSV data.
3. Writes its own report after recreating the report directory.
4. Stages small freshness/report JSONs used by handoff/audit without staging raw CSV/GZ/log/price-bridge data.

Boundary: read-only generated payload commit. Not signal, not broker/execution.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable, List, Dict, Any
import fnmatch
import json
import os
import shutil
import subprocess

ROOT = Path.cwd()
REPORT_DIR = ROOT / "outputs" / "_actions_commit_scope_fix_02"

MAX_STAGE_BYTES = int(os.environ.get("ACTIONS_SAFE_COMMIT_MAX_FILE_MB", "8")) * 1024 * 1024

FORBIDDEN_PATTERNS = [
    "runtime/sig_shadow/live_logs/**",
    "runtime/sig_shadow/price_bridge_h1/**",
    "outputs/**",
    "proofs/**",
    "*.zip",
    "**/*.zip",
    "*.bak",
    "*.bak_*",
    "**/*.bak",
    "**/*.bak_*",
    "data/live_m5/incremental/*.csv",
    "data/live_m5/**/*.csv",
    "data/**/*_canonical.csv",
    "data/**/*_canonical.csv.gz",
    "data/**/*.csv.gz",
    "runtime/**/*.jsonl",
    "**/*.jsonl",
]

ALLOWED_GLOBS = [
    "panel/brain4/*.json",
    "panel/brain4/index.html",
    "panel/brain4/assets/*.js",
    "panel/brain4/assets/*.css",

    # Runtime/status JSONs that are safe to publish and useful for freshness audits.
    "runtime/sig_brain/*.json",
    "runtime/sig_shadow/*current.json",
    "runtime/sig_shadow/price_source_bridge_catalog_current.json",
    "runtime/sig_signal_candidates/*current.json",

    # Small provider/merge/resample reports only. Raw CSV/GZ market data remains forbidden below.
    "data/live_m5/*.json",
    "data/live_m5/incremental/*.json",
    "data/live_m5/reports/*.json",
]

BOUNDARY = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_report_dir() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def write_report(payload: Dict[str, Any]) -> None:
    ensure_report_dir()
    out = REPORT_DIR / "actions_commit_scope_fix_02_result.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def match_any(path: str, patterns: Iterable[str]) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    return any(fnmatch.fnmatch(p, pat) for pat in patterns)


def safe_remove_dir(path: Path, label: str, removed: List[Dict[str, Any]]) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
        removed.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "action": f"removed_{label}"})
    except Exception as e:
        removed.append({"path": str(path), "action": f"remove_{label}_failed", "error": str(e)})


def remove_forbidden_working_files() -> List[Dict[str, Any]]:
    removed: List[Dict[str, Any]] = []

    # Remove raw/generated dirs that must never be pushed.
    safe_remove_dir(ROOT / "runtime" / "sig_shadow" / "live_logs", "live_logs_dir_before_staging", removed)
    safe_remove_dir(ROOT / "runtime" / "sig_shadow" / "price_bridge_h1", "price_bridge_h1_dir_before_staging", removed)

    # 02A deliberately does NOT remove the whole outputs folder until after report creation logic is safe.
    # Remove children inside outputs except the hygiene report dir, then recreate report dir.
    outputs = ROOT / "outputs"
    if outputs.exists():
        for child in outputs.iterdir():
            try:
                if child.name == "_actions_commit_scope_fix_02":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                    removed.append({"path": rel(child), "action": "removed_outputs_child_dir"})
                else:
                    child.unlink()
                    removed.append({"path": rel(child), "action": "removed_outputs_child_file"})
            except Exception as e:
                removed.append({"path": str(child), "action": "remove_outputs_child_failed", "error": str(e)})

    # Remove JSONL anywhere under runtime as a hard guard.
    runtime = ROOT / "runtime"
    if runtime.exists():
        for p in runtime.rglob("*.jsonl"):
            try:
                rp = rel(p)
                p.unlink()
                removed.append({"path": rp, "action": "removed_jsonl_before_staging"})
            except Exception as e:
                removed.append({"path": str(p), "action": "remove_jsonl_failed", "error": str(e)})

    ensure_report_dir()
    return removed


def collect_allowed_files() -> List[Path]:
    files: List[Path] = []
    for pattern in ALLOWED_GLOBS:
        files.extend(ROOT.glob(pattern))

    seen = set()
    out: List[Path] = []
    for p in files:
        if not p.exists() or not p.is_file():
            continue
        rp = rel(p)
        if rp in seen:
            continue
        seen.add(rp)
        if match_any(rp, FORBIDDEN_PATTERNS):
            continue
        out.append(p)
    return sorted(out, key=lambda x: rel(x))


def stage_allowed_files(files: List[Path]) -> Dict[str, Any]:
    staged = []
    skipped_large = []
    skipped_missing = []
    skipped_forbidden = []

    run(["git", "reset"], check=False)

    for p in files:
        rp = rel(p)
        if not p.exists():
            skipped_missing.append(rp)
            continue
        if match_any(rp, FORBIDDEN_PATTERNS):
            skipped_forbidden.append(rp)
            continue
        size = p.stat().st_size
        if size > MAX_STAGE_BYTES:
            skipped_large.append({"path": rp, "size_bytes": size, "max_stage_bytes": MAX_STAGE_BYTES})
            continue
        r = run(["git", "add", "--", rp])
        if r.returncode == 0:
            staged.append({"path": rp, "size_bytes": size})
        else:
            skipped_missing.append({"path": rp, "error": r.stderr.strip()})

    return {
        "staged": staged,
        "skipped_large": skipped_large,
        "skipped_missing": skipped_missing,
        "skipped_forbidden": skipped_forbidden,
    }


def staged_files() -> List[str]:
    r = run(["git", "diff", "--cached", "--name-only"])
    if r.returncode != 0:
        return []
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


def validate_staged_files(paths: List[str]) -> List[str]:
    failures = []
    for p in paths:
        if match_any(p, FORBIDDEN_PATTERNS):
            failures.append(f"forbidden staged path: {p}")
            continue
        fp = ROOT / p
        if fp.exists() and fp.is_file() and fp.stat().st_size > MAX_STAGE_BYTES:
            failures.append(f"staged file too large: {p} ({fp.stat().st_size} bytes)")
    return failures


def commit_and_push(paths: List[str]) -> Dict[str, Any]:
    if not paths:
        return {"status": "NO_STAGED_CHANGES_TO_COMMIT"}

    msg = "Update read-only panel and shadow status payloads"
    r_commit = run(["git", "commit", "-m", msg])
    if r_commit.returncode != 0:
        combined = (r_commit.stdout + "\n" + r_commit.stderr).strip()
        if "nothing to commit" in combined.lower():
            return {"status": "NO_STAGED_CHANGES_TO_COMMIT", "detail": combined}
        return {"status": "COMMIT_FAILED", "stdout": r_commit.stdout, "stderr": r_commit.stderr}

    r_push = run(["git", "push"])
    if r_push.returncode != 0:
        return {"status": "PUSH_FAILED", "stdout": r_push.stdout, "stderr": r_push.stderr}

    return {"status": "COMMIT_AND_PUSH_OK", "commit_stdout": r_commit.stdout, "push_stdout": r_push.stdout}


def main() -> None:
    started = now_utc()

    run(["git", "config", "user.name", "github-actions[bot]"], check=False)
    run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)

    removed = remove_forbidden_working_files()
    candidates = collect_allowed_files()
    stage_report = stage_allowed_files(candidates)
    staged = staged_files()
    failures = validate_staged_files(staged)

    if failures:
        run(["git", "reset"], check=False)
        result = {
            "status": "SAFE_COMMIT_ABORTED_VALIDATION_FAIL",
            "created_utc": started,
            "failures": failures,
            "removed_forbidden_files": removed,
            "stage_report": stage_report,
            "staged_files_before_abort": staged,
            "boundary": BOUNDARY,
        }
        write_report(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    commit_result = commit_and_push(staged)

    result = {
        "status": commit_result.get("status"),
        "created_utc": started,
        "hotfix_version": "ACTIONS_COMMIT_SCOPE_FIX_02B_UI_WORKFLOW_HYGIENE_04",
        "allowed_globs": ALLOWED_GLOBS,
        "forbidden_patterns": FORBIDDEN_PATTERNS,
        "max_stage_bytes": MAX_STAGE_BYTES,
        "removed_forbidden_files": removed,
        "stage_report": stage_report,
        "staged_files": staged,
        "commit_result": commit_result,
        "boundary": BOUNDARY,
    }

    write_report(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if commit_result.get("status") in {"PUSH_FAILED", "COMMIT_FAILED"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
