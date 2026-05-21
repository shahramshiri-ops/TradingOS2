#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
failures = []
warnings = []

index = ROOT / "panel/brain4/index.html"
js = ROOT / "panel/brain4/assets/shadow_ops_panel.js"
css = ROOT / "panel/brain4/assets/shadow_ops_panel.css"
ops_json = ROOT / "panel/brain4/shadow_ops_status_current.json"

if not index.exists():
    failures.append("missing panel/brain4/index.html")
else:
    text = index.read_text(encoding="utf-8", errors="ignore")
    if "assets/shadow_ops_panel.css" not in text:
        failures.append("index.html does not load shadow_ops_panel.css")
    if "assets/shadow_ops_panel.js" not in text:
        failures.append("index.html does not load shadow_ops_panel.js")

if not js.exists():
    failures.append("missing shadow_ops_panel.js")
else:
    jst = js.read_text(encoding="utf-8", errors="ignore")
    for token in ["SHADOW_PANEL_02", "shadow_ops_status_current.json", "NOT_SIGNAL", "NO_ENTRY_STOP_TARGET"]:
        if token not in jst:
            failures.append(f"shadow_ops_panel.js missing token {token}")

if not css.exists():
    failures.append("missing shadow_ops_panel.css")

if ops_json.exists():
    try:
        data = json.loads(ops_json.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False)
        for forbidden in [
            '"signal_authorized": true',
            '"trade_instruction_authorized": true',
            '"broker_execution_authorized": true',
            '"auto_learning_authorized": true',
            '"rule_rewrite_authorized": true',
        ]:
            if forbidden in text:
                failures.append(f"shadow_ops_status has forbidden flag {forbidden}")
    except Exception as e:
        failures.append(f"shadow_ops_status_current.json parse error: {e}")
else:
    warnings.append("panel/brain4/shadow_ops_status_current.json not found; UI will show fallback until workflow deploys it")

result = {
    "validation_name": "SHADOW_PANEL_02_INSTALL_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = ROOT / "proofs/shadow_panel_02_install_validation_result.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))

if failures:
    raise SystemExit(1)
