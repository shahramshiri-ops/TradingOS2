#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
CATALOG = ROOT / "runtime/sig_shadow/price_source_bridge_catalog_current.json"
OUTCOME_STATUS = ROOT / "runtime/sig_shadow/shadow_outcome_status_current.json"
failures, warnings = [], []

def load(path, default):
    if not path.exists():
        failures.append(f"missing {path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"{path} parse error: {e}")
        return default

catalog = load(CATALOG, {})
status = load(OUTCOME_STATUS, {})
text = json.dumps({"catalog": catalog, "status": status}, ensure_ascii=False)
for forbidden in ['"signal_authorized": true','"trade_instruction_authorized": true','"broker_execution_authorized": true','"auto_learning_authorized": true','"rule_rewrite_authorized": true','"pnl_authorized": true','"entry_stop_target_authorized": true']:
    if forbidden in text:
        failures.append(f"forbidden flag present: {forbidden}")

bridges = catalog.get("bridges") or {}
failmap = catalog.get("failures") or {}
if not bridges:
    warnings.append("no instruments bridged; outcome may remain H1_DATA_NOT_FOUND")
else:
    for inst, b in bridges.items():
        p = ROOT / str(b.get("output_path", ""))
        if not p.exists():
            failures.append(f"bridge output missing for {inst}: {p}")

price_breakdown = status.get("price_data_status_breakdown_after_anchor_patch") or status.get("price_data_status_breakdown") or {}
subject_count = int(status.get("subject_count") or 0)
resolved = int(status.get("resolved_price_anchor_subject_count") or 0)
if bridges and subject_count > 0 and resolved == 0:
    warnings.append("bridges exist but outcome subjects are still unresolved; check instrument/timestamp bridge compatibility")
if bridges and price_breakdown.get("H1_DATA_NOT_FOUND") == subject_count and subject_count > 0:
    warnings.append("all subjects still H1_DATA_NOT_FOUND despite bridge; inspect outcome script patch")

result = {
    "validation_name": "SHADOW_OUTCOME_01B_PRICE_SOURCE_BRIDGE_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "bridged_instrument_count": len(bridges),
    "bridges": bridges,
    "unbridged_instruments": failmap,
    "subject_count": subject_count,
    "resolved_price_anchor_subject_count": resolved,
    "complete_horizon_result_count": status.get("complete_horizon_result_count"),
    "pending_horizon_result_count": status.get("pending_horizon_result_count"),
    "price_data_status_breakdown": price_breakdown,
    "boundary": {"signal_authorized": False, "broker_execution_authorized": False, "pnl_authorized": False, "entry_stop_target_authorized": False},
}
PROOFS.mkdir(parents=True, exist_ok=True)
out = PROOFS / "sig_shadow_outcome_01b_price_source_bridge_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
