#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path.cwd()
PROOFS = ROOT / "proofs"
GUARD = ROOT / "runtime/sig_shadow/shadow_outcome_01d_guard_status_current.json"
STATE = ROOT / "runtime/sig_shadow/shadow_outcome_completion_state_current.json"
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

guard = load(GUARD, {})
state = load(STATE, {})
status = load(STATUS, {})

text = json.dumps({"guard": guard, "state": state, "status": status}, ensure_ascii=False)
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

if state.get("payload_version") != "SHADOW_OUTCOME_01D_COMPLETION_STATE_v1_0":
    failures.append("completion state payload_version missing/incorrect")
if guard.get("payload_version") != "SHADOW_OUTCOME_01D_GUARD_STATUS_v1_0":
    failures.append("guard payload_version missing/incorrect")

if int(state.get("duplicate_subject_count_current") or 0) > int(state.get("raw_subject_count_current") or 0):
    failures.append("duplicate_subject_count_current impossible")

fresh = guard.get("freshness_tier_breakdown") or {}
if fresh.get("LIVE_BROKEN") or fresh.get("LIVE_BROKEN_NO_SOURCE_TIME"):
    warnings.append("one or more live price sources are broken")
if fresh.get("LIVE_STALE"):
    warnings.append("one or more live price sources are stale")
if int(guard.get("dropped_incomplete_h1_rows_total") or 0) > 0:
    warnings.append("incomplete H1 rows were dropped before outcome observation")

ladder = state.get("horizon_completion_ladder") or {}
if not ladder:
    warnings.append("no horizon completion ladder found")

result = {
    "validation_name": "SHADOW_OUTCOME_01D_VALIDATION",
    "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "validation_status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "warnings": warnings,
    "freshness_tier_breakdown": fresh,
    "dropped_incomplete_h1_rows_total": guard.get("dropped_incomplete_h1_rows_total"),
    "unique_subject_count_current": state.get("unique_subject_count_current"),
    "duplicate_subject_count_current": state.get("duplicate_subject_count_current"),
    "carry_forward_subject_count_total": state.get("carry_forward_subject_count_total"),
    "carry_forward_complete_horizon_count_total": state.get("carry_forward_complete_horizon_count_total"),
    "carry_forward_pending_horizon_count_total": state.get("carry_forward_pending_horizon_count_total"),
    "horizon_completion_ladder": ladder,
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    },
}

PROOFS.mkdir(parents=True, exist_ok=True)
out = PROOFS / "sig_shadow_outcome_01d_validation_result.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

if failures:
    raise SystemExit(1)
