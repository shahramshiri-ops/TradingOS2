import json
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-PERSIST1-SNAPSHOT"

STATE_FILES = [
    {
        "logical_id": "lane1_obsledger_state",
        "source": "state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json",
        "counter": "refresh_records",
    },
    {
        "logical_id": "lane2_obsledger_state",
        "source": "state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json",
        "counter": "refresh_records",
    },
    {
        "logical_id": "lane1_detector_state",
        "source": "state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector/usdjpy_london_long_state_v1.json",
        "counter": "history",
    },
    {
        "logical_id": "lane2_detector_state",
        "source": "state/sig_e_shadow_detector2/usdjpy_asia_short_state_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector2/usdjpy_asia_short_state_v1.json",
        "counter": "history",
    },
]

CURRENT_FILES = [
    {
        "logical_id": "shadow_portfolio_current",
        "source": "runtime/sig_e/shadow_portfolio_current.json",
        "mirror": "panel/brain4/persist/current/shadow_portfolio_current.json",
    },
    {
        "logical_id": "lane1_obsledger_current",
        "source": "runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json",
        "mirror": "panel/brain4/persist/current/shadow_detector_usdjpy_london_long_obsledger_current.json",
    },
    {
        "logical_id": "lane2_obsledger_current",
        "source": "runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json",
        "mirror": "panel/brain4/persist/current/shadow_detector_usdjpy_asia_short_obsledger_current.json",
    },
]

OUT = Path("outputs/_sig_e_shadow_persist1/sig_e_shadow_persist1_snapshot_result.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_persistence_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_persistence_status_current.json")
MANIFEST = Path("panel/brain4/persist/sig_e_shadow_persistence_manifest.json")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

BOUNDARY = [
    "PERSISTENCE_SNAPSHOT_ONLY",
    "SHADOW_RESEARCH_ONLY",
    "NOT_SIGNAL",
    "NO_TRADE_PROPOSAL",
    "NO_ENTRY_STOP_TARGET",
    "NO_RISK_OR_POSITION_SIZING",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_EXECUTION",
    "NO_MEMORY_PROMOTION",
    "NO_RULE_REWRITE",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def count_records(obj, counter):
    if not isinstance(obj, dict):
        return 0
    v = obj.get(counter)
    return len(v) if isinstance(v, list) else 0

def mirror_file(source, mirror, counter=None):
    src = Path(source)
    dst = Path(mirror)
    item = {"source": source, "mirror": mirror, "source_exists": src.exists(), "mirrored": False, "count": None}
    if not src.exists():
        return item
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    item["mirrored"] = True
    obj = load_json(src)
    if counter:
        item["count"] = count_records(obj, counter)
    return item

def main():
    state_results = []
    for f in STATE_FILES:
        r = mirror_file(f["source"], f["mirror"], f["counter"])
        r["logical_id"] = f["logical_id"]
        state_results.append(r)

    current_results = []
    for f in CURRENT_FILES:
        r = mirror_file(f["source"], f["mirror"])
        r["logical_id"] = f["logical_id"]
        current_results.append(r)

    manifest = {
        "program": PROGRAM,
        "created_utc": now(),
        "state_files": state_results,
        "current_files": current_results,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
    }

    write_json(MANIFEST, manifest)

    current = {
        "program": PROGRAM,
        "created_utc": now(),
        "snapshot_status": "PASS",
        "state_files": state_results,
        "current_files": current_results,
        "manifest": str(MANIFEST),
        "lane1_refresh_count": next((x.get("count") for x in state_results if x.get("logical_id") == "lane1_obsledger_state"), None),
        "lane2_refresh_count": next((x.get("count") for x in state_results if x.get("logical_id") == "lane2_obsledger_state"), None),
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "not_authorized": [
            "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
            "broker/execution", "auto execution", "memory promotion", "rule rewrite"
        ],
    }

    write_json(OUT, current)
    write_json(RUNTIME_OUT, current)
    write_json(PANEL_OUT, current)

    print("SIG_E_SHADOW_PERSIST1_SNAPSHOT_DONE")
    print("LANE1_REFRESH_COUNT=" + str(current["lane1_refresh_count"]))
    print("LANE2_REFRESH_COUNT=" + str(current["lane2_refresh_count"]))
    print("Manifest:", MANIFEST)

if __name__ == "__main__":
    main()
