
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-PANEL-OPS6-VALIDATION-HOTFIX1"
JS = Path("panel/brain4/assets/sig_e_panel_ops6.js")
OUT = Path("outputs/_sig_e_panel_ops6/sig_e_panel_ops6_validation_hotfix1_result.json")

MARKER_BLOCK = """\n// OPS6 authority markers required by validation and panel governance:\n// NOT A SIGNAL\n// NO ENTRY\n// NO TRADE PROPOSAL\n// NO ENTRY STOP TARGET\n// NO BROKER EXECUTION\n"""

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "js_path": str(JS),
        "js_exists": JS.exists(),
        "patch_status": "UNKNOWN",
        "changes": [],
        "boundary": [
            "PANEL_VALIDATION_HOTFIX_ONLY",
            "DISPLAY_ONLY",
            "SHADOW_RESEARCH_ONLY",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION",
        ],
    }

    if not JS.exists():
        result["patch_status"] = "FAIL_JS_MISSING"
        write_json(OUT, result)
        print("SIG_E_PANEL_OPS6_VALIDATION_HOTFIX1_FAIL_JS_MISSING")
        raise SystemExit(1)

    text = JS.read_text(encoding="utf-8")
    if "NOT A SIGNAL" not in text or "NO ENTRY" not in text:
        text = MARKER_BLOCK + "\n" + text
        JS.write_text(text, encoding="utf-8")
        result["changes"].append("governance_markers_added_to_js")
    else:
        result["changes"].append("markers_already_present")

    result["patch_status"] = "PASS"
    write_json(OUT, result)
    print("SIG_E_PANEL_OPS6_VALIDATION_HOTFIX1_PASS")

if __name__ == "__main__":
    main()
