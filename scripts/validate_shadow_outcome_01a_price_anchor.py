#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
LEDGER = ROOT / "runtime/sig_shadow/shadow_outcome_observation_ledger_current.json"
STATUS = ROOT / "runtime/sig_shadow/shadow_outcome_status_current.json"

failures = []
warnings = []

def load(path, default):
    if not path.exists():
        failures.append(f"missing {path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"{path} parse error: {e}")
        return default

ledger = load(LEDGER, {})
status = load(STATUS, {})
observations = ledger.get("observations") or []

text = json.dumps({"ledger": ledger, "status": status}, ensure_ascii=False)
for forbidden in [
    '"signal_authorized": true',
    '"trade_instruction_authorized": true',
    '"broker_execution_authorized": true',
    '"auto_learning_authorized": true',
    '"rule_rewrite_authorized": true',
    '"pnl_authorized": true',
    '"entry_stop_target_authorized": true',
]:
    if forbidden in text:
        failures.append(f"forbidden flag present: {forbidden}")

if status.get("price_anchor_patch_version") != "SHADOW_OUTCOME_01A_PRICE_ANCHOR_v1_0":
    failures.append("price_anchor_patch_version missing from status")

resolved = int(status.get("resolved_price_anchor_subject_count") or 0)
subject_count = int(status.get("subject_count") or len(observations) or 0)

if subject_count > 0 and resolved == 0:
    warnings.append("no subjects resolved to price anchor; check H1 canonical data availability or missing instrument inference")

price_breakdown = status.get("price_data_status_breakdown_after_anchor_patch") or status.get("price_data_status_breakdown") or {}
if subject_count > 0 and price_breakdown.get("NO_PRICE_BAR_ANCHOR") == subject_count:
    warnings.append("all subjects remain NO_PRICE_BAR_ANCHOR")

result = {
    "validation_name": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "subject_count": subject_count,
    "resolved_price_anchor_subject_count": resolved,
    "context_derived_anchor_subject_count": status.get("context_derived_anchor_subject_count"),
    "source_price_anchor_subject_count": status.get("source_price_anchor_subject_count"),
    "anchor_resolution_breakdown": status.get("anchor_resolution_breakdown"),
    "price_data_status_breakdown_after_anchor_patch": price_breakdown,
    "complete_horizon_result_count": status.get("complete_horizon_result_count"),
    "pending_horizon_result_count": status.get("pending_horizon_result_count"),
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    },
}

out = PROOFS / "sig_shadow_outcome_01a_price_anchor_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
