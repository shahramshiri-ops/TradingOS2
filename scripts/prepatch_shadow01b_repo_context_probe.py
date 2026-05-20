from pathlib import Path
import csv
import json
import zipfile
import hashlib
import os
import re
import shutil
import traceback
from datetime import datetime

REPO_ROOT = Path.cwd()
OUT = REPO_ROOT / "outputs" / "_prepatch_shadow01b_repo_context_probe"
COPY_ROOT = OUT / "copied_current_files"
OUT.mkdir(parents=True, exist_ok=True)
COPY_ROOT.mkdir(parents=True, exist_ok=True)

MAX_COPY_MB = int(os.environ.get("MAX_COPY_MB", "12"))
MAX_COPY_BYTES = MAX_COPY_MB * 1024 * 1024

SKIP_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules", ".next", "dist", "build",
    ".pytest_cache", "outputs/_prepatch_shadow01b_repo_context_probe"
}
SKIP_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
}
SENSITIVE_PATTERNS = [
    re.compile(r".*secret.*", re.I),
    re.compile(r".*token.*", re.I),
    re.compile(r".*password.*", re.I),
    re.compile(r".*api[_-]?key.*", re.I),
    re.compile(r".*\.pem$", re.I),
    re.compile(r".*\.key$", re.I),
]

TEXT_EXTS = {
    ".py", ".json", ".md", ".txt", ".csv", ".yml", ".yaml",
    ".js", ".ts", ".html", ".css", ".toml", ".ini", ".cfg"
}

KEYWORDS = [
    # runtime pipeline
    "sig_brain4_runtime_payload_current",
    "sig_brain5_derived_context_latest",
    "sig_live_refresh_status_latest",
    "active_match_count",
    "active_matches",
    "active_runtime_memory",
    "active_in_runtime",
    "memory_id",
    "memory_registry",
    "brain_memory_registry",
    "build_sig_brain4_runtime_payload",
    "build_sig_brain5_live_context",
    "validate_sig_brain5",
    "validate_sig_brain6",
    "runtime_payload",
    "event_history",
    "context_builder",
    "context_registry",
    # signal / shadow terms
    "signal_candidate",
    "signal candidates",
    "sig_signal_candidates",
    "shadow",
    "sig_shadow",
    "shadow_candidate",
    "shadow_ledger",
    "forward_shadow",
    "blocked_candidate",
    "MFE",
    "MAE",
    # github actions integration
    "workflow_dispatch",
    "workflow_run",
    "schedule:",
    "cron:",
    "permissions:",
    "contents: write",
    "actions/checkout",
    "git-auto-commit",
    "deploy-pages",
    "github-pages",
    # panel / pages
    "panel/brain4",
    "brain4_panel",
    "PANEL_VERSION",
    "runtime/sig_brain",
    "runtime/sig_shadow",
    # governance labels
    "NOT_SIGNAL",
    "NO_BROKER",
    "NO_ENTRY_STOP_TARGET",
    "DISPLAY_ONLY",
]

MUST_COPY_PATHS = [
    # registries
    "sig_brain/brain_memory_registry_v1_0.json",
    "sig_brain/memory_context_requirements_matrix_v1_0.json",
    "sig_brain/memory_context_requirements_matrix_v1_0.csv",
    "sig_brain/context_field_registry_v1_0.json",
    "sig_brain/context_builder_support_registry_v1_0.json",
    "sig_brain/feature_family_catalog_v1_0.json",
    # runtime payloads
    "runtime/sig_brain/sig_brain4_runtime_payload_current.json",
    "runtime/sig_brain/sig_brain4_event_history_current.json",
    "runtime/sig_brain/sig_brain5_derived_context_latest.json",
    "runtime/sig_brain/sig_live_refresh_status_latest.json",
    "runtime/sig_brain/sig_brain4_runtime_payload_previous.json",
    # proofs
    "proofs/sig_brain6_context_registry_validation_result.json",
    "proofs/sig_brain6_context_registry_validation_result.csv",
    "proofs/sig_brain6_runtime_context_coverage_result.json",
    "proofs/sig_brain5_context_builder_validation_result.json",
    # key scripts
    "scripts/build_sig_brain4_runtime_payload.py",
    "scripts/build_sig_brain5_live_context.py",
    "scripts/update_sig_brain4_event_history.py",
    "scripts/validate_sig_brain5_context_builder.py",
    "scripts/validate_sig_brain6_context_registry.py",
    "scripts/check_sig_brain6_runtime_context_coverage.py",
    "scripts/fetch_twelvedata_m5_incremental.py",
    "scripts/merge_m5_canonical_store.py",
    "scripts/resample_m5_to_higher_timeframes.py",
    "scripts/build_brain5_raw_bars_from_resampled.py",
    # possible already-installed shadow/sigcand scripts
    "scripts/build_sig_shadow_candidate_ledger.py",
    "scripts/update_sig_shadow_observations.py",
    "scripts/summarize_sig_shadow_ledger.py",
    "scripts/validate_sig_shadow_outputs.py",
    "scripts/run_shadow_01b_once.py",
    "scripts/build_sig_signal_candidate_shadow_intake.py",
    "scripts/validate_sig_signal_candidate_shadow_intake.py",
    # current shadow/sigcand outputs if any
    "runtime/sig_signal_candidates/signal_candidate_payload_current.json",
    "runtime/sig_signal_candidates/signal_candidate_summary_current.json",
    "runtime/sig_shadow/shadow_candidate_ledger_current.json",
    "runtime/sig_shadow/shadow_observation_ledger_current.json",
    "runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json",
    "runtime/sig_shadow/shadow_summary_current.json",
    "proofs/sig_shadow_01b_validation_result.json",
    "proofs/sig_signal_candidate_shadow_intake_validation_result.json",
    # panel
    "panel/brain4/index.html",
    "panel/brain4/assets/brain4_panel.js",
    "panel/brain4/assets/brain4.css",
    # project config
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "README.md",
]

def safe_rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")

def should_skip_path(p: Path) -> bool:
    rel = safe_rel(p)
    parts = set(rel.split("/"))
    if parts.intersection(SKIP_DIRS):
        return True
    if p.name in SKIP_FILES:
        return True
    for pat in SENSITIVE_PATTERNS:
        if pat.match(p.name):
            return True
    return False

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_csv(path: Path, rows):
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def read_text(p: Path, max_bytes=4*1024*1024):
    try:
        if p.stat().st_size > max_bytes:
            return None
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

def copy_file(src: Path, reason: str, copied_rows: list):
    if not src.exists() or not src.is_file():
        copied_rows.append({"path": safe_rel(src), "copied": False, "reason": reason, "note": "missing"})
        return
    if should_skip_path(src):
        copied_rows.append({"path": safe_rel(src), "copied": False, "reason": reason, "note": "skipped_sensitive_or_ignored"})
        return
    size = src.stat().st_size
    if size > MAX_COPY_BYTES:
        copied_rows.append({
            "path": safe_rel(src), "copied": False, "reason": reason,
            "note": f"too_large_{round(size/1024/1024,3)}MB", "sha256": sha256_file(src)
        })
        return
    dest = COPY_ROOT / safe_rel(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    copied_rows.append({
        "path": safe_rel(src), "copied": True, "reason": reason,
        "size_mb": round(size/1024/1024, 4), "sha256": sha256_file(src)
    })

def inventory_all_files():
    rows = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if should_skip_path(p):
            continue
        try:
            st = p.stat()
            rows.append({
                "path": safe_rel(p),
                "ext": p.suffix.lower(),
                "size_mb": round(st.st_size/1024/1024, 4),
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                "sha256": sha256_file(p) if st.st_size <= MAX_COPY_BYTES else "",
            })
        except Exception as e:
            rows.append({"path": safe_rel(p), "error": repr(e)})
    return rows

def scan_keyword_files():
    file_hits = []
    line_hits = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if should_skip_path(p):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        txt = read_text(p)
        if txt is None:
            continue
        found = [k for k in KEYWORDS if k.lower() in txt.lower()]
        if found:
            file_hits.append({
                "path": safe_rel(p),
                "size_mb": round(p.stat().st_size/1024/1024, 4),
                "keywords_found": "|".join(found),
                "sha256": sha256_file(p),
            })
            for i, line in enumerate(txt.splitlines(), 1):
                low = line.lower()
                if any(k.lower() in low for k in found):
                    clean = line.strip()
                    if len(clean) > 1400:
                        clean = clean[:1400] + "..."
                    line_hits.append({"path": safe_rel(p), "line": i, "text": clean})
    return file_hits, line_hits

def workflow_inventory():
    rows = []
    wfdir = REPO_ROOT / ".github" / "workflows"
    if not wfdir.exists():
        return [{"path": ".github/workflows", "exists": False}]
    for p in sorted(wfdir.glob("*")):
        if p.is_file() and p.suffix.lower() in [".yml", ".yaml"]:
            txt = read_text(p, max_bytes=2*1024*1024) or ""
            rows.append({
                "path": safe_rel(p),
                "exists": True,
                "has_schedule": "schedule:" in txt,
                "has_workflow_dispatch": "workflow_dispatch" in txt,
                "has_workflow_run": "workflow_run" in txt,
                "has_pages_deploy": "deploy-pages" in txt or "github-pages" in txt,
                "has_commit_push": "git-auto-commit" in txt or "git commit" in txt or "git push" in txt,
                "mentions_brain": "brain" in txt.lower() or "sig_" in txt.lower(),
                "keywords": "|".join([k for k in KEYWORDS if k.lower() in txt.lower()]),
                "sha256": sha256_file(p),
            })
    return rows

def json_summary(path: Path):
    out = {"path": safe_rel(path), "exists": path.exists()}
    if not path.exists():
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        out["top_level_type"] = type(data).__name__
        if isinstance(data, dict):
            out["top_level_keys"] = "|".join(list(data.keys())[:80])
            # common counts
            for key in ["memories", "active_matches", "events", "candidates", "shadow_candidates", "observations", "blocked_candidates"]:
                if key in data and isinstance(data[key], list):
                    out[f"{key}_count"] = len(data[key])
            if "active_runtime_memory_count" in data:
                out["active_runtime_memory_count"] = data["active_runtime_memory_count"]
            if "active_match_count" in data:
                out["active_match_count"] = data["active_match_count"]
            if "registry_version" in data:
                out["registry_version"] = data["registry_version"]
            if "schema_version" in data:
                out["schema_version"] = data["schema_version"]
        elif isinstance(data, list):
            out["list_count"] = len(data)
    except Exception as e:
        out["error"] = repr(e)
    return out

def csv_schema_summary(path: Path):
    out = {"path": safe_rel(path), "exists": path.exists()}
    if not path.exists():
        return out
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
        out["column_count"] = len(cols)
        out["columns"] = "|".join(cols)
    except Exception as e:
        out["error"] = repr(e)
    return out

def main():
    errors = []
    copied_rows = []

    inventory = inventory_all_files()
    write_csv(OUT / "PREPATCH_repo_file_inventory.csv", inventory)

    file_hits, line_hits = scan_keyword_files()
    write_csv(OUT / "PREPATCH_keyword_file_hits.csv", file_hits)
    write_csv(OUT / "PREPATCH_keyword_line_hits.csv", line_hits)

    workflows = workflow_inventory()
    write_csv(OUT / "PREPATCH_workflow_inventory.csv", workflows)

    # Copy all workflow files
    wfdir = REPO_ROOT / ".github" / "workflows"
    if wfdir.exists():
        for p in sorted(wfdir.glob("*")):
            if p.is_file() and p.suffix.lower() in [".yml", ".yaml"]:
                copy_file(p, "all_workflows", copied_rows)

    # Copy must-have files
    for rel in MUST_COPY_PATHS:
        copy_file(REPO_ROOT / rel, "must_copy_path", copied_rows)

    # Copy keyword-hit source files, within size limit
    for r in file_hits:
        p = REPO_ROOT / r["path"]
        copy_file(p, "keyword_hit", copied_rows)

    write_csv(OUT / "PREPATCH_copied_files_manifest.csv", copied_rows)

    # Summarize key json/csv files
    summary_paths = []
    for rel in MUST_COPY_PATHS:
        p = REPO_ROOT / rel
        if p.suffix.lower() == ".json":
            summary_paths.append(("json", p))
        elif p.suffix.lower() == ".csv":
            summary_paths.append(("csv", p))

    json_rows = [json_summary(p) for typ, p in summary_paths if typ == "json"]
    csv_rows = [csv_schema_summary(p) for typ, p in summary_paths if typ == "csv"]
    write_csv(OUT / "PREPATCH_key_json_summaries.csv", json_rows)
    write_csv(OUT / "PREPATCH_key_csv_schemas.csv", csv_rows)

    # Write markdown summary
    md = []
    md.append("# PREPATCH SHADOW-01B Repository Context Probe\n\n")
    md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
    md.append(f"Repo root: `{REPO_ROOT}`\n\n")
    md.append("## Purpose\n\n")
    md.append("Collect exact current repo context before producing a safe integrated SHADOW-01B patch.\n\n")
    md.append("## Boundary\n\n")
    md.append("- This script does not modify runtime logic.\n")
    md.append("- It only copies selected current repo files into a review pack.\n")
    md.append("- It skips obvious secret/token/env/key files.\n\n")
    md.append("## Workflow files\n\n")
    for r in workflows:
        md.append(f"- `{r.get('path')}` | schedule={r.get('has_schedule')} | dispatch={r.get('has_workflow_dispatch')} | workflow_run={r.get('has_workflow_run')}\n")
    md.append("\n## Important keyword-hit files\n\n")
    for r in file_hits[:250]:
        md.append(f"- `{r['path']}` — `{r['keywords_found']}`\n")
    md.append("\n## Copied files\n\n")
    for r in copied_rows:
        if r.get("copied"):
            md.append(f"- `{r['path']}` — {r.get('reason')}\n")
    md.append("\n## Missing / not copied\n\n")
    for r in copied_rows:
        if not r.get("copied"):
            md.append(f"- `{r['path']}` — {r.get('note')} — {r.get('reason')}\n")
    (OUT / "PREPATCH_SHADOW01B_CONTEXT_SUMMARY.md").write_text("".join(md), encoding="utf-8")

    # Zip
    zpath = REPO_ROOT / "outputs" / "PREPATCH_SHADOW01B_REPO_CONTEXT_PACK.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(OUT))

    print("PREPATCH_SHADOW01B_CONTEXT_PROBE_DONE")
    print("Output folder:", OUT)
    print("Zip pack:", zpath)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        (OUT / "PREPATCH_SHADOW01B_CONTEXT_PROBE_ERROR.txt").write_text(err, encoding="utf-8")
        print(err)
        raise
