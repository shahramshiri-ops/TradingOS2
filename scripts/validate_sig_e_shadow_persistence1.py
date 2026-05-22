import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-PERSIST1"

RUNTIME_RESTORE = Path("runtime/sig_e/shadow_persistence_restore_current.json")
RUNTIME_SNAPSHOT = Path("runtime/sig_e/shadow_persistence_current.json")
PANEL_SNAPSHOT = Path("panel/brain4/sig_e_shadow_persistence_status_current.json")
MANIFEST = Path("panel/brain4/persist/sig_e_shadow_persistence_manifest.json")
OUT = Path("outputs/_sig_e_shadow_persist1/sig_e_shadow_persist1_validation_result.json")

FORBIDDEN = [
    "signal_authorized",
    "trade_proposal_authorized",
    "entry_stop_target_authorized",
    "risk_sizing_authorized",
    "broker_execution_authorized",
    "auto_execution_authorized",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    errors = []
    payloads = {}
    for name, path in [("restore", RUNTIME_RESTORE), ("snapshot", RUNTIME_SNAPSHOT), ("panel_snapshot", PANEL_SNAPSHOT), ("manifest", MANIFEST)]:
        if not path.exists():
            errors.append(f"missing {name}: {path}")
        else:
            try:
                payloads[name] = load(path)
            except Exception as e:
                errors.append(f"bad json {name}: {e}")

    for name, obj in payloads.items():
        auth = obj.get("authority", {})
        for k in FORBIDDEN:
            if auth.get(k) is not False:
                errors.append(f"{name}.authority.{k} must be false")

    snapshot = payloads.get("snapshot", {})
    lane1 = snapshot.get("lane1_refresh_count")
    lane2 = snapshot.get("lane2_refresh_count")
    if lane1 is None:
        errors.append("lane1_refresh_count missing")
    if lane2 is None:
        errors.append("lane2_refresh_count missing")

    manifest = payloads.get("manifest", {})
    mirrored = [x for x in manifest.get("state_files", []) if x.get("mirrored")]
    if len(mirrored) < 2:
        errors.append("expected at least two mirrored state files")

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "lane1_refresh_count": lane1,
        "lane2_refresh_count": lane2,
        "restore_summary": {
            "restored_count": (payloads.get("restore") or {}).get("restored_count"),
            "remote_found_count": (payloads.get("restore") or {}).get("remote_found_count"),
        },
        "snapshot_status": snapshot.get("snapshot_status"),
        "current_runtime_authority": snapshot.get("authority"),
        "next_allowed_use": "LIVE_SHADOW_OBSERVATION_WITH_PERSISTENCE_ONLY",
        "not_authorized": [
            "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
            "broker/execution", "auto execution", "memory promotion", "rule rewrite"
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SIG_E_SHADOW_PERSIST1_VALIDATION_" + result["validation_status"])
    print("Result:", OUT)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
