#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import json

SCRIPTS = [
    "scripts/fix_shadow_outcome_01a_price_anchor.py",
    "scripts/run_sig_shadow_outcome_01.py",
    "scripts/build_shadow_outcome_01a_price_anchor_status.py",
    "scripts/validate_shadow_outcome_01a_price_anchor.py",
]

for script in SCRIPTS:
    print(f"RUN: {sys.executable} {script}")
    subprocess.check_call([sys.executable, script])

print(json.dumps({
    "status": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_PIPELINE_COMPLETED",
    "signal_authorized": False,
    "broker_execution_authorized": False,
    "pnl_authorized": False,
    "entry_stop_target_authorized": False,
}, indent=2))
