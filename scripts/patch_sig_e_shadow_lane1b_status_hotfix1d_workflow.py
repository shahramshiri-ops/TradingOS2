
import json
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1B-STATUS-HOTFIX1D-WORKFLOW-PATCH"

WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
COMMIT = Path("scripts/commit_sig_e_shadow_persistence_outputs.py")
OUT = Path("outputs/_sig_e_shadow_lane1b_status_hotfix1/sig_e_shadow_lane1b_status_hotfix1d_workflow_patch_result.json")

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def backup(path):
    b = path.with_suffix(path.suffix + ".bak_lane1b_status_hotfix1d")
    shutil.copyfile(path, b)
    return str(b)

def patch_workflow():
    item = {"file": str(WORKFLOW), "exists": WORKFLOW.exists(), "patched": False, "reason": None}
    if not WORKFLOW.exists():
        item["reason"] = "MISSING"
        return item
    text = WORKFLOW.read_text(encoding="utf-8-sig")

    if "normalize_sig_e_shadow_lane1b_status_hotfix1d.py" in text:
        item["reason"] = "ALREADY_PRESENT"
        return item

    anchor = "          python scripts/validate_sig_e_shadow_detector1b_overlap_diagnostic.py"
    insert = """          python scripts/normalize_sig_e_shadow_lane1b_status_hotfix1d.py
          python scripts/validate_sig_e_shadow_lane1b_status_hotfix1d.py
"""
    if anchor not in text:
        item["reason"] = "WORKFLOW_ANCHOR_NOT_FOUND"
        return item

    item["backup"] = backup(WORKFLOW)
    text = text.replace(anchor, anchor + "\n" + insert.rstrip("\n"), 1)
    WORKFLOW.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "NORMALIZER_ADDED_AFTER_LANE1B_BUILD_VALIDATE"
    return item

def patch_commit():
    item = {"file": str(COMMIT), "exists": COMMIT.exists(), "patched": False, "reason": None}
    if not COMMIT.exists():
        item["reason"] = "MISSING"
        return item
    text = COMMIT.read_text(encoding="utf-8")
    addition = '    "outputs/_sig_e_shadow_lane1b_status_hotfix1",'
    if addition in text:
        item["reason"] = "ALREADY_PRESENT"
        return item
    marker = '    "outputs/_sig_e_shadow_detector1b_overlap",'
    if marker not in text:
        marker = '    "outputs/_sig_e_shadow_coverage1",'
    if marker not in text:
        item["reason"] = "COMMIT_SAFE_PATH_MARKER_NOT_FOUND"
        return item
    item["backup"] = backup(COMMIT)
    text = text.replace(marker, marker + "\n" + addition, 1)
    COMMIT.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "HOTFIX_OUTPUT_ADDED_TO_COMMIT_SAFE_PATHS"
    return item

def main():
    results = [patch_workflow(), patch_commit()]
    status = "PASS" if all(r.get("patched") or r.get("reason") == "ALREADY_PRESENT" for r in results) else "PARTIAL_OR_FAIL"
    out = {
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
    }
    write_json(OUT, out)
    print("SIG_E_SHADOW_LANE1B_STATUS_HOTFIX1D_WORKFLOW_PATCH_" + status)
    for r in results:
        print(r["file"] + " -> " + str(r["reason"]))
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
