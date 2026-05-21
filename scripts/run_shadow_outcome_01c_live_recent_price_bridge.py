#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import json
from pathlib import Path

for script in [
    "scripts/build_shadow_outcome_01c_live_recent_price_bridge.py",
    "scripts/patch_shadow_outcome_01c_use_live_recent_bridge.py",
]:
    print(f"RUN: {sys.executable} {script}")
    subprocess.check_call([sys.executable, script])

if Path("scripts/run_shadow_outcome_01a_price_anchor.py").exists():
    outcome_runner = "scripts/run_shadow_outcome_01a_price_anchor.py"
elif Path("scripts/run_sig_shadow_outcome_01.py").exists():
    outcome_runner = "scripts/run_sig_shadow_outcome_01.py"
else:
    raise SystemExit("No shadow outcome runner found")

print(f"RUN: {sys.executable} {outcome_runner}")
subprocess.check_call([sys.executable, outcome_runner])

print(f"RUN: {sys.executable} scripts/validate_shadow_outcome_01c_live_recent_price_bridge.py")
subprocess.check_call([sys.executable, "scripts/validate_shadow_outcome_01c_live_recent_price_bridge.py"])

print(json.dumps({
    "status": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_PIPELINE_COMPLETED",
    "signal_authorized": False,
    "broker_execution_authorized": False,
    "pnl_authorized": False,
    "entry_stop_target_authorized": False,
}, indent=2))
