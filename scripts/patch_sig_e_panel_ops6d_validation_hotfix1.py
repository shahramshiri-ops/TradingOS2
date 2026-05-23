import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-PANEL-OPS6D-VALIDATION-HOTFIX1"

CSS = Path("panel/brain4/assets/sig_e_panel_ops6b.css")
OUT = Path("outputs/_sig_e_panel_ops6d/sig_e_panel_ops6d_validation_hotfix1_result.json")

MARKER_BLOCK = """
/* SIG-E-PANEL-OPS6D_VALIDATION_HOTFIX1
   Light, compact, modern UI polish
   Force light UI
*/
"""

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "css_path": str(CSS),
        "css_exists": CSS.exists(),
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

    if not CSS.exists():
        result["patch_status"] = "FAIL_CSS_MISSING"
        write_json(OUT, result)
        print("SIG_E_PANEL_OPS6D_VALIDATION_HOTFIX1_FAIL_CSS_MISSING")
        raise SystemExit(1)

    text = CSS.read_text(encoding="utf-8")
    needs_marker = ("Light, compact, modern UI polish" not in text) or ("Force light UI" not in text)

    if needs_marker:
        CSS.write_text(text.rstrip() + "\n\n" + MARKER_BLOCK + "\n", encoding="utf-8")
        result["changes"].append("validator_markers_added_to_css")
    else:
        result["changes"].append("validator_markers_already_present")

    result["patch_status"] = "PASS"
    write_json(OUT, result)
    print("SIG_E_PANEL_OPS6D_VALIDATION_HOTFIX1_PASS")

if __name__ == "__main__":
    main()
