import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1-OVERLAP-PREFLIGHT1"

RUNTIME_OUT = Path("runtime/sig_e/shadow_lane1_overlap_preflight_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_lane1_overlap_preflight_current.json")
JSON_OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.json")
MD_OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_current.md")
VALIDATION_OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight_validation_result.json")

FORBIDDEN_TRUE = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
    "lane_rule_change_authorized",
    "detector_change_authorized",
]

REQUIRED_BOUNDARY = {
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
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    errors = []
    payloads = {}

    for name, path in [("runtime", RUNTIME_OUT), ("panel", PANEL_OUT), ("json", JSON_OUT)]:
        if not path.exists():
            errors.append(f"missing {name}: {path}")
        else:
            try:
                payloads[name] = load(path)
            except Exception as e:
                errors.append(f"bad json {name}: {e}")

    if not MD_OUT.exists():
        errors.append(f"missing markdown output: {MD_OUT}")

    for name, obj in payloads.items():
        if obj.get("program") != PROGRAM:
            errors.append(f"{name} program mismatch")
        auth = obj.get("authority", {})
        for key in FORBIDDEN_TRUE:
            if auth.get(key) is not False:
                errors.append(f"{name}.authority.{key} must be false")
        boundary = set(obj.get("boundary", []))
        missing = sorted(REQUIRED_BOUNDARY - boundary)
        if missing:
            errors.append(f"{name} missing boundary constants: {', '.join(missing)}")
        if obj.get("preflight_status") not in {"OK_PREFLIGHT_READY", "FAIL_LANE1_STATE_MISSING"}:
            errors.append(f"{name} invalid preflight_status")

    runtime = payloads.get("runtime") or {}
    if runtime.get("preflight_status") == "OK_PREFLIGHT_READY":
        if "windows" not in runtime or "last_7d" not in runtime.get("windows", {}):
            errors.append("runtime windows.last_7d missing")
        if runtime.get("current_recommendation") not in {
            "PREPARE_LANE1B_OVERLAP_SHADOW_VARIANT_PATCH",
            "CONTINUE_OBSERVATION_OR_DIAGNOSTIC_ONLY_LANE1B",
            "WAIT_FOR_MORE_REFRESHES",
            "DO_NOT_ADD_OVERLAP_VARIANT_YET",
        }:
            errors.append("invalid current_recommendation")

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "preflight_status": runtime.get("preflight_status"),
        "current_recommendation": runtime.get("current_recommendation"),
        "last_7d": (runtime.get("windows") or {}).get("last_7d"),
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

    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SIG_E_SHADOW_LANE1_OVERLAP_PREFLIGHT1_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
