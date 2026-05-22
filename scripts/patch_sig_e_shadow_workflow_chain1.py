from pathlib import Path
from datetime import datetime
import json
import shutil
import re

PROGRAM = "SIG-E-SHADOW-WORKFLOW-CHAIN1"

WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
OUT = Path("outputs/_sig_e_shadow_workflow_chain1/sig_e_shadow_workflow_chain1_patch_result.json")

CHAIN_MARKER = "Build SIG-E shadow detector portfolio and persistence chain"
COMMIT_MARKER = "Commit SIG-E shadow persistence generated outputs"

CHAIN_STEP = """      # SIG-E-SHADOW-WORKFLOW-CHAIN1 — detectors + ledgers + portfolio + persistence (NOT_SIGNAL)
      - name: Build SIG-E shadow detector portfolio and persistence chain
        run: |
          set -e
          python scripts/restore_sig_e_shadow_persistence1.py

          python scripts/build_sig_e_shadow_detector1_usdjpy_london_long.py
          python scripts/validate_sig_e_shadow_detector1.py
          python scripts/build_sig_e_shadow_detector1_obsledger.py
          python scripts/validate_sig_e_shadow_detector1_obsledger.py

          python scripts/build_sig_e_shadow_detector2_usdjpy_asia_short.py
          python scripts/validate_sig_e_shadow_detector2.py
          python scripts/build_sig_e_shadow_detector2_obsledger.py
          python scripts/validate_sig_e_shadow_detector2_obsledger.py

          python scripts/build_sig_e_shadow_portfolio1.py
          python scripts/validate_sig_e_shadow_portfolio1.py

          python scripts/build_sig_e_shadow_persistence1_snapshot.py
          python scripts/validate_sig_e_shadow_persistence1.py

"""

COMMIT_STEP = """      - name: Commit SIG-E shadow persistence generated outputs
        if: success()
        run: python scripts/commit_sig_e_shadow_persistence_outputs.py

"""

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def split_steps(lines):
    starts = []
    for i, line in enumerate(lines):
        if re.match(r"^      - name:", line):
            starts.append(i)
    steps = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        steps.append((start, end, "".join(lines[start:end])))
    return steps

def find_step_by_name_contains(lines, text):
    for start, end, block in split_steps(lines):
        if text in block:
            return start, end, block
    return None, None, None

def insert_after_named_step(workflow_text, anchor_text, insert_text, marker):
    if marker in workflow_text:
        return workflow_text, False, "ALREADY_PRESENT"
    lines = workflow_text.splitlines(keepends=True)
    start, end, block = find_step_by_name_contains(lines, anchor_text)
    if start is None:
        return workflow_text, False, "ANCHOR_NOT_FOUND"
    new_lines = lines[:end] + insert_text.splitlines(keepends=True) + lines[end:]
    return "".join(new_lines), True, "INSERTED_AFTER_" + anchor_text

def insert_before_named_step(workflow_text, anchor_text, insert_text, marker):
    if marker in workflow_text:
        return workflow_text, False, "ALREADY_PRESENT"
    lines = workflow_text.splitlines(keepends=True)
    start, end, block = find_step_by_name_contains(lines, anchor_text)
    if start is None:
        return workflow_text, False, "ANCHOR_NOT_FOUND"
    new_lines = lines[:start] + insert_text.splitlines(keepends=True) + lines[start:]
    return "".join(new_lines), True, "INSERTED_BEFORE_" + anchor_text

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "workflow": str(WORKFLOW),
        "workflow_exists": WORKFLOW.exists(),
        "patch_status": "UNKNOWN",
        "chain_step_action": None,
        "commit_step_action": None,
        "required_markers_present_after": {},
        "notes": [],
    }

    if not WORKFLOW.exists():
        result["patch_status"] = "FAIL_WORKFLOW_NOT_FOUND"
        write_json(OUT, result)
        print("SIG_E_SHADOW_WORKFLOW_CHAIN1_FAIL_WORKFLOW_NOT_FOUND")
        raise SystemExit(1)

    original = WORKFLOW.read_text(encoding="utf-8-sig")
    text = original

    backup = WORKFLOW.with_suffix(WORKFLOW.suffix + ".bak_sig_e_shadow_workflow_chain1")
    shutil.copyfile(WORKFLOW, backup)
    result["backup"] = str(backup)

    # Main chain must run after REGIME1 so detectors consume fresh market_state.
    text, changed_chain, action_chain = insert_after_named_step(
        text,
        "Build SIG-E-REGIME1 market state context",
        CHAIN_STEP,
        CHAIN_MARKER
    )
    result["chain_step_action"] = action_chain

    # Persistence/current mirrors must be committed before Deploy Pages trigger.
    text, changed_commit, action_commit = insert_before_named_step(
        text,
        "Trigger static Pages deploy after live refresh",
        COMMIT_STEP,
        COMMIT_MARKER
    )
    result["commit_step_action"] = action_commit

    # Remove old commented manual note if present so future Select-String is meaningful.
    old_note = re.compile(
        r"\n# SIG-E-SHADOW-PERSIST1-WORKFLOW-HOTFIX:.*?Validate SIG-E shadow persistence 1\n",
        re.DOTALL
    )
    text = old_note.sub("\n", text)

    WORKFLOW.write_text(text, encoding="utf-8")

    required = [
        "restore_sig_e_shadow_persistence1.py",
        "build_sig_e_shadow_detector1_usdjpy_london_long.py",
        "build_sig_e_shadow_detector1_obsledger.py",
        "build_sig_e_shadow_detector2_usdjpy_asia_short.py",
        "build_sig_e_shadow_detector2_obsledger.py",
        "build_sig_e_shadow_portfolio1.py",
        "build_sig_e_shadow_persistence1_snapshot.py",
        "validate_sig_e_shadow_persistence1.py",
        "commit_sig_e_shadow_persistence_outputs.py",
    ]
    for marker in required:
        result["required_markers_present_after"][marker] = marker in text

    if action_chain.startswith("INSERTED") and action_commit.startswith("INSERTED") and all(result["required_markers_present_after"].values()):
        result["patch_status"] = "PASS"
    elif "ALREADY_PRESENT" in (action_chain, action_commit) and all(result["required_markers_present_after"].values()):
        result["patch_status"] = "PASS_ALREADY_PRESENT"
    else:
        result["patch_status"] = "FAIL_OR_PARTIAL"

    write_json(OUT, result)

    print("SIG_E_SHADOW_WORKFLOW_CHAIN1_" + result["patch_status"])
    print("Chain:", action_chain)
    print("Commit:", action_commit)
    for marker, present in result["required_markers_present_after"].items():
        print(marker + "=" + str(present))
    print("Result:", OUT)

    if not result["patch_status"].startswith("PASS"):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
