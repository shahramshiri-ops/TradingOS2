#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import json
from pathlib import Path

# Guard the price bridge first.
print(f"RUN: {sys.executable} scripts/build_shadow_outcome_01d_freshness_closed_h1_guard.py")
subprocess.check_call([sys.executable, "scripts/build_shadow_outcome_01d_freshness_closed_h1_guard.py"])

# Rerun outcome after the closed-H1 guard.
if Path("scripts/run_shadow_outcome_01a_price_anchor.py").exists():
    outcome_runner = "scripts/run_shadow_outcome_01a_price_anchor.py"
elif Path("scripts/run_sig_shadow_outcome_01.py").exists():
    outcome_runner = "scripts/run_sig_shadow_outcome_01.py"
else:
    raise SystemExit("No shadow outcome runner found")

print(f"RUN: {sys.executable} {outcome_runner}")
subprocess.check_call([sys.executable, outcome_runner])

# Build completion/carry-forward state.
print(f"RUN: {sys.executable} scripts/build_shadow_outcome_01d_completion_state.py")
subprocess.check_call([sys.executable, "scripts/build_shadow_outcome_01d_completion_state.py"])

print(f"RUN: {sys.executable} scripts/validate_shadow_outcome_01d.py")
subprocess.check_call([sys.executable, "scripts/validate_shadow_outcome_01d.py"])

print(json.dumps({
    "status": "SHADOW_OUTCOME_01D_PIPELINE_COMPLETED",
    "signal_authorized": False,
    "broker_execution_authorized": False,
    "pnl_authorized": False,
    "entry_stop_target_authorized": False,
}, indent=2))
