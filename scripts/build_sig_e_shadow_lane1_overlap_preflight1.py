import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

PROGRAM = "SIG-E-SHADOW-LANE1-OVERLAP-PREFLIGHT1"

LANE1_STATE = Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json")
PORTFOLIO = Path("runtime/sig_e/shadow_portfolio_current.json")
COVERAGE = Path("runtime/sig_e/shadow_coverage1_current.json")

RUNTIME_OUT = Path("runtime/sig_e/shadow_lane1_overlap_preflight_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_lane1_overlap_preflight_current.json")
JSON_OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.json")
MD_OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.md")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
    "lane_rule_change_authorized": False,
    "detector_change_authorized": False,
}

BOUNDARY = [
    "PREFLIGHT_ONLY",
    "WHAT_IF_SESSION_GATE_ONLY",
    "NO_DETECTOR_RULE_CHANGE",
    "NO_PORTFOLIO_LANE_CHANGE",
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

def filter_records(records, cutoff):
    out = []
    for r in records:
        t = parse_dt(r.get("created_utc") or r.get("detector_created_utc"))
        if t and t >= cutoff:
            out.append(r)
    return out

def norm_dir(x):
    s = str(x or "").upper()
    if s in ("UP", "BULL", "BULLISH", "LONG", "1") or "UP" in s or "BULL" in s:
        return "UP"
    if s in ("DOWN", "BEAR", "BEARISH", "SHORT", "-1") or "DOWN" in s or "BEAR" in s:
        return "DOWN"
    if "NEUTRAL" in s:
        return "NEUTRAL"
    return s

def lane1_regime_preflight_pass(record):
    d1 = norm_dir(record.get("d1_trend_state"))
    h4 = norm_dir(record.get("h4_trend_state"))
    htf = str(record.get("htf_alignment") or "").upper()
    vol = str(record.get("volatility_state_or_d1_vol_bucket") or "").upper()

    alignment_ok = (
        (d1 == "UP" and h4 == "UP") or
        ("ALIGNED_UP" in htf)
    )
    vol_known = vol not in ("", "UNKNOWN", "NONE", "NULL")
    vol_ok = vol in {"LOW", "NORMAL", "MIXED"} if vol_known else False

    return alignment_ok and vol_ok, {
        "d1_trend_state": d1,
        "h4_trend_state": h4,
        "htf_alignment": htf,
        "volatility_state_or_d1_vol_bucket": vol,
        "alignment_ok": alignment_ok,
        "vol_known": vol_known,
        "vol_ok": vol_ok,
    }

def is_overlap_session_reject(record):
    return (
        str(record.get("detector_status") or "") == "SESSION_NOT_MATCHED" and
        str(record.get("status_reason") or "") == "session_not_london" and
        str(record.get("session_bucket") or "").upper() == "LONDON_NY_OVERLAP"
    )

def summarize_window(records):
    status_counts = Counter(str(r.get("detector_status") or "UNKNOWN") for r in records)
    session_counts = Counter(str(r.get("session_bucket") or "UNKNOWN") for r in records)

    overlap_rejects = [r for r in records if is_overlap_session_reject(r)]
    preflight_pass = []
    preflight_fail = []
    for r in overlap_rejects:
        ok, meta = lane1_regime_preflight_pass(r)
        item = {
            "created_utc": r.get("created_utc"),
            "detector_created_utc": r.get("detector_created_utc"),
            "session_bucket": r.get("session_bucket"),
            "detector_status": r.get("detector_status"),
            "status_reason": r.get("status_reason"),
            "preflight_regime_pass_if_overlap_allowed": ok,
            "regime_snapshot": meta,
            "important_caveat": "This is a session/regime what-if only. It does not evaluate setup, H1 trigger, M15 confirm, or shadow outcome."
        }
        if ok:
            preflight_pass.append(item)
        else:
            preflight_fail.append(item)

    n = len(records)
    o = len(overlap_rejects)
    p = len(preflight_pass)

    def pct(x, denom):
        return None if denom == 0 else round((x / denom) * 100.0, 2)

    if o < 5:
        verdict = "WAIT_MORE_OVERLAP_OBSERVATIONS"
        interpretation = "Too few overlap session rejects to justify an overlap variant decision."
    elif p / o >= 0.60:
        verdict = "OVERLAP_VARIANT_PREFLIGHT_POSITIVE"
        interpretation = "Many rejected overlap records appear regime-eligible under Lane1-style long conditions. A separate Lane1B overlap shadow variant is worth a controlled patch."
    elif p / o >= 0.30:
        verdict = "OVERLAP_VARIANT_PREFLIGHT_MIXED"
        interpretation = "Some overlap records appear regime-eligible, but evidence is mixed. Continue observation or create only a diagnostic-only lane."
    else:
        verdict = "OVERLAP_VARIANT_PREFLIGHT_NEGATIVE"
        interpretation = "Most overlap rejects do not pass Lane1-style long regime checks. Do not create an overlap variant yet."

    return {
        "record_count": n,
        "status_counts": dict(status_counts),
        "session_counts": dict(session_counts),
        "overlap_session_reject_count": o,
        "overlap_session_reject_rate_pct": pct(o, n),
        "overlap_rejects_regime_preflight_pass_count": p,
        "overlap_rejects_regime_preflight_fail_count": len(preflight_fail),
        "overlap_rejects_regime_preflight_pass_rate_pct": pct(p, o),
        "verdict": verdict,
        "interpretation": interpretation,
        "latest_overlap_preflight_pass_records": preflight_pass[-10:],
        "latest_overlap_preflight_fail_records": preflight_fail[-10:],
    }

def build_markdown(report):
    lines = []
    lines.append("# SIG-E Lane1 Overlap Preflight")
    lines.append("")
    lines.append(f"- created_utc: `{report.get('created_utc')}`")
    lines.append(f"- preflight_status: `{report.get('preflight_status')}`")
    lines.append(f"- current_recommendation: `{report.get('current_recommendation')}`")
    lines.append("")
    lines.append("Boundary: preflight only; no detector rule change, no signal, no trade proposal, no entry/stop/target, no risk sizing, no broker/execution.")
    lines.append("")
    for wname, w in report.get("windows", {}).items():
        lines.append(f"## {wname}")
        lines.append("")
        lines.append(f"- record_count: `{w.get('record_count')}`")
        lines.append(f"- overlap_session_reject_count: `{w.get('overlap_session_reject_count')}`")
        lines.append(f"- overlap_rejects_regime_preflight_pass_count: `{w.get('overlap_rejects_regime_preflight_pass_count')}`")
        lines.append(f"- overlap_rejects_regime_preflight_pass_rate_pct: `{w.get('overlap_rejects_regime_preflight_pass_rate_pct')}`")
        lines.append(f"- verdict: `{w.get('verdict')}`")
        lines.append(f"- interpretation: {w.get('interpretation')}")
        lines.append("")
    return "\n".join(lines)

def main():
    state = load_json(LANE1_STATE)
    portfolio = load_json(PORTFOLIO) or {}
    coverage = load_json(COVERAGE) or {}

    if not isinstance(state, dict):
        report = {
            "program": PROGRAM,
            "created_utc": now(),
            "preflight_status": "FAIL_LANE1_STATE_MISSING",
            "lane_id": "SIGE_SD1_USDJPY_LONDON_LONG_H1_M15",
            "state_file": str(LANE1_STATE),
            "authority": AUTHORITY,
            "boundary": BOUNDARY,
            "not_authorized": [
                "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
                "broker/execution", "auto execution", "detector rule change"
            ],
        }
        write_json(RUNTIME_OUT, report)
        write_json(PANEL_OUT, report)
        write_json(JSON_OUT, report)
        write_text(MD_OUT, build_markdown(report))
        print("SIG_E_SHADOW_LANE1_OVERLAP_PREFLIGHT1_FAIL_LANE1_STATE_MISSING")
        raise SystemExit(1)

    records = state.get("refresh_records") if isinstance(state.get("refresh_records"), list) else []
    tnow = utcnow()
    windows = {
        "last_24h": summarize_window(filter_records(records, tnow - timedelta(hours=24))),
        "last_7d": summarize_window(filter_records(records, tnow - timedelta(days=7))),
        "all_time": summarize_window(records),
    }

    last7 = windows["last_7d"]
    verdict = last7["verdict"]

    if verdict == "OVERLAP_VARIANT_PREFLIGHT_POSITIVE":
        recommendation = "PREPARE_LANE1B_OVERLAP_SHADOW_VARIANT_PATCH"
    elif verdict == "OVERLAP_VARIANT_PREFLIGHT_MIXED":
        recommendation = "CONTINUE_OBSERVATION_OR_DIAGNOSTIC_ONLY_LANE1B"
    elif verdict == "WAIT_MORE_OVERLAP_OBSERVATIONS":
        recommendation = "WAIT_FOR_MORE_REFRESHES"
    else:
        recommendation = "DO_NOT_ADD_OVERLAP_VARIANT_YET"

    report = {
        "program": PROGRAM,
        "created_utc": now(),
        "preflight_status": "OK_PREFLIGHT_READY",
        "lane_id": "SIGE_SD1_USDJPY_LONDON_LONG_H1_M15",
        "display_name": "USDJPY London Long H1+M15",
        "state_file": str(LANE1_STATE),
        "source_refresh_record_count": len(records),
        "portfolio_status": portfolio.get("portfolio_status"),
        "coverage_status": coverage.get("coverage_status"),
        "method": {
            "question": "If Lane1 accepted LONDON_NY_OVERLAP as a session, how many rejected overlap records appear regime-eligible under Lane1-style long conditions?",
            "scope": "Session and regime what-if only.",
            "explicit_limitations": [
                "Does not evaluate H1 setup on rejected overlap records.",
                "Does not evaluate H1 trigger.",
                "Does not evaluate M15 confirmation.",
                "Does not create a new lane.",
                "Does not change Lane1 rules.",
                "Does not create signal or trade proposal authority."
            ],
        },
        "windows": windows,
        "current_recommendation": recommendation,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "not_authorized": [
            "signal",
            "manual trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution",
            "auto execution",
            "detector rule change",
            "portfolio lane change",
            "memory promotion",
        ],
    }

    write_json(RUNTIME_OUT, report)
    write_json(PANEL_OUT, report)
    write_json(JSON_OUT, report)
    write_text(MD_OUT, build_markdown(report))

    print("SIG_E_SHADOW_LANE1_OVERLAP_PREFLIGHT1_DONE")
    print("PREFLIGHT_STATUS=OK_PREFLIGHT_READY")
    print("LAST7_VERDICT=" + str(verdict))
    print("RECOMMENDATION=" + str(recommendation))
    print("LAST7_OVERLAP_REJECTS=" + str(last7.get("overlap_session_reject_count")))
    print("LAST7_PREFLIGHT_PASS=" + str(last7.get("overlap_rejects_regime_preflight_pass_count")))

if __name__ == "__main__":
    main()
