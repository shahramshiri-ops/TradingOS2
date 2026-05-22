import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-DETECTOR2-OBSLEDGER1"
DETECTOR_ID = "SIG_E_SHADOW_DETECTOR_USDJPY_ASIA_SHORT_H1_M15_CAVEATED_v1_0"
SOURCE_SPEC_ID = "SIG_E_RUNTIME_SPEC_USDJPY_ASIA_SHORT_H1_M15_CAVEATED_v1_0"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector2_obsledger_status_current.json")
STATE = Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json")
OUT = Path("outputs/_sig_e_shadow_detector2_obsledger/sig_e_shadow_detector2_obsledger_validation_result.json")

FORBID = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized"
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main():
    errors = []
    payload = {}

    for name, p in [("runtime", RUNTIME), ("panel", PANEL), ("state", STATE)]:
        if not p.exists():
            errors.append(f"missing {name}: {p}")
        else:
            try:
                payload[name] = load(p)
            except Exception as e:
                errors.append(f"bad json {name}: {e}")

    for name, obj in payload.items():
        if obj.get("program") != PROGRAM:
            errors.append(f"{name} program mismatch")
        if obj.get("detector_id") != DETECTOR_ID:
            errors.append(f"{name} detector_id missing/mismatch")
        if obj.get("source_spec_id") != SOURCE_SPEC_ID:
            errors.append(f"{name} source_spec_id missing/mismatch")
        auth = obj.get("authority", {})
        for k in FORBID:
            if auth.get(k) is not False:
                errors.append(f"{name}.authority.{k} must be false")

    result = {
        "program": "SIG-E-SHADOW-DETECTOR2-OBSLEDGER1-HOTFIX1",
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "detector_id": DETECTOR_ID,
        "source_spec_id": SOURCE_SPEC_ID,
        "summary": (payload.get("runtime") or {}).get("summary"),
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("SIG_E_SHADOW_DETECTOR2_OBSLEDGER1_HOTFIX1_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
