import csv
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

CONFIG_PATH = Path("config/sig_e/shadow_detectors/usdjpy_london_long_h1_m15_v1_0.json")
SPEC_PATH = Path("config/sig_e/runtime_specs/usdjpy_london_long_h1_m15_v1_0.json")

RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_status_current.json")
STATE_PATH = Path("state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json")
BUILD_RESULT = Path("outputs/_sig_e_shadow_detector1/sig_e_shadow_detector1_build_result.json")

VALID_STATUS = {
    "INPUT_INSUFFICIENT",
    "DATA_STALE",
    "SESSION_NOT_MATCHED",
    "REGIME_NOT_MATCHED",
    "SETUP_NOT_FORMED",
    "H1_TRIGGER_WAIT",
    "H1_TRIGGER_NOT_CONFIRMED",
    "M15_TRIGGER_WAIT",
    "SHADOW_MATCH_CONFIRMED",
    "EXPIRED",
}

def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def parse_dt(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
    ]:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
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

def detect_delimiter(line):
    candidates = [",", ";", "\t", "|"]
    counts = {c: line.count(c) for c in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","

def norm(s):
    return str(s).strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")

def pick_col(fieldnames, aliases):
    if not fieldnames:
        return None
    nmap = {norm(c): c for c in fieldnames}
    for a in aliases:
        if norm(a) in nmap:
            return nmap[norm(a)]
    for c in fieldnames:
        nc = norm(c)
        for a in aliases:
            na = norm(a)
            if na in nc or nc in na:
                return c
    return None

def to_float(v):
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None

def read_csv_rows(path, max_tail=2000):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
        if not first:
            return []
        delim = detect_delimiter(first)
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) > max_tail:
                rows = rows[-max_tail:]
        return rows

def standardize_ohlc_rows(rows):
    if not rows:
        return []
    fieldnames = list(rows[0].keys())
    ts_col = pick_col(fieldnames, ["bar_open_ts_utc", "timestamp", "datetime", "time", "date"])
    open_col = pick_col(fieldnames, ["open", "o"])
    high_col = pick_col(fieldnames, ["high", "h"])
    low_col = pick_col(fieldnames, ["low", "l"])
    close_col = pick_col(fieldnames, ["close", "c"])
    out = []
    for r in rows:
        dt = parse_dt(r.get(ts_col)) if ts_col else None
        o = to_float(r.get(open_col)) if open_col else None
        h = to_float(r.get(high_col)) if high_col else None
        l = to_float(r.get(low_col)) if low_col else None
        c = to_float(r.get(close_col)) if close_col else None
        if dt is None or None in (o, h, l, c):
            continue
        if h < l:
            continue
        out.append({"ts": dt, "open": o, "high": h, "low": l, "close": c})
    out.sort(key=lambda x: x["ts"])
    return out

def flatten_surfaces(payload):
    surfaces = []
    if isinstance(payload, dict):
        if isinstance(payload.get("surfaces"), list):
            surfaces.extend(payload["surfaces"])
        bc = payload.get("brain_context")
        if isinstance(bc, dict) and isinstance(bc.get("surfaces"), list):
            surfaces.extend(bc["surfaces"])
        # Some payloads may be a latest object
        latest = payload.get("latest")
        if isinstance(latest, dict):
            surfaces.append(latest)
    return surfaces

def find_surface(payloads, instrument="USDJPY", timeframe="H1"):
    candidates = []
    for payload in payloads:
        for s in flatten_surfaces(payload):
            if not isinstance(s, dict):
                continue
            inst = str(s.get("instrument", "")).upper()
            tf = str(s.get("timeframe") or s.get("base_timeframe") or "").upper()
            if inst == instrument and tf == timeframe:
                candidates.append(s)
    if not candidates:
        return None
    def dt_key(s):
        return parse_dt(s.get("bar_open_ts_utc") or s.get("latest_bar_open_ts_utc") or s.get("latest_h1_bar_open_ts_utc")) or datetime.min
    return sorted(candidates, key=dt_key)[-1]

def extract_paths_from_refresh_status(instrument="USDJPY"):
    paths = {}
    for path in [
        Path("panel/brain4/sig_live_refresh_status_latest.json"),
        Path("runtime/sig_brain/sig_live_refresh_status_latest.json"),
        Path("data/live_m5/reports/resampled_from_m5_summary.json"),
    ]:
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        rows = []
        rd = payload.get("resampled_data")
        if isinstance(rd, dict) and isinstance(rd.get("rows"), list):
            rows.extend(rd["rows"])
        if isinstance(payload.get("rows"), list):
            rows.extend(payload["rows"])
        for r in rows:
            if str(r.get("instrument", "")).upper() == instrument:
                tf = str(r.get("timeframe", "")).upper()
                p = r.get("path")
                if tf and p:
                    paths[tf] = str(p)
    return paths

def find_live_ohlc_path(instrument, timeframe):
    candidates = []
    refresh_paths = extract_paths_from_refresh_status(instrument)
    if timeframe in refresh_paths:
        candidates.append(Path(refresh_paths[timeframe]))
    # Common repository paths
    candidates += [
        Path("data/live_resampled") / f"{instrument}_{timeframe}.csv",
        Path("data/live_m5/resampled") / f"{instrument}_{timeframe}.csv",
        Path("data/canonical") / f"{instrument}_{timeframe}.csv",
        Path("data/live") / f"{instrument}_{timeframe}.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def h1_range(row):
    return row["high"] - row["low"]

def lower_rejection_long(row, min_lower_wick=0.30, min_close_location=0.55):
    rng = h1_range(row)
    if rng <= 0:
        return False, {"reason": "zero_range"}
    lower_wick = min(row["open"], row["close"]) - row["low"]
    close_location = (row["close"] - row["low"]) / rng
    lower_ratio = lower_wick / rng
    return (lower_ratio >= min_lower_wick and close_location >= min_close_location), {
        "range": rng,
        "lower_wick": lower_wick,
        "lower_wick_to_range": lower_ratio,
        "close_location": close_location,
        "bullish_close": row["close"] > row["open"]
    }

def range_expanded(rows, setup_index, min_ratio=1.15):
    if setup_index < 4:
        return False, {"reason": "not_enough_prior_h1_ranges"}
    setup_range = h1_range(rows[setup_index])
    prior = [h1_range(r) for r in rows[max(0, setup_index-4):setup_index] if h1_range(r) > 0]
    if len(prior) < 3:
        return False, {"reason": "not_enough_valid_prior_ranges"}
    avg_prior = sum(prior) / len(prior)
    ratio = setup_range / avg_prior if avg_prior > 0 else None
    return (ratio is not None and ratio >= min_ratio), {
        "setup_range": setup_range,
        "prior_range_avg": avg_prior,
        "range_expansion_ratio": ratio
    }

def direction_confirm_long(row):
    return row["close"] > row["open"], {
        "open": row["open"],
        "close": row["close"],
        "direction": "UP" if row["close"] > row["open"] else ("DOWN" if row["close"] < row["open"] else "FLAT")
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

def regime_matches(surface):
    if not surface:
        return False, {"reason": "no_h1_surface"}
    session = str(surface.get("session_bucket", "")).upper()
    d1 = str(surface.get("d1_trend_state") or surface.get("d1_trend_safe") or "").upper()
    h4 = str(surface.get("h4_trend_state") or surface.get("h4_trend_safe") or "").upper()
    htf = str(surface.get("htf_alignment") or "").upper()
    vol = str(surface.get("d1_vol_bucket") or surface.get("volatility_state") or "").upper()
    tradeability = str(surface.get("tradeability_context") or "").upper()

    session_ok = session == "LONDON"
    alignment_ok = (d1 == "UP" and h4 == "UP") or ("ALIGNED_UP" in htf) or bool(surface.get("h4_h1_up_context") is True)
    vol_ok = vol in {"LOW", "NORMAL"}  # LOW preferred; NORMAL accepted with caveat because runtime may expose broad vol state only.
    return session_ok and alignment_ok and vol_ok, {
        "session_bucket": session,
        "d1_trend_state": d1,
        "h4_trend_state": h4,
        "htf_alignment": htf,
        "volatility_state_or_d1_vol_bucket": vol,
        "tradeability_context": tradeability,
        "session_ok": session_ok,
        "alignment_ok": alignment_ok,
        "vol_ok": vol_ok,
        "volatility_caveat": "NORMAL accepted as runtime proxy if D1 vol bucket is unavailable" if vol == "NORMAL" else None
    }

def freshness_status(payloads):
    # Best-effort only; do not block unless explicit stale markers appear.
    for p in payloads:
        if not isinstance(p, dict):
            continue
        lag = p.get("lag_diagnostic")
        if isinstance(lag, dict):
            reason = str(lag.get("lag_reason_code", "")).upper()
            if "STALE" in reason or "LAG" in reason and "ALIGNED" not in reason:
                return "DATA_STALE", {"lag_reason_code": reason}
        src = p.get("source_context")
        if isinstance(src, dict):
            rs = src.get("refresh_status_summary")
            if isinstance(rs, dict):
                reason = str(rs.get("lag_reason_code", "")).upper()
                if "STALE" in reason:
                    return "DATA_STALE", {"lag_reason_code": reason}
    return "FRESHNESS_NOT_BLOCKING", {}

def load_state():
    state = load_json(STATE_PATH)
    if not isinstance(state, dict):
        state = {
            "state_version": "sig_e_shadow_detector_state_v1",
            "detector_id": "SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0",
            "created_utc": utc_now(),
            "history": []
        }
    if "history" not in state or not isinstance(state["history"], list):
        state["history"] = []
    return state

def update_state(state, current):
    hist = state.get("history", [])
    key = current.get("shadow_event_id") or current.get("detector_run_id")
    existing = set(x.get("shadow_event_id") or x.get("detector_run_id") for x in hist if isinstance(x, dict))
    if key not in existing:
        hist.append({
            "detector_run_id": current.get("detector_run_id"),
            "shadow_event_id": current.get("shadow_event_id"),
            "created_utc": current.get("created_utc"),
            "status": current.get("detector_status"),
            "setup_h1_open_ts_utc": current.get("setup_h1_open_ts_utc"),
            "trigger_h1_open_ts_utc": current.get("trigger_h1_open_ts_utc"),
            "m15_confirm_ts_utc": current.get("m15_confirm_ts_utc"),
            "authority": current.get("authority")
        })
    state["history"] = hist[-500:]
    state["last_updated_utc"] = utc_now()
    state["last_status"] = current.get("detector_status")
    state["last_shadow_event_id"] = current.get("shadow_event_id")
    return state

def build_current_result():
    config = load_json(CONFIG_PATH) or {}
    spec = load_json(SPEC_PATH) or {}

    payloads = []
    for p in [
        Path("runtime/sig_e/market_state_current.json"),
        Path("runtime/sig_e/sig_e_regime1_market_state_current.json"),
        Path("panel/brain4/sig_e_market_state_current.json"),
        Path("runtime/sig_brain/sig_brain5_derived_context_latest.json"),
        Path("inputs/sig_brain4_live_context_latest.json"),
        Path("panel/brain4/sig_live_refresh_status_latest.json"),
    ]:
        data = load_json(p)
        if data is not None:
            payloads.append(data)

    h1_surface = find_surface(payloads, "USDJPY", "H1")
    m15_surface = find_surface(payloads, "USDJPY", "M15")

    detector_run_id = "SIGE_SD1_USDJPY_" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    result = {
        "program": "SIG-E-RUNTIME-SHADOW-DETECTOR1",
        "detector_id": config.get("detector_id", "SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0"),
        "source_spec_id": config.get("source_spec_id"),
        "detector_run_id": detector_run_id,
        "created_utc": utc_now(),
        "instrument": "USDJPY",
        "direction": "LONG",
        "detector_status": "INPUT_INSUFFICIENT",
        "status_reason": None,
        "is_shadow_match": False,
        "is_signal": False,
        "is_trade_proposal": False,
        "authority": {
            "signal_authorized": False,
            "trade_proposal_authorized": False,
            "entry_stop_target_authorized": False,
            "risk_sizing_authorized": False,
            "broker_execution_authorized": False,
            "auto_execution_authorized": False
        },
        "boundary": config.get("boundary", []),
        "surface_snapshot": {
            "h1_surface_available": h1_surface is not None,
            "m15_surface_available": m15_surface is not None,
            "h1_bar_open_ts_utc": h1_surface.get("bar_open_ts_utc") if isinstance(h1_surface, dict) else None,
            "m15_bar_open_ts_utc": m15_surface.get("bar_open_ts_utc") if isinstance(m15_surface, dict) else None,
        },
        "checks": [],
        "not_authorized": [
            "signal",
            "manual trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution",
            "auto execution",
            "memory promotion"
        ]
    }

    fresh_status, fresh_meta = freshness_status(payloads)
    result["freshness_check"] = {"status": fresh_status, **fresh_meta}
    if fresh_status == "DATA_STALE":
        result["detector_status"] = "DATA_STALE"
        result["status_reason"] = "freshness_blocked"
        return result

    regime_ok, regime_meta = regime_matches(h1_surface)
    result["checks"].append({"check_id": "REGIME", "passed": regime_ok, "details": regime_meta})
    if h1_surface is None:
        result["detector_status"] = "INPUT_INSUFFICIENT"
        result["status_reason"] = "missing_usdjpy_h1_surface"
        return result

    if str(regime_meta.get("session_bucket", "")).upper() != "LONDON":
        result["detector_status"] = "SESSION_NOT_MATCHED"
        result["status_reason"] = "session_not_london"
        return result

    if not regime_ok:
        result["detector_status"] = "REGIME_NOT_MATCHED"
        result["status_reason"] = "d1_h4_vol_regime_not_matched"
        return result

    h1_path = find_live_ohlc_path("USDJPY", "H1")
    m15_path = find_live_ohlc_path("USDJPY", "M15")
    result["source_paths"] = {
        "h1_ohlc_path": str(h1_path) if h1_path else None,
        "m15_ohlc_path": str(m15_path) if m15_path else None
    }

    h1_rows = standardize_ohlc_rows(read_csv_rows(h1_path)) if h1_path else []
    m15_rows = standardize_ohlc_rows(read_csv_rows(m15_path)) if m15_path else []
    result["data_counts"] = {
        "h1_rows_loaded": len(h1_rows),
        "m15_rows_loaded": len(m15_rows)
    }

    if len(h1_rows) < 6:
        result["detector_status"] = "INPUT_INSUFFICIENT"
        result["status_reason"] = "not_enough_h1_rows_for_setup_trigger_window"
        return result

    latest_idx = len(h1_rows) - 1
    setup_idx = latest_idx - 1
    setup_bar = h1_rows[setup_idx]
    trigger_bar = h1_rows[latest_idx]
    result["setup_h1_open_ts_utc"] = iso(setup_bar["ts"])
    result["trigger_h1_open_ts_utc"] = iso(trigger_bar["ts"])

    # Check if current latest H1 is setup but no next H1 trigger yet.
    current_setup_reject, current_reject_meta = lower_rejection_long(trigger_bar, 
        config.get("setup_requirements", {}).get("lower_rejection_long", {}).get("min_lower_wick_to_range", 0.30),
        config.get("setup_requirements", {}).get("lower_rejection_long", {}).get("min_close_location", 0.55)
    )
    current_expanded, current_expand_meta = range_expanded(h1_rows, latest_idx, 
        config.get("setup_requirements", {}).get("h1_range_expansion", {}).get("min_ratio", 1.15)
    )

    setup_reject, reject_meta = lower_rejection_long(setup_bar,
        config.get("setup_requirements", {}).get("lower_rejection_long", {}).get("min_lower_wick_to_range", 0.30),
        config.get("setup_requirements", {}).get("lower_rejection_long", {}).get("min_close_location", 0.55)
    )
    setup_expanded, expand_meta = range_expanded(h1_rows, setup_idx,
        config.get("setup_requirements", {}).get("h1_range_expansion", {}).get("min_ratio", 1.15)
    )

    setup_ok = setup_reject and setup_expanded
    result["checks"].append({
        "check_id": "H1_SETUP_PREVIOUS_BAR",
        "passed": setup_ok,
        "details": {
            "setup_h1_open_ts_utc": iso(setup_bar["ts"]),
            "lower_rejection": reject_meta,
            "range_expansion": expand_meta
        }
    })

    if not setup_ok:
        if current_setup_reject and current_expanded:
            result["detector_status"] = "H1_TRIGGER_WAIT"
            result["status_reason"] = "latest_h1_bar_forms_setup_waiting_for_next_h1_close"
            result["current_setup_candidate"] = {
                "setup_h1_open_ts_utc": iso(trigger_bar["ts"]),
                "lower_rejection": current_reject_meta,
                "range_expansion": current_expand_meta
            }
        else:
            result["detector_status"] = "SETUP_NOT_FORMED"
            result["status_reason"] = "previous_h1_bar_did_not_match_lower_rejection_expansion_setup"
        return result

    h1_confirm, h1_confirm_meta = direction_confirm_long(trigger_bar)
    result["checks"].append({
        "check_id": "NEXT_H1_DIRECTION_CONFIRM",
        "passed": h1_confirm,
        "details": {
            "trigger_h1_open_ts_utc": iso(trigger_bar["ts"]),
            **h1_confirm_meta
        }
    })

    if not h1_confirm:
        result["detector_status"] = "H1_TRIGGER_NOT_CONFIRMED"
        result["status_reason"] = "next_h1_bar_did_not_confirm_long_direction"
        return result

    if not m15_rows:
        result["detector_status"] = "INPUT_INSUFFICIENT"
        result["status_reason"] = "m15_ohlc_rows_missing"
        return result

    m15_confirm, m15_meta = m15_inside_confirm(m15_rows, trigger_bar["ts"])
    result["checks"].append({
        "check_id": "M15_INSIDE_H1_DIRECTIONAL_CLOSE_CONFIRM",
        "passed": m15_confirm,
        "details": m15_meta
    })

    if not m15_confirm:
        result["detector_status"] = "M15_TRIGGER_WAIT"
        result["status_reason"] = "h1_confirmed_but_no_inside_h1_m15_directional_close_yet"
        return result

    shadow_event_id = "SIGE_SD1_USDJPY_LONDON_LONG_" + iso(trigger_bar["ts"]).replace("-", "").replace(":", "").replace("Z", "")
    result["detector_status"] = "SHADOW_MATCH_CONFIRMED"
    result["status_reason"] = "regime_setup_h1_trigger_m15_trigger_all_confirmed"
    result["is_shadow_match"] = True
    result["shadow_event_id"] = shadow_event_id
    result["m15_confirm_ts_utc"] = m15_meta.get("first_confirm_m15_open_ts_utc")
    result["observation_horizon"] = {
        "horizon_h1_bars": 16,
        "observation_end_ts_utc": iso(trigger_bar["ts"] + timedelta(hours=16)),
        "outcome_tracking_authorized": True,
        "trade_execution_authorized": False
    }
    return result

def main():
    result = build_current_result()

    if result.get("detector_status") not in VALID_STATUS:
        result["detector_status"] = "INPUT_INSUFFICIENT"
        result["status_reason"] = "invalid_status_guardrail"

    state = load_state()
    state = update_state(state, result)

    write_json(RUNTIME_OUT, result)
    write_json(PANEL_OUT, result)
    write_json(STATE_PATH, state)
    write_json(BUILD_RESULT, {
        "program": "SIG-E-RUNTIME-SHADOW-DETECTOR1",
        "created_utc": utc_now(),
        "build_status": "PASS",
        "detector_status": result.get("detector_status"),
        "is_shadow_match": result.get("is_shadow_match"),
        "runtime_out": str(RUNTIME_OUT),
        "panel_out": str(PANEL_OUT),
        "state_path": str(STATE_PATH),
        "authority": result.get("authority")
    })

    print("SIG_E_SHADOW_DETECTOR1_BUILD_DONE")
    print("DETECTOR_STATUS=" + str(result.get("detector_status")))
    print("IS_SHADOW_MATCH=" + str(result.get("is_shadow_match")))
    print("Runtime out:", RUNTIME_OUT)
    print("Panel out:", PANEL_OUT)

if __name__ == "__main__":
    main()
