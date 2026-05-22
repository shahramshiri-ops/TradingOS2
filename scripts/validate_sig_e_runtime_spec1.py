import json
from pathlib import Path
from datetime import datetime

REQUIRED_BOUNDARY = {
    "SPEC_CONTRACT_ONLY",
    "CURRENT_RUNTIME_NOT_SIGNAL",
    "NO_RUNTIME_SETUP_ACTIVATION",
    "NO_RUNTIME_TRIGGER_ACTIVATION",
    "NO_TRADE_PROPOSAL",
    "NO_ENTRY_STOP_TARGET",
    "NO_RISK_OR_POSITION_SIZING",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_EXECUTION",
    "NO_RULE_REWRITE",
    "NO_MEMORY_PROMOTION",
}

FORBIDDEN_TRUE_AUTHORITY_KEYS = [
    "current_runtime_signal_authorized",
    "runtime_setup_activation_authorized",
    "runtime_trigger_activation_authorized",
    "trade_plan_authorized",
    "entry_stop_target_authorized",
    "risk_position_sizing_authorized",
    "broker_execution_authorized",
]

def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    spec_path = Path("config/sig_e/runtime_specs/usdjpy_london_long_h1_m15_v1_0.json")
    out_dir = Path("outputs/_sig_e_runtime_spec1")
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "sig_e_runtime_spec1_validation_result.json"

    errors = []
    if not spec_path.exists():
        errors.append(f"missing spec: {spec_path}")
        spec = {}
    else:
        spec = load_json(spec_path)

    if spec.get("program") != "SIG-E-RUNTIME-SPEC1":
        errors.append("program must be SIG-E-RUNTIME-SPEC1")

    if spec.get("status") != "SPEC_DRAFT_NOT_RUNTIME_DETECTOR":
        errors.append("status must remain SPEC_DRAFT_NOT_RUNTIME_DETECTOR")

    boundary = set(spec.get("boundary", []))
    missing_boundary = sorted(REQUIRED_BOUNDARY - boundary)
    if missing_boundary:
        errors.append("missing boundary constants: " + ", ".join(missing_boundary))

    authority = spec.get("runtime_authority", {})
    for k in FORBIDDEN_TRUE_AUTHORITY_KEYS:
        if authority.get(k) is not False:
            errors.append(f"runtime_authority.{k} must be false")

    if authority.get("manual_review_required_always") is not True:
        errors.append("manual_review_required_always must be true")

    lane = spec.get("lane", {})
    expected = {
        "instrument": "USDJPY",
        "session_bucket": "LONDON",
        "direction": "LONG",
        "setup_family": "H1_RANGE_EXPANSION_LOWER_REJECTION_LONG",
        "h1_trigger_type": "NEXT_H1_DIRECTION_CONFIRM",
        "m15_trigger_policy": "M15_INSIDE_H1_DIRECTIONAL_CLOSE_CONFIRM",
        "horizon_h1_bars": 16,
    }
    for k, v in expected.items():
        if lane.get(k) != v:
            errors.append(f"lane.{k} must be {v!r}")

    evidence = spec.get("evidence", {})
    if evidence.get("m15_validation_n", 0) < 50:
        errors.append("m15_validation_n must be >= 50 for this spec")
    if evidence.get("m15_validation_max_year_share", 1) > 0.35:
        errors.append("m15_validation_max_year_share must be <= 0.35 for this spec")
    if evidence.get("delta_validation_favorable_rate_vs_h1_reference", 0) <= 0:
        errors.append("delta favorable must be positive")
    if evidence.get("delta_validation_avg_move_norm_atr_vs_h1_reference", 0) <= 0:
        errors.append("delta avg move must be positive")

    status = "PASS" if not errors else "FAIL"
    result = {
        "program": "SIG-E-RUNTIME-SPEC1",
        "created_utc": utc_now(),
        "validation_status": status,
        "errors": errors,
        "spec_path": str(spec_path),
        "boundary": spec.get("boundary", []),
        "next_allowed_use": "SPEC_COMPATIBILITY_PROBE_ONLY",
        "not_authorized": [
            "signal",
            "runtime setup activation",
            "runtime trigger activation",
            "trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution"
        ]
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("SIG_E_RUNTIME_SPEC1_VALIDATION_" + status)
    print("Result:", result_path)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
