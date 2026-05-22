
import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-PANEL-OPS6C-VISUAL-POLISH-VALIDATION"

FILES = {
    "index": Path("panel/brain4/index.html"),
    "css": Path("panel/brain4/assets/sig_e_panel_ops6b.css"),
    "js": Path("panel/brain4/assets/sig_e_panel_ops6b.js"),
}
OUT = Path("outputs/_sig_e_panel_ops6c/sig_e_panel_ops6c_validation_result.json")

REQUIRED_MARKERS = {
    "index": [
        "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0",
        "tabbar-shell",
        "tabUpdateAge",
        "tabUpdateTime",
        "Cockpit",
        "Diagnostics",
    ],
    "css": [
        "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0",
        ".tabbar-shell",
        ".tab-update-age",
        "color-scheme: dark",
        "@media (prefers-color-scheme: light)",
        "low contrast",
    ],
    "js": [
        "SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0",
        "function updateTabRefreshAge",
        "Updated just now",
        "Updated ${age}m ago",
        "tabUpdateAge",
        "tabUpdateTime",
    ],
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def main():
    errors = []
    checks = {}
    for key, path in FILES.items():
        item = {"path": str(path), "exists": path.exists(), "missing_markers": []}
        if not path.exists():
            errors.append(f"missing {key}: {path}")
        else:
            text = path.read_text(encoding="utf-8")
            for marker in REQUIRED_MARKERS[key]:
                if marker not in text:
                    item["missing_markers"].append(marker)
                    errors.append(f"{key} missing marker: {marker}")
        checks[key] = item

    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checks": checks,
        "boundary": [
            "PANEL_VISUAL_POLISH_ONLY",
            "DISPLAY_ONLY",
            "SHADOW_RESEARCH_ONLY",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("SIG_E_PANEL_OPS6C_VALIDATION_" + result["validation_status"])
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
