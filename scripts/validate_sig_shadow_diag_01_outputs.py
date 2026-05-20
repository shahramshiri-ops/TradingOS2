#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

paths = {
    "near_miss_detail": ROOT / "runtime" / "sig_shadow" / "near_miss_detail_ledger_current.json",
    "blocker_breakdown": ROOT / "runtime" / "sig_shadow" / "blocker_reason_breakdown_current.json",
    "eligibility": ROOT / "runtime" / "sig_shadow" / "eligibility_diagnostic_current.json",
    "panel_runtime": ROOT / "runtime" / "sig_shadow" / "shadow_near_miss_summary_current.json",
    "panel_brain4": ROOT / "panel" / "brain4" / "shadow_near_miss_summary_current.json",
}

failures = []
warnings = []

def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"{path} parse error: {e}")
        return {}

payloads = {}
for name, path in paths.items():
    if not path.exists():
        failures.append(f"missing {path}")
    else:
        payloads[name] = load(path)

for name, data in payloads.items():
    text = json.dumps(data, ensure_ascii=False)
    for forbidden_true in [
        '"signal_authorized": true',
        '"trade_instruction_authorized": true',
        '"broker_execution_authorized": true',
        '"auto_learning_authorized": true',
        '"rule_rewrite_authorized": true',
    ]:
        if forbidden_true in text:
            failures.append(f"{name} has forbidden boundary flag {forbidden_true}")

near = payloads.get("near_miss_detail", {})
elig = payloads.get("eligibility", {})
panel = payloads.get("panel_runtime", {})

if near:
    if "records" not in near or not isinstance(near.get("records"), list):
        failures.append("near_miss_detail.records missing or not list")
    if near.get("near_miss_detail_count", 0) != len(near.get("records", [])):
        failures.append("near_miss_detail_count does not match records length")

if elig:
    if "event_diagnostics" not in elig or not isinstance(elig.get("event_diagnostics"), list):
        warnings.append("eligibility.event_diagnostics missing or not list")
    if "stage_failed_breakdown" not in elig:
        failures.append("eligibility stage_failed_breakdown missing")

if panel:
    if "top_stage_failed" not in panel:
        failures.append("panel summary missing top_stage_failed")
    if "display_badge" not in panel:
        failures.append("panel summary missing display_badge")

result = {
    "validation_name": "SHADOW_DIAG_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "near_miss_detail_count": near.get("near_miss_detail_count"),
    "near_miss_high_count": near.get("near_miss_high_count"),
    "candidate_count": elig.get("candidate_count"),
    "blocked_candidate_count": elig.get("blocked_candidate_count"),
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = PROOFS / "sig_shadow_diag_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
