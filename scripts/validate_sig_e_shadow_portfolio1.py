import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-PORTFOLIO1"
RUNTIME_OUT = Path("runtime/sig_e/shadow_portfolio_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_portfolio_status_current.json")
VALIDATION_OUT = Path("outputs/_sig_e_shadow_portfolio1/sig_e_shadow_portfolio1_validation_result.json")

FORBIDDEN_AUTH_TRUE = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
]

REQUIRED_BOUNDARY = {
    "PORTFOLIO_OBSERVATION_ONLY",
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

def now_utc():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    errors = []
    payloads = {}

    for name, path in [("runtime", RUNTIME_OUT), ("panel", PANEL_OUT)]:
        if not path.exists():
            errors.append(f"missing {name}: {path}")
        else:
            try:
                payloads[name] = load(path)
            except Exception as e:
                errors.append(f"invalid json {name}: {e}")

    for name, obj in payloads.items():
        if obj.get("program") != PROGRAM:
            errors.append(f"{name} program mismatch")
        auth = obj.get("authority", {})
        for k in FORBIDDEN_AUTH_TRUE:
            if auth.get(k) is not False:
                errors.append(f"{name}.authority.{k} must be false")
        boundary = set(obj.get("boundary", []))
        missing = sorted(REQUIRED_BOUNDARY - boundary)
        if missing:
            errors.append(f"{name} missing boundary constants: {', '.join(missing)}")

        lanes = obj.get("lanes")
        if not isinstance(lanes, list) or len(lanes) < 2:
            errors.append(f"{name} must contain at least two lanes")

        for lane in lanes if isinstance(lanes, list) else []:
            if lane.get("is_signal") is not False:
                errors.append(f"{name}.{lane.get('lane_id')}.is_signal must be false")
            if lane.get("is_trade_proposal") is not False:
                errors.append(f"{name}.{lane.get('lane_id')}.is_trade_proposal must be false")

    result = {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "summary": (payloads.get("runtime") or {}).get("summary"),
        "portfolio_status": (payloads.get("runtime") or {}).get("portfolio_status"),
        "current_runtime_authority": (payloads.get("runtime") or {}).get("authority"),
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_REVIEW_ONLY",
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
    }

    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SIG_E_SHADOW_PORTFOLIO1_VALIDATION_" + result["validation_status"])
    print("Result:", VALIDATION_OUT)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
