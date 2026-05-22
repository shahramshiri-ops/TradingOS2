import json
from pathlib import Path
from datetime import datetime

RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_status_current.json")
STATE_PATH = Path("state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json")
VALIDATION_OUT = Path("outputs/_sig_e_shadow_detector1/sig_e_shadow_detector1_validation_result.json")

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
    "EXPIRED"
}

FORBIDDEN_TRUE = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized"
]

def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    errors = []
    payloads = {}
    for name, path in [("runtime", RUNTIME_OUT), ("panel", PANEL_OUT), ("state", STATE_PATH)]:
        if not path.exists():
            errors.append(f"missing {name} output: {path}")
        else:
            try:
                payloads[name] = load(path)
            except Exception as e:
                errors.append(f"invalid json {name}: {e}")

    runtime = payloads.get("runtime", {})
    panel = payloads.get("panel", {})

    if runtime.get("program") != "SIG-E-RUNTIME-SHADOW-DETECTOR1":
        errors.append("runtime program mismatch")
    if panel.get("program") != "SIG-E-RUNTIME-SHADOW-DETECTOR1":
        errors.append("panel program mismatch")

    status = runtime.get("detector_status")
    if status not in VALID_STATUS:
        errors.append(f"invalid detector_status: {status}")

    if runtime.get("is_signal") is not False:
        errors.append("is_signal must be false")
    if runtime.get("is_trade_proposal") is not False:
        errors.append("is_trade_proposal must be false")

    authority = runtime.get("authority", {})
    for k in FORBIDDEN_TRUE:
        if authority.get(k) is not False:
            errors.append(f"authority.{k} must be false")

    boundary = set(runtime.get("boundary", []))
    required_boundary = {
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
    missing = sorted(required_boundary - boundary)
    if missing:
        errors.append("missing boundary constants: " + ", ".join(missing))

    if runtime.get("is_shadow_match") is True and status != "SHADOW_MATCH_CONFIRMED":
        errors.append("is_shadow_match true requires SHADOW_MATCH_CONFIRMED")

    result = {
        "program": "SIG-E-RUNTIME-SHADOW-DETECTOR1",
        "created_utc": utc_now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "detector_status": status,
        "is_shadow_match": runtime.get("is_shadow_match"),
        "current_runtime_authority": authority,
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_ONLY",
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

    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("SIG_E_SHADOW_DETECTOR1_VALIDATION_" + result["validation_status"])
    print("Result:", VALIDATION_OUT)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
