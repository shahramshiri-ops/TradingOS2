
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-GATEFLOW-HOTFIX2-VALIDATION"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_gateflow_hotfix2/sig_e_shadow_lane1b_gateflow_hotfix2_validation_result.json")

VALID_STATUS = {
    "INPUT_INSUFFICIENT",
    "DATA_STALE",
    "SESSION_NOT_MATCHED",
    "REGIME_NOT_MATCHED",
    "LIVE_OHLC_SOURCE_MISSING",
    "LIVE_H1_HISTORY_INSUFFICIENT",
    "LIVE_M15_HISTORY_INSUFFICIENT",
    "SETUP_NOT_FORMED",
    "H1_TRIGGER_WAIT",
    "H1_TRIGGER_NOT_CONFIRMED",
    "M15_TRIGGER_WAIT",
    "DIAGNOSTIC_SHADOW_MATCH_CONFIRMED",
    "EXPIRED",
}

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

def as_bool(value):
    if value is True:
        return True
    if value is False:
        return False
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "y", "pass", "passed", "ok"):
        return True
    if s in ("false", "0", "no", "n", "fail", "failed"):
        return False
    return None

def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for x in walk_dicts(v):
                yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in walk_dicts(v):
                yield x

def regime_check_obj(obj):
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
            return chk
    return None

def regime_details(obj):
    chk = regime_check_obj(obj)
    if isinstance(chk, dict) and isinstance(chk.get("details"), dict):
        return chk.get("details") or {}
    for d in walk_dicts(obj):
        if isinstance(d, dict) and ("session_ok" in d or "alignment_ok" in d or "vol_ok" in d):
            return d
    return {}

def regime_passed(obj):
    chk = regime_check_obj(obj)
    if isinstance(chk, dict) and chk.get("passed") is True:
        return True
    d = regime_details(obj)
    return as_bool(d.get("session_ok")) is True and as_bool(d.get("alignment_ok")) is True and as_bool(d.get("vol_ok")) is True

def check_one(name, path, errors):
    if not path.exists():
        errors.append("%s missing: %s" % (name, path))
        return None
    try:
        obj = load(path)
    except Exception as e:
        errors.append("%s bad json: %s" % (name, e))
        return None

    if obj.get("program") != "SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1":
        errors.append("%s program mismatch" % name)

    if obj.get("detector_status") not in VALID_STATUS:
        errors.append("%s invalid detector_status: %s" % (name, obj.get("detector_status")))

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

    if regime_passed(obj):
        if obj.get("detector_status") in ("SESSION_NOT_MATCHED", "REGIME_NOT_MATCHED"):
            errors.append("%s regime passed but status still %s" % (name, obj.get("detector_status")))
        if "gateflow_hotfix2_action" not in obj:
            errors.append("%s missing gateflow_hotfix2_action after regime pass" % name)

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
        "runtime_gateflow_action": runtime.get("gateflow_hotfix2_action") if isinstance(runtime, dict) else None,
        "runtime_regime_passed": regime_passed(runtime) if isinstance(runtime, dict) else None,
        "runtime_data_counts": runtime.get("data_counts") if isinstance(runtime, dict) else None,
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

    print("SIG_E_SHADOW_LANE1B_GATEFLOW_HOTFIX2_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
