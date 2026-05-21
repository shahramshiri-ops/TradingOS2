#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
CATALOG = ROOT / "runtime/sig_shadow/price_source_bridge_catalog_current.json"
OUTCOME_STATUS = ROOT / "runtime/sig_shadow/shadow_outcome_status_current.json"
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

catalog = load(CATALOG, {})
status = load(OUTCOME_STATUS, {})

if catalog.get("payload_version") != "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_GUARD_v1_0":
    failures.append("catalog is not 01C live-recent bridge")

text = json.dumps({"catalog": catalog, "status": status}, ensure_ascii=False)
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

bridges = catalog.get("bridges") or {}
failures_map = catalog.get("failures") or {}
for inst, bridge in bridges.items():
    source_path = str(bridge.get("source_path", "")).lower().replace("\\", "/")
    for tok in ["mem_audit", "sample", "historical", "derived_rebuild", "_factory_registry", "factory_registry", "backtest", "discovery", "validation", "holdout"]:
        if tok in source_path:
            failures.append(f"{inst} bridge selected forbidden source: {bridge.get('source_path')}")
    if "live" not in source_path and "incremental" not in source_path:
        warnings.append(f"{inst} source is not clearly live/incremental: {bridge.get('source_path')}")
    out = ROOT / str(bridge.get("output_path", ""))
    if not out.exists():
        failures.append(f"{inst} bridge output missing: {out}")
    if bridge.get("live_recency_status") == "LIVE_PRICE_STALE":
        warnings.append(f"{inst} live price source is stale by {bridge.get('source_staleness_hours')} hours")

if not bridges:
    warnings.append("no instruments bridged from live M5; outcome may remain H1_DATA_NOT_FOUND")

subject_count = int(status.get("subject_count") or 0)
resolved = int(status.get("resolved_price_anchor_subject_count") or 0)
price_breakdown = status.get("price_data_status_breakdown_after_anchor_patch") or status.get("price_data_status_breakdown") or {}
if bridges and subject_count > 0 and resolved == 0:
    warnings.append("bridges exist but no outcome subjects resolved; check timestamp/instrument compatibility")
if bridges and price_breakdown.get("H1_DATA_NOT_FOUND") == subject_count and subject_count > 0:
    warnings.append("all subjects still H1_DATA_NOT_FOUND despite live bridge")

result = {
    "validation_name": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "bridged_instrument_count": len(bridges),
    "bridges": bridges,
    "unbridged_instruments": failures_map,
    "subject_count": subject_count,
    "resolved_price_anchor_subject_count": resolved,
    "complete_horizon_result_count": status.get("complete_horizon_result_count"),
    "pending_horizon_result_count": status.get("pending_horizon_result_count"),
    "price_data_status_breakdown": price_breakdown,
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    },
}
PROOFS.mkdir(parents=True, exist_ok=True)
out = PROOFS / "sig_shadow_outcome_01c_live_recent_price_bridge_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
