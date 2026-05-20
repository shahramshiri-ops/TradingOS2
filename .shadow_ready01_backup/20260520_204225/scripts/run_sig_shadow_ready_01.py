#!/usr/bin/env python3
"""Run SHADOW-READY-01 once after SHADOW-01B integrated pipeline."""
from __future__ import annotations
import json, subprocess, sys

def run(args):
    print("RUN:", " ".join([sys.executable] + args))
    subprocess.run([sys.executable] + args, check=True)

def main() -> int:
    steps = [
        ["scripts/build_sig_shadow_ready_01_outputs.py"],
        ["scripts/validate_sig_shadow_ready_01_outputs.py"],
    ]
    for s in steps:
        run(s)
    print(json.dumps({
        "status": "SHADOW_READY_01_PIPELINE_COMPLETED",
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
