from __future__ import annotations

from pathlib import Path
import csv
import json
import os
import zipfile
import traceback
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path.cwd()
DISCOVERY_ROOT = Path(os.environ.get("SIG_DISCOVERY_ROOT", "")).resolve()
FEATURE_DIR = DISCOVERY_ROOT / "data" / "features"
REGISTRY_PATH = REPO_ROOT / "sig_brain" / "brain_memory_registry_v1_0.json"
OUT = REPO_ROOT / "outputs" / "_mem_audit_01d_derived_rebuild"
OUT.mkdir(parents=True, exist_ok=True)

DISCOVERY_START = "2004-01-01"
DISCOVERY_END = "2014-12-31"
VALIDATION_START = "2015-01-01"
VALIDATION_END = "2019-12-31"
HOLDOUT_START = "2020-01-01"
HOLDOUT_END = "2024-12-31"

FAILED_BREAKOUT_POLICY = "PRIOR_DAY_LOW_CLOSED_D1_v1_0"
TARGETED_LONDON_LOW_POLICY = "SIG_MTF_DIR_W16_TARGETED_EURUSD_H1_FAILED_BREAKOUT_SESSION_SWEEP_v1_0"
STRICT_LONDON_LOW_RECLAIM_POLICY = "SIG_MTF_DIR_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_D1UP_H4UP_H1_v1_0"

ACTIVE_ONLY = True

def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    keys: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def nstr(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, bool):
        return "true" if x else "false"
    return str(x).strip()

def parse_bool(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    s = nstr(x).lower()
    if s in ("true", "1", "yes", "y", "t"):
        return True
    if s in ("false", "0", "no", "n", "f", ""):
        return False
    return None

def fnum(x: Any) -> Optional[float]:
    try:
        s = nstr(x)
        if s == "":
            return None
        return float(s.replace(",", ""))
    except Exception:
        return None

def fnum_req(x: Any, default: float = 0.0) -> float:
    v = fnum(x)
    return default if v is None else v

def parse_ts(x: Any) -> Optional[datetime]:
    s = nstr(x)
    if not s:
        return None
    try:
        # Handles "YYYY-MM-DD HH:MM:SS", ISO, and Z suffix.
        s2 = s.replace("Z", "+00:00")
        if " " in s2 and "T" not in s2:
            s2 = s2.replace(" ", "T")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

def date_str_from_ts(ts: Optional[datetime]) -> str:
    return ts.date().isoformat() if ts else ""

def split_for_date(d: str) -> str:
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

def year_for_date(d: str) -> str:
    return d[:4] if d else "UNKNOWN"

def trend_safe(state: Any) -> str:
    s = nstr(state).upper()
    return s if s in ("UP", "DOWN") else "NEUTRAL"

def h1_bar_direction(row: Dict[str, Any]) -> str:
    o = fnum(row.get("open"))
    c = fnum(row.get("close"))
    if o is None or c is None:
        return "UNKNOWN"
    if c > o:
        return "BULLISH"
    if c < o:
        return "BEARISH"
    return "NEUTRAL"

def find_feature_file(instrument: str, timeframe: str) -> Optional[Path]:
    candidates = [
        FEATURE_DIR / f"{instrument}_{timeframe}_context.csv",
        FEATURE_DIR / f"{instrument}_{timeframe}.csv",
        FEATURE_DIR / f"{instrument}_{timeframe.lower()}_context.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    hits = sorted(FEATURE_DIR.glob(f"*{instrument}*{timeframe}*context*.csv"))
    return hits[0] if hits else None

def load_feature_rows(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or []
    rows.sort(key=lambda r: nstr(r.get("bar_open_ts_utc") or r.get("timestamp_utc") or r.get("timestamp") or ""))
    return rows, cols

def tr_value(row: Dict[str, Any], prev_close: Optional[float]) -> Optional[float]:
    high = fnum(row.get("high"))
    low = fnum(row.get("low"))
    close = fnum(row.get("close"))
    if high is None or low is None or close is None:
        return None
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))

def week_start_utc(ts: datetime) -> datetime:
    return (ts - timedelta(days=ts.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

def build_date_index(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        ts = parse_ts(r.get("bar_open_ts_utc"))
        d = date_str_from_ts(ts)
        if d:
            out.setdefault(d, []).append(r)
    return out

def london_morning_range_closed(rows_by_date: Dict[str, List[Dict[str, Any]]], eval_ts: datetime) -> Dict[str, Any]:
    d = eval_ts.date().isoformat()
    selected = []
    for r in rows_by_date.get(d, []):
        ts = parse_ts(r.get("bar_open_ts_utc"))
        if ts and ts.date() == eval_ts.date() and 7 <= ts.hour <= 11 and ts < eval_ts:
            selected.append(r)
    if not selected:
        return {"available": False, "low": None, "high": None, "bar_count": 0}
    return {
        "available": len(selected) >= 4,
        "low": min(fnum_req(r.get("low")) for r in selected),
        "high": max(fnum_req(r.get("high")) for r in selected),
        "bar_count": len(selected),
    }

def asian_range_closed(rows_by_date: Dict[str, List[Dict[str, Any]]], eval_ts: datetime) -> Dict[str, Any]:
    d = eval_ts.date().isoformat()
    selected = []
    for r in rows_by_date.get(d, []):
        ts = parse_ts(r.get("bar_open_ts_utc"))
        if ts and ts.date() == eval_ts.date() and 0 <= ts.hour <= 6 and ts < eval_ts:
            selected.append(r)
    if not selected:
        return {"available": False, "low": None, "high": None, "bar_count": 0}
    return {
        "available": len(selected) >= 4,
        "low": min(fnum_req(r.get("low")) for r in selected),
        "high": max(fnum_req(r.get("high")) for r in selected),
        "bar_count": len(selected),
    }

def current_week_first_bar(rows: List[Dict[str, Any]], idx: int, eval_ts: datetime) -> Optional[Dict[str, Any]]:
    ws = week_start_utc(eval_ts)
    # Search backward until before week start, then return earliest in the week among rows[:idx+1].
    j = idx
    earliest: Optional[Dict[str, Any]] = None
    while j >= 0:
        ts = parse_ts(rows[j].get("bar_open_ts_utc"))
        if not ts:
            j -= 1
            continue
        if ts < ws:
            break
        earliest = rows[j]
        j -= 1
    return earliest

def compare_eq(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        b = parse_bool(actual)
        return b is not None and b == expected
    if isinstance(expected, (int, float)):
        x = fnum(actual)
        return x is not None and x == float(expected)
    return nstr(actual).upper() == nstr(expected).upper()

def eval_condition(row: Dict[str, Any], cond: Dict[str, Any]) -> Tuple[bool, str]:
    op = cond.get("op")
    field = cond.get("field")
    if not field:
        return False, "UNSUPPORTED_NO_FIELD"
    if field not in row:
        return False, f"MISSING_FIELD:{field}"
    actual = row.get(field)
    expected = cond.get("value")
    if op in ("eq", "equals"):
        return compare_eq(actual, expected), ""
    if op == "not_eq":
        return (not compare_eq(actual, expected)), ""
    if op == "bool_eq":
        b = parse_bool(actual)
        if b is None:
            return False, f"BOOL_PARSE_FAIL:{field}"
        return b == bool(expected), ""
    if op == "in":
        vals = expected if isinstance(expected, list) else [expected]
        return any(compare_eq(actual, v) for v in vals), ""
    if op == "gt":
        x = fnum(actual)
        return (x is not None and x > float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "gte":
        x = fnum(actual)
        return (x is not None and x >= float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "lt":
        x = fnum(actual)
        return (x is not None and x < float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    if op == "lte":
        x = fnum(actual)
        return (x is not None and x <= float(expected)), "" if x is not None else f"NUMERIC_PARSE_FAIL:{field}"
    return False, f"UNSUPPORTED_OP:{op}"

def registry_ev(mem: Dict[str, Any]) -> Dict[str, Any]:
    ev = mem.get("evidence_summary", {}) or {}
    return {
        "registry_discovery_rows": ev.get("discovery_rows", ""),
        "registry_validation_rows": ev.get("validation_rows", ev.get("candidate_rows_min", "")),
        "registry_avg_delta": ev.get("avg_delta", ev.get("validation_avg_delta", ev.get("validation_avg_delta_vs_baseline1", ev.get("validation_avg_gross_delta", "")))),
        "registry_discovery_avg_delta": ev.get("discovery_avg_delta", ev.get("discovery_avg_delta_vs_baseline1", "")),
        "registry_positive_horizons": ev.get("positive_horizons", ev.get("positive_horizon_share", ev.get("validation_positive_horizons", ""))),
        "registry_tau": ev.get("tau", ev.get("effect_retention_tau", ev.get("effect_retention_tau_vs_discovery_b1", ""))),
        "registry_max_year_share": ev.get("max_year_share", ev.get("validation_max_year_share", "")),
        "registry_holdout_touched": ev.get("holdout_2020_2024_touched", ev.get("holdout_touched", "")),
    }

def recommended_use(mem: Dict[str, Any], validation_count: int) -> str:
    active = bool(mem.get("active_in_runtime"))
    status = nstr(mem.get("activation_status")).upper()
    cls = nstr(mem.get("memory_class")).upper()
    ev = mem.get("evidence_summary", {}) or {}

    def to_float(v: Any) -> Optional[float]:
        try:
            if v is None or v == "":
                return None
            return float(v)
        except Exception:
            return None

    val_delta = to_float(ev.get("avg_delta", ev.get("validation_avg_delta", ev.get("validation_avg_delta_vs_baseline1", ""))))
    disc_delta = to_float(ev.get("discovery_avg_delta", ev.get("discovery_avg_delta_vs_baseline1", "")))
    max_year = to_float(ev.get("max_year_share", ev.get("validation_max_year_share", "")))

    if "REJECT" in status or "FAIL" in status:
        return "REJECT_OR_ARCHIVE_NO_RUNTIME_USE"
    if not active:
        if "OBSERVATION" in status or "PARK" in status:
            return "EXTENDED_OBSERVATION_ONLY"
        return "ARCHIVE_NO_RUNTIME_USE"
    if "NO_TRADE" in cls or "AVOID" in cls:
        return "BLOCKER_ONLY"
    if disc_delta is not None and disc_delta <= 0 and val_delta is not None and val_delta > 0:
        return "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW"
    if validation_count >= 50 and (val_delta is None or val_delta > 0):
        return "CORE_SETUP_TRIGGER_PILOT_CAVEATED"
    if validation_count >= 30:
        return "EXTENDED_OBSERVATION_ONLY"
    return "DISPLAY_CONTEXT_OR_EXTENDED_OBSERVATION_ONLY"

def sample_grade(validation_count: int, max_year_share: Optional[float], active: bool) -> str:
    if validation_count >= 100 and (max_year_share is None or max_year_share <= 0.35):
        return "STRONG"
    if validation_count >= 50 and (max_year_share is None or max_year_share <= 0.40):
        return "ADEQUATE"
    if validation_count >= 30:
        return "CAVEATED"
    if validation_count == 0 and active:
        return "UNREBUILT_OR_ZERO_MATCH"
    return "WEAK"

def max_year_share_from_counts(year_counts: Dict[str, int]) -> Optional[float]:
    total = sum(year_counts.values())
    if total <= 0:
        return None
    return max(year_counts.values()) / total

def derive_rows_for_instrument(instrument: str, path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows, cols = load_feature_rows(path)
    rows_by_date = build_date_index(rows)

    trs: List[Optional[float]] = []
    prev_close: Optional[float] = None
    for r in rows:
        tr = tr_value(r, prev_close)
        trs.append(tr)
        c = fnum(r.get("close"))
        if c is not None:
            prev_close = c

    derived: List[Dict[str, Any]] = []
    prev_session = "UNKNOWN"

    for idx, raw in enumerate(rows):
        row = dict(raw)
        ts = parse_ts(row.get("bar_open_ts_utc"))
        sess = nstr(row.get("session_bucket"))
        d1_state = nstr(row.get("d1_trend_state")).upper()
        h4_state = nstr(row.get("h4_trend_state")).upper()

        # Core aliases expected by registry.
        row["instrument"] = instrument
        row["timeframe"] = "H1"
        row["base_timeframe"] = "H1"
        row["latest_bar_open_ts_utc"] = row.get("bar_open_ts_utc", "")
        row["latest_h1_bar_open_ts_utc"] = row.get("bar_open_ts_utc", "")
        row["d1_trend_safe"] = trend_safe(d1_state)
        row["h4_trend_safe"] = trend_safe(h4_state)
        row["d1_atr20_safe"] = row.get("d1_atr20", "")
        row["h1_open"] = row.get("open", "")
        row["h1_high"] = row.get("high", "")
        row["h1_low"] = row.get("low", "")
        row["h1_close"] = row.get("close", "")

        # Prior session and session-open logic.
        row["prior_h1_session"] = prev_session
        first_overlap = bool(sess == "LONDON_NY_OVERLAP" and prev_session != "LONDON_NY_OVERLAP")
        row["is_first_h1_bar_of_session"] = first_overlap
        direction = h1_bar_direction(row)
        row["h1_bar_direction"] = direction
        session_open_state = "NONE"
        if first_overlap and direction == "BULLISH" and row["d1_trend_safe"] == "UP":
            session_open_state = "SESSION_OPEN_TREND_LONG"
        elif first_overlap and direction == "BEARISH" and row["d1_trend_safe"] == "DOWN":
            session_open_state = "SESSION_OPEN_TREND_SHORT"
        row["session_open_trend_trigger_state"] = session_open_state

        # H1 ATR20 prior, excluding current bar.
        prior_trs = [x for x in trs[max(0, idx-20):idx] if x is not None]
        h1_atr20 = sum(prior_trs) / len(prior_trs) if len(prior_trs) >= 20 else None
        row["h1_atr20"] = h1_atr20 if h1_atr20 is not None else ""

        if ts:
            low = fnum_req(row.get("low"))
            high = fnum_req(row.get("high"))
            close = fnum_req(row.get("close"))
            tol = abs(close) * 0.00003

            # Failed breakout: prior-day low reclaim.
            pdl = fnum(row.get("prior_day_low"))
            if pdl is None:
                row["failed_breakout_event_type"] = "UNKNOWN"
                row["failed_breakout_level_type"] = "UNKNOWN"
                row["failed_breakout_reference_policy_id"] = FAILED_BREAKOUT_POLICY
            else:
                fb_event = bool(low < pdl - tol and close >= pdl)
                row["failed_breakout_event_type"] = "FAILED_DOWNSIDE_BREAKOUT_RECLAIM_INSIDE" if fb_event else "NONE"
                row["failed_breakout_level_type"] = "PRIOR_DAY_LOW" if fb_event else "NONE"
                row["failed_breakout_reference_policy_id"] = FAILED_BREAKOUT_POLICY
                row["failed_breakout_reference_value"] = pdl

            # London morning low / range helpers.
            london = london_morning_range_closed(rows_by_date, ts)
            row["same_utc_date_london_range_available"] = bool(london["available"])
            row["london_session_low"] = london["low"] if london["low"] is not None else ""
            row["london_session_high"] = london["high"] if london["high"] is not None else ""
            row["london_session_bar_count"] = london["bar_count"]
            if london["available"] and london["low"] is not None and h1_atr20 is not None:
                row["london_low_swept_and_reclaimed_by_closed_h1"] = bool(low <= london["low"] - 0.10 * h1_atr20 and close > london["low"])
            else:
                row["london_low_swept_and_reclaimed_by_closed_h1"] = ""

            # Preserve/raise H1 quality tier to HIGH when enough H1+ATR exists.
            row["h1_quality_tier"] = "HIGH" if idx >= 24 and h1_atr20 is not None else nstr(row.get("h1_quality_tier") or "LIMITED")

            # Targeted London morning low failed downside.
            base_state = "UNKNOWN"
            fail_side = "UNKNOWN"
            dir_side = "UNKNOWN"
            target_level = "UNKNOWN"
            if london["low"] is None:
                base_state = "UNKNOWN"
            else:
                target_event = bool(low < london["low"] - tol and close >= london["low"])
                if target_event:
                    base_state = "LONDON_MORNING_LOW_FAILED_DOWNSIDE_RECLAIM_INSIDE"
                    target_level = "LONDON_MORNING_LOW"
                    fail_side = "FAILED_DOWNSIDE"
                    dir_side = "LONG"
                else:
                    base_state = "NONE"
                    target_level = "NONE"
                    fail_side = "NONE"
                    dir_side = "NONE"
            row["h1_failed_breakout_or_session_sweep_state"] = base_state
            # If prior-day failed breakout already set the level to PRIOR_DAY_LOW and targeted event is not true,
            # do not overwrite for the prior-day memory. Registry conditions will choose the correct one.
            row["targeted_failed_breakout_level_type"] = target_level
            row["failed_breakout_failure_side"] = fail_side
            row["directional_side"] = dir_side
            row["policy_id"] = TARGETED_LONDON_LOW_POLICY
            if base_state == "LONDON_MORNING_LOW_FAILED_DOWNSIDE_RECLAIM_INSIDE":
                row["failed_breakout_level_type"] = "LONDON_MORNING_LOW"

            # Asian range.
            asian = asian_range_closed(rows_by_date, ts)
            row["same_utc_date_asian_range_available"] = bool(asian["available"])
            row["asian_session_high"] = asian["high"] if asian["high"] is not None else ""
            row["asian_session_low"] = asian["low"] if asian["low"] is not None else ""
            row["asian_session_bar_count"] = asian["bar_count"]
            d1_atr = fnum(row.get("d1_atr20"))
            if asian["available"] and asian["high"] is not None and d1_atr is not None:
                threshold = 0.05 * d1_atr
                row["asian_high_swept_and_reclaimed_by_closed_h1"] = bool(high >= asian["high"] + threshold and close < asian["high"])
                row["asian_high_breakout_continuation_by_closed_h1"] = bool(close > asian["high"] + threshold)
            else:
                row["asian_high_swept_and_reclaimed_by_closed_h1"] = ""
                row["asian_high_breakout_continuation_by_closed_h1"] = ""

            # Weekly open.
            wk_first = current_week_first_bar(rows, idx, ts)
            wk_open = fnum(row.get("weekly_open"))
            if wk_open is None and wk_first is not None:
                wk_open = fnum(wk_first.get("open"))
            is_wk_open = False
            wk_ts = ""
            if wk_first is not None:
                wk_first_ts = parse_ts(wk_first.get("bar_open_ts_utc"))
                is_wk_open = bool(wk_first_ts == ts)
                wk_ts = wk_first.get("bar_open_ts_utc", "")
            row["weekly_open"] = wk_open if wk_open is not None else ""
            row["weekly_open_ts"] = row.get("weekly_open_ts") or wk_ts
            row["is_weekly_open_bar"] = is_wk_open
            if wk_open is not None and d1_atr is not None:
                threshold = 0.05 * d1_atr
                if (not is_wk_open) and high >= wk_open + threshold and close < wk_open:
                    row["weekly_open_reclaim_short_state"] = "WEEKLY_OPEN_RECLAIM_SHORT"
                else:
                    row["weekly_open_reclaim_short_state"] = "NONE"
            else:
                row["weekly_open_reclaim_short_state"] = "UNKNOWN"

        derived.append(row)
        prev_session = sess if sess else prev_session

    return derived, cols

def main() -> None:
    errors: List[str] = []
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Missing registry: {REGISTRY_PATH}")
    if not FEATURE_DIR.exists():
        raise FileNotFoundError(f"Missing feature dir: {FEATURE_DIR}")

    registry = read_json(REGISTRY_PATH)
    memories = registry.get("memories", [])
    if ACTIVE_ONLY:
        memories = [m for m in memories if m.get("active_in_runtime") is True]

    instruments = sorted(set(nstr(m.get("instrument")).upper() for m in memories if nstr(m.get("timeframe")).upper() == "H1"))
    derived_by_instrument: Dict[str, List[Dict[str, Any]]] = {}
    feature_sources: Dict[str, str] = {}
    feature_cols: Dict[str, List[str]] = {}

    for inst in instruments:
        path = find_feature_file(inst, "H1")
        if not path:
            errors.append(f"No H1 feature file found for {inst}")
            continue
        rows, cols = derive_rows_for_instrument(inst, path)
        derived_by_instrument[inst] = rows
        feature_sources[inst] = str(path)
        feature_cols[inst] = cols

        # Write augmented per-instrument sample/schema, but not the full huge context unless user needs it.
        if rows:
            sample_path = OUT / f"MEM_AUDIT_01D_augmented_{inst}_H1_sample.csv"
            write_csv(sample_path, rows[:200])

    inventory_rows: List[Dict[str, Any]] = []
    by_year_rows: List[Dict[str, Any]] = []
    event_samples: List[Dict[str, Any]] = []
    field_coverage_rows: List[Dict[str, Any]] = []
    matched_events_by_memory: Dict[str, Dict[str, set]] = {}

    for mem in memories:
        mid = nstr(mem.get("memory_id"))
        inst = nstr(mem.get("instrument")).upper()
        tf = nstr(mem.get("timeframe")).upper()
        rule = mem.get("matching_rule", {}) or {}
        conditions = rule.get("required_all", []) or []

        base = {
            "memory_id": mid,
            "active_in_runtime": mem.get("active_in_runtime"),
            "activation_status": mem.get("activation_status"),
            "memory_class": mem.get("memory_class"),
            "instrument": inst,
            "timeframe": tf,
            "feature_file": feature_sources.get(inst, ""),
        }
        base.update(registry_ev(mem))

        rows = derived_by_instrument.get(inst, [])
        if tf != "H1" or not rows:
            inventory_rows.append({
                **base,
                "rebuild_status": "NOT_REBUILT",
                "reason": "NO_DERIVED_H1_ROWS_OR_NON_H1",
                "discovery_count": 0,
                "validation_count": 0,
                "holdout_count_only": 0,
                "recommended_use": recommended_use(mem, 0),
            })
            continue

        # Field coverage after derived context.
        available_fields = set(rows[0].keys()) if rows else set()
        required_fields = [c.get("field") for c in conditions if c.get("field")]
        missing_after = [f for f in required_fields if f not in available_fields]
        unsupported_ops = [c.get("op") for c in conditions if c.get("op") not in ("eq","equals","not_eq","bool_eq","in","gt","gte","lt","lte")]

        field_coverage_rows.append({
            **base,
            "required_condition_count": len(conditions),
            "missing_fields_after_derived": "|".join(sorted(set(missing_after))),
            "unsupported_ops_after_derived": "|".join(sorted(set([nstr(x) for x in unsupported_ops if x]))),
            "available_field_count": len(available_fields),
            "original_feature_columns": "|".join(feature_cols.get(inst, [])),
        })

        split_counts: Dict[str, int] = {}
        split_events: Dict[str, set] = {}
        split_year_counts: Dict[Tuple[str, str], int] = {}
        first_fail_reasons: Dict[str, int] = {}
        total_scanned = 0
        matched_total = 0

        for idx, row in enumerate(rows, 1):
            total_scanned += 1
            ts = parse_ts(row.get("bar_open_ts_utc"))
            d = date_str_from_ts(ts)
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
                first_fail_reasons[fail_reason] = idx
            if not ok:
                continue

            matched_total += 1
            eid = nstr(row.get("event_id")) or nstr(row.get("activation_id")) or nstr(row.get("bar_open_ts_utc")) or f"ROW_{idx}"
            event_key = f"{inst}|H1|{eid}"
            split_counts[split] = split_counts.get(split, 0) + 1
            split_events.setdefault(split, set()).add(event_key)
            split_year_counts[(split, year)] = split_year_counts.get((split, year), 0) + 1

            if len(event_samples) < 10000:
                event_samples.append({
                    "memory_id": mid,
                    "split": split,
                    "event_key": event_key,
                    "bar_open_ts_utc": row.get("bar_open_ts_utc", ""),
                    "instrument": inst,
                    "timeframe": "H1",
                    "session_bucket": row.get("session_bucket", ""),
                    "d1_trend_state": row.get("d1_trend_state", ""),
                    "h4_trend_state": row.get("h4_trend_state", ""),
                    "d1_trend_safe": row.get("d1_trend_safe", ""),
                    "h4_trend_safe": row.get("h4_trend_safe", ""),
                    "h1_bar_direction": row.get("h1_bar_direction", ""),
                    "session_open_trend_trigger_state": row.get("session_open_trend_trigger_state", ""),
                    "failed_breakout_event_type": row.get("failed_breakout_event_type", ""),
                    "h1_failed_breakout_or_session_sweep_state": row.get("h1_failed_breakout_or_session_sweep_state", ""),
                    "london_low_swept_and_reclaimed_by_closed_h1": row.get("london_low_swept_and_reclaimed_by_closed_h1", ""),
                    "asian_high_swept_and_reclaimed_by_closed_h1": row.get("asian_high_swept_and_reclaimed_by_closed_h1", ""),
                    "weekly_open_reclaim_short_state": row.get("weekly_open_reclaim_short_state", ""),
                })

        matched_events_by_memory[mid] = split_events

        for (split, year), cnt in sorted(split_year_counts.items()):
            by_year_rows.append({
                "memory_id": mid,
                "split": split,
                "year": year,
                "matched_event_count": cnt,
            })

        val_year_counts = {year: cnt for (split, year), cnt in split_year_counts.items() if split == "VALIDATION_2015_2019"}
        max_year_share_val = max_year_share_from_counts(val_year_counts)
        validation_count = len(split_events.get("VALIDATION_2015_2019", set()))
        discovery_count = len(split_events.get("DISCOVERY_2004_2014", set()))
        holdout_count = len(split_events.get("HOLDOUT_2020_2024_COUNT_ONLY", set()))

        reg_validation = base.get("registry_validation_rows", "")
        reg_discovery = base.get("registry_discovery_rows", "")
        try:
            reg_validation_num = int(float(reg_validation)) if nstr(reg_validation) != "" else None
        except Exception:
            reg_validation_num = None
        try:
            reg_discovery_num = int(float(reg_discovery)) if nstr(reg_discovery) != "" else None
        except Exception:
            reg_discovery_num = None

        inventory_rows.append({
            **base,
            "rebuild_status": "REBUILT_WITH_DERIVED_H1_CONTEXT",
            "total_rows_scanned": total_scanned,
            "matched_total_all_splits": matched_total,
            "discovery_count": discovery_count,
            "validation_count": validation_count,
            "holdout_count_only": holdout_count,
            "pre_discovery_count": len(split_events.get("PRE_DISCOVERY", set())),
            "post_holdout_or_other_count": len(split_events.get("POST_HOLDOUT_OR_OTHER", set())),
            "unknown_date_count": len(split_events.get("UNKNOWN_DATE", set())),
            "validation_rebuild_minus_registry": "" if reg_validation_num is None else validation_count - reg_validation_num,
            "discovery_rebuild_minus_registry": "" if reg_discovery_num is None else discovery_count - reg_discovery_num,
            "validation_max_year_share_rebuilt": "" if max_year_share_val is None else round(max_year_share_val, 6),
            "sample_grade_rebuilt": sample_grade(validation_count, max_year_share_val, bool(mem.get("active_in_runtime"))),
            "first_fail_reasons_seen": "|".join(list(first_fail_reasons.keys())[:30]),
            "recommended_use": recommended_use(mem, validation_count),
            "holdout_boundary_note": "COUNT_ONLY_NO_OUTCOME_EVALUATION",
        })

    overlap_rows: List[Dict[str, Any]] = []
    active_ids = [r["memory_id"] for r in inventory_rows if r.get("active_in_runtime") is True]
    for i, a in enumerate(active_ids):
        for b in active_ids[i+1:]:
            aset = set()
            bset = set()
            for split in ("DISCOVERY_2004_2014", "VALIDATION_2015_2019"):
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

    write_csv(OUT / "MEM_AUDIT_01D_active_memory_occurrence_rebuild_table.csv", inventory_rows)
    write_csv(OUT / "MEM_AUDIT_01D_match_counts_by_year.csv", by_year_rows)
    write_csv(OUT / "MEM_AUDIT_01D_field_coverage_after_derived.csv", field_coverage_rows)
    write_csv(OUT / "MEM_AUDIT_01D_active_memory_overlap_matrix.csv", overlap_rows)
    write_csv(OUT / "MEM_AUDIT_01D_matched_event_samples.csv", event_samples)

    with (OUT / "MEM_AUDIT_01D_active_memory_occurrence_rebuild_table.json").open("w", encoding="utf-8") as f:
        json.dump(inventory_rows, f, ensure_ascii=False, indent=2)

    lines: List[str] = []
    lines.append("# MEM-AUDIT-01D — Historical Derived Context Rebuild\n\n")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append(f"Repo root: `{REPO_ROOT}`\n\n")
    lines.append(f"Discovery root: `{DISCOVERY_ROOT}`\n\n")
    lines.append("## Boundary\n\n")
    lines.append("- Occurrence/count rebuild only.\n")
    lines.append("- No discovery, no validation rerun, no signal, no entry/stop/target, no broker/execution.\n")
    lines.append("- Holdout is count-only; no holdout outcome is evaluated.\n\n")
    lines.append("## Active memory occurrence counts\n\n")
    lines.append("| Memory | Discovery | Validation | Holdout count-only | Registry validation | Recommended use |\n")
    lines.append("|---|---:|---:|---:|---:|---|\n")
    for r in inventory_rows:
        lines.append(
            f"| `{r.get('memory_id')}` | {r.get('discovery_count')} | {r.get('validation_count')} | "
            f"{r.get('holdout_count_only')} | {r.get('registry_validation_rows')} | `{r.get('recommended_use')}` |\n"
        )
    lines.append("\n## Caveats\n\n")
    lines.append("- If rebuilt counts differ materially from registry evidence rows, treat the difference as a mapping issue to review, not as automatic invalidation.\n")
    lines.append("- The two split-stability-caveated memories with negative/flat discovery delta should remain extended-observation unless PMO explicitly approves core inclusion.\n")
    if errors:
        lines.append("\n## Errors\n\n")
        lines.append("See `MEM_AUDIT_01D_ERRORS.txt`.\n")
        (OUT / "MEM_AUDIT_01D_ERRORS.txt").write_text("\n\n".join(errors), encoding="utf-8")

    (OUT / "MEM_AUDIT_01D_Final_Report.md").write_text("".join(lines), encoding="utf-8")

    zpath = REPO_ROOT / "outputs" / "MEM_AUDIT_01D_DERIVED_HISTORICAL_OCCURRENCE_PACK.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(OUT))

    print("MEM_AUDIT_01D_DERIVED_HISTORICAL_OCCURRENCE_DONE")
    print("Output folder:", OUT)
    print("Zip pack:", zpath)

if __name__ == "__main__":
    main()
