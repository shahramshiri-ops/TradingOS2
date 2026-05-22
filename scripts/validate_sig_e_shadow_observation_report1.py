import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-OBSREPORT1"
RUNTIME_OUT = Path("runtime/sig_e/shadow_observation_report_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_observation_report_current.json")
JSON_OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.json")
MD_OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_current.md")
VALIDATION_OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_observation_report_validation_result.json")

FORBIDDEN = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
]

REQUIRED_BOUNDARY = {
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
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

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
        errors.append(f"missing markdown report: {MD_OUT}")

    for name, obj in payloads.items():
        if obj.get("program") != PROGRAM:
            errors.append(f"{name} program mismatch")
        lanes = obj.get("lanes")
        if not isinstance(lanes, list) or len(lanes) < 1:
            errors.append(f"{name} lanes missing")
        auth = obj.get("authority", {})
        for k in FORBIDDEN:
            if auth.get(k) is not False:
                errors.append(f"{name}.authority.{k} must be false")
        boundary = set(obj.get("boundary", []))
        missing = sorted(REQUIRED_BOUNDARY - boundary)
        if missing:
            errors.append(f"{name} missing boundary constants: {', '.join(missing)}")

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "report_status": (payloads.get("runtime") or {}).get("report_status"),
        "summary": (payloads.get("runtime") or {}).get("summary"),
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

    print("SIG_E_SHADOW_OBSREPORT1_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
