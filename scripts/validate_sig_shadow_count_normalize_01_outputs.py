#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

files = {
    "semantics_runtime": ROOT / "runtime/sig_shadow/shadow_count_semantics_current.json",
    "semantics_panel": ROOT / "panel/brain4/shadow_count_semantics_current.json",
    "ops_runtime": ROOT / "runtime/sig_shadow/shadow_ops_status_current.json",
    "ops_panel": ROOT / "panel/brain4/shadow_ops_status_current.json",
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

for name, data in payloads.items():
    text = json.dumps(data, ensure_ascii=False)
    for forbidden in [
        '"signal_authorized": true',
        '"trade_instruction_authorized": true',
        '"broker_execution_authorized": true',
        '"auto_learning_authorized": true',
        '"rule_rewrite_authorized": true',
    ]:
        if forbidden in text:
            failures.append(f"{name} has forbidden flag {forbidden}")

sem = payloads.get("semantics_runtime", {})
if sem:
    required = [
        "diagnostic_record_count_last_run",
        "unique_market_near_miss_event_count_last_run",
        "unique_memory_involved_count_last_run",
        "record_class_breakdown",
        "count_policy",
    ]
    for k in required:
        if k not in sem:
            failures.append(f"semantics missing {k}")
    if not sem.get("count_policy", {}).get("near_miss_is_not_trade_opportunity"):
        failures.append("count_policy.near_miss_is_not_trade_opportunity must be true")
    if sem.get("diagnostic_record_count_last_run") != len(sem.get("records", [])):
        failures.append("diagnostic_record_count_last_run does not match records length")
    if sem.get("raw_near_miss_count_from_ops") and sem.get("raw_near_miss_count_from_ops") != sem.get("unique_market_near_miss_event_count_last_run"):
        warnings.append("raw near-miss count differs from unique market near-miss event count; expected after normalization")

ops = payloads.get("ops_panel", {})
if ops:
    if "count_semantics_version" not in ops:
        failures.append("ops panel not updated with count_semantics_version")
    if ops.get("near_miss_count_label") != "DIAGNOSTIC_RECORD_COUNT_NOT_MARKET_OPPORTUNITY_COUNT":
        failures.append("ops panel near_miss_count_label missing/incorrect")

result = {
    "validation_name": "COUNT_NORMALIZE_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "candidate_count": sem.get("candidate_count"),
    "raw_near_miss_count_from_ops": sem.get("raw_near_miss_count_from_ops"),
    "diagnostic_record_count_last_run": sem.get("diagnostic_record_count_last_run"),
    "unique_market_near_miss_event_count_last_run": sem.get("unique_market_near_miss_event_count_last_run"),
    "unique_memory_involved_count_last_run": sem.get("unique_memory_involved_count_last_run"),
    "instrumentation_gap_record_count_last_run": sem.get("instrumentation_gap_record_count_last_run"),
    "active_watch_count": sem.get("active_watch_count"),
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = PROOFS / "sig_shadow_count_normalize_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
