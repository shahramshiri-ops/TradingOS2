# SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1 H1 OHLC HISTORY HOTFIX
# USDJPY Overlap Long Diagnostic H1+M15 — shadow/research only.

import csv
import gzip
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

CONFIG_PATH = Path("config/sig_e/shadow_detectors/usdjpy_overlap_long_diagnostic_h1_m15_v1_0.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
STATE_PATH = Path("state/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json")
BUILD_RESULT = Path("outputs/_sig_e_shadow_detector1b_overlap/sig_e_shadow_detector1b_overlap_build_result.json")

MIN_H1_ROWS_FOR_SETUP_TRIGGER = 6
MIN_M15_ROWS_FOR_TRIGGER = 1

VALID_STATUS = {
    "INPUT_INSUFFICIENT",
    "DATA_STALE",
    "SESSION_NOT_MATCHED",
    "REGIME_NOT_MATCHED",
    "FIELD_MAPPING_INCOMPLETE",
    "LIVE_OHLC_SOURCE_MISSING",
    "LIVE_H1_HISTORY_INSUFFICIENT",
    "LIVE_M15_HISTORY_INSUFFICIENT",
    "SETUP_NOT_FORMED",
    "H1_TRIGGER_WAIT",
    "H1_TRIGGER_NOT_CONFIRMED",
    "M15_TRIGGER_WAIT",
    "DIAGNOSTIC_SHADOW_MATCH_CONFIRMED",
    "EXPIRED",
}

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
    "primary_lane_authorized": False,
    "lane_rule_change_authorized": False,
}

def utc_now():
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

def iso(dt):
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"

def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None

def tf_of(surface):
    return str(first_nonempty(surface.get("timeframe"), surface.get("base_timeframe"), "")).upper() if isinstance(surface, dict) else ""

def surface_ts(surface):
    if not isinstance(surface, dict):
        return None
    return parse_dt(first_nonempty(
        surface.get("bar_open_ts_utc"),
        surface.get("latest_bar_open_ts_utc"),
        surface.get("latest_h1_bar_open_ts_utc"),
        surface.get("latest_m15_bar_open_ts_utc"),
        surface.get("bar_close_ts_utc"),
        surface.get("latest_bar_close_ts_utc")
    ))

def surface_lists(payload, source_path):
    out = []
    if isinstance(payload, dict):
        if isinstance(payload.get("surfaces"), list):
            out += [(s, source_path) for s in payload["surfaces"]]
        bc = payload.get("brain_context")
        if isinstance(bc, dict) and isinstance(bc.get("surfaces"), list):
            out += [(s, source_path) for s in bc["surfaces"]]
        if isinstance(payload.get("latest"), dict):
            out.append((payload["latest"], source_path))
    return out

def has_value(surface, key):
    if not isinstance(surface, dict):
        return False
    v = surface.get(key)
    return v is not None and not (isinstance(v, str) and not v.strip())

def source_priority(source_path):
    s = str(source_path).replace("\\", "/")
    if s == "runtime/sig_e/market_state_current.json":
        return 300
    if s == "runtime/sig_e/sig_e_regime1_market_state_current.json":
        return 290
    if s == "panel/brain4/sig_e_market_state_current.json":
        return 280
    if "sig_brain5_derived_context_latest" in s:
        return 100
    if "sig_brain4_live_context_latest" in s:
        return 90
    return 0

def surface_score(surface, instrument, timeframe, source_path=""):
    if not isinstance(surface, dict):
        return -999
    score = source_priority(source_path)
    if str(surface.get("instrument", "")).upper() == instrument:
        score += 10
    if tf_of(surface) == timeframe:
        score += 10
    if surface_ts(surface):
        score += 8
    for k in [
        "session_bucket", "d1_trend_state", "d1_trend_safe", "h4_trend_state", "h4_trend_safe",
        "htf_alignment", "volatility_state", "d1_vol_bucket", "range_state",
        "h1_open", "h1_high", "h1_low", "h1_close", "m15_dir", "tradeability_context"
    ]:
        if has_value(surface, k):
            score += 2
    if isinstance(surface.get("direction_inputs"), dict):
        score += 4
    if isinstance(surface.get("regime_metrics"), dict):
        score += 3
    if surface.get("h4_h1_up_context") is True:
        score += 3
    return score

def find_surface(payload_pairs, instrument="USDJPY", timeframe="H1"):
    candidates = []
    for payload, source_path in payload_pairs:
        for s, sp in surface_lists(payload, source_path):
            if isinstance(s, dict) and str(s.get("instrument", "")).upper() == instrument and tf_of(s) == timeframe:
                candidates.append((s, sp))
    if not candidates:
        return None, None
    return sorted(
        candidates,
        key=lambda pair: (surface_score(pair[0], instrument, timeframe, pair[1]), surface_ts(pair[0]) or datetime.min),
        reverse=True
    )[0]

def direction_input(surface, key):
    di = surface.get("direction_inputs") if isinstance(surface, dict) else None
    if isinstance(di, dict):
        v = di.get(key)
        if isinstance(v, dict):
            return first_nonempty(v.get("dir"), v.get("direction"), v.get("trend_state"), v.get("state"))
        return v
    return None

def norm_dir(v):
    s = str(v or "").upper()
    if s in ("1", "UP", "BULL", "BULLISH", "LONG") or "UP" in s or "BULL" in s:
        return "UP"
    if s in ("-1", "DOWN", "BEAR", "BEARISH", "SHORT") or "DOWN" in s or "BEAR" in s:
        return "DOWN"
    return s

def regime_check(surface, source_path):
    if not surface:
        return False, {"reason": "no_h1_surface"}
    session = str(surface.get("session_bucket", "")).upper()
    d1 = norm_dir(first_nonempty(surface.get("d1_trend_state"), surface.get("d1_trend_safe"), direction_input(surface, "d1")))
    h4 = norm_dir(first_nonempty(surface.get("h4_trend_state"), surface.get("h4_trend_safe"), direction_input(surface, "h4")))
    htf = str(surface.get("htf_alignment") or "").upper()
    vol = str(first_nonempty(surface.get("d1_vol_bucket"), surface.get("d1_volatility_bucket"), surface.get("volatility_state")) or "").upper()

    align_ok = (d1 == "UP" and h4 == "UP") or ("ALIGNED_UP" in htf) or surface.get("h4_h1_up_context") is True
    vol_known = vol not in ("", "UNKNOWN", "NONE", "NULL")
    vol_ok = vol in {"LOW", "NORMAL", "MIXED"} if vol_known else False

    missing = []
    if not session:
        missing.append("session_bucket")
    if not (d1 or h4 or htf or surface.get("h4_h1_up_context") is not None):
        missing.append("d1_h4_alignment_fields")
    if not vol_known:
        missing.append("volatility_state_or_d1_vol_bucket")

    return session == "LONDON_NY_OVERLAP" and align_ok and vol_ok and not missing, {
        "selected_surface_source": source_path,
        "source_priority": source_priority(source_path),
        "session_bucket": session,
        "d1_trend_state": d1,
        "h4_trend_state": h4,
        "htf_alignment": htf,
        "volatility_state_or_d1_vol_bucket": vol,
        "volatility_source_policy": surface.get("volatility_source_policy"),
        "tradeability_context": str(surface.get("tradeability_context") or "").upper(),
        "range_state": str(surface.get("range_state") or "").upper(),
        "h4_h1_up_context": surface.get("h4_h1_up_context"),
        "session_ok": session == "LONDON_NY_OVERLAP",
        "alignment_ok": align_ok,
        "vol_known": vol_known,
        "vol_ok": vol_ok,
        "missing_regime_fields": missing,
        "selected_surface_score": surface_score(surface, "USDJPY", "H1", source_path),
        "volatility_caveat": "Runtime proxy/UNKNOWN must not be treated as historical D1 LOW proof" if vol in {"NORMAL", "MIXED", "UNKNOWN"} else None
    }

def freshness_check(payloads):
    for p in payloads:
        if not isinstance(p, dict):
            continue
        lag = p.get("lag_diagnostic")
        if isinstance(lag, dict):
            reason = str(lag.get("lag_reason_code", "")).upper()
            if "STALE" in reason or ("LAG" in reason and "ALIGNED" not in reason):
                return "DATA_STALE", {"lag_reason_code": reason}
    return "FRESHNESS_NOT_BLOCKING", {}

def path_forbidden(path):
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

def path_live_allowed(path):
    if not path:
        return False
    s = str(path).replace("\\", "/").lower()
    if path_forbidden(s):
        return False
    return (
        "live" in s or
        s.startswith("runtime/") or
        s.startswith("panel/") or
        s.startswith("inputs/") or
        s.startswith("data/")
    )

def resolve_path(path):
    if not path:
        return None
    p = Path(str(path).replace("/", os.sep))
    return p if p.exists() and path_live_allowed(p) else None

def refresh_report_paths(instrument, timeframe):
    found = []
    for f in [
        "panel/brain4/sig_live_refresh_status_latest.json",
        "runtime/sig_brain/sig_live_refresh_status_latest.json",
        "data/live_m5/reports/resampled_from_m5_summary.json",
        "data/live_m5/reports/resample_report.json",
        "outputs/live_m5/resampled_from_m5_summary.json",
    ]:
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
            inst = str(first_nonempty(r.get("instrument"), r.get("symbol"), "")).upper()
            tf = str(first_nonempty(r.get("timeframe"), r.get("tf"), "")).upper()
            p = first_nonempty(r.get("path"), r.get("file"), r.get("filepath"), r.get("output_path"))
            if inst == instrument and tf == timeframe:
                rp = resolve_path(p)
                if rp:
                    found.append(("refresh_report", rp))
    return found

def glob_candidate_paths(instrument, timeframe):
    patterns = [
        f"data/live*/**/*{instrument}*{timeframe}*.csv",
        f"data/**/live*/**/*{instrument}*{timeframe}*.csv",
        f"data/live_m5*/**/*{instrument}*{timeframe}*.csv",
        f"data/live_resampled*/**/*{instrument}*{timeframe}*.csv",
        f"runtime/**/*{instrument}*{timeframe}*.csv",
        f"outputs/**/*live*{instrument}*{timeframe}*.csv",
    ]
    out = []
    seen = set()
    for pat in patterns:
        for p in Path(".").glob(pat):
            if not p.is_file():
                continue
            sp = str(p).replace("\\", "/")
            if sp in seen:
                continue
            seen.add(sp)
            if path_live_allowed(sp) and not path_forbidden(sp):
                out.append(("glob_live", p))
    return out

def detect_delimiter(line):
    candidates = [",", ";", "\t", "|"]
    return max(candidates, key=lambda c: line.count(c)) if line else ","

def pick_col(cols, names):
    low = {c.lower().replace(" ", "_"): c for c in cols}
    for n in names:
        key = n.lower().replace(" ", "_")
        if key in low:
            return low[key]
    for c in cols:
        lc = c.lower()
        for n in names:
            ln = n.lower()
            if ln in lc or lc in ln:
                return c
    return None

def to_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None

def read_csv_rows(path, max_tail=10000):
    if not path or not Path(path).exists():
        return []
    p = Path(path)
    try:
        if str(p).lower().endswith(".gz"):
            import gzip
            opener = lambda: gzip.open(p, "rt", encoding="utf-8", errors="replace", newline="")
            fmt = "csv.gz"
        else:
            opener = lambda: open(p, "r", encoding="utf-8", errors="replace", newline="")
            fmt = "csv"
        with opener() as f:
            first = f.readline()
            delim = detect_delimiter(first)
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delim)
            rows = []
            for r in reader:
                if isinstance(r, dict) and any(v not in (None, "") for v in r.values()):
                    r["_sig_e_source_file_format"] = fmt
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

def candidate_diagnostics(instrument, timeframe):
    raw_candidates = refresh_report_paths(instrument, timeframe) + glob_candidate_paths(instrument, timeframe)
    seen = set()
    diagnostics = []
    best = None

    for source, path in raw_candidates:
        sp = str(path).replace("\\", "/")
        if sp in seen:
            continue
        seen.add(sp)
        rows = standardize_ohlc(read_csv_rows(path))
        latest = rows[-1]["ts"] if rows else None
        count = len(rows)
        score = count
        if latest:
            score += 1000000
        # Prefer accumulated/resampled live stores over single latest snapshots.
        low = sp.lower()
        if "accum" in low or "store" in low or "resampled" in low or "live_m5" in low:
            score += 5000
        if "current" in low or "latest" in low:
            score -= 250
        item = {
            "source": source,
            "path": sp,
            "rows": count,
            "latest_bar_open_ts_utc": iso(latest),
            "score": score,
            "forbidden": path_forbidden(sp)
        }
        diagnostics.append(item)
        if count > 0 and not item["forbidden"]:
            if best is None or score > best["score"]:
                best = {"path": path, "rows": rows, "diagnostic": item, "score": score}

    diagnostics.sort(key=lambda x: (x.get("score") or 0, x.get("rows") or 0), reverse=True)
    return best, diagnostics[:20]

def row_range(row):
    return row["high"] - row["low"]

def lower_rejection_long(row, min_lower_wick=0.30, min_close_location=0.55):
    rng = row_range(row)
    if rng <= 0:
        return False, {"reason": "zero_range"}
    lower_wick = min(row["open"], row["close"]) - row["low"]
    close_location = (row["close"] - row["low"]) / rng
    lower_ratio = lower_wick / rng
    return lower_ratio >= min_lower_wick and close_location >= min_close_location, {
        "range": rng,
        "lower_wick": lower_wick,
        "lower_wick_to_range": lower_ratio,
        "close_location": close_location,
        "bullish_close": row["close"] > row["open"]
    }

def range_expanded(rows, setup_index, min_ratio=1.15):
    if setup_index < 4:
        return False, {"reason": "not_enough_prior_h1_ranges"}
    prior = [row_range(r) for r in rows[max(0, setup_index - 4):setup_index] if row_range(r) > 0]
    if len(prior) < 3:
        return False, {"reason": "not_enough_valid_prior_ranges"}
    avg = sum(prior) / len(prior)
    ratio = row_range(rows[setup_index]) / avg if avg > 0 else None
    return ratio is not None and ratio >= min_ratio, {
        "setup_range": row_range(rows[setup_index]),
        "prior_range_avg": avg,
        "range_expansion_ratio": ratio
    }

def m15_inside_confirm(m15_rows, h1_start):
    h1_end = h1_start + timedelta(hours=1)
    inside = [r for r in m15_rows if h1_start <= r["ts"] < h1_end]
    confirms = [r for r in inside if r["close"] > r["open"]]
    return bool(confirms), {
        "h1_window_start": iso(h1_start),
        "h1_window_end": iso(h1_end),
        "m15_inside_count": len(inside),
        "m15_confirm_count": len(confirms),
        "first_confirm_m15_open_ts_utc": iso(confirms[0]["ts"]) if confirms else None
    }

def load_state():
    state = load_json(STATE_PATH)
    if not isinstance(state, dict):
        state = {
            "state_version": "sig_e_shadow_detector_state_v1",
            "detector_id": "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0",
            "created_utc": utc_now(),
            "history": []
        }
    if not isinstance(state.get("history"), list):
        state["history"] = []
    return state

def update_state(state, current):
    hist = state.get("history", [])
    key = current.get("shadow_event_id") or current.get("detector_run_id")
    existing = {h.get("shadow_event_id") or h.get("detector_run_id") for h in hist if isinstance(h, dict)}
    if key not in existing:
        hist.append({
            "detector_run_id": current.get("detector_run_id"),
            "shadow_event_id": current.get("shadow_event_id"),
            "created_utc": current.get("created_utc"),
            "detector_status": current.get("detector_status"),
            "status_reason": current.get("status_reason"),
            "setup_h1_open_ts_utc": current.get("setup_h1_open_ts_utc"),
            "trigger_h1_open_ts_utc": current.get("trigger_h1_open_ts_utc"),
            "authority": current.get("authority"),
        })
    state["history"] = hist[-500:]
    state["last_updated_utc"] = utc_now()
    state["last_status"] = current.get("detector_status")
    state["last_shadow_event_id"] = current.get("shadow_event_id")
    return state

def build():
    config = load_json(CONFIG_PATH) or {}

    payload_pairs = []
    payloads = []
    loaded_files = []
    for p in [
        "runtime/sig_e/market_state_current.json",
        "runtime/sig_e/sig_e_regime1_market_state_current.json",
        "panel/brain4/sig_e_market_state_current.json",
        "runtime/sig_brain/sig_brain5_derived_context_latest.json",
        "inputs/sig_brain4_live_context_latest.json",
        "panel/brain4/sig_live_refresh_status_latest.json",
    ]:
        x = load_json(p)
        if x is not None:
            payload_pairs.append((x, p))
            payloads.append(x)
            loaded_files.append(p)

    h1_surface, h1_surface_source = find_surface(payload_pairs, "USDJPY", "H1")
    m15_surface, m15_surface_source = find_surface(payload_pairs, "USDJPY", "M15")

    run_id = "SIGE_SD1B_USDJPY_OVERLAP_" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    result = {
        "program": "SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1",
        "detector_id": config.get("detector_id", "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"),
        "source_spec_id": config.get("source_spec_id"),
        "detector_run_id": run_id,
        "created_utc": utc_now(),
        "instrument": "USDJPY",
        "direction": "LONG",
        "detector_status": "INPUT_INSUFFICIENT",
        "status_reason": None,
        "is_shadow_match": False,
        "is_signal": False,
        "is_trade_proposal": False,
        "classification": "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY",
        "is_diagnostic_shadow_match": False,
        "authority": AUTHORITY,
        "boundary": config.get("boundary", []),
        "loaded_source_files": loaded_files,
        "surface_snapshot": {
            "h1_surface_available": h1_surface is not None,
            "m15_surface_available": m15_surface is not None,
            "h1_surface_source": h1_surface_source,
            "m15_surface_source": m15_surface_source,
            "h1_bar_open_ts_utc": iso(surface_ts(h1_surface)) if h1_surface else None,
            "m15_bar_open_ts_utc": iso(surface_ts(m15_surface)) if m15_surface else None,
            "h1_surface_score": surface_score(h1_surface, "USDJPY", "H1", h1_surface_source) if h1_surface else None,
            "m15_surface_score": surface_score(m15_surface, "USDJPY", "M15", m15_surface_source) if m15_surface else None,
        },
        "checks": [],
        "not_authorized": [
            "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
            "broker/execution", "auto execution", "memory promotion"
        ],
    }

    fresh_status, fresh_meta = freshness_check(payloads)
    result["freshness_check"] = {"status": fresh_status, **fresh_meta}
    if fresh_status == "DATA_STALE":
        result["detector_status"] = "DATA_STALE"
        result["status_reason"] = "freshness_blocked"
        return result

    regime_ok, regime_meta = regime_check(h1_surface, h1_surface_source)
    result["checks"].append({"check_id": "REGIME", "passed": regime_ok, "details": regime_meta})

    if h1_surface is None:
        result["status_reason"] = "missing_usdjpy_h1_surface"
        return result
    if regime_meta.get("session_bucket") != "LONDON":
        result["detector_status"] = "SESSION_NOT_MATCHED"
        result["status_reason"] = "session_not_london_ny_overlap"
        return result
    if not regime_meta.get("alignment_ok"):
        result["detector_status"] = "REGIME_NOT_MATCHED"
        result["status_reason"] = "d1_h4_alignment_not_matched"
        return result
    if "volatility_state_or_d1_vol_bucket" in regime_meta.get("missing_regime_fields", []):
        result["detector_status"] = "FIELD_MAPPING_INCOMPLETE"
        result["status_reason"] = "missing_required_volatility_field_after_session_alignment_match"
        return result
    if not regime_meta.get("vol_ok"):
        result["detector_status"] = "REGIME_NOT_MATCHED"
        result["status_reason"] = "volatility_regime_not_matched"
        return result

    h1_best, h1_candidates = candidate_diagnostics("USDJPY", "H1")
    m15_best, m15_candidates = candidate_diagnostics("USDJPY", "M15")

    h1_rows = h1_best["rows"] if h1_best else []
    m15_rows = m15_best["rows"] if m15_best else []
    h1_path = h1_best["path"] if h1_best else None
    m15_path = m15_best["path"] if m15_best else None

    result["source_paths"] = {
        "h1_ohlc_path": str(h1_path) if h1_path else None,
        "m15_ohlc_path": str(m15_path) if m15_path else None,
        "live_source_policy": "live_only_no_data_canonical_fallback",
        "h1_selection_policy": "prefer_live_accumulated_resampled_store_with_most_rows",
        "m15_selection_policy": "prefer_live_accumulated_resampled_store_with_most_rows",
    }
    result["ohlc_source_diagnostics"] = {
        "h1_candidates_top": h1_candidates,
        "m15_candidates_top": m15_candidates,
    }
    result["data_counts"] = {
        "h1_rows_loaded": len(h1_rows),
        "m15_rows_loaded": len(m15_rows),
        "h1_latest_bar_open_ts_utc": iso(h1_rows[-1]["ts"]) if h1_rows else None,
        "m15_latest_bar_open_ts_utc": iso(m15_rows[-1]["ts"]) if m15_rows else None,
    }

    if h1_path is None or m15_path is None:
        result["detector_status"] = "LIVE_OHLC_SOURCE_MISSING"
        result["status_reason"] = "live_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed"
        return result

    if len(h1_rows) < MIN_H1_ROWS_FOR_SETUP_TRIGGER:
        result["detector_status"] = "LIVE_H1_HISTORY_INSUFFICIENT"
        result["status_reason"] = f"h1_rows_loaded_lt_{MIN_H1_ROWS_FOR_SETUP_TRIGGER}_for_setup_trigger_window"
        return result

    if len(m15_rows) < MIN_M15_ROWS_FOR_TRIGGER:
        result["detector_status"] = "LIVE_M15_HISTORY_INSUFFICIENT"
        result["status_reason"] = "m15_rows_missing_for_trigger_window"
        return result

    latest = len(h1_rows) - 1
    setup_i = latest - 1
    setup_bar = h1_rows[setup_i]
    trigger_bar = h1_rows[latest]

    result["setup_h1_open_ts_utc"] = iso(setup_bar["ts"])
    result["trigger_h1_open_ts_utc"] = iso(trigger_bar["ts"])

    setup_reject, reject_meta = lower_rejection_long(setup_bar)
    setup_expanded, expand_meta = range_expanded(h1_rows, setup_i)
    setup_ok = setup_reject and setup_expanded
    result["checks"].append({
        "check_id": "H1_SETUP_PREVIOUS_BAR",
        "passed": setup_ok,
        "details": {
            "setup_h1_open_ts_utc": iso(setup_bar["ts"]),
            "lower_rejection": reject_meta,
            "range_expansion": expand_meta,
        }
    })

    if not setup_ok:
        cur_reject, cur_reject_meta = lower_rejection_long(trigger_bar)
        cur_expanded, cur_expand_meta = range_expanded(h1_rows, latest)
        if cur_reject and cur_expanded:
            result["detector_status"] = "H1_TRIGGER_WAIT"
            result["status_reason"] = "latest_h1_bar_forms_setup_waiting_for_next_h1_close"
            result["current_setup_candidate"] = {
                "setup_h1_open_ts_utc": iso(trigger_bar["ts"]),
                "lower_rejection": cur_reject_meta,
                "range_expansion": cur_expand_meta,
            }
        else:
            result["detector_status"] = "SETUP_NOT_FORMED"
            result["status_reason"] = "previous_h1_bar_did_not_match_lower_rejection_expansion_setup"
        return result

    h1_confirm = trigger_bar["close"] > trigger_bar["open"]
    result["checks"].append({
        "check_id": "NEXT_H1_DIRECTION_CONFIRM",
        "passed": h1_confirm,
        "details": {
            "trigger_h1_open_ts_utc": iso(trigger_bar["ts"]),
            "open": trigger_bar["open"],
            "close": trigger_bar["close"],
            "direction": "UP" if h1_confirm else "NOT_UP"
        }
    })

    if not h1_confirm:
        result["detector_status"] = "H1_TRIGGER_NOT_CONFIRMED"
        result["status_reason"] = "next_h1_bar_did_not_confirm_long_direction"
        return result

    m15_confirm, m15_meta = m15_inside_confirm(m15_rows, trigger_bar["ts"])
    result["checks"].append({
        "check_id": "M15_INSIDE_H1_DIRECTIONAL_CLOSE_CONFIRM",
        "passed": m15_confirm,
        "details": m15_meta,
    })

    if not m15_confirm:
        result["detector_status"] = "M15_TRIGGER_WAIT"
        result["status_reason"] = "h1_confirmed_but_no_inside_h1_m15_directional_close_yet"
        return result

    result["detector_status"] = "DIAGNOSTIC_SHADOW_MATCH_CONFIRMED"
    result["status_reason"] = "regime_setup_h1_trigger_m15_trigger_all_confirmed"
    result["is_shadow_match"] = True
    result["is_diagnostic_shadow_match"] = True
    result["shadow_event_id"] = "SIGE_SD1B_USDJPY_OVERLAP_LONDON_LONG_" + iso(trigger_bar["ts"]).replace("-", "").replace(":", "").replace("Z", "")
    result["m15_confirm_ts_utc"] = m15_meta.get("first_confirm_m15_open_ts_utc")
    result["observation_horizon"] = {
        "horizon_h1_bars": 16,
        "observation_end_ts_utc": iso(trigger_bar["ts"] + timedelta(hours=16)),
        "outcome_tracking_authorized": True,
        "trade_execution_authorized": False,
    }
    return result


def normalize_lane1b_status_hotfix1(result):
    # SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1:
    # Status/metadata normalization only. Does not change setup, trigger,
    # M15 confirmation, shadow-match logic, Lane1, portfolio rules, signals,
    # trade proposals, or execution authority.
    if not isinstance(result, dict):
        return result

    if not result.get("source_spec_id"):
        result["source_spec_id"] = "SIG_E_RUNTIME_SPEC_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"

    if result.get("detector_id") == "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0":
        result.setdefault("classification", "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY")
        result["is_signal"] = False
        result["is_trade_proposal"] = False

    details = {}
    for chk in result.get("checks", []) or []:
        if isinstance(chk, dict):
            cid = str(chk.get("check_id") or "").upper()
            if "REGIME" in cid:
                details = chk.get("details") or {}
                break

    session_ok = details.get("session_ok")
    alignment_ok = details.get("alignment_ok")
    vol_ok = details.get("vol_ok")

    if result.get("detector_status") == "SESSION_NOT_MATCHED" and session_ok is True:
        if alignment_ok is False or vol_ok is False:
            result["detector_status"] = "REGIME_NOT_MATCHED"
            result["status_reason"] = "overlap_long_diagnostic_regime_not_matched"
            result["status_hotfix_applied"] = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1"
            result["status_hotfix_reason"] = "session_ok_true_but_regime_alignment_or_vol_failed"

    result.setdefault("authority", {})
    for k in [
        "signal_authorized",
        "trade_proposal_authorized",
        "entry_stop_target_authorized",
        "risk_sizing_authorized",
        "broker_execution_authorized",
        "auto_execution_authorized",
        "primary_lane_authorized",
        "lane_rule_change_authorized",
    ]:
        result["authority"][k] = False

    return result

def main():
    result = build()
    if result.get("detector_status") not in VALID_STATUS:
        result["detector_status"] = "INPUT_INSUFFICIENT"
        result["status_reason"] = "invalid_status_guardrail"

    state = update_state(load_state(), result)

    write_json(RUNTIME_OUT, result)
    write_json(PANEL_OUT, result)
    write_json(STATE_PATH, state)
    write_json(BUILD_RESULT, {
        "program": "SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1",
        "created_utc": utc_now(),
        "build_status": "PASS",
        "detector_status": result.get("detector_status"),
        "status_reason": result.get("status_reason"),
        "is_shadow_match": result.get("is_shadow_match"),
        "data_counts": result.get("data_counts"),
        "source_paths": result.get("source_paths"),
        "hotfixes": [
            "accumulated_live_h1_ohlc_candidate_selection",
            "live_h1_history_insufficient_status",
            "live_m15_history_insufficient_status",
            "candidate_source_diagnostics",
            "no_historical_canonical_fallback"
        ],
        "authority": result.get("authority"),
    })

    print("SIG_E_SHADOW_DETECTOR1_H1_OHLC_HISTORY_HOTFIX_DONE")
    print("DETECTOR_STATUS=" + str(result.get("detector_status")))
    print("STATUS_REASON=" + str(result.get("status_reason")))
    print("H1_ROWS_LOADED=" + str((result.get("data_counts") or {}).get("h1_rows_loaded")))
    print("M15_ROWS_LOADED=" + str((result.get("data_counts") or {}).get("m15_rows_loaded")))
    print("H1_PATH=" + str((result.get("source_paths") or {}).get("h1_ohlc_path")))

if __name__ == "__main__":
    main()
