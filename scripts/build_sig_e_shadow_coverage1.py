import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

PROGRAM = "SIG-E-SHADOW-COVERAGE1"

PORTFOLIO = Path("runtime/sig_e/shadow_portfolio_current.json")

LANE_STATES = [
    {
        "lane_id": "SIGE_SD1_USDJPY_LONDON_LONG_H1_M15",
        "display_name": "USDJPY London Long H1+M15",
        "state_path": Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json"),
    },
    {
        "lane_id": "SIGE_SD2_USDJPY_ASIA_SHORT_H1_M15_CAVEATED",
        "display_name": "USDJPY Asia Short H1+M15 Caveated",
        "state_path": Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json"),
    },
    {
        "lane_id": "SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15",
        "display_name": "EURUSD London/Overlap Prior-Day-Low Trap Long H1+M15",
        "state_path": Path("state/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json"),
    },
]

RUNTIME_OUT = Path("runtime/sig_e/shadow_coverage1_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_coverage1_current.json")
JSON_OUT = Path("outputs/_sig_e_shadow_coverage1/sig_e_shadow_coverage1_current.json")
MD_OUT = Path("outputs/_sig_e_shadow_coverage1/sig_e_shadow_coverage1_current.md")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

BOUNDARY = [
    "COVERAGE_MONITOR_ONLY",
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

DATA_STATUSES = {
    "INPUT_INSUFFICIENT",
    "FIELD_MAPPING_INCOMPLETE",
    "LIVE_OHLC_SOURCE_MISSING",
    "LIVE_H1_HISTORY_INSUFFICIENT",
    "LIVE_M15_HISTORY_INSUFFICIENT",
    "REFERENCE_LEVEL_UNAVAILABLE",
}

PROGRESS_STATUSES = {
    "H1_TRIGGER_WAIT",
    "M15_TRIGGER_WAIT",
    "M15_NO_FAILURE_POLICY_WAIT",
}

MATCH_STATUSES = {
    "SHADOW_MATCH_CONFIRMED",
    "CAVEATED_SHADOW_MATCH_CONFIRMED",
}

def utcnow():
    return datetime.utcnow().replace(microsecond=0)

def now():
    return utcnow().isoformat() + "Z"

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
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
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

def status_to_gate(record):
    status = str(record.get("detector_status") or "UNKNOWN")
    reason = record.get("status_reason")

    gate = {
        "status": status,
        "reason": reason,
        "freshness_gate": "PASS",
        "session_gate": "UNKNOWN",
        "regime_gate": "UNKNOWN",
        "data_gate": "UNKNOWN",
        "setup_gate": "UNKNOWN",
        "h1_trigger_gate": "UNKNOWN",
        "m15_confirm_gate": "UNKNOWN",
        "shadow_match_gate": "FAIL",
        "terminal_stage": "UNKNOWN",
        "eligible_for_setup_eval": False,
        "eligible_for_trigger_eval": False,
        "eligible_for_match_eval": False,
    }

    if status == "DATA_STALE":
        gate.update({
            "freshness_gate": "FAIL",
            "terminal_stage": "FRESHNESS_FAIL",
        })
    elif status == "SESSION_NOT_MATCHED":
        gate.update({
            "session_gate": "FAIL",
            "terminal_stage": "SESSION_FAIL",
        })
    elif status == "REGIME_NOT_MATCHED":
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "FAIL",
            "terminal_stage": "REGIME_FAIL",
        })
    elif status in DATA_STATUSES:
        gate.update({
            "session_gate": "PASS_OR_UNKNOWN",
            "regime_gate": "PASS_OR_UNKNOWN",
            "data_gate": "FAIL",
            "terminal_stage": "DATA_OR_REFERENCE_FAIL",
        })
    elif status == "SETUP_NOT_FORMED":
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "PASS",
            "data_gate": "PASS",
            "setup_gate": "FAIL",
            "terminal_stage": "SETUP_FAIL",
            "eligible_for_setup_eval": True,
        })
    elif status in {"H1_TRIGGER_WAIT"}:
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "PASS",
            "data_gate": "PASS",
            "setup_gate": "PASS_CURRENT_BAR_WAIT",
            "h1_trigger_gate": "WAIT",
            "terminal_stage": "H1_TRIGGER_WAIT",
            "eligible_for_setup_eval": True,
            "eligible_for_trigger_eval": True,
        })
    elif status == "H1_TRIGGER_NOT_CONFIRMED":
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "PASS",
            "data_gate": "PASS",
            "setup_gate": "PASS",
            "h1_trigger_gate": "FAIL",
            "terminal_stage": "H1_TRIGGER_FAIL",
            "eligible_for_setup_eval": True,
            "eligible_for_trigger_eval": True,
        })
    elif status in {"M15_TRIGGER_WAIT", "M15_NO_FAILURE_POLICY_WAIT", "M15_FAILURE_BLOCKED"}:
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "PASS",
            "data_gate": "PASS",
            "setup_gate": "PASS",
            "h1_trigger_gate": "PASS_OR_WAIT",
            "m15_confirm_gate": "WAIT_OR_FAIL",
            "terminal_stage": "M15_CONFIRM_WAIT_OR_FAIL",
            "eligible_for_setup_eval": True,
            "eligible_for_trigger_eval": True,
            "eligible_for_match_eval": True,
        })
    elif status in MATCH_STATUSES:
        gate.update({
            "session_gate": "PASS",
            "regime_gate": "PASS",
            "data_gate": "PASS",
            "setup_gate": "PASS",
            "h1_trigger_gate": "PASS",
            "m15_confirm_gate": "PASS",
            "shadow_match_gate": "PASS",
            "terminal_stage": "SHADOW_MATCH",
            "eligible_for_setup_eval": True,
            "eligible_for_trigger_eval": True,
            "eligible_for_match_eval": True,
        })
    else:
        gate.update({
            "terminal_stage": "UNKNOWN_OR_UNMAPPED",
        })

    return gate

def filter_records(records, cutoff):
    out = []
    for r in records:
        t = parse_dt(r.get("created_utc") or r.get("detector_created_utc"))
        if t and t >= cutoff:
            out.append(r)
    return out

def summarize_window(records):
    status_counts = Counter()
    reason_counts = Counter()
    stage_counts = Counter()
    gate_counts = {
        "freshness_gate": Counter(),
        "session_gate": Counter(),
        "regime_gate": Counter(),
        "data_gate": Counter(),
        "setup_gate": Counter(),
        "h1_trigger_gate": Counter(),
        "m15_confirm_gate": Counter(),
        "shadow_match_gate": Counter(),
    }

    eligible_setup = 0
    eligible_trigger = 0
    eligible_match = 0
    matches = 0

    gate_records = []
    for r in records:
        status = str(r.get("detector_status") or "UNKNOWN")
        status_counts[status] += 1
        if r.get("status_reason"):
            reason_counts[str(r.get("status_reason"))] += 1

        g = status_to_gate(r)
        stage_counts[g["terminal_stage"]] += 1
        for key in gate_counts:
            gate_counts[key][g[key]] += 1
        if g["eligible_for_setup_eval"]:
            eligible_setup += 1
        if g["eligible_for_trigger_eval"]:
            eligible_trigger += 1
        if g["eligible_for_match_eval"]:
            eligible_match += 1
        if g["shadow_match_gate"] == "PASS":
            matches += 1

        gate_records.append({
            "created_utc": r.get("created_utc"),
            "detector_created_utc": r.get("detector_created_utc"),
            "detector_status": status,
            "status_reason": r.get("status_reason"),
            "session_bucket": r.get("session_bucket"),
            "d1_trend_state": r.get("d1_trend_state"),
            "h4_trend_state": r.get("h4_trend_state"),
            "htf_alignment": r.get("htf_alignment"),
            "volatility_state_or_d1_vol_bucket": r.get("volatility_state_or_d1_vol_bucket"),
            "terminal_stage": g["terminal_stage"],
            "gate_snapshot": g,
        })

    n = len(records)
    def pct(x):
        return None if n == 0 else round((x / n) * 100.0, 2)

    return {
        "record_count": n,
        "status_counts": dict(status_counts),
        "top_reasons": dict(reason_counts.most_common(12)),
        "terminal_stage_counts": dict(stage_counts),
        "gate_counts": {k: dict(v) for k, v in gate_counts.items()},
        "eligible_for_setup_eval_count": eligible_setup,
        "eligible_for_trigger_eval_count": eligible_trigger,
        "eligible_for_match_eval_count": eligible_match,
        "shadow_match_count": matches,
        "setup_eval_rate_pct": pct(eligible_setup),
        "trigger_eval_rate_pct": pct(eligible_trigger),
        "match_eval_rate_pct": pct(eligible_match),
        "shadow_match_rate_pct": pct(matches),
        "latest_gate_records": gate_records[-10:],
    }

def classify_lane_health(lane_summary):
    last7 = lane_summary.get("windows", {}).get("last_7d", {})
    n = last7.get("record_count", 0)
    stages = last7.get("terminal_stage_counts", {})
    if n == 0:
        return {
            "health": "NO_RECENT_RECORDS",
            "interpretation": "Lane is not being observed recently; workflow/persistence should be checked.",
        }

    session_fail = stages.get("SESSION_FAIL", 0)
    regime_fail = stages.get("REGIME_FAIL", 0)
    setup_fail = stages.get("SETUP_FAIL", 0)
    data_fail = stages.get("DATA_OR_REFERENCE_FAIL", 0)
    matches = stages.get("SHADOW_MATCH", 0)

    if data_fail / n >= 0.5:
        return {
            "health": "DATA_OR_REFERENCE_BLOCKED",
            "interpretation": "Too many observations fail data/reference gates; fix data source or reference extraction before adding more lanes.",
        }
    if session_fail / n >= 0.7:
        return {
            "health": "SESSION_TOO_NARROW_OR_OUT_OF_SESSION",
            "interpretation": "Most observations are outside this lane's session. Consider a session variant only if historically justified.",
        }
    if regime_fail / n >= 0.7:
        return {
            "health": "REGIME_TOO_NARROW_OR_MARKET_NOT_SUPPORTIVE",
            "interpretation": "The lane is mostly rejected at regime gate. Do not loosen without historical evidence.",
        }
    if setup_fail / n >= 0.5:
        return {
            "health": "REGIME_PASS_SETUP_RARE",
            "interpretation": "The lane often reaches setup evaluation but setup is rare. This is normal for narrow shadow detectors.",
        }
    if matches > 0:
        return {
            "health": "HAS_SHADOW_EVENTS",
            "interpretation": "Lane has produced at least one shadow event; outcome tracking should be reviewed.",
        }
    return {
        "health": "OBSERVING_NORMAL_NON_MATCH",
        "interpretation": "Lane is being observed and non-match states appear normal.",
    }

def summarize_lane(lane_cfg, tnow):
    state = load_json(lane_cfg["state_path"])
    if not isinstance(state, dict):
        return {
            "lane_id": lane_cfg["lane_id"],
            "display_name": lane_cfg["display_name"],
            "state_file": str(lane_cfg["state_path"]),
            "state_loaded": False,
            "health": {
                "health": "STATE_MISSING",
                "interpretation": "State file missing; lane is not producing coverage history.",
            },
            "windows": {},
        }

    refresh = state.get("refresh_records") if isinstance(state.get("refresh_records"), list) else []
    windows = {
        "last_24h": tnow - timedelta(hours=24),
        "last_7d": tnow - timedelta(days=7),
        "all_time": datetime.min,
    }

    window_summaries = {
        name: summarize_window(filter_records(refresh, cutoff))
        for name, cutoff in windows.items()
    }

    lane = {
        "lane_id": lane_cfg["lane_id"],
        "display_name": lane_cfg["display_name"],
        "state_file": str(lane_cfg["state_path"]),
        "state_loaded": True,
        "detector_id": state.get("detector_id"),
        "source_spec_id": state.get("source_spec_id"),
        "refresh_count_total": len(refresh),
        "last_updated_utc": state.get("last_updated_utc"),
        "windows": window_summaries,
    }
    lane["health"] = classify_lane_health(lane)
    return lane

def build_markdown(report):
    lines = []
    lines.append("# SIG-E Shadow Coverage Monitor")
    lines.append("")
    lines.append(f"- created_utc: `{report.get('created_utc')}`")
    lines.append(f"- coverage_status: `{report.get('coverage_status')}`")
    lines.append(f"- portfolio_status: `{report.get('portfolio_status')}`")
    lines.append(f"- lane_count: `{report.get('summary', {}).get('lane_count')}`")
    lines.append(f"- total_refresh_records_all_time: `{report.get('summary', {}).get('total_refresh_records_all_time')}`")
    lines.append("")
    lines.append("Boundary: coverage/dropoff monitor only; not signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.")
    lines.append("")

    for lane in report.get("lanes", []):
        lines.append(f"## {lane.get('display_name')}")
        lines.append("")
        lines.append(f"- lane_id: `{lane.get('lane_id')}`")
        lines.append(f"- health: `{lane.get('health', {}).get('health')}`")
        lines.append(f"- interpretation: {lane.get('health', {}).get('interpretation')}")
        lines.append(f"- refresh_count_total: `{lane.get('refresh_count_total')}`")
        lines.append("")
        for win in ["last_24h", "last_7d", "all_time"]:
            w = lane.get("windows", {}).get(win, {})
            lines.append(f"### {win}")
            lines.append(f"- record_count: `{w.get('record_count')}`")
            lines.append(f"- terminal_stage_counts: `{json.dumps(w.get('terminal_stage_counts'), ensure_ascii=False)}`")
            lines.append(f"- eligible_for_setup_eval_count: `{w.get('eligible_for_setup_eval_count')}`")
            lines.append(f"- shadow_match_count: `{w.get('shadow_match_count')}`")
            lines.append("")
    return "\n".join(lines)

def main():
    tnow = utcnow()
    portfolio = load_json(PORTFOLIO) or {}
    lanes = [summarize_lane(cfg, tnow) for cfg in LANE_STATES]

    missing = [l for l in lanes if not l.get("state_loaded")]
    total_all = sum(l.get("refresh_count_total") or 0 for l in lanes if l.get("state_loaded"))
    total_24 = sum(l.get("windows", {}).get("last_24h", {}).get("record_count", 0) for l in lanes)
    total_matches = sum(l.get("windows", {}).get("all_time", {}).get("shadow_match_count", 0) for l in lanes)

    if missing:
        coverage_status = "ATTENTION_MISSING_LANE_STATE"
    elif total_24 == 0:
        coverage_status = "ATTENTION_NO_RECENT_COVERAGE_RECORDS"
    else:
        coverage_status = "OK_COVERAGE_MONITOR_READY"

    report = {
        "program": PROGRAM,
        "created_utc": now(),
        "coverage_status": coverage_status,
        "portfolio_status": portfolio.get("portfolio_status"),
        "portfolio_summary": portfolio.get("summary"),
        "summary": {
            "lane_count": len(lanes),
            "state_loaded_count": len([l for l in lanes if l.get("state_loaded")]),
            "total_refresh_records_last_24h": total_24,
            "total_refresh_records_all_time": total_all,
            "total_shadow_matches_all_time": total_matches,
            "active_shadow_match_count": (portfolio.get("summary") or {}).get("active_shadow_match_count"),
            "data_or_field_attention_count": (portfolio.get("summary") or {}).get("data_or_field_attention_count"),
        },
        "lanes": lanes,
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
        "next_allowed_use": "LIVE_SHADOW_COVERAGE_REVIEW_ONLY",
    }

    write_json(RUNTIME_OUT, report)
    write_json(PANEL_OUT, report)
    write_json(JSON_OUT, report)
    write_text(MD_OUT, build_markdown(report))

    print("SIG_E_SHADOW_COVERAGE1_DONE")
    print("COVERAGE_STATUS=" + coverage_status)
    print("LANE_COUNT=" + str(len(lanes)))
    print("TOTAL_REFRESH_24H=" + str(total_24))
    print("TOTAL_REFRESH_ALL=" + str(total_all))

if __name__ == "__main__":
    main()
