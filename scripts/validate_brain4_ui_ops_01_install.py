#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
failures = []
warnings = []

index = ROOT / 'panel/brain4/index.html'
js = ROOT / 'panel/brain4/assets/brain4_ui_ops_01.js'
css = ROOT / 'panel/brain4/assets/brain4_ui_ops_01.css'

if not index.exists():
    failures.append('missing panel/brain4/index.html')
else:
    text = index.read_text(encoding='utf-8', errors='ignore')
    if 'assets/brain4_ui_ops_01.css' not in text:
        failures.append('index.html does not load brain4_ui_ops_01.css')
    if 'assets/brain4_ui_ops_01.js' not in text:
        failures.append('index.html does not load brain4_ui_ops_01.js')

if not js.exists():
    failures.append('missing brain4_ui_ops_01.js')
if not css.exists():
    failures.append('missing brain4_ui_ops_01.css')

result = {
    'validation_name': 'BRAIN4_UI_OPS_01_INSTALL_VALIDATION',
    'created_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
    'validation_status': 'PASS' if not failures else 'FAIL',
    'failures': failures,
    'warnings': warnings,
    'boundary': {
        'ui_only_patch': True,
        'signal_authorized': False,
        'broker_execution_authorized': False,
        'rule_rewrite_authorized': False,
    }
}

out = ROOT / 'proofs/brain4_ui_ops_01_install_validation_result.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
