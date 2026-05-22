import json
import re
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-OBSREPORT1-WORKFLOW-PATCH"
WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
COMMIT_SCRIPT = Path("scripts/commit_sig_e_shadow_persistence_outputs.py")
OUT = Path("outputs/_sig_e_shadow_report1/sig_e_shadow_obsreport1_workflow_patch_result.json")

REPORT_LINES = """          python scripts/build_sig_e_shadow_observation_report1.py
          python scripts/validate_sig_e_shadow_observation_report1.py

"""

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def patch_workflow():
    item = {"path": str(WORKFLOW), "exists": WORKFLOW.exists(), "patched": False, "reason": None}
    if not WORKFLOW.exists():
        item["reason"] = "WORKFLOW_MISSING"
        return item
    text = WORKFLOW.read_text(encoding="utf-8-sig")
    if "build_sig_e_shadow_observation_report1.py" in text:
        item["reason"] = "ALREADY_PRESENT"
        return item

    backup = WORKFLOW.with_suffix(WORKFLOW.suffix + ".bak_sig_e_obsreport1")
    shutil.copyfile(WORKFLOW, backup)
    item["backup"] = str(backup)

    # Best case: inside existing chain run block, after portfolio validation and before persistence snapshot.
    anchor = "          python scripts/validate_sig_e_shadow_portfolio1.py\n\n          python scripts/build_sig_e_shadow_persistence1_snapshot.py"
    if anchor in text:
        text = text.replace(anchor, "          python scripts/validate_sig_e_shadow_portfolio1.py\n\n" + REPORT_LINES + "          python scripts/build_sig_e_shadow_persistence1_snapshot.py", 1)
        WORKFLOW.write_text(text, encoding="utf-8")
        item["patched"] = True
        item["reason"] = "INSERTED_IN_CHAIN_BEFORE_PERSISTENCE_SNAPSHOT"
        return item

    # Fallback: add separate steps after a portfolio validation step.
    step_anchor = "      - name: Validate SIG-E shadow portfolio 1"
    pos = text.find(step_anchor)
    if pos >= 0:
        next_step = text.find("\n      - name:", pos + len(step_anchor))
        if next_step < 0:
            next_step = len(text)
        block = """\n      - name: Build SIG-E shadow observation report 1\n        run: python scripts/build_sig_e_shadow_observation_report1.py\n\n      - name: Validate SIG-E shadow observation report 1\n        run: python scripts/validate_sig_e_shadow_observation_report1.py\n"""
        text = text[:next_step] + block + text[next_step:]
        WORKFLOW.write_text(text, encoding="utf-8")
        item["patched"] = True
        item["reason"] = "INSERTED_AS_SEPARATE_STEPS_AFTER_PORTFOLIO_VALIDATE"
        return item

    item["reason"] = "ANCHOR_NOT_FOUND"
    return item

def patch_commit_script():
    item = {"path": str(COMMIT_SCRIPT), "exists": COMMIT_SCRIPT.exists(), "patched": False, "reason": None}
    if not COMMIT_SCRIPT.exists():
        item["reason"] = "COMMIT_SCRIPT_MISSING"
        return item
    text = COMMIT_SCRIPT.read_text(encoding="utf-8")
    additions = [
        '    "runtime/sig_e/shadow_observation_report_current.json",',
        '    "panel/brain4/sig_e_shadow_observation_report_current.json",',
        '    "outputs/_sig_e_shadow_report1",',
    ]
    if all(a in text for a in additions):
        item["reason"] = "ALREADY_PRESENT"
        return item

    backup = COMMIT_SCRIPT.with_suffix(COMMIT_SCRIPT.suffix + ".bak_sig_e_obsreport1")
    shutil.copyfile(COMMIT_SCRIPT, backup)
    item["backup"] = str(backup)

    marker = '    "outputs/_sig_e_shadow_workflow_chain1",'
    if marker in text:
        insert = "\n" + "\n".join(a for a in additions if a not in text)
        text = text.replace(marker, marker + insert, 1)
    else:
        # Append before closing SAFE_PATHS if marker is absent.
        text = text.replace("]\n\nAUTHORITY", "".join("\n" + a for a in additions if a not in text) + "\n]\n\nAUTHORITY", 1)
    COMMIT_SCRIPT.write_text(text, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "ADDED_REPORT_OUTPUTS_TO_SAFE_PATHS"
    return item

def main():
    wf = patch_workflow()
    cs = patch_commit_script()
    status = "PASS" if (wf["patched"] or wf["reason"] == "ALREADY_PRESENT") and (cs["patched"] or cs["reason"] == "ALREADY_PRESENT") else "PARTIAL_OR_FAIL"
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "patch_status": status,
        "workflow": wf,
        "commit_script": cs,
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
    print("SIG_E_SHADOW_OBSREPORT1_WORKFLOW_PATCH_" + status)
    print("Workflow:", wf["reason"])
    print("Commit script:", cs["reason"])
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
