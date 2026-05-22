
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1E-RUNTIME-NORMALIZER"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1e_normalizer_result.json")

SOURCE_SPEC_ID = "SIG_E_RUNTIME_SPEC_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"
DETECTOR_ID = "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"

AUTH_FALSE_KEYS = [
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

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

def get_regime_details(obj):
    # Prefer explicit regime checks.
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict):
            cid = str(chk.get("check_id") or "").upper()
            if "REGIME" in cid:
                details = chk.get("details")
                if isinstance(details, dict):
                    return details

    # Fallback: search any nested dict that contains session/alignment/vol flags.
    for d in walk_dicts(obj):
        if not isinstance(d, dict):
            continue
        keys = set(d.keys())
        if ("session_ok" in keys) or ("alignment_ok" in keys) or ("vol_ok" in keys):
            return d

    return {}

def normalize_obj(obj, label):
    changes = []
    if not isinstance(obj, dict):
        return obj, ["not_json_object"], {}

    if not obj.get("source_spec_id"):
        obj["source_spec_id"] = SOURCE_SPEC_ID
        changes.append("source_spec_id_filled")

    if not obj.get("detector_id"):
        obj["detector_id"] = DETECTOR_ID
        changes.append("detector_id_filled")

    obj.setdefault("classification", "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY")
    obj["is_signal"] = False
    obj["is_trade_proposal"] = False

    obj.setdefault("authority", {})
    for key in AUTH_FALSE_KEYS:
        if obj["authority"].get(key) is not False:
            obj["authority"][key] = False
            changes.append("authority_%s_false" % key)

    details = get_regime_details(obj)

    session_ok = as_bool(details.get("session_ok"))
    alignment_ok = as_bool(details.get("alignment_ok"))
    vol_ok = as_bool(details.get("vol_ok"))

    session_bucket = str(details.get("session_bucket") or obj.get("session_bucket") or "").upper()
    status = str(obj.get("detector_status") or "")
    reason = str(obj.get("status_reason") or "")

    # Robust fallback: if the reason says session_not_london_ny_overlap but the
    # details/session bucket show LONDON_NY_OVERLAP, this is not a session failure.
    overlap_seen = (
        session_ok is True
        or session_bucket == "LONDON_NY_OVERLAP"
        or "LONDON_NY_OVERLAP" in json.dumps(obj, ensure_ascii=False)
    )

    regime_component_failed = (
        alignment_ok is False
        or vol_ok is False
        or "H4_H1_CONFLICT" in str(details.get("htf_alignment") or "").upper()
        or "CONFLICT" in str(details.get("htf_alignment") or "").upper()
    )

    if status == "SESSION_NOT_MATCHED" and overlap_seen:
        if regime_component_failed or "session_not_london_ny_overlap" in reason:
            obj["detector_status"] = "REGIME_NOT_MATCHED"
            obj["status_reason"] = "overlap_long_diagnostic_regime_not_matched"
            obj["status_hotfix_applied"] = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1E"
            obj["status_hotfix_reason"] = "overlap_session_seen_but_regime_component_failed_or_old_reason"
            changes.append("status_reclassified_session_to_regime")

    obj["status_hotfix1e_last_normalized_utc"] = now()

    diagnostic = {
        "session_ok_raw": details.get("session_ok"),
        "alignment_ok_raw": details.get("alignment_ok"),
        "vol_ok_raw": details.get("vol_ok"),
        "session_ok": session_ok,
        "alignment_ok": alignment_ok,
        "vol_ok": vol_ok,
        "session_bucket": session_bucket,
        "overlap_seen": overlap_seen,
        "regime_component_failed": regime_component_failed,
        "status_after": obj.get("detector_status"),
        "reason_after": obj.get("status_reason"),
    }
    return obj, changes, diagnostic

def normalize_file(path, label):
    obj = load(path)
    if obj is None:
        return {
            "label": label,
            "path": str(path),
            "exists": path.exists(),
            "status": "SKIPPED_MISSING_OR_BAD_JSON",
            "changes": [],
            "diagnostic": {},
        }

    normalized, changes, diag = normalize_obj(obj, label)
    write(path, normalized)

    return {
        "label": label,
        "path": str(path),
        "exists": True,
        "status": "NORMALIZED",
        "changes": changes,
        "detector_status": normalized.get("detector_status"),
        "status_reason": normalized.get("status_reason"),
        "source_spec_id": normalized.get("source_spec_id"),
        "diagnostic": diag,
    }

def main():
    results = [
        normalize_file(RUNTIME, "runtime"),
        normalize_file(PANEL, "panel"),
    ]

    errors = []
    for r in results:
        if r["status"] != "NORMALIZED":
            errors.append("%s not normalized: %s" % (r["label"], r["status"]))
        if not r.get("source_spec_id"):
            errors.append("%s source_spec_id still empty" % r["label"])
        diag = r.get("diagnostic") or {}
        if r.get("detector_status") == "SESSION_NOT_MATCHED" and diag.get("overlap_seen"):
            errors.append("%s still SESSION_NOT_MATCHED although overlap_seen=true" % r["label"])

    out = {
        "program": PROGRAM,
        "created_utc": now(),
        "normalization_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "results": results,
        "authority": {
            "signal_authorized": False,
            "trade_proposal_authorized": False,
            "entry_stop_target_authorized": False,
            "risk_sizing_authorized": False,
            "broker_execution_authorized": False,
            "auto_execution_authorized": False,
            "primary_lane_authorized": False,
            "lane_rule_change_authorized": False,
        },
        "boundary": [
            "RUNTIME_STATUS_METADATA_NORMALIZER_ONLY",
            "DOES_NOT_CHANGE_SETUP_TRIGGER_OR_M15_LOGIC",
            "DOES_NOT_CHANGE_LANE1",
            "DIAGNOSTIC_ONLY_LANE",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION",
        ],
    }
    write(OUT, out)

    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1E_NORMALIZATION_" + out["normalization_status"])
    for r in results:
        diag = r.get("diagnostic") or {}
        print("%s -> %s / %s / changes=%s / overlap_seen=%s / alignment=%s / vol=%s" % (
            r["label"],
            r.get("detector_status"),
            r.get("status_reason"),
            ",".join(r.get("changes") or []),
            diag.get("overlap_seen"),
            diag.get("alignment_ok"),
            diag.get("vol_ok"),
        ))
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
