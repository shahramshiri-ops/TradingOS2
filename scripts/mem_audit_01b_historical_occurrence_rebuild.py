from pathlib import Path
import csv
import json
import zipfile
import os
import traceback
from datetime import datetime

REPO_ROOT = Path.cwd()
DISCOVERY_ROOT = Path(os.environ.get("SIG_DISCOVERY_ROOT", "")).resolve() if os.environ.get("SIG_DISCOVERY_ROOT") else None

if DISCOVERY_ROOT is None or not DISCOVERY_ROOT.exists():
    candidates = [
        Path.home() / "Documents" / "SIG_BRAIN_DISCOVERY",
        Path.home() / "OneDrive" / "Documents" / "SIG_BRAIN_DISCOVERY",
    ]
    DISCOVERY_ROOT = next((p for p in candidates if p.exists()), None)

OUT = REPO_ROOT / "outputs" / "_mem_audit_01b_occurrence"
OUT.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = REPO_ROOT / "sig_brain" / "brain_memory_registry_v1_0.json"
FEATURE_DIR = DISCOVERY_ROOT / "data" / "features" if DISCOVERY_ROOT else None

DISCOVERY_START = "2004-01-01"
DISCOVERY_END = "2014-12-31"
VALIDATION_START = "2015-01-01"
VALIDATION_END = "2019-12-31"
HOLDOUT_START = "2020-01-01"
HOLDOUT_END = "2024-12-31"

TIMESTAMP_COLUMNS = [
    "bar_open_ts_utc", "timestamp_utc", "ts_utc", "datetime_utc",
    "timestamp", "datetime", "time", "date", "bar_time"
]

BOOL_TRUE = {"true", "1", "yes", "y", "t"}
BOOL_FALSE = {"false", "0", "no", "n", "f", ""}

FIELD_ALIASES = {
    "d1_trend_safe": ["d1_trend_safe", "d1_trend_state", "d1_state", "d1_dir"],
    "h4_trend_safe": ["h4_trend_safe", "h4_trend_state", "h4_state", "h4_dir"],
    "d1_trend_state": ["d1_trend_state", "d1_trend_safe", "d1_state", "d1_dir"],
    "h4_trend_state": ["h4_trend_state", "h4_trend_safe", "h4_state", "h4_dir"],
    "timeframe": ["timeframe", "base_timeframe"],
    "base_timeframe": ["base_timeframe", "timeframe"],
    "session_bucket": ["session_bucket", "session", "session_name"],
    "h1_bar_direction": ["h1_bar_direction", "bar_direction", "candle_direction"],
}

def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def norm_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).strip()

def parse_bool(v):
    if isinstance(v, bool):
        return v
    s = norm_text(v).lower()
    if s in BOOL_TRUE:
        return True
    if s in BOOL_FALSE:
        return False
    return None

def parse_float(v):
    try:
        if v is None or norm_text(v) == "":
            return None
        return float(str(v).replace(",", ""))
    except Exception:
        return None

def extract_date_str(v):
    s = norm_text(v)
    if not s:
        return ""
    # Works for YYYY-MM-DD, YYYY-MM-DDTHH, YYYY-MM-DD HH, etc.
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return s[:10]
    return s[:10]

def split_for_date(d):
    if not d:
        return "UNKNOWN_DATE"
    if DISCOVERY_START <= d <= DISCOVERY_END:
        return "DISCOVERY_2004_2014"
    if VALIDATION_START <= d <= VALIDATION_END:
        return "VALIDATION_2015_2019"
    if HOLDOUT_START <= d <= HOLDOUT_END:
        return "HOLDOUT_2020_2024_COUNT_ONLY"
    if d < DISCOVERY_START:
        return "PRE_DISCOVERY"
    return "POST_HOLDOUT_OR_OTHER"

def year_for_date(d):
    return d[:4] if d and len(d) >= 4 else "UNKNOWN"

def get_with_alias(row, field):
    if field in row:
        return row.get(field), field
    for alt in FIELD_ALIASES.get(field, []):
        if alt in row:
            return row.get(alt), alt
    return None, None

def compare_eq(actual, expected):
    if isinstance(expected, bool):
        b = parse_bool(actual)
        return b is not None and b == expected
    if isinstance(expected, (int, float)):
        x = parse_float(actual)
        return x is not None and x == float(expected)
    return norm_text(actual).upper() == norm_text(expected).upper()

def eval_condition(row, cond):
    op = cond.get("op")
    field = cond.get("field")

    if op == "not_pair_eq":
        left = cond.get("left_field")
        right = cond.get("right_field")
        value = cond.get("value")
        lv, lsrc = get_with_alias(row, left)
        rv, rsrc = get_with_alias(row, right)
        if lsrc is None or rsrc is None:
            return False, f"MISSING_PAIR:{left}|{right}"
        return not (compare_eq(lv, value) and compare_eq(rv, value)), ""

    if not field:
        return False, f"UNSUPPORTED_NO_FIELD_OP:{op}"

    actual, src = get_with_alias(row, field)
    if src is None:
        return False, f"MISSING_FIELD:{field}"

    expected = cond.get("value")

    if op in ("eq", "equals"):
        return compare_eq(actual, expected), ""
    if op == "not_eq":
        return not compare_eq(actual, expected), ""
    if op == "bool_eq":
        b = parse_bool(actual)
        if b is None:
            return False, f"BOOL_PARSE_FAIL:{field}"
        return b == bool(expected), ""
    if op == "in":
        vals = expected if isinstance(expected, list) else [expected]
        return any(compare_eq(actual, v) for v in vals), ""
    if op == "between":
        x = parse_float(actual)
        if x is None:
            return False, f"NUMERIC_PARSE_FAIL:{field}"
        lo, hi = expected
        return float(lo) <= x <= float(hi), ""
    if op == "gt":
        x = parse_float(actual)
        return (x is not None and x > float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "gte":
        x = parse_float(actual)
        return (x is not None and x >= float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "lt":
        x = parse_float(actual)
        return (x is not None and x < float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "lte":
        x = parse_float(actual)
        return (x is not None and x <= float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"

    return False, f"UNSUPPORTED_OP:{op}"

def infer_file(instrument, timeframe):
    if not FEATURE_DIR:
        return None
    candidates = [
        FEATURE_DIR / f"{instrument}_{timeframe}_context.csv",
        FEATURE_DIR / f"{instrument}_{timeframe}.csv",
        FEATURE_DIR / f"{instrument}_{timeframe.lower()}_context.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def timestamp_from_row(row):
    for c in TIMESTAMP_COLUMNS:
        if c in row and norm_text(row.get(c)):
            return norm_text(row.get(c)), c
    return "", ""

def inject_derived_fields(row, instrument, timeframe, prev_session):
    row = dict(row)
    row.setdefault("instrument", instrument)
    row.setdefault("timeframe", timeframe)
    row.setdefault("base_timeframe", timeframe)

    if "session_bucket" in row:
        row.setdefault("session", row.get("session_bucket"))
    elif "session" in row:
        row.setdefault("session_bucket", row.get("session"))

    current_session = row.get("session_bucket", "")
    row.setdefault("prior_h1_session", prev_session or "")

    if "is_first_h1_bar_of_session" not in row:
        row["is_first_h1_bar_of_session"] = (
            "true" if current_session and current_session != prev_session else "false"
        )

    if "h1_bar_direction" not in row:
        open_candidates = ["open", "h1_open", "bar_open"]
        close_candidates = ["close", "h1_close", "bar_close"]
        o = next((parse_float(row.get(c)) for c in open_candidates if c in row and parse_float(row.get(c)) is not None), None)
        cl = next((parse_float(row.get(c)) for c in close_candidates if c in row and parse_float(row.get(c)) is not None), None)
        if o is not None and cl is not None:
            if cl > o:
                row["h1_bar_direction"] = "BULLISH"
            elif cl < o:
                row["h1_bar_direction"] = "BEARISH"
            else:
                row["h1_bar_direction"] = "FLAT"

    if "session_open_trend_trigger_state" not in row:
        first = parse_bool(row.get("is_first_h1_bar_of_session"))
        direction = norm_text(row.get("h1_bar_direction")).upper()
        if first and direction == "BULLISH":
            row["session_open_trend_trigger_state"] = "SESSION_OPEN_TREND_LONG"
        elif first and direction == "BEARISH":
            row["session_open_trend_trigger_state"] = "SESSION_OPEN_TREND_SHORT"

    return row

def load_registry():
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def schema_for_csv(path):
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            return reader.fieldnames or []
    except Exception:
        return []

def memory_summary_from_evidence(mem):
    ev = mem.get("evidence_summary", {}) or {}
    return {
        "registry_validation_rows": ev.get("validation_rows", ev.get("candidate_rows_min", "")),
        "registry_discovery_rows": ev.get("discovery_rows", ""),
        "registry_avg_delta": ev.get("avg_delta", ev.get("validation_avg_delta", ev.get("validation_avg_gross_delta", ""))),
        "registry_discovery_avg_delta": ev.get("discovery_avg_delta", ""),
        "registry_positive_horizons": ev.get("positive_horizons", ev.get("positive_horizon_count", ev.get("positive_horizon_share", ""))),
        "registry_tau": ev.get("tau", ev.get("effect_retention_tau", ev.get("effect_retention_ratio_validation_vs_discovery", ""))),
        "registry_max_year_share": ev.get("max_year_share", ""),
    }

def recommended_use(mem, counts):
    active = bool(mem.get("active_in_runtime"))
    status = norm_text(mem.get("activation_status"))
    cls = norm_text(mem.get("memory_class"))
    ev = mem.get("evidence_summary", {}) or {}
    validation_rows = ev.get("validation_rows", ev.get("candidate_rows_min", 0)) or 0
    try:
        validation_rows = int(float(validation_rows))
    except Exception:
        validation_rows = 0

    val_delta = ev.get("avg_delta", ev.get("validation_avg_delta", ev.get("validation_avg_gross_delta", 0))) or 0
    disc_delta = ev.get("discovery_avg_delta", None)
    try:
        val_delta = float(val_delta)
    except Exception:
        val_delta = 0
    try:
        disc_delta_num = float(disc_delta) if disc_delta is not None and disc_delta != "" else None
    except Exception:
        disc_delta_num = None

    if "REJECT" in status or "FAIL" in status:
        return "REJECT_OR_ARCHIVE_NO_RUNTIME_USE"
    if not active:
        if "EXTENDED_OBSERVATION" in status or "PARKED" in status:
            return "EXTENDED_OBSERVATION_ONLY"
        return "ARCHIVE_NO_RUNTIME_USE"

    if "NO_TRADE" in cls or "avoid" in cls.lower():
        return "BLOCKER_ONLY"

    if disc_delta_num is not None and disc_delta_num <= 0 and val_delta > 0:
        return "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW"

    if validation_rows >= 50 and val_delta > 0:
        return "CORE_SETUP_TRIGGER_PILOT_CAVEATED"

    return "DISPLAY_CONTEXT_OR_EXTENDED_OBSERVATION_ONLY"

def main():
    errors = []
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry not found: {REGISTRY_PATH}")
    if not FEATURE_DIR or not FEATURE_DIR.exists():
        raise FileNotFoundError(f"Feature dir not found: {FEATURE_DIR}")

    registry = load_registry()
    memories = registry.get("memories", [])

    inventory_rows = []
    coverage_rows = []
    match_rows = []
    event_samples = []
    missing_rows = []
    matched_events_by_memory = {}

    for mem in memories:
        mid = mem.get("memory_id", "")
        instrument = mem.get("instrument", "")
        timeframe = mem.get("timeframe", "")
        rule = mem.get("matching_rule", {}) or {}
        conditions = rule.get("required_all", []) or []

        fpath = infer_file(instrument, timeframe)
        schema = schema_for_csv(fpath) if fpath else []

        base = {
            "memory_id": mid,
            "active_in_runtime": mem.get("active_in_runtime"),
            "activation_status": mem.get("activation_status"),
            "memory_class": mem.get("memory_class"),
            "instrument": instrument,
            "timeframe": timeframe,
            "feature_file": str(fpath) if fpath else "",
        }
        base.update(memory_summary_from_evidence(mem))

        # Pre-check fields
        missing_fields = []
        unsupported_ops = []
        for cond in conditions:
            op = cond.get("op")
            if op == "not_pair_eq":
                for lf in [cond.get("left_field"), cond.get("right_field")]:
                    if lf not in ["instrument", "timeframe", "base_timeframe"] and not any(x in schema for x in [lf] + FIELD_ALIASES.get(lf, [])):
                        missing_fields.append(lf)
            else:
                fld = cond.get("field")
                if op not in ["eq", "equals", "not_eq", "bool_eq", "in", "between", "gt", "gte", "lt", "lte"]:
                    unsupported_ops.append(op)
                if fld not in ["instrument", "timeframe", "base_timeframe"] and fld and not any(x in schema for x in [fld] + FIELD_ALIASES.get(fld, [])):
                    # Derived fields are allowed later, don't mark as fatal yet
                    if fld not in ["prior_h1_session", "is_first_h1_bar_of_session", "h1_bar_direction", "session_open_trend_trigger_state"]:
                        missing_fields.append(fld)

        coverage_rows.append({
            **base,
            "required_condition_count": len(conditions),
            "feature_file_exists": bool(fpath),
            "schema_column_count": len(schema),
            "missing_fields_precheck": "|".join(sorted(set(missing_fields))),
            "unsupported_ops_precheck": "|".join(sorted(set([str(x) for x in unsupported_ops if x]))),
            "schema_columns": "|".join(schema),
        })

        if not fpath or not conditions:
            missing_rows.append({
                **base,
                "reason": "NO_FEATURE_FILE_OR_EMPTY_RULE",
                "missing_fields": "|".join(sorted(set(missing_fields))),
            })
            matched_events_by_memory[mid] = {}
            inventory_rows.append({
                **base,
                "rebuild_status": "NOT_REBUILT",
                "reason": "NO_FEATURE_FILE_OR_EMPTY_RULE",
                "discovery_count": 0,
                "validation_count": 0,
                "holdout_count_only": 0,
                "recommended_use": recommended_use(mem, {}),
            })
            continue

        counts = {}
        year_counts = {}
        first_fail_reasons = {}
        total_rows = 0
        matched_total = 0
        prev_session = ""
        event_sets = {}

        try:
            with fpath.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for raw in reader:
                    total_rows += 1
                    row = inject_derived_fields(raw, instrument, timeframe, prev_session)
                    prev_session = norm_text(row.get("session_bucket"))

                    ts, ts_col = timestamp_from_row(row)
                    d = extract_date_str(ts)
                    split = split_for_date(d)
                    year = year_for_date(d)

                    ok = True
                    fail_reason = ""
                    for cond in conditions:
                        cond_ok, reason = eval_condition(row, cond)
                        if not cond_ok:
                            ok = False
                            fail_reason = reason
                            break

                    if fail_reason and fail_reason not in first_fail_reasons:
                        first_fail_reasons[fail_reason] = total_rows

                    if ok:
                        matched_total += 1
                        eid = norm_text(row.get("event_id")) or norm_text(row.get("activation_id")) or ts or f"ROW_{total_rows}"
                        event_key = f"{instrument}|{timeframe}|{eid}"
                        event_sets.setdefault(split, set()).add(event_key)
                        counts[split] = counts.get(split, 0) + 1
                        year_counts[(split, year)] = year_counts.get((split, year), 0) + 1

                        if len(event_samples) < 5000:
                            event_samples.append({
                                "memory_id": mid,
                                "split": split,
                                "event_key": event_key,
                                "timestamp": ts,
                                "timestamp_column": ts_col,
                                "instrument": instrument,
                                "timeframe": timeframe,
                                "session_bucket": row.get("session_bucket", ""),
                                "d1_trend_state": row.get("d1_trend_state", row.get("d1_trend_safe", "")),
                                "h4_trend_state": row.get("h4_trend_state", row.get("h4_trend_safe", "")),
                            })

            matched_events_by_memory[mid] = event_sets

            for (split, year), cnt in sorted(year_counts.items()):
                match_rows.append({
                    "memory_id": mid,
                    "split": split,
                    "year": year,
                    "matched_rows": cnt,
                })

            inventory_rows.append({
                **base,
                "rebuild_status": "REBUILT_FROM_FEATURE_FILE",
                "total_rows_scanned": total_rows,
                "matched_total_all_splits": matched_total,
                "discovery_count": counts.get("DISCOVERY_2004_2014", 0),
                "validation_count": counts.get("VALIDATION_2015_2019", 0),
                "holdout_count_only": counts.get("HOLDOUT_2020_2024_COUNT_ONLY", 0),
                "pre_discovery_count": counts.get("PRE_DISCOVERY", 0),
                "post_holdout_or_other_count": counts.get("POST_HOLDOUT_OR_OTHER", 0),
                "unknown_date_count": counts.get("UNKNOWN_DATE", 0),
                "unique_discovery_events": len(event_sets.get("DISCOVERY_2004_2014", set())),
                "unique_validation_events": len(event_sets.get("VALIDATION_2015_2019", set())),
                "unique_holdout_events_count_only": len(event_sets.get("HOLDOUT_2020_2024_COUNT_ONLY", set())),
                "first_fail_reasons_seen": "|".join(list(first_fail_reasons.keys())[:20]),
                "recommended_use": recommended_use(mem, counts),
            })

        except Exception:
            errors.append(f"{mid}\n{traceback.format_exc()}")
            inventory_rows.append({
                **base,
                "rebuild_status": "ERROR",
                "reason": "SEE_ERRORS_FILE",
                "recommended_use": recommended_use(mem, {}),
            })

    # Overlap matrix for active memories, discovery + validation only
    overlap_rows = []
    active_ids = [m.get("memory_id") for m in memories if m.get("active_in_runtime")]
    for i, a in enumerate(active_ids):
        for b in active_ids[i+1:]:
            aset = set()
            bset = set()
            for split in ["DISCOVERY_2004_2014", "VALIDATION_2015_2019"]:
                aset |= matched_events_by_memory.get(a, {}).get(split, set())
                bset |= matched_events_by_memory.get(b, {}).get(split, set())
            if not aset and not bset:
                continue
            inter = aset & bset
            union = aset | bset
            overlap_rows.append({
                "memory_a": a,
                "memory_b": b,
                "count_a_discovery_validation": len(aset),
                "count_b_discovery_validation": len(bset),
                "overlap_count": len(inter),
                "jaccard": round(len(inter) / len(union), 6) if union else 0,
                "overlap_share_of_smaller": round(len(inter) / min(len(aset), len(bset)), 6) if min(len(aset), len(bset)) else 0,
            })

    write_csv(OUT / "MEM_AUDIT_01B_memory_occurrence_rebuild_table.csv", inventory_rows)
    write_csv(OUT / "MEM_AUDIT_01B_match_counts_by_year.csv", match_rows)
    write_csv(OUT / "MEM_AUDIT_01B_field_coverage.csv", coverage_rows)
    write_csv(OUT / "MEM_AUDIT_01B_active_memory_overlap_matrix.csv", overlap_rows)
    write_csv(OUT / "MEM_AUDIT_01B_matched_event_samples.csv", event_samples)
    write_csv(OUT / "MEM_AUDIT_01B_missing_or_unrebuildable_rules.csv", missing_rows)

    with (OUT / "MEM_AUDIT_01B_memory_occurrence_rebuild_table.json").open("w", encoding="utf-8") as f:
        json.dump(inventory_rows, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("# MEM-AUDIT-01B — Historical Occurrence Rebuild Report\n\n")
    lines.append(f"Generated UTC/local: {datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append(f"Repo root: `{REPO_ROOT}`\n\n")
    lines.append(f"Discovery root: `{DISCOVERY_ROOT}`\n\n")
    lines.append(f"Registry: `{REGISTRY_PATH}`\n\n")
    lines.append("## Boundary\n\n")
    lines.append("- This is occurrence/count rebuild only.\n")
    lines.append("- No discovery, no validation rerun, no signal, no entry/stop/target, no broker/execution.\n")
    lines.append("- Holdout is count-only where matched; no holdout outcome is evaluated.\n\n")

    lines.append("## Summary by memory\n\n")
    for r in inventory_rows:
        lines.append(f"### {r.get('memory_id')}\n\n")
        lines.append(f"- active_in_runtime: `{r.get('active_in_runtime')}`\n")
        lines.append(f"- status: `{r.get('activation_status')}`\n")
        lines.append(f"- rebuild_status: `{r.get('rebuild_status')}`\n")
        lines.append(f"- discovery_count: `{r.get('discovery_count')}`\n")
        lines.append(f"- validation_count: `{r.get('validation_count')}`\n")
        lines.append(f"- holdout_count_only: `{r.get('holdout_count_only')}`\n")
        lines.append(f"- registry_validation_rows: `{r.get('registry_validation_rows')}`\n")
        lines.append(f"- recommended_use: `{r.get('recommended_use')}`\n\n")

    if errors:
        (OUT / "MEM_AUDIT_01B_ERRORS.txt").write_text("\n\n".join(errors), encoding="utf-8")
        lines.append("\n## Errors\n\nSome memories had rebuild errors. See `MEM_AUDIT_01B_ERRORS.txt`.\n")

    (OUT / "MEM_AUDIT_01B_Final_Report.md").write_text("".join(lines), encoding="utf-8")

    zpath = REPO_ROOT / "outputs" / "MEM_AUDIT_01B_HISTORICAL_OCCURRENCE_PACK.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(OUT))

    print("MEM_AUDIT_01B_HISTORICAL_OCCURRENCE_DONE")
    print("Output folder:", OUT)
    print("Zip pack:", zpath)

if __name__ == "__main__":
    main()
