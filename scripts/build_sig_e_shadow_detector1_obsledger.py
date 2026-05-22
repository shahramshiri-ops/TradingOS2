import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

PROGRAM = "SIG-E-SHADOW-DETECTOR1-OBSLEDGER1"

DETECTOR_CURRENT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
LEDGER_STATE = Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_obsledger_status_current.json")
BUILD_OUT = Path("outputs/_sig_e_shadow_detector_obsledger1/sig_e_shadow_detector_obsledger1_build_result.json")

MAX_REFRESH_RECORDS = 20000
MAX_NEAR_MISS_RECORDS = 5000
MAX_EVENT_RECORDS = 1000

STATUS_ORDER = [
    "INPUT_INSUFFICIENT",
    "DATA_STALE",
    "SESSION_NOT_MATCHED",
    "REGIME_NOT_MATCHED",
    "FIELD_MAPPING_INCOMPLETE",
    "LIVE_OHLC_SOURCE_MISSING",
    "SETUP_NOT_FORMED",
    "H1_TRIGGER_WAIT",
    "H1_TRIGGER_NOT_CONFIRMED",
    "M15_TRIGGER_WAIT",
    "SHADOW_MATCH_CONFIRMED",
    "EXPIRED",
]

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

BOUNDARY = [
    "OBSERVATION_LEDGER_ONLY",
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

def now_utc():
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

def read_csv_tail(path, max_tail=5000):
    if not path or not Path(path).exists():
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
        delim = detect_delimiter(first)
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) > max_tail:
                rows = rows[-max_tail:]
        return rows

def normalize_ohlc(rows):
    if not rows:
        return []
    cols = list(rows[0].keys())
    tcol = pick_col(cols, ["bar_open_ts_utc", "timestamp", "datetime", "time", "date"])
    ocol = pick_col(cols, ["open", "o"])
    hcol = pick_col(cols, ["high", "h"])
    lcol = pick_col(cols, ["low", "l"])
    ccol = pick_col(cols, ["close", "c"])
    out = []
    for r in rows:
        ts = parse_dt(r.get(tcol)) if tcol else None
        o = to_float(r.get(ocol)) if ocol else None
        h = to_float(r.get(hcol)) if hcol else None
        l = to_float(r.get(lcol)) if lcol else None
        c = to_float(r.get(ccol)) if ccol else None
        if ts and None not in (o, h, l, c) and h >= l:
            out.append({"ts": ts, "open": o, "high": h, "low": l, "close": c})
    out.sort(key=lambda x: x["ts"])
    return out

def path_is_live_allowed(path):
    if not path:
        return False
    s = str(path).replace("\\", "/").lower()
    if any(x in s for x in [
        "data/canonical/",
        "data/raw/",
        "data/features/",
        "holdout_2020_2024",
        "validation_2015_2019",
        "discovery_2004_2014",
        "future_after_2024",
    ]):
        return False
    return "live" in s or s.startswith("panel/") or s.startswith("runtime/") or s.startswith("inputs/")

def load_state():
    state = load_json(LEDGER_STATE)
    if not isinstance(state, dict):
        state = {
            "state_version": "sig_e_shadow_detector_obsledger_v1",
            "program": PROGRAM,
            "created_utc": now_utc(),
            "detector_id": "SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0",
            "refresh_records": [],
            "near_miss_records": [],
            "shadow_events": [],
            "outcome_records": [],
        }
    for k in ["refresh_records", "near_miss_records", "shadow_events", "outcome_records"]:
        if not isinstance(state.get(k), list):
            state[k] = []
    return state

def compact_refresh_record(detector):
    check = {}
    for c in detector.get("checks", []):
        if c.get("check_id") == "REGIME":
            check = c.get("details", {}) or {}
            break
    return {
        "detector_run_id": detector.get("detector_run_id"),
        "created_utc": detector.get("created_utc"),
        "detector_status": detector.get("detector_status"),
        "status_reason": detector.get("status_reason"),
        "is_shadow_match": detector.get("is_shadow_match") is True,
        "instrument": detector.get("instrument"),
        "direction": detector.get("direction"),
        "session_bucket": check.get("session_bucket"),
        "d1_trend_state": check.get("d1_trend_state"),
        "h4_trend_state": check.get("h4_trend_state"),
        "htf_alignment": check.get("htf_alignment"),
        "volatility_state_or_d1_vol_bucket": check.get("volatility_state_or_d1_vol_bucket"),
        "range_state": check.get("range_state"),
        "tradeability_context": check.get("tradeability_context"),
        "h1_bar_open_ts_utc": (detector.get("surface_snapshot") or {}).get("h1_bar_open_ts_utc"),
        "m15_bar_open_ts_utc": (detector.get("surface_snapshot") or {}).get("m15_bar_open_ts_utc"),
        "setup_h1_open_ts_utc": detector.get("setup_h1_open_ts_utc"),
        "trigger_h1_open_ts_utc": detector.get("trigger_h1_open_ts_utc"),
        "m15_confirm_ts_utc": detector.get("m15_confirm_ts_utc"),
        "shadow_event_id": detector.get("shadow_event_id"),
    }

def near_miss_score(status):
    return {
        "REGIME_NOT_MATCHED": 1,
        "SETUP_NOT_FORMED": 2,
        "H1_TRIGGER_WAIT": 3,
        "H1_TRIGGER_NOT_CONFIRMED": 3,
        "M15_TRIGGER_WAIT": 4,
        "SHADOW_MATCH_CONFIRMED": 5,
    }.get(status, 0)

def should_record_near_miss(record):
    return record.get("detector_status") in {
        "REGIME_NOT_MATCHED",
        "SETUP_NOT_FORMED",
        "H1_TRIGGER_WAIT",
        "H1_TRIGGER_NOT_CONFIRMED",
        "M15_TRIGGER_WAIT",
        "SHADOW_MATCH_CONFIRMED",
    }

def event_from_detector(detector):
    if detector.get("detector_status") != "SHADOW_MATCH_CONFIRMED":
        return None
    event_id = detector.get("shadow_event_id")
    if not event_id:
        return None
    trigger_ts = detector.get("trigger_h1_open_ts_utc")
    end_dt = parse_dt(trigger_ts)
    observation_end = iso(end_dt + timedelta(hours=16)) if end_dt else None
    source_paths = detector.get("source_paths") or {}
    return {
        "shadow_event_id": event_id,
        "created_utc": detector.get("created_utc"),
        "instrument": "USDJPY",
        "direction": "LONG",
        "detector_status": "SHADOW_MATCH_CONFIRMED",
        "setup_h1_open_ts_utc": detector.get("setup_h1_open_ts_utc"),
        "trigger_h1_open_ts_utc": trigger_ts,
        "m15_confirm_ts_utc": detector.get("m15_confirm_ts_utc"),
        "observation_horizon_h1_bars": 16,
        "observation_end_ts_utc": observation_end,
        "outcome_status": "PENDING",
        "source_paths": {
            "h1_ohlc_path": source_paths.get("h1_ohlc_path"),
            "m15_ohlc_path": source_paths.get("m15_ohlc_path"),
            "live_source_policy": source_paths.get("live_source_policy"),
        },
        "authority": AUTHORITY,
    }

def try_close_event(event):
    if event.get("outcome_status") == "CLOSED":
        return None
    h1_path = (event.get("source_paths") or {}).get("h1_ohlc_path")
    if not path_is_live_allowed(h1_path):
        return None
    rows = normalize_ohlc(read_csv_tail(h1_path, max_tail=5000))
    if not rows:
        return None
    trigger_dt = parse_dt(event.get("trigger_h1_open_ts_utc"))
    if not trigger_dt:
        return None
    horizon_dt = trigger_dt + timedelta(hours=int(event.get("observation_horizon_h1_bars", 16)))
    trigger_bar = None
    horizon_bar = None
    highs = []
    lows = []
    for r in rows:
        if r["ts"] == trigger_dt:
            trigger_bar = r
        if r["ts"] == horizon_dt:
            horizon_bar = r
        if trigger_dt <= r["ts"] <= horizon_dt:
            highs.append(r["high"])
            lows.append(r["low"])
    if trigger_bar is None or horizon_bar is None:
        return None

    start = trigger_bar["close"]
    end = horizon_bar["close"]
    move = end - start
    mfe = max(highs) - start if highs else None
    mae = min(lows) - start if lows else None

    outcome = {
        "shadow_event_id": event.get("shadow_event_id"),
        "closed_utc": now_utc(),
        "trigger_h1_open_ts_utc": event.get("trigger_h1_open_ts_utc"),
        "observation_end_ts_utc": iso(horizon_dt),
        "direction": "LONG",
        "trigger_close": start,
        "horizon_close": end,
        "close_to_close_move": move,
        "max_favorable_excursion": mfe,
        "max_adverse_excursion": mae,
        "outcome_label": "FAVORABLE" if move > 0 else ("ADVERSE" if move < 0 else "NEUTRAL"),
        "boundary": BOUNDARY,
        "authority": AUTHORITY,
    }
    event["outcome_status"] = "CLOSED"
    event["outcome_closed_utc"] = outcome["closed_utc"]
    event["outcome_label"] = outcome["outcome_label"]
    return outcome

def aggregate(state):
    refresh = state.get("refresh_records", [])
    events = state.get("shadow_events", [])
    outcomes = state.get("outcome_records", [])

    status_counts = Counter(r.get("detector_status") for r in refresh)
    reason_counts = Counter(r.get("status_reason") for r in refresh if r.get("status_reason"))
    last_100 = refresh[-100:]
    last_100_counts = Counter(r.get("detector_status") for r in last_100)

    event_counts = Counter(e.get("outcome_status") for e in events)
    outcome_counts = Counter(o.get("outcome_label") for o in outcomes)

    return {
        "refresh_count_total": len(refresh),
        "status_counts_total": {s: status_counts.get(s, 0) for s in STATUS_ORDER if status_counts.get(s, 0)},
        "status_counts_last_100": {s: last_100_counts.get(s, 0) for s in STATUS_ORDER if last_100_counts.get(s, 0)},
        "top_status_reasons": dict(reason_counts.most_common(12)),
        "near_miss_count": len(state.get("near_miss_records", [])),
        "shadow_event_count": len(events),
        "pending_shadow_event_count": event_counts.get("PENDING", 0),
        "closed_shadow_event_count": event_counts.get("CLOSED", 0),
        "outcome_counts": dict(outcome_counts),
        "last_status": refresh[-1].get("detector_status") if refresh else None,
        "last_status_reason": refresh[-1].get("status_reason") if refresh else None,
        "last_shadow_event_id": events[-1].get("shadow_event_id") if events else None,
    }

def update_ledger():
    detector = load_json(DETECTOR_CURRENT)
    state = load_state()

    if not isinstance(detector, dict):
        result = {
            "program": PROGRAM,
            "created_utc": now_utc(),
            "build_status": "BLOCKED",
            "reason": "current detector json missing or invalid",
            "detector_current": str(DETECTOR_CURRENT),
            "authority": AUTHORITY,
            "boundary": BOUNDARY,
        }
        write_json(RUNTIME_OUT, result)
        write_json(PANEL_OUT, result)
        write_json(BUILD_OUT, result)
        return result

    record = compact_refresh_record(detector)
    run_id = record.get("detector_run_id")

    existing_run_ids = {r.get("detector_run_id") for r in state["refresh_records"] if isinstance(r, dict)}
    if run_id and run_id not in existing_run_ids:
        state["refresh_records"].append(record)

    if should_record_near_miss(record):
        near_key = run_id + "|" + str(record.get("detector_status")) if run_id else None
        existing_near = {
            str(r.get("detector_run_id")) + "|" + str(r.get("detector_status"))
            for r in state["near_miss_records"]
            if isinstance(r, dict)
        }
        if near_key and near_key not in existing_near:
            nm = dict(record)
            nm["near_miss_score"] = near_miss_score(record.get("detector_status"))
            state["near_miss_records"].append(nm)

    event = event_from_detector(detector)
    if event:
        existing_event_ids = {e.get("shadow_event_id") for e in state["shadow_events"] if isinstance(e, dict)}
        if event["shadow_event_id"] not in existing_event_ids:
            state["shadow_events"].append(event)

    # Try to close pending events using live H1 rows. No historical fallback allowed.
    existing_outcomes = {o.get("shadow_event_id") for o in state["outcome_records"] if isinstance(o, dict)}
    new_outcomes = []
    for ev in state["shadow_events"]:
        if not isinstance(ev, dict):
            continue
        if ev.get("outcome_status") == "PENDING":
            out = try_close_event(ev)
            if out and out.get("shadow_event_id") not in existing_outcomes:
                state["outcome_records"].append(out)
                existing_outcomes.add(out.get("shadow_event_id"))
                new_outcomes.append(out)

    state["refresh_records"] = state["refresh_records"][-MAX_REFRESH_RECORDS:]
    state["near_miss_records"] = sorted(
        state["near_miss_records"][-MAX_NEAR_MISS_RECORDS:],
        key=lambda r: (str(r.get("created_utc")), r.get("near_miss_score", 0))
    )
    state["shadow_events"] = state["shadow_events"][-MAX_EVENT_RECORDS:]
    state["outcome_records"] = state["outcome_records"][-MAX_EVENT_RECORDS:]
    state["last_updated_utc"] = now_utc()
    state["authority"] = AUTHORITY
    state["boundary"] = BOUNDARY

    summary = aggregate(state)

    current = {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "ledger_status": "PASS",
        "detector_id": state.get("detector_id"),
        "latest_detector_run_id": run_id,
        "latest_detector_status": record.get("detector_status"),
        "latest_status_reason": record.get("status_reason"),
        "summary": summary,
        "new_outcomes_closed_this_run": new_outcomes,
        "latest_near_miss": state["near_miss_records"][-1] if state.get("near_miss_records") else None,
        "latest_shadow_event": state["shadow_events"][-1] if state.get("shadow_events") else None,
        "latest_outcome": state["outcome_records"][-1] if state.get("outcome_records") else None,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "not_authorized": [
            "signal",
            "manual trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution",
            "auto execution",
            "memory promotion",
        ],
    }

    write_json(LEDGER_STATE, state)
    write_json(RUNTIME_OUT, current)
    write_json(PANEL_OUT, current)
    write_json(BUILD_OUT, {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "build_status": "PASS",
        "ledger_state": str(LEDGER_STATE),
        "runtime_out": str(RUNTIME_OUT),
        "panel_out": str(PANEL_OUT),
        "summary": summary,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
    })
    return current

def main():
    result = update_ledger()
    print("SIG_E_SHADOW_DETECTOR1_OBSLEDGER1_DONE")
    print("LEDGER_STATUS=" + str(result.get("ledger_status") or result.get("build_status")))
    print("LATEST_DETECTOR_STATUS=" + str(result.get("latest_detector_status")))
    print("Runtime out:", RUNTIME_OUT)
    print("Panel out:", PANEL_OUT)
    print("State:", LEDGER_STATE)

if __name__ == "__main__":
    main()
