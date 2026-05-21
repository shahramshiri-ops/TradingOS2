#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import json

SCRIPTS = [
    "scripts/build_sig_shadow_count_normalize_01_outputs.py",
    "scripts/validate_sig_shadow_count_normalize_01_outputs.py",
]

for script in SCRIPTS:
    print(f"RUN: {sys.executable} {script}")
    subprocess.check_call([sys.executable, script])

print(json.dumps({
    "status": "COUNT_NORMALIZE_01_PIPELINE_COMPLETED",
    "signal_authorized": False,
    "broker_execution_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
}, indent=2))
