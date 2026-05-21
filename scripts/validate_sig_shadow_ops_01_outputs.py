#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
PROOFS.mkdir(parents=True, exist_ok=True)

files = {
    "reason_enriched": ROOT / "runtime/sig_shadow/near_miss_reason_enriched_current.json",
    "eligibility": ROOT / "runtime/sig_shadow/eligibility_status_current.json",
    "last_run": ROOT / "runtime/sig_shadow/shadow_last_run_summary_current.json",
    "history": ROOT / "runtime/sig_shadow/shadow_ops_run_history_current.json",
    "daily": ROOT / "runtime/sig_shadow/shadow_daily_rollup_current.json",
    "weekly": ROOT / "runtime/sig_shadow/shadow_weekly_rollup_current.json",
    "cohort": ROOT / "runtime/sig_shadow/shadow_cohort_rollup_current.json",
    "health": ROOT / "runtime/sig_shadow/shadow_pipeline_health_current.json",
    "review_queue": ROOT / "runtime/sig_shadow/shadow_review_queue_current.json",
    "panel_ops": ROOT / "panel/brain4/shadow_ops_status_current.json",
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

# Boundary checks.
for name, data in payloads.items():
    text = json.dumps(data, ensure_ascii=False)
    for token in [
        '"signal_authorized": true',
        '"trade_instruction_authorized": true',
        '"broker_execution_authorized": true',
        '"auto_learning_authorized": true',
        '"rule_rewrite_authorized": true',
    ]:
        if token in text:
            failures.append(f"{name} has forbidden boundary token {token}")

reason = payloads.get("reason_enriched", {})
if reason:
    if not isinstance(reason.get("records"), list):
        failures.append("reason_enriched.records missing/not list")
    if reason.get("near_miss_count") != len(reason.get("records", [])):
        failures.append("near_miss_count mismatch records length")
    if "reason_breakdown" not in reason:
        failures.append("reason_breakdown missing")

last_run = payloads.get("last_run", {})
history = payloads.get("history", {})
if last_run and history:
    if not isinstance(history.get("runs"), list):
        failures.append("history.runs missing/not list")
    elif len(history.get("runs", [])) < 1:
        failures.append("history.runs empty")

health = payloads.get("health", {})
if health:
    if health.get("health_status") not in {"PASS", "WARN", "FAIL"}:
        failures.append("health_status invalid")
    if "freshness_minutes" not in health:
        warnings.append("health freshness_minutes missing")

panel = payloads.get("panel_ops", {})
if panel:
    if "top_reason_breakdown" not in panel:
        failures.append("panel top_reason_breakdown missing")
    if "cohort_rollup" not in panel:
        failures.append("panel cohort_rollup missing")

result = {
    "validation_name": "SHADOW_OPS_01_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "candidate_count": last_run.get("candidate_count"),
    "near_miss_count": last_run.get("near_miss_count"),
    "near_miss_high_count": last_run.get("near_miss_high_count"),
    "blocked_candidate_count": last_run.get("blocked_candidate_count"),
    "health_status": health.get("health_status"),
    "review_item_count": payloads.get("review_queue", {}).get("review_item_count"),
    "boundary": {
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    },
}

out = PROOFS / "sig_shadow_ops_01_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
