#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess, sys, json
from pathlib import Path

for script in ["scripts/build_shadow_outcome_01b_price_source_bridge.py", "scripts/patch_shadow_outcome_01b_use_price_bridge.py"]:
    print(f"RUN: {sys.executable} {script}")
    subprocess.check_call([sys.executable, script])

if Path("scripts/run_shadow_outcome_01a_price_anchor.py").exists():
    runner = "scripts/run_shadow_outcome_01a_price_anchor.py"
elif Path("scripts/run_sig_shadow_outcome_01.py").exists():
    runner = "scripts/run_sig_shadow_outcome_01.py"
else:
    raise SystemExit("No shadow outcome runner found")
print(f"RUN: {sys.executable} {runner}")
subprocess.check_call([sys.executable, runner])

print(f"RUN: {sys.executable} scripts/validate_shadow_outcome_01b_price_source_bridge.py")
subprocess.check_call([sys.executable, "scripts/validate_shadow_outcome_01b_price_source_bridge.py"])

print(json.dumps({"status": "SHADOW_OUTCOME_01B_PRICE_SOURCE_BRIDGE_PIPELINE_COMPLETED", "signal_authorized": False, "broker_execution_authorized": False, "pnl_authorized": False, "entry_stop_target_authorized": False}, indent=2))
