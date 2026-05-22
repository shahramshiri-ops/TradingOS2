
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1D-RUNTIME-NORMALIZER"

RUNTIME = Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
PANEL = Path("panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1d_normalizer_result.json")

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

def regime_details(obj):
    for chk in obj.get("checks", []) or []:
        if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
            return chk.get("details") or {}
    return {}

def normalize_obj(obj, label):
    changes = []
    if not isinstance(obj, dict):
        return obj, ["not_json_object"]

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

    details = regime_details(obj)
    session_ok = details.get("session_ok")
    alignment_ok = details.get("alignment_ok")
    vol_ok = details.get("vol_ok")

    if obj.get("detector_status") == "SESSION_NOT_MATCHED" and session_ok is True:
        if alignment_ok is False or vol_ok is False:
            obj["detector_status"] = "REGIME_NOT_MATCHED"
            obj["status_reason"] = "overlap_long_diagnostic_regime_not_matched"
            obj["status_hotfix_applied"] = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1D"
            obj["status_hotfix_reason"] = "session_ok_true_but_regime_alignment_or_vol_failed"
            changes.append("status_reclassified_session_to_regime")

    obj["status_hotfix1d_last_normalized_utc"] = now()
    return obj, changes

def normalize_file(path, label):
    obj = load(path)
    if obj is None:
        return {
            "label": label,
            "path": str(path),
            "exists": path.exists(),
            "status": "SKIPPED_MISSING_OR_BAD_JSON",
            "changes": [],
        }

    normalized, changes = normalize_obj(obj, label)
    write(path, normalized)

    details = regime_details(normalized)
    return {
        "label": label,
        "path": str(path),
        "exists": True,
        "status": "NORMALIZED",
        "changes": changes,
        "detector_status": normalized.get("detector_status"),
        "status_reason": normalized.get("status_reason"),
        "source_spec_id": normalized.get("source_spec_id"),
        "session_ok": details.get("session_ok"),
        "alignment_ok": details.get("alignment_ok"),
        "vol_ok": details.get("vol_ok"),
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
        if r.get("detector_status") == "SESSION_NOT_MATCHED" and r.get("session_ok") is True:
            errors.append("%s still invalid SESSION_NOT_MATCHED with session_ok=true" % r["label"])

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

    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1D_NORMALIZATION_" + out["normalization_status"])
    for r in results:
        print("%s -> %s / %s / %s" % (r["label"], r.get("detector_status"), r.get("status_reason"), ",".join(r.get("changes") or [])))
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
