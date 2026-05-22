import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

PROGRAM = "SIG-E-SHADOW-OBSREPORT1"

PORTFOLIO = Path("runtime/sig_e/shadow_portfolio_current.json")
LANE_STATES = [
    Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json"),
    Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json"),
    Path("state/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json"),
]

RUNTIME_OUT = Path("runtime/sig_e/shadow_observation_report_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_observation_report_current.json")
JSON_OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.json")
MD_OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.md")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

BOUNDARY = [
    "OBSERVATION_REPORT_ONLY",
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

def now_dt():
    return datetime.utcnow().replace(microsecond=0)

def now():
    return now_dt().isoformat() + "Z"

def parse_dt(x):
    if not x:
        return None
    s = str(x).strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception:
        return None

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

def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def lane_name_from_state(state, fallback):
    detector_id = state.get("detector_id") or fallback
    if "ASIA_SHORT" in detector_id:
        return "USDJPY Asia Short H1+M15 Caveated"
    if "LONDON_LONG" in detector_id:
        return "USDJPY London Long H1+M15"
    return detector_id

def bucket_records(records, cutoff):
    out = []
    for r in records:
        t = parse_dt(r.get("created_utc") or r.get("detector_created_utc"))
        if t and t >= cutoff:
            out.append(r)
    return out

def summarize_records(records):
    status_counts = Counter(r.get("detector_status") or "UNKNOWN" for r in records)
    reason_counts = Counter(r.get("status_reason") for r in records if r.get("status_reason"))
    shadow_matches = [r for r in records if r.get("is_shadow_match") is True or str(r.get("detector_status", "")).endswith("SHADOW_MATCH_CONFIRMED")]
    nearish = [r for r in records if r.get("detector_status") in {
        "REGIME_NOT_MATCHED",
        "SETUP_NOT_FORMED",
        "H1_TRIGGER_WAIT",
        "H1_TRIGGER_NOT_CONFIRMED",
        "M15_TRIGGER_WAIT",
        "M15_NO_FAILURE_POLICY_WAIT",
        "M15_FAILURE_BLOCKED",
        "SHADOW_MATCH_CONFIRMED",
        "CAVEATED_SHADOW_MATCH_CONFIRMED",
    }]
    return {
        "record_count": len(records),
        "status_counts": dict(status_counts),
        "top_reasons": dict(reason_counts.most_common(10)),
        "shadow_match_count": len(shadow_matches),
        "near_miss_or_progress_count": len(nearish),
        "last_record": records[-1] if records else None,
    }

def summarize_lane_state(path, state, tnow):
    refresh = state.get("refresh_records") if isinstance(state.get("refresh_records"), list) else []
    near = state.get("near_miss_records") if isinstance(state.get("near_miss_records"), list) else []
    events = state.get("shadow_events") if isinstance(state.get("shadow_events"), list) else []
    outcomes = state.get("outcome_records") if isinstance(state.get("outcome_records"), list) else []

    windows = {
        "last_24h": tnow - timedelta(hours=24),
        "last_7d": tnow - timedelta(days=7),
        "all_time": datetime.min,
    }

    window_summaries = {}
    for name, cutoff in windows.items():
        window_summaries[name] = summarize_records(bucket_records(refresh, cutoff))

    event_status_counts = Counter(e.get("outcome_status") for e in events)
    outcome_counts = Counter(o.get("outcome_label") for o in outcomes)

    return {
        "state_file": str(path),
        "detector_id": state.get("detector_id"),
        "source_spec_id": state.get("source_spec_id"),
        "display_name": lane_name_from_state(state, path.stem),
        "refresh_count_total": len(refresh),
        "near_miss_count_total": len(near),
        "shadow_event_count_total": len(events),
        "pending_shadow_event_count": event_status_counts.get("PENDING", 0),
        "closed_shadow_event_count": event_status_counts.get("CLOSED", 0),
        "outcome_counts_total": dict(outcome_counts),
        "last_updated_utc": state.get("last_updated_utc"),
        "windows": window_summaries,
        "latest_near_miss": near[-1] if near else None,
        "latest_shadow_event": events[-1] if events else None,
        "latest_outcome": outcomes[-1] if outcomes else None,
    }

def build_markdown(report):
    lines = []
    lines.append("# SIG-E Shadow Observation Report")
    lines.append("")
    lines.append(f"- created_utc: `{report.get('created_utc')}`")
    lines.append(f"- report_status: `{report.get('report_status')}`")
    lines.append(f"- portfolio_status: `{report.get('portfolio_status')}`")
    lines.append(f"- detector_count: `{report.get('portfolio_summary', {}).get('detector_count')}`")
    lines.append(f"- active_shadow_match_count: `{report.get('portfolio_summary', {}).get('active_shadow_match_count')}`")
    lines.append(f"- total_refresh_records: `{report.get('portfolio_summary', {}).get('total_refresh_records')}`")
    lines.append("")
    lines.append("Boundary: observation/report only; not signal, not trade proposal, no entry/stop/target, no risk sizing, no broker/execution.")
    lines.append("")

    for lane in report.get("lanes", []):
        lines.append(f"## {lane.get('display_name')}")
        lines.append("")
        lines.append(f"- detector_id: `{lane.get('detector_id')}`")
        lines.append(f"- refresh_count_total: `{lane.get('refresh_count_total')}`")
        lines.append(f"- near_miss_count_total: `{lane.get('near_miss_count_total')}`")
        lines.append(f"- shadow_event_count_total: `{lane.get('shadow_event_count_total')}`")
        lines.append(f"- pending_shadow_event_count: `{lane.get('pending_shadow_event_count')}`")
        lines.append(f"- closed_shadow_event_count: `{lane.get('closed_shadow_event_count')}`")
        lines.append("")
        for win_name, win in lane.get("windows", {}).items():
            lines.append(f"### {win_name}")
            lines.append(f"- record_count: `{win.get('record_count')}`")
            lines.append(f"- shadow_match_count: `{win.get('shadow_match_count')}`")
            lines.append(f"- near_miss_or_progress_count: `{win.get('near_miss_or_progress_count')}`")
            lines.append(f"- status_counts: `{json.dumps(win.get('status_counts'), ensure_ascii=False)}`")
            lines.append("")
    return "\n".join(lines)

def main():
    tnow = now_dt()
    portfolio = load_json(PORTFOLIO) or {}

    lane_reports = []
    missing_states = []
    for p in LANE_STATES:
        state = load_json(p)
        if isinstance(state, dict):
            lane_reports.append(summarize_lane_state(p, state, tnow))
        else:
            missing_states.append(str(p))

    total_24h = sum(l.get("windows", {}).get("last_24h", {}).get("record_count", 0) for l in lane_reports)
    total_7d = sum(l.get("windows", {}).get("last_7d", {}).get("record_count", 0) for l in lane_reports)
    total_shadow_events = sum(l.get("shadow_event_count_total", 0) for l in lane_reports)

    if missing_states:
        report_status = "ATTENTION_MISSING_STATE"
    elif total_24h == 0:
        report_status = "ATTENTION_NO_REFRESH_RECORDS_LAST_24H"
    else:
        report_status = "OK_OBSERVATION_REPORT_READY"

    report = {
        "program": PROGRAM,
        "created_utc": now(),
        "report_status": report_status,
        "portfolio_status": portfolio.get("portfolio_status"),
        "portfolio_summary": portfolio.get("summary"),
        "missing_state_files": missing_states,
        "summary": {
            "lane_count": len(lane_reports),
            "total_refresh_records_last_24h": total_24h,
            "total_refresh_records_last_7d": total_7d,
            "total_shadow_events_all_time": total_shadow_events,
            "active_shadow_match_count": (portfolio.get("summary") or {}).get("active_shadow_match_count"),
            "data_or_field_attention_count": (portfolio.get("summary") or {}).get("data_or_field_attention_count"),
        },
        "lanes": lane_reports,
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
            "rule rewrite",
        ],
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_REVIEW_ONLY",
    }

    write_json(RUNTIME_OUT, report)
    write_json(PANEL_OUT, report)
    write_json(JSON_OUT, report)
    write_text(MD_OUT, build_markdown(report))

    print("SIG_E_SHADOW_OBSREPORT1_DONE")
    print("REPORT_STATUS=" + report_status)
    print("LANE_COUNT=" + str(len(lane_reports)))
    print("TOTAL_REFRESH_24H=" + str(total_24h))
    print("TOTAL_SHADOW_EVENTS=" + str(total_shadow_events))

if __name__ == "__main__":
    main()

