from pathlib import Path
import csv, json, zipfile, os, re
from datetime import datetime

REPO_ROOT = Path.cwd()
DISCOVERY_ROOT = Path(os.environ["SIG_DISCOVERY_ROOT"])
OUT = REPO_ROOT / "outputs" / "_mem_audit_01c_source_mapping"
OUT.mkdir(parents=True, exist_ok=True)

TERMS = [
    "failed_breakout_event_type",
    "failed_breakout_level_type",
    "failed_breakout_reference_policy_id",
    "same_utc_date_london_range_available",
    "london_low_swept_and_reclaimed_by_closed_h1",
    "h1_failed_breakout_or_session_sweep_state",
    "directional_side",
    "failed_breakout_failure_side",
    "policy_id",
    "same_utc_date_asian_range_available",
    "asian_high_swept_and_reclaimed_by_closed_h1",
    "is_weekly_open_bar",
    "weekly_open_reclaim_short_state",
    "vol_expansion_after_contraction_state",
    "asian_high_breakout_continuation_by_closed_h1",

    "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_CAVEATED_WATCH_v1_0",
    "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_LONDON_ASIAN_HIGH_SWEEP_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0",
    "XAUUSD_H1_WEEKLY_OPEN_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0",
]

TEXT_EXTS = {".py",".json",".md",".txt",".csv",".yml",".yaml"}
SKIP_DIRS = {".git",".venv","__pycache__","node_modules"}
MAX_SCAN = 120 * 1024 * 1024

def safe_rel(root, p):
    try:
        return str(p.relative_to(root)).replace("\\","/")
    except Exception:
        return str(p).replace("\\","/")

def should_skip(p):
    return bool(set(p.parts).intersection(SKIP_DIRS))

def write_csv(path, rows):
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow(r)

def scan_root(label, root):
    file_hits=[]
    line_hits=[]
    csv_schema=[]
    for p in root.rglob("*"):
        if should_skip(p) or not p.is_file(): continue
        if p.suffix.lower() not in TEXT_EXTS: continue
        try:
            size=p.stat().st_size
            if size > MAX_SCAN: continue
            txt=p.read_text(encoding="utf-8",errors="ignore")
        except Exception:
            continue

        found=[t for t in TERMS if t in txt]
        if found:
            rel=safe_rel(root,p)
            file_hits.append({
                "root": label,
                "path": rel,
                "size_mb": round(size/1024/1024,4),
                "terms_found": "|".join(found)
            })
            for i,line in enumerate(txt.splitlines(),1):
                if any(t in line for t in found):
                    clean=line.strip()
                    if len(clean)>1200: clean=clean[:1200]+"..."
                    line_hits.append({
                        "root": label,
                        "path": rel,
                        "line": i,
                        "text": clean
                    })

        if p.suffix.lower()==".csv":
            try:
                with p.open("r",encoding="utf-8-sig",errors="ignore",newline="") as f:
                    reader=csv.DictReader(f)
                    cols=reader.fieldnames or []
                matched_cols=[c for c in cols if c in TERMS or any(t in c for t in TERMS)]
                if matched_cols or found:
                    csv_schema.append({
                        "root": label,
                        "path": safe_rel(root,p),
                        "size_mb": round(size/1024/1024,4),
                        "matched_columns": "|".join(matched_cols),
                        "all_columns": "|".join(cols)
                    })
            except Exception as e:
                pass

    return file_hits,line_hits,csv_schema

all_file_hits=[]
all_line_hits=[]
all_csv_schema=[]

for label, root in [("REPO", REPO_ROOT), ("DISCOVERY", DISCOVERY_ROOT)]:
    fh, lh, cs = scan_root(label, root)
    all_file_hits.extend(fh)
    all_line_hits.extend(lh)
    all_csv_schema.extend(cs)

write_csv(OUT / "MEM_AUDIT_01C_source_file_hits.csv", all_file_hits)
write_csv(OUT / "MEM_AUDIT_01C_source_line_hits.csv", all_line_hits)
write_csv(OUT / "MEM_AUDIT_01C_csv_schema_hits.csv", all_csv_schema)

# copy small matching files for review
copy_dir = OUT / "matched_files_excerpt_pack"
copy_dir.mkdir(exist_ok=True)
for r in all_file_hits:
    root = REPO_ROOT if r["root"]=="REPO" else DISCOVERY_ROOT
    src = root / r["path"]
    if src.exists() and src.stat().st_size <= 8 * 1024 * 1024:
        dest = copy_dir / r["root"] / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(src.read_bytes())
        except Exception:
            pass

md=[]
md.append("# MEM-AUDIT-01C — Missing Field / Source Ledger Mapping\n\n")
md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
md.append("## Purpose\n\nFind where missing event fields / memory IDs exist in repo or discovery outputs/scripts.\n\n")
md.append("## File hits\n\n")
for r in all_file_hits[:300]:
    md.append(f"- `{r['root']}::{r['path']}` — `{r['terms_found']}`\n")
(OUT / "MEM_AUDIT_01C_SUMMARY.md").write_text("".join(md), encoding="utf-8")

zpath = REPO_ROOT / "outputs" / "MEM_AUDIT_01C_SOURCE_MAPPING_PACK.zip"
if zpath.exists(): zpath.unlink()
with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(OUT))

print("MEM_AUDIT_01C_SOURCE_MAPPING_DONE")
print("Zip pack:", zpath)
