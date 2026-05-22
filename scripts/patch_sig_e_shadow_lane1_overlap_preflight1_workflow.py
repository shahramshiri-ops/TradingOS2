import json
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-LANE1-OVERLAP-PREFLIGHT1-WORKFLOW-PATCH"

OUT = Path("outputs/_sig_e_shadow_lane1_overlap_preflight1/sig_e_shadow_lane1_overlap_preflight1_workflow_patch_result.json")
WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
COMMIT = Path("scripts/commit_sig_e_shadow_persistence_outputs.py")

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def backup(path):
    b = path.with_suffix(path.suffix + ".bak_lane1_overlap_preflight1")
    shutil.copyfile(path, b)
    return str(b)

def patch_workflow():
    item = {"file": str(WORKFLOW), "exists": WORKFLOW.exists(), "patched": False, "reason": None}
    if not WORKFLOW.exists():
        item["reason"] = "MISSING"
        return item

    text = WORKFLOW.read_text(encoding="utf-8-sig")
    if "build_sig_e_shadow_lane1_overlap_preflight1.py" in text:
        item["reason"] = "ALREADY_PRESENT"
        return item

    block = """          python scripts/build_sig_e_shadow_lane1_overlap_preflight1.py
          python scripts/validate_sig_e_shadow_lane1_overlap_preflight1.py

"""

    anchor = "          python scripts/build_sig_e_shadow_coverage1.py"
    if anchor in text:
        anchor2 = "          python scripts/validate_sig_e_shadow_coverage1.py"
        if anchor2 in text:
            text = text.replace(anchor2, anchor2 + "\n" + block.rstrip("\n"), 1)
        else:
            text = text.replace(anchor, anchor + "\n" + block.rstrip("\n"), 1)
    else:
        anchor = "          python scripts/build_sig_e_shadow_persistence1_snapshot.py"
        if anchor not in text:
            item["reason"] = "WORKFLOW_ANCHOR_NOT_FOUND"
            return item
        text = text.replace(anchor, block + anchor, 1)

    item["backup"] = backup(WORKFLOW)
    WORKFLOW.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "PREFLIGHT_ADDED_TO_WORKFLOW"
    return item

def patch_commit():
    item = {"file": str(COMMIT), "exists": COMMIT.exists(), "patched": False, "reason": None}
    if not COMMIT.exists():
        item["reason"] = "MISSING"
        return item

    text = COMMIT.read_text(encoding="utf-8")
    additions = [
        '    "runtime/sig_e/shadow_lane1_overlap_preflight_current.json",',
        '    "panel/brain4/sig_e_shadow_lane1_overlap_preflight_current.json",',
        '    "outputs/_sig_e_shadow_lane1_overlap_preflight1",',
    ]
    missing = [a for a in additions if a not in text]
    if not missing:
        item["reason"] = "ALREADY_PRESENT"
        return item

    marker = '    "outputs/_sig_e_shadow_coverage1",'
    if marker not in text:
        marker = '    "outputs/_sig_e_shadow_report1",'
    if marker not in text:
        marker = '    "outputs/_sig_e_shadow_persist1",'
    if marker not in text:
        item["reason"] = "COMMIT_SAFE_PATH_MARKER_NOT_FOUND"
        return item

    item["backup"] = backup(COMMIT)
    text = text.replace(marker, marker + "\n" + "\n".join(missing), 1)
    COMMIT.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "PREFLIGHT_ADDED_TO_COMMIT_SAFE_PATHS"
    return item

def main():
    results = [patch_workflow(), patch_commit()]
    status = "PASS" if all(x.get("patched") or x.get("reason") == "ALREADY_PRESENT" for x in results) else "PARTIAL_OR_FAIL"
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
        },
    }
    write_json(OUT, result)

    print("SIG_E_SHADOW_LANE1_OVERLAP_PREFLIGHT1_WORKFLOW_PATCH_" + status)
    for r in results:
        print(r["file"] + " -> " + str(r["reason"]))
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
