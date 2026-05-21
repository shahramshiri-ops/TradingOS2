#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
REPO-HYGIENE-01 — Generated Runtime File Conflict Control

Purpose:
- Keep source-code changes.
- Remove/restore generated/live/current/test-output changes that cause repeated merge conflicts.
- Do not use force push.
- Do not delete source scripts, docs, panel assets, policies, or workflows.

Safe default: dry-run. Use --apply to execute.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import fnmatch
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import List, Tuple, Dict

ROOT = Path.cwd()
REPORT_DIR = ROOT / "outputs" / "_repo_hygiene_01"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Generated / runtime / local-test paths that should not be committed manually.
GENERATED_PATTERNS = [
    "outputs/**",
    "data/live_m5/**",
    "data/**/incremental_latest.csv",
    "data/**/fetch_report.json",
    "data/**/*_canonical.csv.gz",
    "data/**/*_canonical.csv",
    "runtime/sig_shadow/*current.json",
    "runtime/sig_shadow/live_logs/**",
    "runtime/sig_shadow/price_bridge_h1/**",
    "runtime/sig_shadow/price_source_bridge_catalog_current.json",
    "runtime/sig_signal_candidates/*current.json",
    "panel/brain4/*current.json",
    "panel/brain4/price_source_bridge_catalog_current.json",
    "proofs/*.json",
    "proofs/**/*.json",
    "*.zip",
    "*.bak_*",
    "*.bak",
    "*.tmp",
]

# Never clean these even if a broad pattern would match.
SOURCE_ALLOW_PATTERNS = [
    "scripts/*.py",
    "scripts/**/*.py",
    "panel/brain4/assets/*.js",
    "panel/brain4/assets/*.css",
    "panel/brain4/index.html",
    "sig_brain/*.json",
    "docs/*.md",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitignore",
    ".gitattributes",
    "README.md",
]

# Policy JSONs are source; current/status JSONs are generated.
SOURCE_DENY_EXACT_SUFFIXES = [
    "_current.json",
    "_result.json",
    "_status_current.json",
    "_ledger_current.json",
    "_summary_current.json",
    "_catalog_current.json",
]


def run(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def git_ok() -> bool:
    r = run(["git", "rev-parse", "--show-toplevel"])
    return r.returncode == 0


def rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def match_any(path: str, patterns: List[str]) -> bool:
    p = rel(path)
    return any(fnmatch.fnmatch(p, pat) for pat in patterns)


def is_source_allowed(path: str) -> bool:
    p = rel(path)
    if any(p.endswith(suf) for suf in SOURCE_DENY_EXACT_SUFFIXES):
        return False
    return match_any(p, SOURCE_ALLOW_PATTERNS)


def is_generated(path: str) -> bool:
    p = rel(path)
    if is_source_allowed(p):
        return False
    return match_any(p, GENERATED_PATTERNS)


def parse_porcelain_z(raw: bytes) -> List[Tuple[str, str]]:
    # git status --porcelain=v1 -z format: XY path\0, renames have second path too.
    text = raw.decode("utf-8", errors="replace")
    parts = text.split("\0")
    out: List[Tuple[str, str]] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        status = part[:2]
        path = part[3:] if len(part) > 3 else ""
        out.append((status, rel(path)))
        if status.strip().startswith("R") or status.strip().startswith("C"):
            i += 2
        else:
            i += 1
    return out


def get_changed_files() -> List[Tuple[str, str]]:
    r = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode("utf-8", errors="replace"))
    return parse_porcelain_z(r.stdout)


def has_origin_main() -> bool:
    r = run(["git", "rev-parse", "--verify", "origin/main"])
    return r.returncode == 0


def file_is_tracked(path: str) -> bool:
    r = run(["git", "ls-files", "--error-unmatch", "--", path])
    return r.returncode == 0


def restore_path(path: str, source: str) -> Dict[str, str]:
    tracked = file_is_tracked(path)
    if tracked:
        r = run(["git", "restore", "--source", source, "--", path])
        if r.returncode != 0:
            # Fallback to HEAD when origin/main lacks the file.
            r2 = run(["git", "restore", "--", path])
            if r2.returncode != 0:
                return {"path": path, "action": "restore_failed", "error": (r.stderr + r2.stderr).strip()}
            return {"path": path, "action": "restored_from_HEAD"}
        return {"path": path, "action": f"restored_from_{source}"}

    # Untracked generated file/dir: remove.
    p = ROOT / path
    try:
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
            return {"path": path, "action": "removed_untracked_dir"}
        if p.exists():
            p.unlink()
            return {"path": path, "action": "removed_untracked_file"}
        return {"path": path, "action": "already_absent"}
    except Exception as e:
        return {"path": path, "action": "remove_failed", "error": str(e)}


def add_local_exclude() -> Dict[str, object]:
    info = ROOT / ".git" / "info"
    exclude = info / "exclude"
    info.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8", errors="ignore") if exclude.exists() else ""
    block = """
# REPO-HYGIENE-01 local/generated outputs
outputs/**
*.zip
*.bak_*
*.tmp
runtime/sig_shadow/live_logs/**
runtime/sig_shadow/price_bridge_h1/**
"""
    if "REPO-HYGIENE-01 local/generated outputs" not in existing:
        exclude.write_text(existing.rstrip() + "\n" + block + "\n", encoding="utf-8")
        return {"updated": True, "path": ".git/info/exclude"}
    return {"updated": False, "path": ".git/info/exclude"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Apply cleanup. Without this, only reports.")
    ap.add_argument("--source", default=None, help="Restore tracked generated files from this ref. Default: origin/main if available else HEAD.")
    ap.add_argument("--abort-merge", action="store_true", help="Run git merge --abort first if MERGE_HEAD exists.")
    args = ap.parse_args()

    if not git_ok():
        raise SystemExit("Not inside a git repository.")

    if args.abort_merge and (ROOT / ".git" / "MERGE_HEAD").exists():
        r = run(["git", "merge", "--abort"])
        if r.returncode != 0:
            raise SystemExit("git merge --abort failed:\n" + r.stderr)

    source = args.source or ("origin/main" if has_origin_main() else "HEAD")

    changed = get_changed_files()
    generated = []
    kept = []
    for status, path in changed:
        if is_generated(path):
            generated.append({"status": status, "path": path, "tracked": file_is_tracked(path)})
        else:
            kept.append({"status": status, "path": path, "tracked": file_is_tracked(path)})

    actions = []
    exclude_result = None
    if args.apply:
        exclude_result = add_local_exclude()
        # Clean generated children first; stable sort by path length descending helps remove files before parent dirs.
        for item in sorted(generated, key=lambda x: len(x["path"]), reverse=True):
            actions.append(restore_path(item["path"], source))

    report = {
        "report_name": "REPO_HYGIENE_01_CLEAN_GENERATED_CHANGES",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "restore_source": source,
        "generated_change_count": len(generated),
        "kept_source_change_count": len(kept),
        "generated_changes": generated,
        "kept_source_changes": kept,
        "actions": actions,
        "local_exclude": exclude_result,
        "guidance": {
            "commit": "Commit kept_source_changes only.",
            "do_not_force_push": True,
            "do_not_commit": [
                "outputs/**",
                "data/live_m5/**",
                "runtime/sig_shadow/*current.json",
                "runtime/sig_shadow/live_logs/**",
                "runtime/sig_shadow/price_bridge_h1/**",
                "panel/brain4/*current.json",
                "proofs/*.json",
                "zip/local test outputs",
            ],
        },
    }

    out = REPORT_DIR / "repo_hygiene_01_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "REPO_HYGIENE_01_APPLIED" if args.apply else "REPO_HYGIENE_01_DRY_RUN",
        "generated_change_count": len(generated),
        "kept_source_change_count": len(kept),
        "report": str(out).replace("\\", "/"),
        "do_not_force_push": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
