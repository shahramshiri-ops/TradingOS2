
import json
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-DETECTOR3-INTEGRATION-HOTFIX"
OUT = Path("outputs/_sig_e_shadow_detector3/sig_e_shadow_detector3_integration_hotfix_result.json")

PORTFOLIO = Path("scripts/build_sig_e_shadow_portfolio1.py")
REPORT = Path("scripts/build_sig_e_shadow_observation_report1.py")
RESTORE = Path("scripts/restore_sig_e_shadow_persistence1.py")
SNAPSHOT = Path("scripts/build_sig_e_shadow_persistence1_snapshot.py")
WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
COMMIT = Path("scripts/commit_sig_e_shadow_persistence_outputs.py")

LANE3_ID = "SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15"

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def read(path):
    return path.read_text(encoding="utf-8-sig")

def write(path, text):
    path.write_text(text, encoding="utf-8")

def backup(path):
    b = path.with_suffix(path.suffix + ".bak_detector3_integration_hotfix")
    shutil.copyfile(path, b)
    return str(b)

def lines_to_text(lines):
    return "\n".join(lines) + "\n"

def patch_portfolio():
    item = {"file": str(PORTFOLIO), "exists": PORTFOLIO.exists(), "patched": False, "reason": None}
    if not PORTFOLIO.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(PORTFOLIO)
    if LANE3_ID in txt:
        item["reason"] = "ALREADY_PRESENT"
        return item

    lane = lines_to_text([
        '    {',
        '        "lane_id": "SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15",',
        '        "display_name": "EURUSD London/Overlap Prior-Day-Low Trap Long H1+M15",',
        '        "classification": "PRIMARY_SHADOW_OBSERVATION",',
        '        "instrument": "EURUSD",',
        '        "direction": "LONG",',
        '        "detector_file": Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json"),',
        '        "ledger_file": Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json"),',
        '        "expected_shadow_match_statuses": ["SHADOW_MATCH_CONFIRMED"],',
        '    },',
    ])

    marker = "]\n\nDATA_OR_FIELD_STATUSES"
    if marker not in txt:
        item["reason"] = "LANES_END_MARKER_NOT_FOUND"
        return item

    item["backup"] = backup(PORTFOLIO)
    txt = txt.replace(marker, lane + marker, 1)
    write(PORTFOLIO, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_PORTFOLIO"
    return item

def patch_report():
    item = {"file": str(REPORT), "exists": REPORT.exists(), "patched": False, "reason": None}
    if not REPORT.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(REPORT)
    changed = False
    if "eurusd_london_pdlow_trap_long_obsledger_v1.json" not in txt:
        marker = '    Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json"),'
        add = '    Path("state/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json"),'
        if marker not in txt:
            item["reason"] = "REPORT_STATE_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, marker + "\n" + add, 1)
        changed = True

    if "EURUSD_LONDON_PDLOW_TRAP_LONG" not in txt:
        marker2 = '    if "LONDON_LONG" in detector_id:\n        return "USDJPY London Long H1+M15"'
        repl2 = marker2 + '\n    if "EURUSD_LONDON_PDLOW_TRAP_LONG" in detector_id:\n        return "EURUSD London/Overlap Prior-Day-Low Trap Long H1+M15"'
        if marker2 in txt:
            txt = txt.replace(marker2, repl2, 1)
            changed = True

    if not changed:
        item["reason"] = "ALREADY_PRESENT"
        return item

    item["backup"] = backup(REPORT)
    write(REPORT, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_OBSREPORT"
    return item

def patch_restore():
    item = {"file": str(RESTORE), "exists": RESTORE.exists(), "patched": False, "reason": None}
    if not RESTORE.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(RESTORE)
    changed = False

    if "lane3_obsledger_state" not in txt:
        block = lines_to_text([
            '    {',
            '        "logical_id": "lane3_obsledger_state",',
            '        "local_path": "state/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json",',
            '        "mirror_path": "persist/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json",',
            '        "counter_key": "refresh_records",',
            '    },',
        ])
        marker = "]\n\nOUT = Path"
        if marker not in txt:
            item["reason"] = "RESTORE_FILES_END_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, block + marker, 1)
        changed = True

    if "lane3_detector_state" not in txt:
        block = lines_to_text([
            '    {',
            '        "logical_id": "lane3_detector_state",',
            '        "local_path": "state/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json",',
            '        "mirror_path": "persist/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json",',
            '        "counter_key": "history",',
            '    },',
        ])
        marker = "]\n\nOUT = Path"
        if marker not in txt:
            item["reason"] = "RESTORE_FILES_END_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, block + marker, 1)
        changed = True

    if not changed:
        item["reason"] = "ALREADY_PRESENT"
        return item

    item["backup"] = backup(RESTORE)
    write(RESTORE, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_RESTORE"
    return item

def patch_snapshot():
    item = {"file": str(SNAPSHOT), "exists": SNAPSHOT.exists(), "patched": False, "reason": None}
    if not SNAPSHOT.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(SNAPSHOT)
    changed = False

    if "lane3_obsledger_state" not in txt:
        block = lines_to_text([
            '    {',
            '        "logical_id": "lane3_obsledger_state",',
            '        "source": "state/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json",',
            '        "mirror": "panel/brain4/persist/sig_e_shadow_detector_observation/eurusd_london_pdlow_trap_long_obsledger_v1.json",',
            '        "counter": "refresh_records",',
            '    },',
        ])
        marker = "]\n\nCURRENT_FILES"
        if marker not in txt:
            item["reason"] = "SNAPSHOT_STATE_FILES_END_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, block + marker, 1)
        changed = True

    if "lane3_detector_state" not in txt:
        block = lines_to_text([
            '    {',
            '        "logical_id": "lane3_detector_state",',
            '        "source": "state/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json",',
            '        "mirror": "panel/brain4/persist/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json",',
            '        "counter": "history",',
            '    },',
        ])
        marker = "]\n\nCURRENT_FILES"
        if marker not in txt:
            item["reason"] = "SNAPSHOT_STATE_FILES_END_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, block + marker, 1)
        changed = True

    if "lane3_obsledger_current" not in txt:
        block = lines_to_text([
            '    {',
            '        "logical_id": "lane3_obsledger_current",',
            '        "source": "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json",',
            '        "mirror": "panel/brain4/persist/current/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json",',
            '    },',
            '    {',
            '        "logical_id": "lane3_detector_current",',
            '        "source": "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json",',
            '        "mirror": "panel/brain4/persist/current/shadow_detector_eurusd_london_pdlow_trap_long_current.json",',
            '    },',
        ])
        marker = "]\n\nOUT = Path"
        if marker not in txt:
            item["reason"] = "SNAPSHOT_CURRENT_FILES_END_MARKER_NOT_FOUND"
            return item
        txt = txt.replace(marker, block + marker, 1)
        changed = True

    if not changed:
        item["reason"] = "ALREADY_PRESENT"
        return item

    item["backup"] = backup(SNAPSHOT)
    write(SNAPSHOT, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_SNAPSHOT"
    return item

def patch_workflow():
    item = {"file": str(WORKFLOW), "exists": WORKFLOW.exists(), "patched": False, "reason": None}
    if not WORKFLOW.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(WORKFLOW)
    if "build_sig_e_shadow_detector3_eurusd_pdlow_trap_long.py" in txt:
        item["reason"] = "ALREADY_PRESENT"
        return item

    block = lines_to_text([
        '          python scripts/build_sig_e_shadow_detector3_eurusd_pdlow_trap_long.py',
        '          python scripts/validate_sig_e_shadow_detector3.py',
        '          python scripts/build_sig_e_shadow_detector3_obsledger.py',
        '          python scripts/validate_sig_e_shadow_detector3_obsledger.py',
        '',
    ])
    anchor = "          python scripts/build_sig_e_shadow_portfolio1.py"
    if anchor not in txt:
        item["reason"] = "WORKFLOW_PORTFOLIO_ANCHOR_NOT_FOUND"
        return item

    item["backup"] = backup(WORKFLOW)
    txt = txt.replace(anchor, block + anchor, 1)
    write(WORKFLOW, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_WORKFLOW_CHAIN"
    return item

def patch_commit():
    item = {"file": str(COMMIT), "exists": COMMIT.exists(), "patched": False, "reason": None}
    if not COMMIT.exists():
        item["reason"] = "MISSING"
        return item

    txt = read(COMMIT)
    additions = [
        '    "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json",',
        '    "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json",',
        '    "panel/brain4/sig_e_shadow_detector3_status_current.json",',
        '    "panel/brain4/sig_e_shadow_detector3_obsledger_status_current.json",',
        '    "state/sig_e_shadow_detector3",',
        '    "outputs/_sig_e_shadow_detector3",',
        '    "outputs/_sig_e_shadow_detector3_obsledger",',
    ]

    missing = [a for a in additions if a not in txt]
    if not missing:
        item["reason"] = "ALREADY_PRESENT"
        return item

    marker = '    "outputs/_sig_e_shadow_report1",'
    if marker not in txt:
        marker = '    "outputs/_sig_e_shadow_persist1",'
    if marker not in txt:
        item["reason"] = "COMMIT_SAFE_PATH_MARKER_NOT_FOUND"
        return item

    item["backup"] = backup(COMMIT)
    txt = txt.replace(marker, marker + "\n" + "\n".join(missing), 1)
    write(COMMIT, txt)
    item["patched"] = True
    item["reason"] = "LANE3_ADDED_TO_COMMIT_SAFE_PATHS"
    return item

def main():
    results = [
        patch_portfolio(),
        patch_report(),
        patch_restore(),
        patch_snapshot(),
        patch_workflow(),
        patch_commit(),
    ]
    status = "PASS" if all(r.get("patched") or r.get("reason") == "ALREADY_PRESENT" for r in results) else "PARTIAL_OR_FAIL"
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "patch_status": status,
        "results": results,
        "authority": AUTHORITY,
        "boundary": [
            "INTEGRATION_HOTFIX_ONLY",
            "SHADOW_RESEARCH_ONLY",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_RISK_OR_POSITION_SIZING",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION",
            "NO_MEMORY_PROMOTION",
            "NO_RULE_REWRITE",
        ],
    }
    write_json(OUT, result)

    print("SIG_E_SHADOW_DETECTOR3_INTEGRATION_HOTFIX_" + status)
    for r in results:
        print(r["file"] + " -> " + str(r["reason"]))
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
