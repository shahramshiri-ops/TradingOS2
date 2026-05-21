#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

files = {
    "ledger": ROOT / "runtime/sig_shadow/shadow_outcome_observation_ledger_current.json",
    "runtime_status": ROOT / "runtime/sig_shadow/shadow_outcome_status_current.json",
    "panel_status": ROOT / "panel/brain4/shadow_outcome_status_current.json",
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
        '"pnl_authorized": true',
        '"entry_stop_target_authorized": true',
    ]:
        if forbidden in text:
            failures.append(f"{name} has forbidden flag {forbidden}")

ledger = payloads.get("ledger", {})
status = payloads.get("runtime_status", {})

if ledger:
    if "observations" not in ledger or not isinstance(ledger.get("observations"), list):
        failures.append("ledger.observations missing/not list")
    if "summary" not in ledger:
        failures.append("ledger.summary missing")
    for obs in ledger.get("observations", []):
        # Any complete observation must explicitly be path-only not trade.
        for hr in obs.get("horizon_results") or []:
            if hr.get("completion_status") == "COMPLETE":
                if hr.get("interpretation_boundary") != "PATH_OBSERVATION_ONLY_NOT_PNL_NOT_TRADE":
                    failures.append("complete horizon missing interpretation boundary")
                    break

if status:
    if "subject_count" not in status:
        failures.append("status.subject_count missing")
    if "append_result" not in status:
        failures.append("status.append_result missing")
    if int(status.get("subject_count") or 0) == 0:
        warnings.append("no outcome subjects found; live foundation may not have generated logs yet")

result = {
    "validation_name": "SHADOW_OUTCOME_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "subject_count": status.get("subject_count"),
    "complete_horizon_result_count": status.get("complete_horizon_result_count"),
    "pending_horizon_result_count": status.get("pending_horizon_result_count"),
    "observation_status_breakdown": status.get("observation_status_breakdown"),
    "price_data_status_breakdown": status.get("price_data_status_breakdown"),
    "directional_outcome_breakdown": status.get("directional_outcome_breakdown"),
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    },
}

out = PROOFS / "sig_shadow_outcome_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
