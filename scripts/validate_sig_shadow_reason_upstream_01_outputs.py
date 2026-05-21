#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

files = {
    "reason_source": ROOT / "runtime/sig_shadow/near_miss_reason_source_current.json",
    "reason_quality": ROOT / "runtime/sig_shadow/near_miss_reason_quality_current.json",
    "reason_enriched": ROOT / "runtime/sig_shadow/near_miss_reason_enriched_current.json",
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

src = payloads.get("reason_source", {})
quality = payloads.get("reason_quality", {})
if src:
    if "records" not in src or not isinstance(src.get("records"), list):
        failures.append("reason_source.records missing/not list")
    if src.get("record_count") != len(src.get("records", [])):
        failures.append("reason_source record_count mismatch")
    if "reason_breakdown" not in src:
        failures.append("reason_source reason_breakdown missing")

if quality:
    if quality.get("unknown_reason_count_after") not in {0, None}:
        warnings.append("unknown_reason_count_after remains non-zero")
    if int(quality.get("instrumentation_gap_count") or 0) > 0:
        warnings.append("some records still require upstream setup/trigger/blocker instrumentation")

ops = payloads.get("ops_panel", {})
if ops:
    if "reason_upstream_version" not in ops:
        failures.append("panel ops status not updated with reason_upstream_version")
    if "top_reason_breakdown" not in ops:
        failures.append("panel ops status missing top_reason_breakdown")

result = {
    "validation_name": "REASON_UPSTREAM_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "record_count": src.get("record_count"),
    "unknown_reason_count_before": src.get("unknown_reason_count_before"),
    "unknown_reason_count_after": src.get("unknown_reason_count_after"),
    "instrumentation_gap_count": src.get("instrumentation_gap_count"),
    "low_confidence_reason_count": src.get("low_confidence_reason_count"),
    "quality_status": quality.get("quality_status"),
    "top_reason_breakdown": list((src.get("reason_breakdown") or {}).items())[:5] if isinstance(src.get("reason_breakdown"), dict) else None,
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = PROOFS / "sig_shadow_reason_upstream_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
