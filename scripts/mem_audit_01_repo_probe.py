from pathlib import Path
import csv
import json
import re
import zipfile
import traceback
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "_mem_audit_01_repo_probe"
OUT.mkdir(parents=True, exist_ok=True)

KNOWN_IDS = [
    "EURUSD_SESSION_UPSIDE_SWEEP_REJECTION_FADE_DOWN_CAVEATED_WATCH_v1_0",
    "USDJPY_ALIGNMENT_ABSENT_CHOP_AVOID_SHORT_CONTEXT_CAVEATED_WATCH_v1_0",
    "USDJPY_PRIOR48_NY_UPSIDE_SWEEP_REJECTION_FADE_DOWN_CAVEATED_WATCH_v1_0",
    "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_REJECT_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_NY_UP_EXTENSION_UPPER_REJECTION_FADE_DOWN_v1_0",
    "USDJPY_LONDON_ASIA_LOW_SWEEP_RECLAIM_LONG_D1NEUTRAL_H4NEUTRAL_H1_v1",
    "USDJPY_LONDON_ASIA_HIGH_SWEEP_RECLAIM_SHORT_D1DOWN_H4NEUTRAL_H1_v1",
    "EURUSD_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_H1_v1",
    "EURUSD_OVERLAP_LONDON_HIGH_SWEEP_RECLAIM_SHORT_D1DOWN_H4DOWN_H1_v1",
    "USDJPY_OVERLAP_LONDON_HIGH_SWEEP_RECLAIM_SHORT_D1NEUTRAL_H4NEUTRAL_H1_v1",
    "XAUUSD_M15_EVENT_SESSION_RANGE_EXPANSION_CANDIDATE_LIKE_OBJECT_v1_0",
    "SIGC_EURUSD_H1_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_v1_0",
]

SEARCH_TERMS = [
    "memory_id",
    "active_in_runtime",
    "registry_status",
    "ACTIVE_CAVEATED",
    "ACTIVE_CAVEATED_WATCH",
    "ARCHIVED",
    "WEAKENED",
    "REJECTED",
    "NO_TRADE",
    "BLOCKER",
    "DIRECTIONAL_WATCH",
    "CAVEATED_VALIDATION",
    "CORE_SETUP_TRIGGER",
    "EXTENDED_OBSERVATION",
    "sig_brain",
    "memory_registry",
    "runtime_memory",
]

TEXT_EXTS = {".py", ".json", ".md", ".txt", ".csv", ".yml", ".yaml", ".js", ".ts", ".html", ".css"}
SKIP_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules",
    ".next", "dist", "build", ".pytest_cache"
}
MAX_TEXT_SCAN = 60 * 1024 * 1024

GENERIC_ID_RE = re.compile(r"\b(?:EURUSD|USDJPY|XAUUSD|SIGC)[A-Za-z0-9_]{16,}\b")

def safe_rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")

def should_skip(p: Path) -> bool:
    return bool(set(p.parts).intersection(SKIP_DIRS))

def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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

def file_inventory():
    rows = []
    for p in ROOT.rglob("*"):
        if should_skip(p) or not p.is_file():
            continue
        try:
            st = p.stat()
            rows.append({
                "path": safe_rel(p),
                "ext": p.suffix.lower(),
                "size_mb": round(st.st_size / 1024 / 1024, 4),
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            })
        except Exception:
            pass
    return rows

def read_text(p: Path):
    try:
        if p.stat().st_size > MAX_TEXT_SCAN:
            return None
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

def scan_files():
    text_hit_files = []
    line_hits = []
    discovered_ids = {}

    for p in ROOT.rglob("*"):
        if should_skip(p) or not p.is_file():
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue

        rel = safe_rel(p)
        txt = read_text(p)
        if txt is None:
            continue

        known_found = [mid for mid in KNOWN_IDS if mid in txt]
        term_found = [t for t in SEARCH_TERMS if t.lower() in txt.lower()]
        generic_found = sorted(set(GENERIC_ID_RE.findall(txt)))

        for gid in generic_found:
            discovered_ids[gid] = discovered_ids.get(gid, 0) + 1

        if known_found or term_found or generic_found:
            text_hit_files.append({
                "path": rel,
                "known_ids_found": "|".join(known_found),
                "terms_found": "|".join(term_found[:30]),
                "generic_ids_found": "|".join(generic_found[:80]),
                "size_mb": round(p.stat().st_size / 1024 / 1024, 4),
            })

            lines = txt.splitlines()
            for idx, line in enumerate(lines, 1):
                low = line.lower()
                if (
                    any(mid in line for mid in KNOWN_IDS)
                    or any(t.lower() in low for t in SEARCH_TERMS)
                    or GENERIC_ID_RE.search(line)
                ):
                    clean = line.strip()
                    if len(clean) > 1200:
                        clean = clean[:1200] + "..."
                    line_hits.append({
                        "path": rel,
                        "line": idx,
                        "text": clean,
                    })

    id_rows = [{"id": k, "file_hit_count": v} for k, v in sorted(discovered_ids.items(), key=lambda x: (-x[1], x[0]))]
    return text_hit_files, line_hits, id_rows

def csv_schema_and_hits():
    schema_rows = []
    csv_hit_rows = []

    for p in ROOT.rglob("*.csv"):
        if should_skip(p) or not p.is_file():
            continue
        rel = safe_rel(p)

        try:
            with p.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                cols = reader.fieldnames or []
                schema_rows.append({
                    "path": rel,
                    "size_mb": round(p.stat().st_size / 1024 / 1024, 4),
                    "column_count": len(cols),
                    "columns": "|".join(cols),
                })

                row_num = 0
                for row in reader:
                    row_num += 1
                    if row_num > 200000:
                        break
                    row_text = json.dumps(row, ensure_ascii=False)
                    matched_known = [mid for mid in KNOWN_IDS if mid in row_text]
                    matched_generic = GENERIC_ID_RE.findall(row_text)
                    if matched_known or matched_generic:
                        compact = {
                            k: v for k, v in row.items()
                            if any(s in k.lower() for s in [
                                "memory", "id", "status", "active", "stage", "classification",
                                "rows", "count", "delta", "horizon", "instrument", "timeframe",
                                "session", "family", "direction", "tau", "year", "cost"
                            ])
                        }
                        csv_hit_rows.append({
                            "path": rel,
                            "row_number": row_num,
                            "matched_known": "|".join(matched_known),
                            "matched_generic": "|".join(sorted(set(matched_generic))[:20]),
                            "row_excerpt": json.dumps(compact if compact else row, ensure_ascii=False)[:3000],
                        })
        except Exception as e:
            schema_rows.append({
                "path": rel,
                "error": repr(e),
            })

    return schema_rows, csv_hit_rows

def walk_json(obj, path=""):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from walk_json(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, f"{path}[{i}]")

def json_hits():
    rows = []

    for p in ROOT.rglob("*.json"):
        if should_skip(p) or not p.is_file():
            continue
        rel = safe_rel(p)
        try:
            if p.stat().st_size > 80 * 1024 * 1024:
                continue
            data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception as e:
            rows.append({"path": rel, "json_path": "", "matched": "__JSON_PARSE_ERROR__", "excerpt": repr(e)})
            continue

        for jpath, obj in walk_json(data):
            txt = json.dumps(obj, ensure_ascii=False)
            matched_known = [mid for mid in KNOWN_IDS if mid in txt]
            matched_generic = sorted(set(GENERIC_ID_RE.findall(txt)))
            matched_terms = [t for t in SEARCH_TERMS if t.lower() in txt.lower()]

            if matched_known or matched_generic or matched_terms:
                if isinstance(obj, dict):
                    compact = {
                        k: v for k, v in obj.items()
                        if any(s in str(k).lower() for s in [
                            "memory", "id", "status", "active", "stage", "classification",
                            "rows", "count", "delta", "horizon", "instrument", "timeframe",
                            "session", "family", "direction", "tau", "year", "cost",
                            "runtime", "validation", "discovery", "holdout"
                        ])
                    }
                    excerpt_obj = compact if compact else obj
                else:
                    excerpt_obj = obj

                rows.append({
                    "path": rel,
                    "json_path": jpath,
                    "matched_known": "|".join(matched_known),
                    "matched_generic": "|".join(matched_generic[:30]),
                    "matched_terms": "|".join(matched_terms[:30]),
                    "excerpt": json.dumps(excerpt_obj, ensure_ascii=False)[:3500],
                })

    return rows

def make_markdown_summary(inv, text_files, ids, csv_schema, csv_rows, json_rows):
    lines = []
    lines.append("# MEM-AUDIT-01 TradingOS2 Repo Probe Summary\n\n")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append(f"Root: `{ROOT}`\n\n")

    lines.append("## Top-level file counts\n\n")
    counts = {}
    for r in inv:
        top = r["path"].split("/")[0] if "/" in r["path"] else "."
        counts[top] = counts.get(top, 0) + 1
    for k, v in sorted(counts.items()):
        lines.append(f"- `{k}`: {v}\n")

    lines.append("\n## Most frequent discovered candidate/memory-like IDs\n\n")
    for r in ids[:100]:
        lines.append(f"- `{r['id']}` — files: {r['file_hit_count']}\n")

    lines.append("\n## Important files with memory/status terms\n\n")
    for r in text_files[:150]:
        lines.append(f"- `{r['path']}`\n")
        if r.get("known_ids_found"):
            lines.append(f"  - known: `{r['known_ids_found']}`\n")
        if r.get("terms_found"):
            lines.append(f"  - terms: `{r['terms_found']}`\n")
        if r.get("generic_ids_found"):
            lines.append(f"  - ids: `{r['generic_ids_found'][:500]}`\n")

    lines.append("\n## CSV/JSON hit counts\n\n")
    lines.append(f"- CSV schemas: {len(csv_schema)}\n")
    lines.append(f"- CSV row hits: {len(csv_rows)}\n")
    lines.append(f"- JSON object hits: {len(json_rows)}\n")

    lines.append("\n## What to send back\n\n")
    lines.append("Send `MEM_AUDIT_01_REPO_PROBE_PACK.zip` back to ChatGPT.\n")

    (OUT / "MEM_AUDIT_01_REPO_PROBE_SUMMARY.md").write_text("".join(lines), encoding="utf-8")

def zip_pack():
    zpath = OUT / "MEM_AUDIT_01_REPO_PROBE_PACK.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file() and p.name != zpath.name:
                z.write(p, p.relative_to(OUT))
    return zpath

def main():
    errors = []
    inv = []
    text_files = []
    line_rows = []
    ids = []
    csv_schema = []
    csv_rows = []
    jrows = []

    try:
        inv = file_inventory()
        write_csv(OUT / "MEM_AUDIT_01_repo_file_inventory.csv", inv)
    except Exception:
        errors.append("file_inventory\n" + traceback.format_exc())

    try:
        text_files, line_rows, ids = scan_files()
        write_csv(OUT / "MEM_AUDIT_01_repo_text_hit_files.csv", text_files)
        write_csv(OUT / "MEM_AUDIT_01_repo_line_hits.csv", line_rows)
        write_csv(OUT / "MEM_AUDIT_01_discovered_memory_like_ids.csv", ids)
    except Exception:
        errors.append("scan_files\n" + traceback.format_exc())

    try:
        csv_schema, csv_rows = csv_schema_and_hits()
        write_csv(OUT / "MEM_AUDIT_01_repo_csv_schema.csv", csv_schema)
        write_csv(OUT / "MEM_AUDIT_01_repo_csv_row_hits.csv", csv_rows)
    except Exception:
        errors.append("csv_schema_and_hits\n" + traceback.format_exc())

    try:
        jrows = json_hits()
        write_csv(OUT / "MEM_AUDIT_01_repo_json_hits.csv", jrows)
    except Exception:
        errors.append("json_hits\n" + traceback.format_exc())

    try:
        make_markdown_summary(inv, text_files, ids, csv_schema, csv_rows, jrows)
    except Exception:
        errors.append("make_markdown_summary\n" + traceback.format_exc())

    if errors:
        (OUT / "MEM_AUDIT_01_REPO_PROBE_ERRORS.txt").write_text("\n\n".join(errors), encoding="utf-8")

    zpath = zip_pack()

    print("MEM_AUDIT_01_REPO_PROBE_DONE")
    print("Output folder:", OUT)
    print("Zip pack:", zpath)

if __name__ == "__main__":
    main()
