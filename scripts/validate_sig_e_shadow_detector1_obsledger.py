import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-DETECTOR1-OBSLEDGER1"
LEDGER_STATE = Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_obsledger_status_current.json")
VALIDATION_OUT = Path("outputs/_sig_e_shadow_detector_obsledger1/sig_e_shadow_detector_obsledger1_validation_result.json")

FORBIDDEN_AUTH_TRUE = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
]

REQUIRED_BOUNDARY = {
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
}

def now_utc():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def path_forbidden(path):
    s = str(path or "").replace("\\", "/").lower()
    return any(x in s for x in [
        "data/canonical/",
        "data/raw/",
        "data/features/",
        "holdout_2020_2024",
        "validation_2015_2019",
        "discovery_2004_2014",
        "future_after_2024",
    ])

def main():
    errors = []
    payloads = {}
    for name, path in [("state", LEDGER_STATE), ("runtime", RUNTIME_OUT), ("panel", PANEL_OUT)]:
        if not path.exists():
            errors.append(f"missing {name}: {path}")
        else:
            try:
                payloads[name] = load(path)
            except Exception as e:
                errors.append(f"invalid json {name}: {e}")

    runtime = payloads.get("runtime", {})
    panel = payloads.get("panel", {})
    state = payloads.get("state", {})

    if runtime.get("program") != PROGRAM:
        errors.append("runtime program mismatch")
    if panel.get("program") != PROGRAM:
        errors.append("panel program mismatch")
    if state.get("program") != PROGRAM:
        errors.append("state program mismatch")

    for name, obj in [("runtime", runtime), ("panel", panel), ("state", state)]:
        auth = obj.get("authority", {})
        for k in FORBIDDEN_AUTH_TRUE:
            if auth.get(k) is not False:
                errors.append(f"{name}.authority.{k} must be false")
        boundary = set(obj.get("boundary", []))
        missing = sorted(REQUIRED_BOUNDARY - boundary)
        if missing:
            errors.append(f"{name} missing boundary constants: {', '.join(missing)}")

    # Safety: no outcome may be closed from historical/canonical source paths.
    for ev in state.get("shadow_events", []):
        if not isinstance(ev, dict):
            continue
        sp = ev.get("source_paths") or {}
        for k in ["h1_ohlc_path", "m15_ohlc_path"]:
            if path_forbidden(sp.get(k)):
                errors.append(f"shadow_event {ev.get('shadow_event_id')} uses forbidden source path {k}: {sp.get(k)}")

    result = {
        "program": PROGRAM,
        "created_utc": now_utc(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "summary": runtime.get("summary"),
        "current_runtime_authority": runtime.get("authority"),
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_AND_REVIEW_ONLY",
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
    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("SIG_E_SHADOW_DETECTOR1_OBSLEDGER1_VALIDATION_" + result["validation_status"])
    print("Result:", VALIDATION_OUT)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
