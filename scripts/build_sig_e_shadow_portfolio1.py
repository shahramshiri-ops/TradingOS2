import json
from pathlib import Path
from datetime import datetime
from collections import Counter

PROGRAM = "SIG-E-SHADOW-PORTFOLIO1"

RUNTIME_OUT = Path("runtime/sig_e/shadow_portfolio_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_portfolio_status_current.json")
BUILD_OUT = Path("outputs/_sig_e_shadow_portfolio1/sig_e_shadow_portfolio1_build_result.json")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False
}

BOUNDARY = [
    "PORTFOLIO_OBSERVATION_ONLY",
    "SHADOW_RESEARCH_ONLY",
    "NOT_SIGNAL",
    "NO_TRADE_PROPOSAL",
    "NO_ENTRY_STOP_TARGET",
    "NO_RISK_OR_POSITION_SIZING",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_EXECUTION",
    "NO_MEMORY_PROMOTION",
    "NO_RULE_REWRITE"
]

LANES = [
    {
        "lane_id": "SIGE_SD1_USDJPY_LONDON_LONG_H1_M15",
        "display_name": "USDJPY London Long H1+M15",
        "classification": "PRIMARY_SHADOW_OBSERVATION",
        "instrument": "USDJPY",
        "direction": "LONG",
        "detector_file": Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json"),
        "ledger_file": Path("runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json"),
        "expected_shadow_match_statuses": ["SHADOW_MATCH_CONFIRMED"],
    },
    {
        "lane_id": "SIGE_SD2_USDJPY_ASIA_SHORT_H1_M15_CAVEATED",
        "display_name": "USDJPY Asia Short H1+M15 Caveated",
        "classification": "CAVEATED_OBSERVATION_ONLY",
        "instrument": "USDJPY",
        "direction": "SHORT",
        "detector_file": Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_current.json"),
        "ledger_file": Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json"),
        "expected_shadow_match_statuses": ["CAVEATED_SHADOW_MATCH_CONFIRMED"],
    },
    {
        "lane_id": "SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15",
        "display_name": "EURUSD London/Overlap Prior-Day-Low Trap Long H1+M15",
        "classification": "PRIMARY_SHADOW_OBSERVATION",
        "instrument": "EURUSD",
        "direction": "LONG",
        "detector_file": Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json"),
        "ledger_file": Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json"),
        "expected_shadow_match_statuses": ["SHADOW_MATCH_CONFIRMED"],
    },]

DATA_OR_FIELD_STATUSES = {
    "DATA_STALE",
    "LIVE_OHLC_SOURCE_MISSING",
    "FIELD_MAPPING_INCOMPLETE",
    "INPUT_INSUFFICIENT",
    "LIVE_H1_HISTORY_INSUFFICIENT",
    "LIVE_M15_HISTORY_INSUFFICIENT",
}

NORMAL_NON_MATCH_STATUSES = {
    "REGIME_NOT_MATCHED",
    "SESSION_NOT_MATCHED",
    "SETUP_NOT_FORMED",
    "H1_TRIGGER_NOT_CONFIRMED",
    "M15_FAILURE_BLOCKED",
}

PROGRESS_STATUSES = {
    "H1_TRIGGER_WAIT",
    "M15_TRIGGER_WAIT",
    "M15_NO_FAILURE_POLICY_WAIT",
}

def now_utc():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

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

def false_authority_ok(obj):
    auth = obj.get("authority", {}) if isinstance(obj, dict) else {}
    return all(auth.get(k) is False for k in AUTHORITY.keys())

def summarize_lane(lane):
    detector = load_json(lane["detector_file"])
    ledger = load_json(lane["ledger_file"])

    detector_missing = detector is None
    ledger_missing = ledger is None

    detector_status = None
    detector_reason = None
    is_shadow_match = False
    is_signal = None
    is_trade_proposal = None
    detector_run_id = None
    created_utc = None
    surface_snapshot = None
    checks = []
    detector_authority_ok = False
    data_counts = None
    source_paths = None
    ohlc_source_diagnostics = None

    if isinstance(detector, dict):
        detector_status = detector.get("detector_status")
        detector_reason = detector.get("status_reason")
        is_shadow_match = detector.get("is_shadow_match") is True
        is_signal = detector.get("is_signal")
        is_trade_proposal = detector.get("is_trade_proposal")
        detector_run_id = detector.get("detector_run_id")
        created_utc = detector.get("created_utc")
        surface_snapshot = detector.get("surface_snapshot")
        checks = detector.get("checks") if isinstance(detector.get("checks"), list) else []
        detector_authority_ok = false_authority_ok(detector)
        data_counts = detector.get("data_counts")
        source_paths = detector.get("source_paths")
        ohlc_source_diagnostics = detector.get("ohlc_source_diagnostics")

    ledger_summary = {}
    ledger_status = None
    ledger_authority_ok = False
    latest_near_miss = None
    latest_shadow_event = None
    latest_outcome = None

    if isinstance(ledger, dict):
        ledger_status = ledger.get("ledger_status")
        ledger_summary = ledger.get("summary") if isinstance(ledger.get("summary"), dict) else {}
        ledger_authority_ok = false_authority_ok(ledger)
        latest_near_miss = ledger.get("latest_near_miss")
        latest_shadow_event = ledger.get("latest_shadow_event")
        latest_outcome = ledger.get("latest_outcome")

    active_match = detector_status in lane["expected_shadow_match_statuses"] or is_shadow_match
    caveated = lane["classification"] == "CAVEATED_OBSERVATION_ONLY"

    attention = []
    if detector_missing:
        attention.append("DETECTOR_CURRENT_MISSING")
    if ledger_missing:
        attention.append("OBSLEDGER_CURRENT_MISSING")
    if not detector_missing and not detector_authority_ok:
        attention.append("DETECTOR_AUTHORITY_CHECK_FAILED")
    if not ledger_missing and not ledger_authority_ok:
        attention.append("LEDGER_AUTHORITY_CHECK_FAILED")
    if active_match:
        attention.append("SHADOW_MATCH_ACTIVE_CAVEATED" if caveated else "SHADOW_MATCH_ACTIVE_PRIMARY")
    elif detector_status in PROGRESS_STATUSES:
        attention.append("WATCH_PROGRESSING_THROUGH_TRIGGER_CHAIN")
    elif detector_status in DATA_OR_FIELD_STATUSES:
        attention.append("DATA_OR_FIELD_ATTENTION")
    elif detector_status in NORMAL_NON_MATCH_STATUSES:
        attention.append("NO_ACTION_NORMAL_NON_MATCH")

    return {
        "lane_id": lane["lane_id"],
        "display_name": lane["display_name"],
        "classification": lane["classification"],
        "instrument": lane["instrument"],
        "direction": lane["direction"],
        "detector_file": str(lane["detector_file"]),
        "ledger_file": str(lane["ledger_file"]),
        "detector_file_loaded": not detector_missing,
        "ledger_file_loaded": not ledger_missing,
        "detector_run_id": detector_run_id,
        "detector_created_utc": created_utc,
        "detector_status": detector_status,
        "status_reason": detector_reason,
        "is_shadow_match": bool(active_match),
        "is_caveated": caveated,
        "is_signal": is_signal,
        "is_trade_proposal": is_trade_proposal,
        "surface_snapshot": surface_snapshot,
        "data_counts": data_counts,
        "source_paths": source_paths,
        "ohlc_source_diagnostics": ohlc_source_diagnostics,
        "checks": checks,
        "ledger_status": ledger_status,
        "ledger_summary": ledger_summary,
        "latest_near_miss": latest_near_miss,
        "latest_shadow_event": latest_shadow_event,
        "latest_outcome": latest_outcome,
        "detector_authority_ok": detector_authority_ok,
        "ledger_authority_ok": ledger_authority_ok,
        "attention_flags": attention,
    }

def aggregate(lanes):
    status_counts = Counter(x.get("detector_status") or "MISSING" for x in lanes)
    classification_counts = Counter(x.get("classification") for x in lanes)

    active = [x for x in lanes if x.get("is_shadow_match") is True]
    active_primary = [x for x in active if not x.get("is_caveated")]
    active_caveated = [x for x in active if x.get("is_caveated")]

    data_attention = [
        x for x in lanes
        if any(f in x.get("attention_flags", []) for f in ["DATA_OR_FIELD_ATTENTION", "DETECTOR_CURRENT_MISSING", "OBSLEDGER_CURRENT_MISSING"])
    ]

    total_refresh = 0
    total_near_miss = 0
    total_shadow_events = 0
    total_pending = 0
    total_closed = 0
    outcome_counts = Counter()

    for x in lanes:
        summary = x.get("ledger_summary") or {}
        total_refresh += int(summary.get("refresh_count_total") or 0)
        total_near_miss += int(summary.get("near_miss_count") or 0)
        total_shadow_events += int(summary.get("shadow_event_count") or 0)
        total_pending += int(summary.get("pending_shadow_event_count") or 0)
        total_closed += int(summary.get("closed_shadow_event_count") or 0)
        oc = summary.get("outcome_counts")
        if isinstance(oc, dict):
            for k, v in oc.items():
                try:
                    outcome_counts[k] += int(v)
                except Exception:
                    pass

    if data_attention:
        portfolio_status = "ATTENTION_DATA_OR_FIELD"
    elif active_primary:
        portfolio_status = "PRIMARY_SHADOW_MATCH_ACTIVE_REVIEW_ONLY"
    elif active_caveated:
        portfolio_status = "CAVEATED_SHADOW_MATCH_ACTIVE_REVIEW_ONLY"
    else:
        portfolio_status = "NO_ACTIVE_SHADOW_MATCH"

    return {
        "portfolio_status": portfolio_status,
        "detector_count": len(lanes),
        "detector_status_counts": dict(status_counts),
        "classification_counts": dict(classification_counts),
        "active_shadow_match_count": len(active),
        "active_primary_shadow_match_count": len(active_primary),
        "active_caveated_shadow_match_count": len(active_caveated),
        "data_or_field_attention_count": len(data_attention),
        "total_refresh_records": total_refresh,
        "total_near_misses": total_near_miss,
        "total_shadow_events": total_shadow_events,
        "total_pending_shadow_events": total_pending,
        "total_closed_shadow_events": total_closed,
        "portfolio_outcome_counts": dict(outcome_counts),
        "lanes_requiring_attention": [
            {"lane_id": x["lane_id"], "flags": x.get("attention_flags", []), "status": x.get("detector_status")}
            for x in lanes if x.get("attention_flags")
        ],
    }

def main():
    lane_summaries = [summarize_lane(l) for l in LANES]
    summary = aggregate(lane_summaries)

    current = {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "portfolio_status": summary["portfolio_status"],
        "summary": summary,
        "lanes": lane_summaries,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "not_authorized": [
            "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
            "broker/execution", "auto execution", "memory promotion", "rule rewrite"
        ],
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_REVIEW_ONLY",
    }

    write_json(RUNTIME_OUT, current)
    write_json(PANEL_OUT, current)
    write_json(BUILD_OUT, {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "build_status": "PASS",
        "portfolio_status": summary["portfolio_status"],
        "runtime_out": str(RUNTIME_OUT),
        "panel_out": str(PANEL_OUT),
        "summary": summary,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
    })

    print("SIG_E_SHADOW_PORTFOLIO1_DONE")
    print("PORTFOLIO_STATUS=" + str(summary["portfolio_status"]))
    print("DETECTOR_COUNT=" + str(summary["detector_count"]))
    print("ACTIVE_SHADOW_MATCH_COUNT=" + str(summary["active_shadow_match_count"]))

if __name__ == "__main__":
    main()

