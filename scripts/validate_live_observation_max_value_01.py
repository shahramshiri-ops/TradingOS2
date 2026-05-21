#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate LIVE_OBSERVATION_MAX_VALUE_01 outputs and boundaries."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

ROOT = Path.cwd()
REQUIRED_FILES = [
    "state/live_observation/live_observation_state_v1.json",
    "runtime/sig_live_observation/live_observation_state_current.json",
    "panel/brain4/live_observation_current.json",
    "panel/brain4/live_memory_evaluation_current.json",
    "panel/brain4/live_event_ledger_current.json",
    "panel/brain4/live_observation_daily_summary_current.json",
    "panel/brain4/live_observation_weekly_summary_current.json",
    "panel/brain4/live_observation_monthly_review_pack_current.json",
]

FORBIDDEN_TRUE_FLAGS = [
    "signal_authorized",
    "trade_instruction_authorized",
    "action_surface_authorized",
    "broker_execution_authorized",
    "entry_stop_target_authorized",
    "position_size_authorized",
    "profitability_claim_authorized",
    "auto_learning_authorized",
    "rule_rewrite_authorized",
]


def read_json(rel: str) -> Any:
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8"))


def collect_boundary_failures(obj: Any, path: str = "$", failures: List[str] | None = None) -> List[str]:
    if failures is None:
        failures = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_TRUE_FLAGS and v is True:
                failures.append(f"{path}.{k} is true")
            if k == "boundary" and isinstance(v, dict):
                for flag in FORBIDDEN_TRUE_FLAGS:
                    if v.get(flag) is True:
                        failures.append(f"{path}.boundary.{flag} is true")
            collect_boundary_failures(v, f"{path}.{k}", failures)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:2000]):
            collect_boundary_failures(v, f"{path}[{i}]", failures)
    return failures


def main() -> None:
    failures: List[str] = []
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if not p.exists():
            failures.append(f"missing required file: {rel}")
            continue
        try:
            data = read_json(rel)
        except Exception as exc:
            failures.append(f"invalid json {rel}: {exc}")
            continue
        failures.extend([f"{rel}: {x}" for x in collect_boundary_failures(data)])

    state = read_json("state/live_observation/live_observation_state_v1.json") if (ROOT / "state/live_observation/live_observation_state_v1.json").exists() else {}
    current = read_json("panel/brain4/live_observation_current.json") if (ROOT / "panel/brain4/live_observation_current.json").exists() else {}
    eval_current = read_json("panel/brain4/live_memory_evaluation_current.json") if (ROOT / "panel/brain4/live_memory_evaluation_current.json").exists() else {}

    if state.get("state_version") != "LIVE_OBSERVATION_STATE_v1_0":
        failures.append("state_version mismatch")
    if current.get("payload_version") != "LIVE_OBSERVATION_MAX_VALUE_01_v1_0":
        failures.append("current payload_version mismatch")
    if not isinstance(eval_current.get("rows"), list):
        failures.append("live_memory_evaluation_current.rows is not a list")
    if eval_current.get("row_count") != len(eval_current.get("rows", [])):
        failures.append("live_memory_evaluation_current row_count mismatch")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "validation_version": "LIVE_OBSERVATION_MAX_VALUE_01_VALIDATOR_v1_0",
        "required_files": REQUIRED_FILES,
        "failures": failures,
        "boundary_checked_flags": FORBIDDEN_TRUE_FLAGS,
        "boundary": {
            "display_only": True,
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }
    out = ROOT / "proofs" / "live_observation_max_value_01_validation_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
