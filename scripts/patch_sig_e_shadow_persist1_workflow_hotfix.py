from pathlib import Path
from datetime import datetime
import json
import shutil
import re

PROGRAM = "SIG-E-SHADOW-PERSIST1-WORKFLOW-HOTFIX"

WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
OUT = Path("outputs/_sig_e_shadow_persist1/sig_e_shadow_persist1_workflow_hotfix_result.json")

RESTORE_STEP = """      - name: Restore SIG-E shadow persistence 1
        run: python scripts/restore_sig_e_shadow_persistence1.py

"""

SNAPSHOT_STEPS = """      - name: Build SIG-E shadow persistence 1 snapshot
        run: python scripts/build_sig_e_shadow_persistence1_snapshot.py

      - name: Validate SIG-E shadow persistence 1
        run: python scripts/validate_sig_e_shadow_persistence1.py

"""

REQUIRED_MARKERS = [
    "restore_sig_e_shadow_persistence1.py",
    "build_sig_e_shadow_persistence1_snapshot.py",
    "validate_sig_e_shadow_persistence1.py",
]

OBSLEDGER_MARKERS = [
    "build_sig_e_shadow_detector1_obsledger.py",
    "build_sig_e_shadow_detector2_obsledger.py",
]

PORTFOLIO_MARKERS = [
    "validate_sig_e_shadow_portfolio1.py",
    "build_sig_e_shadow_portfolio1.py",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def split_steps(lines):
    # Return list of (start_index, end_index, block_text)
    # A step starts at a line beginning with 6 spaces + "- name:".
    starts = []
    for i, line in enumerate(lines):
        if re.match(r"^      - name:", line):
            starts.append(i)
    steps = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        steps.append((start, end, "".join(lines[start:end])))
    return steps

def find_step_index_containing(lines, markers):
    for start, end, block in split_steps(lines):
        for marker in markers:
            if marker in block:
                return start, end, marker
    return None, None, None

def insert_before_step(text, markers, block_to_insert, already_marker):
    if already_marker in text:
        return text, False, "ALREADY_PRESENT"
    lines = text.splitlines(keepends=True)
    start, end, marker = find_step_index_containing(lines, markers)
    if start is None:
        return text, False, "ANCHOR_NOT_FOUND"
    new_lines = lines[:start] + block_to_insert.splitlines(keepends=True) + lines[start:]
    return "".join(new_lines), True, "INSERTED_BEFORE_" + marker

def insert_after_step(text, markers, block_to_insert, already_marker):
    if already_marker in text:
        return text, False, "ALREADY_PRESENT"
    lines = text.splitlines(keepends=True)
    start, end, marker = find_step_index_containing(lines, markers)
    if start is None:
        return text, False, "ANCHOR_NOT_FOUND"
    new_lines = lines[:end] + block_to_insert.splitlines(keepends=True) + lines[end:]
    return "".join(new_lines), True, "INSERTED_AFTER_" + marker

def append_manual_note(text):
    note = """

# SIG-E-SHADOW-PERSIST1-WORKFLOW-HOTFIX:
# The automatic patch could not find safe anchors. Add these steps manually:
#
#      - name: Restore SIG-E shadow persistence 1
#        run: python scripts/restore_sig_e_shadow_persistence1.py
#
#      - name: Build SIG-E shadow persistence 1 snapshot
#        run: python scripts/build_sig_e_shadow_persistence1_snapshot.py
#
#      - name: Validate SIG-E shadow persistence 1
#        run: python scripts/validate_sig_e_shadow_persistence1.py
"""
    if "SIG-E-SHADOW-PERSIST1-WORKFLOW-HOTFIX" not in text:
        return text.rstrip() + note + "\n", True
    return text, False

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "workflow": str(WORKFLOW),
        "workflow_exists": WORKFLOW.exists(),
        "patch_status": "UNKNOWN",
        "restore_step_action": None,
        "snapshot_steps_action": None,
        "required_markers_present_after": {},
        "notes": [],
    }

    if not WORKFLOW.exists():
        result["patch_status"] = "FAIL_WORKFLOW_NOT_FOUND"
        write_json(OUT, result)
        print("SIG_E_SHADOW_PERSIST1_WORKFLOW_HOTFIX_FAIL")
        print("Workflow not found:", WORKFLOW)
        raise SystemExit(1)

    original = WORKFLOW.read_text(encoding="utf-8")
    text = original

    # Backup first.
    backup = WORKFLOW.with_suffix(WORKFLOW.suffix + ".bak_sig_e_persist1_workflow_hotfix")
    shutil.copyfile(WORKFLOW, backup)
    result["backup"] = str(backup)

    # Restore must run before any obsledger build, otherwise state may already be reset.
    text, changed_restore, action_restore = insert_before_step(
        text,
        OBSLEDGER_MARKERS,
        RESTORE_STEP,
        "restore_sig_e_shadow_persistence1.py"
    )
    result["restore_step_action"] = action_restore

    # Snapshot/validate should run after portfolio validation/build, or after obsledger if portfolio anchor is absent.
    text2, changed_snapshot, action_snapshot = insert_after_step(
        text,
        PORTFOLIO_MARKERS,
        SNAPSHOT_STEPS,
        "build_sig_e_shadow_persistence1_snapshot.py"
    )
    if action_snapshot == "ANCHOR_NOT_FOUND":
        text2, changed_snapshot, action_snapshot = insert_after_step(
            text,
            ["validate_sig_e_shadow_detector2_obsledger.py", "build_sig_e_shadow_detector2_obsledger.py"],
            SNAPSHOT_STEPS,
            "build_sig_e_shadow_persistence1_snapshot.py"
        )
    text = text2
    result["snapshot_steps_action"] = action_snapshot

    if action_restore == "ANCHOR_NOT_FOUND" or action_snapshot == "ANCHOR_NOT_FOUND":
        text, note_added = append_manual_note(text)
        result["notes"].append("One or more anchors were not found; manual note appended to workflow.")
        if note_added:
            result["notes"].append("Manual YAML snippet appended as comments.")

    WORKFLOW.write_text(text, encoding="utf-8")

    for marker in REQUIRED_MARKERS:
        result["required_markers_present_after"][marker] = marker in text

    if all(result["required_markers_present_after"].values()):
        result["patch_status"] = "PASS"
    else:
        result["patch_status"] = "PARTIAL_MANUAL_REVIEW_REQUIRED"

    write_json(OUT, result)

    print("SIG_E_SHADOW_PERSIST1_WORKFLOW_HOTFIX_" + result["patch_status"])
    print("Restore:", action_restore)
    print("Snapshot:", action_snapshot)
    for marker, present in result["required_markers_present_after"].items():
        print(marker + "=" + str(present))
    print("Result:", OUT)

    if result["patch_status"] != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
