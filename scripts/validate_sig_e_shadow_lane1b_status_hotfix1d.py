
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1D-VALIDATION"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1d_validation_result.json")

FORBID = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
    "primary_lane_authorized",
    "lane_rule_change_authorized",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def regime_details(obj):
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
            return chk.get("details") or {}
    return {}

def check_one(name, path, errors):
    if not path.exists():
        errors.append("%s missing: %s" % (name, path))
        return None
    try:
        obj = load(path)
    except Exception as e:
        errors.append("%s bad json: %s" % (name, e))
        return None

    if not obj.get("source_spec_id"):
        errors.append("%s source_spec_id must not be null/empty" % name)

    if obj.get("is_signal") is not False:
        errors.append("%s is_signal must be false" % name)
    if obj.get("is_trade_proposal") is not False:
        errors.append("%s is_trade_proposal must be false" % name)

    auth = obj.get("authority") or {}
    for k in FORBID:
        if auth.get(k) is not False:
            errors.append("%s authority.%s must be false" % (name, k))

    details = regime_details(obj)
    if obj.get("detector_status") == "SESSION_NOT_MATCHED" and details.get("session_ok") is True:
        errors.append("%s SESSION_NOT_MATCHED invalid when regime.details.session_ok=true" % name)

    if details.get("session_ok") is True and (details.get("alignment_ok") is False or details.get("vol_ok") is False):
        if obj.get("detector_status") != "REGIME_NOT_MATCHED":
            errors.append("%s expected REGIME_NOT_MATCHED when session_ok=true and regime component failed" % name)

    return obj

def main():
    errors = []
    runtime = check_one("runtime", RUNTIME, errors)
    panel = check_one("panel", PANEL, errors)

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "runtime_status": runtime.get("detector_status") if isinstance(runtime, dict) else None,
        "runtime_status_reason": runtime.get("status_reason") if isinstance(runtime, dict) else None,
        "runtime_source_spec_id": runtime.get("source_spec_id") if isinstance(runtime, dict) else None,
        "runtime_regime_details": regime_details(runtime) if isinstance(runtime, dict) else None,
        "not_authorized": [
            "signal",
            "manual trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution",
            "auto execution",
            "primary lane promotion",
            "Lane1 rule change",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1D_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
