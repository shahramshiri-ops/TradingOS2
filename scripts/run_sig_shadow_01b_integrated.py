#!/usr/bin/env python3
"""
Run SHADOW-01B integrated shadow pipeline once.

This script is safe to call from the existing SIG live refresh workflow after
Brain4 payload has been built/validated.
"""
from __future__ import annotations

import json
import subprocess
import sys

def run(args):
    print("RUN:", " ".join([sys.executable] + args))
    subprocess.run([sys.executable] + args, check=True)

def main() -> int:
    steps = [
        ["scripts/build_sig_signal_candidate_shadow_intake.py"],
        ["scripts/update_sig_shadow_candidate_ledger.py"],
        ["scripts/update_sig_shadow_observations.py"],
        ["scripts/summarize_sig_shadow_ledger.py"],
        ["scripts/validate_sig_shadow_01b_integrated_outputs.py"],
    ]
    for s in steps:
        run(s)
    print(json.dumps({
        "status": "SIG_SHADOW_01B_INTEGRATED_PIPELINE_COMPLETED",
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
