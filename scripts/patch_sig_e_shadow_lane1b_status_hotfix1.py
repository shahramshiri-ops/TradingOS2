
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1"

TARGET = Path("scripts/build_sig_e_shadow_detector1b_overlap_diagnostic.py")
VALIDATOR = Path("scripts/validate_sig_e_shadow_detector1b_overlap_diagnostic.py")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1_patch_result.json")

NORMALIZER = '''
def normalize_lane1b_status_hotfix1(result):
    # SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1:
    # Status/metadata normalization only. Does not change setup, trigger,
    # M15 confirmation, shadow-match logic, Lane1, portfolio rules, signals,
    # trade proposals, or execution authority.
    if not isinstance(result, dict):
        return result

    if not result.get("source_spec_id"):
        result["source_spec_id"] = "SIG_E_RUNTIME_SPEC_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"

    if result.get("detector_id") == "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0":
        result.setdefault("classification", "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY")
        result["is_signal"] = False
        result["is_trade_proposal"] = False

    details = {}
    for chk in result.get("checks", []) or []:
        if isinstance(chk, dict):
            cid = str(chk.get("check_id") or "").upper()
            if "REGIME" in cid:
                details = chk.get("details") or {}
                break

    session_ok = details.get("session_ok")
    alignment_ok = details.get("alignment_ok")
    vol_ok = details.get("vol_ok")

    if result.get("detector_status") == "SESSION_NOT_MATCHED" and session_ok is True:
        if alignment_ok is False or vol_ok is False:
            result["detector_status"] = "REGIME_NOT_MATCHED"
            result["status_reason"] = "overlap_long_diagnostic_regime_not_matched"
            result["status_hotfix_applied"] = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1"
            result["status_hotfix_reason"] = "session_ok_true_but_regime_alignment_or_vol_failed"

    result.setdefault("authority", {})
    for k in [
        "signal_authorized",
        "trade_proposal_authorized",
        "entry_stop_target_authorized",
        "risk_sizing_authorized",
        "broker_execution_authorized",
        "auto_execution_authorized",
        "primary_lane_authorized",
        "lane_rule_change_authorized",
    ]:
        result["authority"][k] = False

    return result
'''

VALIDATOR_SNIPPET = '''
    # SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1 invariant:
    # SESSION_NOT_MATCHED is only allowed when the regime details say session_ok=false.
    if r.get("detector_status") == "SESSION_NOT_MATCHED":
        details = {}
        for chk in r.get("checks", []) or []:
            if isinstance(chk, dict) and "REGIME" in str(chk.get("check_id", "")).upper():
                details = chk.get("details") or {}
                break
        if details.get("session_ok") is True:
            errors.append("SESSION_NOT_MATCHED is invalid when regime.details.session_ok is true; expected REGIME_NOT_MATCHED or later gate")
    if not r.get("source_spec_id"):
        errors.append("source_spec_id must not be null/empty")
'''

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def backup(path):
    b = path.with_suffix(path.suffix + ".bak_lane1b_status_hotfix1")
    shutil.copyfile(path, b)
    return str(b)

def patch_detector():
    item = {"file": str(TARGET), "exists": TARGET.exists(), "patched": False, "reason": None}
    if not TARGET.exists():
        item["reason"] = "TARGET_MISSING"
        return item

    text = TARGET.read_text(encoding="utf-8")

    changed = False
    if "def normalize_lane1b_status_hotfix1" not in text:
        marker = "\ndef main():"
        if marker in text:
            text = text.replace(marker, "\n" + NORMALIZER + marker, 1)
        else:
            marker2 = '\nif __name__ == "__main__":'
            if marker2 in text:
                text = text.replace(marker2, "\n" + NORMALIZER + marker2, 1)
            else:
                text += "\n\n" + NORMALIZER + "\n"
        changed = True

    if "normalize_lane1b_status_hotfix1(result)" not in text and "normalize_lane1b_status_hotfix1(res)" not in text:
        patterns = [
            (r"(result\s*=\s*build\(\)\s*\n)", "result"),
            (r"(res\s*=\s*build\(\)\s*\n)", "res"),
        ]
        inserted = False
        for pat, var in patterns:
            m = re.search(pat, text)
            if m:
                replacement = m.group(1) + "    %s = normalize_lane1b_status_hotfix1(%s)\n" % (var, var)
                text = text[:m.start()] + replacement + text[m.end():]
                inserted = True
                changed = True
                break
        if not inserted:
            item["reason"] = "BUILD_CALL_PATTERN_NOT_FOUND"
            return item

    if changed:
        item["backup"] = backup(TARGET)
        TARGET.write_text(text, encoding="utf-8")
        item["patched"] = True
        item["reason"] = "DETECTOR_NORMALIZER_INSERTED"
    else:
        item["reason"] = "ALREADY_PRESENT"
    return item

def patch_validator():
    item = {"file": str(VALIDATOR), "exists": VALIDATOR.exists(), "patched": False, "reason": None}
    if not VALIDATOR.exists():
        item["reason"] = "VALIDATOR_MISSING"
        return item

    text = VALIDATOR.read_text(encoding="utf-8")
    if "SESSION_NOT_MATCHED is invalid when regime.details.session_ok is true" in text:
        item["reason"] = "ALREADY_PRESENT"
        return item

    marker = "result = {"
    if marker not in text:
        item["reason"] = "VALIDATOR_RESULT_MARKER_NOT_FOUND"
        return item

    item["backup"] = backup(VALIDATOR)
    text = text.replace(marker, VALIDATOR_SNIPPET + "\n    " + marker, 1)
    VALIDATOR.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "VALIDATOR_INVARIANT_ADDED"
    return item

def main():
    results = [patch_detector(), patch_validator()]
    status = "PASS" if all(r.get("patched") or r.get("reason") == "ALREADY_PRESENT" for r in results) else "PARTIAL_OR_FAIL"
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "patch_status": status,
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
            "STATUS_METADATA_HOTFIX_ONLY",
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
    write_json(OUT, result)
    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1_" + status)
    for r in results:
        print(r["file"] + " -> " + str(r["reason"]))
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
