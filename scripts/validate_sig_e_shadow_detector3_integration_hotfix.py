
import json
from pathlib import Path
from datetime import datetime

OUT = Path("outputs/_sig_e_shadow_detector3/sig_e_shadow_detector3_integration_hotfix_validation_result.json")

FILES = {
    "portfolio": Path("scripts/build_sig_e_shadow_portfolio1.py"),
    "report": Path("scripts/build_sig_e_shadow_observation_report1.py"),
    "restore": Path("scripts/restore_sig_e_shadow_persistence1.py"),
    "snapshot": Path("scripts/build_sig_e_shadow_persistence1_snapshot.py"),
    "workflow": Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml"),
    "commit": Path("scripts/commit_sig_e_shadow_persistence_outputs.py"),
}

REQUIRED = {
    "portfolio": ["SIGE_SD3_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15", "shadow_detector_eurusd_london_pdlow_trap_long_current.json"],
    "report": ["eurusd_london_pdlow_trap_long_obsledger_v1.json"],
    "restore": ["lane3_obsledger_state", "lane3_detector_state"],
    "snapshot": ["lane3_obsledger_state", "lane3_detector_state", "lane3_obsledger_current"],
    "workflow": ["build_sig_e_shadow_detector3_eurusd_pdlow_trap_long.py", "build_sig_e_shadow_detector3_obsledger.py"],
    "commit": ["shadow_detector_eurusd_london_pdlow_trap_long_current.json", "outputs/_sig_e_shadow_detector3"],
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def main():
    errors = []
    checks = {}
    for key, path in FILES.items():
        item = {"exists": path.exists(), "missing_markers": []}
        if not path.exists():
            errors.append(f"{key} missing: {path}")
        else:
            txt = path.read_text(encoding="utf-8-sig")
            for marker in REQUIRED[key]:
                if marker not in txt:
                    item["missing_markers"].append(marker)
                    errors.append(f"{key} missing marker: {marker}")
        checks[key] = item

    result = {
        "program": "SIG-E-SHADOW-DETECTOR3-INTEGRATION-HOTFIX-VALIDATION",
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checks": checks,
        "not_authorized": [
            "signal",
            "manual trade proposal",
            "entry/stop/target",
            "risk sizing",
            "broker/execution",
            "auto execution",
            "memory promotion",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("SIG_E_SHADOW_DETECTOR3_INTEGRATION_HOTFIX_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
