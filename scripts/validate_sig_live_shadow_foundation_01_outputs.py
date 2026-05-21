#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

files = {
    "runtime_status": ROOT / "runtime/sig_shadow/live_shadow_foundation_status_current.json",
    "panel_status": ROOT / "panel/brain4/live_shadow_foundation_status_current.json",
}

failures = []
warnings = []
payloads = {}

for name, path in files.items():
    if not path.exists():
        failures.append(f"missing {path}")
        continue
    try:
        payloads[name] = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"{path} parse error: {e}")

status = payloads.get("runtime_status", {})
if status:
    required = [
        "context_snapshot_count_today",
        "setup_shadow_count_today",
        "trigger_shadow_count_today",
        "blocker_shadow_count_today",
        "candidate_shadow_count_today",
        "diagnostic_record_count_today",
        "append_results",
        "boundary",
    ]
    for k in required:
        if k not in status:
            failures.append(f"status missing {k}")

    # Verify log files exist and boundaries are safe.
    for name, result in (status.get("append_results") or {}).items():
        p = ROOT / str(result.get("path", ""))
        if not p.exists():
            warnings.append(f"log path missing after append: {p}")

    text = json.dumps(status, ensure_ascii=False)
    for forbidden in [
        '"signal_authorized": true',
        '"trade_instruction_authorized": true',
        '"broker_execution_authorized": true',
        '"auto_learning_authorized": true',
        '"rule_rewrite_authorized": true',
        '"outcome_observation_authorized": true',
    ]:
        if forbidden in text:
            failures.append(f"forbidden boundary flag in status: {forbidden}")

    if int(status.get("context_snapshot_count_today") or 0) < 1:
        failures.append("context_snapshot_count_today must be at least 1")

result = {
    "validation_name": "LIVE_SHADOW_FOUNDATION_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "context_snapshot_count_today": status.get("context_snapshot_count_today"),
    "setup_shadow_count_today": status.get("setup_shadow_count_today"),
    "trigger_shadow_count_today": status.get("trigger_shadow_count_today"),
    "blocker_shadow_count_today": status.get("blocker_shadow_count_today"),
    "candidate_shadow_count_today": status.get("candidate_shadow_count_today"),
    "diagnostic_record_count_today": status.get("diagnostic_record_count_today"),
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "outcome_observation_authorized": False,
    },
}

out = PROOFS / "sig_live_shadow_foundation_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
