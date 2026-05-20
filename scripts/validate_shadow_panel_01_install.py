from pathlib import Path
import json
from datetime import datetime

ROOT = Path.cwd()
failures = []
warnings = []

index = ROOT / "panel" / "brain4" / "index.html"
js = ROOT / "panel" / "brain4" / "assets" / "shadow_panel_status.js"
css = ROOT / "panel" / "brain4" / "assets" / "shadow_panel_status.css"
panel_status = ROOT / "panel" / "brain4" / "shadow_panel_status_current.json"
runtime_status = ROOT / "runtime" / "sig_shadow" / "shadow_panel_status_current.json"

if not index.exists():
    failures.append("missing panel/brain4/index.html")
else:
    text = index.read_text(encoding="utf-8", errors="ignore")
    if "assets/shadow_panel_status.css" not in text:
        failures.append("index.html does not load shadow_panel_status.css")
    if "assets/shadow_panel_status.js" not in text:
        failures.append("index.html does not load shadow_panel_status.js")

if not js.exists():
    failures.append("missing panel/brain4/assets/shadow_panel_status.js")
else:
    jst = js.read_text(encoding="utf-8", errors="ignore")
    required = ["SHADOW_PANEL_01", "NOT_SIGNAL", "NO_ENTRY_STOP_TARGET", "shadow_panel_status_current.json"]
    for token in required:
        if token not in jst:
            failures.append(f"shadow_panel_status.js missing token {token}")

if not css.exists():
    failures.append("missing panel/brain4/assets/shadow_panel_status.css")

if not panel_status.exists():
    warnings.append("panel/brain4/shadow_panel_status_current.json not present; UI will try runtime fallback where possible")
else:
    try:
        data = json.loads(panel_status.read_text(encoding="utf-8"))
        if data.get("signal_authorized") is not False:
            failures.append("panel shadow status must keep signal_authorized=false")
        if data.get("broker_execution_authorized") is not False:
            failures.append("panel shadow status must keep broker_execution_authorized=false")
    except Exception as e:
        failures.append(f"panel shadow status json parse error: {e}")

if not runtime_status.exists():
    warnings.append("runtime/sig_shadow/shadow_panel_status_current.json not present in local checkout")

result = {
    "validation_name": "SHADOW_PANEL_01_INSTALL_VALIDATION",
    "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
    },
}

out = ROOT / "proofs" / "shadow_panel_01_install_validation_result.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))

if failures:
    raise SystemExit(1)
