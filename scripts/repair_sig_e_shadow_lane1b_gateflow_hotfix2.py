
import csv
import gzip
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROGRAM = "SIG-E-SHADOW-LANE1B-GATEFLOW-HOTFIX2"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_gateflow_hotfix2/sig_e_shadow_lane1b_gateflow_hotfix2_result.json")

SOURCE_SPEC_ID = "SIG_E_RUNTIME_SPEC_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"
DETECTOR_ID = "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"

AUTH_FALSE_KEYS = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
    "primary_lane_authorized",
    "lane_rule_change_authorized",
]

BOUNDARY = [
    "GATEFLOW_REPAIR_ONLY",
    "DIAGNOSTIC_ONLY_LANE",
    "OVERLAP_VARIANT_RESEARCH_ONLY",
    "DOES_NOT_CHANGE_LANE1",
    "SHADOW_RESEARCH_ONLY",
    "NOT_SIGNAL",
    "NO_TRADE_PROPOSAL",
    "NO_ENTRY_STOP_TARGET",
    "NO_RISK_OR_POSITION_SIZING",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_EXECUTION",
    "NO_MEMORY_PROMOTION",
    "NO_RULE_REWRITE",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def parse_dt(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def iso(x):
    if x is None:
        return None
    return x.replace(microsecond=0).isoformat() + "Z"

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def first(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None

def as_bool(value):
    if value is True:
        return True
    if value is False:
        return False
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "y", "pass", "passed", "ok"):
        return True
    if s in ("false", "0", "no", "n", "fail", "failed"):
        return False
    return None

def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for x in walk_dicts(v):
                yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in walk_dicts(v):
                yield x

def regime_check_obj(obj):
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
            return chk
    return None

def regime_details(obj):
    chk = regime_check_obj(obj)
    if chk and isinstance(chk.get("details"), dict):
        return chk.get("details") or {}
    for d in walk_dicts(obj):
        if isinstance(d, dict) and ("session_ok" in d or "alignment_ok" in d or "vol_ok" in d):
            return d
    return {}

def regime_passed(obj):
    chk = regime_check_obj(obj)
    if isinstance(chk, dict) and chk.get("passed") is True:
        return True
    d = regime_details(obj)
    return as_bool(d.get("session_ok")) is True and as_bool(d.get("alignment_ok")) is True and as_bool(d.get("vol_ok")) is True

def ensure_authority(obj):
    obj.setdefault("authority", {})
    for key in AUTH_FALSE_KEYS:
        obj["authority"][key] = False
    obj["is_signal"] = False
    obj["is_trade_proposal"] = False
    obj["source_spec_id"] = obj.get("source_spec_id") or SOURCE_SPEC_ID
    obj["detector_id"] = obj.get("detector_id") or DETECTOR_ID
    obj.setdefault("classification", "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY")
    obj["boundary"] = list(dict.fromkeys(list(obj.get("boundary") or []) + BOUNDARY))
    obj["not_authorized"] = [
        "signal",
        "manual trade proposal",
        "entry/stop/target",
        "risk sizing",
        "broker/execution",
        "auto execution",
        "primary lane promotion",
        "Lane1 rule change",
    ]
    return obj

def forbidden_path(path):
    s = str(path or "").replace("\\", "/").lower()
    return any(x in s for x in [
        "data/canonical/",
        "data/raw/",
        "data/features/",
        "holdout_2020_2024",
        "validation_2015_2019",
        "discovery_2004_2014",
        "future_after_2024",
    ])

def live_allowed(path):
    if not path or forbidden_path(path):
        return False
    s = str(path).replace("\\", "/").lower()
    return "live" in s or s.startswith("runtime/") or s.startswith("panel/") or s.startswith("inputs/") or s.startswith("data/")

def resolve_path(path):
    if not path:
        return None
    p = Path(str(path).replace("/", os.sep))
    if p.exists() and live_allowed(str(p)):
        return p
    return None

def detect_delimiter(line):
    if not line:
        return ","
    return max([",", ";", "\t", "|"], key=lambda c: line.count(c))

def pick_col(cols, names):
    low = {c.lower().replace(" ", "_"): c for c in cols}
    for n in names:
        k = n.lower().replace(" ", "_")
        if k in low:
            return low[k]
    for c in cols:
        for n in names:
            if n.lower() in c.lower() or c.lower() in n.lower():
                return c
    return None

def to_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None

def read_csv_rows(path, max_tail=12000):
    p = Path(path) if path else None
    if not p or not p.exists():
        return []
    try:
        if str(p).lower().endswith(".gz"):
            opener = lambda: gzip.open(p, "rt", encoding="utf-8", errors="replace", newline="")
        else:
            opener = lambda: open(p, "r", encoding="utf-8", errors="replace", newline="")
        with opener() as f:
            first_line = f.readline()
            delim = detect_delimiter(first_line)
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delim)
            rows = []
            for r in reader:
                if isinstance(r, dict) and any(v not in (None, "") for v in r.values()):
                    rows.append(r)
                if len(rows) > max_tail:
                    rows = rows[-max_tail:]
            return rows
    except Exception:
        return []

def standardize_ohlc(rows):
    if not rows:
        return []
    cols = list(rows[0].keys())
    tc = pick_col(cols, ["bar_open_ts_utc", "timestamp", "datetime", "time", "date"])
    oc = pick_col(cols, ["open", "o"])
    hc = pick_col(cols, ["high", "h"])
    lc = pick_col(cols, ["low", "l"])
    cc = pick_col(cols, ["close", "c"])
    out = []
    for r in rows:
        t = parse_dt(r.get(tc)) if tc else None
        o = to_float(r.get(oc)) if oc else None
        h = to_float(r.get(hc)) if hc else None
        l = to_float(r.get(lc)) if lc else None
        c = to_float(r.get(cc)) if cc else None
        if t and None not in (o, h, l, c) and h >= l:
            out.append({"ts": t, "open": o, "high": h, "low": l, "close": c})
    out.sort(key=lambda x: x["ts"])
    return out

def report_paths(instrument, timeframe):
    found = []
    files = [
        "panel/brain4/sig_live_refresh_status_latest.json",
        "runtime/sig_brain/sig_live_refresh_status_latest.json",
        "data/live_m5/reports/resampled_from_m5_summary.json",
        "data/live_m5/reports/resample_report.json",
        "outputs/live_m5/resampled_from_m5_summary.json",
        "runtime/sig_e/market_state_current.json",
        "panel/brain4/sig_e_market_state_current.json",
    ]
    for f in files:
        payload = load_json(f)
        if not isinstance(payload, dict):
            continue
        rows = []
        rd = payload.get("resampled_data")
        if isinstance(rd, dict) and isinstance(rd.get("rows"), list):
            rows += rd["rows"]
        if isinstance(payload.get("rows"), list):
            rows += payload["rows"]
        if isinstance(payload.get("files"), list):
            rows += payload["files"]
        for r in rows:
            if not isinstance(r, dict):
                continue
            inst = str(first(r.get("instrument"), r.get("symbol"), "")).upper()
            tfv = str(first(r.get("timeframe"), r.get("tf"), "")).upper()
            p = first(r.get("path"), r.get("file"), r.get("filepath"), r.get("output_path"))
            if inst == instrument and tfv == timeframe:
                rp = resolve_path(p)
                if rp:
                    found.append(("refresh_report", rp))
    return found

def glob_candidate_paths(instrument, timeframe):
    patterns = [
        "data/live*/**/*%s*%s*.csv" % (instrument, timeframe),
        "data/live*/**/*%s*%s*.csv.gz" % (instrument, timeframe),
        "data/**/live*/**/*%s*%s*.csv" % (instrument, timeframe),
        "data/**/live*/**/*%s*%s*.csv.gz" % (instrument, timeframe),
        "runtime/**/*%s*%s*.csv" % (instrument, timeframe),
        "runtime/**/*%s*%s*.csv.gz" % (instrument, timeframe),
    ]
    out = []
    seen = set()
    for pat in patterns:
        for p in Path(".").glob(pat):
            sp = str(p).replace("\\", "/")
            if p.is_file() and sp not in seen and live_allowed(sp):
                seen.add(sp)
                out.append(("glob_live", p))
    return out

def candidate_diagnostics(instrument, timeframe):
    raw = report_paths(instrument, timeframe) + glob_candidate_paths(instrument, timeframe)
    diagnostics = []
    best = None
    seen = set()

    for source, path in raw:
        sp = str(path).replace("\\", "/")
        if sp in seen:
            continue
        seen.add(sp)
        rows = standardize_ohlc(read_csv_rows(path))
        latest = rows[-1]["ts"] if rows else None
        score = len(rows)
        if latest:
            score += 1000000
        low = sp.lower()
        if "resampled" in low or "live_m5" in low or low.endswith(".gz"):
            score += 5000
        if "current" in low or "latest" in low:
            score -= 250
        item = {
            "source": source,
            "path": sp,
            "rows": len(rows),
            "latest_bar_open_ts_utc": iso(latest),
            "score": score,
            "forbidden": forbidden_path(sp),
        }
        diagnostics.append(item)
        if rows and not item["forbidden"] and (best is None or score > best["score"]):
            best = {"path": path, "rows": rows, "diagnostic": item, "score": score}

    diagnostics.sort(key=lambda x: (x.get("score") or 0, x.get("rows") or 0), reverse=True)
    return best, diagnostics[:20]

def row_range(row):
    return row["high"] - row["low"]

def median(values):
    if not values:
        return None
    vals = sorted(values)
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0

def lower_rejection_expansion_setup(rows, idx):
    row = rows[idx]
    rng = row_range(row)
    if rng <= 0:
        return False, {"reason": "zero_range"}
    lookback = rows[max(0, idx - 12):idx]
    prior_ranges = [row_range(r) for r in lookback if row_range(r) > 0]
    med = median(prior_ranges)
    if med is None or med <= 0:
        return False, {"reason": "insufficient_prior_ranges"}
    lower_wick = min(row["open"], row["close"]) - row["low"]
    lower_wick_to_range = lower_wick / rng
    expansion_ratio = rng / med
    close_location = (row["close"] - row["low"]) / rng
    bullish_close = row["close"] > row["open"]
    ok = lower_wick_to_range >= 0.30 and expansion_ratio >= 1.15 and close_location >= 0.50
    return ok, {
        "setup_h1_open_ts_utc": iso(row["ts"]),
        "open": row["open"],
        "high": row["high"],
        "low": row["low"],
        "close": row["close"],
        "range": rng,
        "prior_12_range_median": med,
        "range_expansion_ratio": expansion_ratio,
        "lower_wick": lower_wick,
        "lower_wick_to_range": lower_wick_to_range,
        "close_location": close_location,
        "bullish_close": bullish_close,
        "requirements": {
            "lower_wick_to_range_min": 0.30,
            "range_expansion_ratio_min": 1.15,
            "close_location_min": 0.50,
        },
    }

def m15_confirm(m15_rows, h1_start):
    end = h1_start + timedelta(hours=1)
    inside = [r for r in m15_rows if h1_start <= r["ts"] < end]
    confirms = [r for r in inside if r["close"] > r["open"]]
    return bool(confirms), {
        "h1_window_start": iso(h1_start),
        "h1_window_end": iso(end),
        "m15_inside_count": len(inside),
        "m15_confirm_count": len(confirms),
        "first_confirm_m15_open_ts_utc": iso(confirms[0]["ts"]) if confirms else None,
    }

def set_status(obj, status, reason):
    obj["detector_status"] = status
    obj["status_reason"] = reason
    return obj

def append_or_replace_check(obj, check_id, passed, details):
    checks = obj.setdefault("checks", [])
    for chk in checks:
        if isinstance(chk, dict) and chk.get("check_id") == check_id:
            chk["passed"] = passed
            chk["details"] = details
            return
    checks.append({"check_id": check_id, "passed": passed, "details": details})

def repair_gateflow(obj):
    obj = ensure_authority(obj)
    obj["gateflow_hotfix2_checked_utc"] = now()

    if not regime_passed(obj):
        d = regime_details(obj)
        session_ok = as_bool(d.get("session_ok"))
        alignment_ok = as_bool(d.get("alignment_ok"))
        vol_ok = as_bool(d.get("vol_ok"))
        if session_ok is True and (alignment_ok is False or vol_ok is False):
            set_status(obj, "REGIME_NOT_MATCHED", "overlap_long_diagnostic_regime_not_matched")
        obj["gateflow_hotfix2_action"] = "NO_GATEFLOW_REPAIR_REGIME_NOT_PASSED"
        return obj

    # If regime is passed, earlier terminal statuses are invalid. Continue to live OHLC/data/setup.
    h1_best, h1_diag = candidate_diagnostics("USDJPY", "H1")
    m15_best, m15_diag = candidate_diagnostics("USDJPY", "M15")
    h1_rows = h1_best["rows"] if h1_best else []
    m15_rows = m15_best["rows"] if m15_best else []

    obj["source_paths"] = {
        "h1_ohlc_path": str(h1_best["path"]) if h1_best else None,
        "m15_ohlc_path": str(m15_best["path"]) if m15_best else None,
        "live_source_policy": "live_only_no_data_canonical_fallback",
    }
    obj["ohlc_source_diagnostics"] = {
        "h1_candidates_top": h1_diag,
        "m15_candidates_top": m15_diag,
    }
    obj["data_counts"] = {
        "h1_rows_loaded": len(h1_rows),
        "m15_rows_loaded": len(m15_rows),
        "h1_latest_bar_open_ts_utc": iso(h1_rows[-1]["ts"]) if h1_rows else None,
        "m15_latest_bar_open_ts_utc": iso(m15_rows[-1]["ts"]) if m15_rows else None,
    }

    if not h1_best or not m15_best:
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_TO_LIVE_OHLC_SOURCE_MISSING"
        return set_status(obj, "LIVE_OHLC_SOURCE_MISSING", "live_usdjpy_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed")

    if len(h1_rows) < 24:
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_TO_H1_HISTORY_INSUFFICIENT"
        return set_status(obj, "LIVE_H1_HISTORY_INSUFFICIENT", "h1_rows_lt_24_for_overlap_diagnostic_setup")

    if len(m15_rows) < 4:
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_TO_M15_HISTORY_INSUFFICIENT"
        return set_status(obj, "LIVE_M15_HISTORY_INSUFFICIENT", "m15_rows_lt_4_for_trigger_window")

    latest = len(h1_rows) - 1
    setup_i = latest - 1
    setup = h1_rows[setup_i]
    trigger = h1_rows[latest]

    setup_ok, setup_meta = lower_rejection_expansion_setup(h1_rows, setup_i)
    obj["setup_h1_open_ts_utc"] = iso(setup["ts"])
    obj["trigger_h1_open_ts_utc"] = iso(trigger["ts"])
    append_or_replace_check(obj, "H1_SETUP_PREVIOUS_BAR_LOWER_REJECTION_EXPANSION", setup_ok, setup_meta)

    if not setup_ok:
        current_ok, current_meta = lower_rejection_expansion_setup(h1_rows, latest)
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_TO_SETUP_NOT_FORMED"
        if current_ok:
            obj["current_setup_candidate"] = current_meta
            return set_status(obj, "H1_TRIGGER_WAIT", "latest_h1_bar_forms_overlap_lower_rejection_expansion_setup_waiting_for_next_h1_close")
        return set_status(obj, "SETUP_NOT_FORMED", "previous_h1_bar_did_not_match_overlap_lower_rejection_expansion_setup")

    h1_confirm = trigger["close"] > trigger["open"]
    append_or_replace_check(obj, "NEXT_H1_BULLISH_CLOSE_CONFIRM", h1_confirm, {
        "trigger_h1_open_ts_utc": iso(trigger["ts"]),
        "open": trigger["open"],
        "close": trigger["close"],
        "bullish_close": h1_confirm,
    })

    if not h1_confirm:
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_SETUP_PASS_H1_TRIGGER_FAIL"
        return set_status(obj, "H1_TRIGGER_NOT_CONFIRMED", "next_h1_bar_did_not_confirm_bullish_overlap_followthrough")

    m15_ok, m15_meta = m15_confirm(m15_rows, trigger["ts"])
    append_or_replace_check(obj, "M15_BULLISH_CLOSE_INSIDE_TRIGGER_H1", m15_ok, m15_meta)

    if not m15_ok:
        obj["is_shadow_match"] = False
        obj["is_diagnostic_shadow_match"] = False
        obj["gateflow_hotfix2_action"] = "REGIME_PASS_SETUP_PASS_H1_PASS_M15_WAIT"
        return set_status(obj, "M15_TRIGGER_WAIT", "h1_confirmed_but_no_inside_h1_m15_bullish_close")

    obj["is_shadow_match"] = True
    obj["is_diagnostic_shadow_match"] = True
    obj["m15_confirm_ts_utc"] = m15_meta.get("first_confirm_m15_open_ts_utc")
    obj["shadow_event_id"] = "SIGE_SD1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_" + iso(trigger["ts"]).replace("-", "").replace(":", "").replace("Z", "")
    obj["observation_horizon"] = {
        "horizon_h1_bars": 12,
        "observation_end_ts_utc": iso(trigger["ts"] + timedelta(hours=12)),
        "outcome_tracking_authorized": True,
        "trade_execution_authorized": False,
        "primary_lane_authorized": False,
    }
    obj["gateflow_hotfix2_action"] = "REGIME_PASS_TO_DIAGNOSTIC_SHADOW_MATCH_CONFIRMED"
    return set_status(obj, "DIAGNOSTIC_SHADOW_MATCH_CONFIRMED", "usdjpy_overlap_lower_rejection_expansion_long_diagnostic_shadow_match_confirmed")

def main():
    runtime = load_json(RUNTIME)
    if not isinstance(runtime, dict):
        out = {
            "program": PROGRAM,
            "created_utc": now(),
            "repair_status": "FAIL_RUNTIME_MISSING_OR_BAD_JSON",
        }
        write_json(OUT, out)
        print("SIG_E_SHADOW_LANE1B_GATEFLOW_HOTFIX2_FAIL_RUNTIME_MISSING")
        raise SystemExit(1)

    before = {
        "detector_status": runtime.get("detector_status"),
        "status_reason": runtime.get("status_reason"),
        "source_spec_id": runtime.get("source_spec_id"),
        "regime_passed": regime_passed(runtime),
        "regime_details": regime_details(runtime),
    }

    repaired = repair_gateflow(runtime)

    write_json(RUNTIME, repaired)
    write_json(PANEL, repaired)

    after = {
        "detector_status": repaired.get("detector_status"),
        "status_reason": repaired.get("status_reason"),
        "source_spec_id": repaired.get("source_spec_id"),
        "regime_passed": regime_passed(repaired),
        "data_counts": repaired.get("data_counts"),
        "source_paths": repaired.get("source_paths"),
        "gateflow_hotfix2_action": repaired.get("gateflow_hotfix2_action"),
        "is_diagnostic_shadow_match": repaired.get("is_diagnostic_shadow_match"),
    }

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "repair_status": "PASS",
        "before": before,
        "after": after,
        "authority": {k: False for k in AUTH_FALSE_KEYS},
        "boundary": BOUNDARY,
        "not_authorized": repaired.get("not_authorized"),
    }
    write_json(OUT, result)

    print("SIG_E_SHADOW_LANE1B_GATEFLOW_HOTFIX2_PASS")
    print("BEFORE_STATUS=" + str(before.get("detector_status")))
    print("AFTER_STATUS=" + str(after.get("detector_status")))
    print("AFTER_REASON=" + str(after.get("status_reason")))
    print("ACTION=" + str(after.get("gateflow_hotfix2_action")))

if __name__ == "__main__":
    main()
