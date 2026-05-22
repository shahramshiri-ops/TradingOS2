
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1E-VALIDATION"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1e_validation_result.json")

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

def regime_details(obj):
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
            d = chk.get("details") or {}
            if isinstance(d, dict):
                return d
    for d in walk_dicts(obj):
        if isinstance(d, dict) and ("session_ok" in d or "alignment_ok" in d or "vol_ok" in d):
            return d
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
    session_ok = as_bool(details.get("session_ok"))
    alignment_ok = as_bool(details.get("alignment_ok"))
    vol_ok = as_bool(details.get("vol_ok"))
    session_bucket = str(details.get("session_bucket") or obj.get("session_bucket") or "").upper()

    overlap_seen = (
        session_ok is True
        or session_bucket == "LONDON_NY_OVERLAP"
        or "LONDON_NY_OVERLAP" in json.dumps(obj, ensure_ascii=False)
    )

    if obj.get("detector_status") == "SESSION_NOT_MATCHED" and overlap_seen:
        errors.append("%s SESSION_NOT_MATCHED invalid when overlap context is present" % name)

    if overlap_seen and (alignment_ok is False or vol_ok is False or "CONFLICT" in str(details.get("htf_alignment") or "").upper()):
        if obj.get("detector_status") != "REGIME_NOT_MATCHED":
            errors.append("%s expected REGIME_NOT_MATCHED when overlap context exists and regime component failed" % name)

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

    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1E_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
