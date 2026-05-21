#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate SHADOW_CANDIDATE_OUTCOME_BASELINE_01 outputs and hard non-authority boundaries."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

ROOT = Path.cwd()
REQUIRED_FILES = [
    "state/shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_state_v1.json",
    "runtime/sig_shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_current.json",
    "runtime/sig_shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_summary_current.json",
    "runtime/sig_shadow_candidate_outcome_baseline/shadow_candidate_promotion_review_current.json",
    "panel/brain4/shadow_candidate_outcome_baseline_summary_current.json",
    "panel/brain4/shadow_candidate_outcome_baseline_current.json",
    "panel/brain4/shadow_candidate_promotion_review_current.json",
    "panel/brain4/shadow_candidate_outcome_baseline_research_pack_current.json",
]

FORBIDDEN_TRUE_FLAGS = [
    "active_memory_authorized",
    "memory_promotion_authorized",
    "signal_authorized",
    "trade_instruction_authorized",
    "buy_sell_recommendation_authorized",
    "broker_execution_authorized",
    "action_surface_authorized",
    "entry_stop_target_authorized",
    "position_size_authorized",
    "profitability_claim_authorized",
    "pnl_claim_authorized",
    "auto_learning_authorized",
    "rule_rewrite_authorized",
    "auto_promotion_authorized",
    "memory_creation_authorized",
]


def read_json(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


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
        for i, v in enumerate(obj[:5000]):
            collect_boundary_failures(v, f"{path}[{i}]", failures)
    return failures


def main() -> None:
    failures: List[str] = []
    loaded: Dict[str, Any] = {}
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if not p.exists():
            failures.append(f"missing required file: {rel}")
            continue
        try:
            data = read_json(rel)
            loaded[rel] = data
        except Exception as exc:
            failures.append(f"invalid json {rel}: {exc}")
            continue
        failures.extend([f"{rel}: {x}" for x in collect_boundary_failures(data)])

    state = loaded.get("state/shadow_candidate_outcome_baseline/shadow_candidate_outcome_baseline_state_v1.json", {})
    current = loaded.get("panel/brain4/shadow_candidate_outcome_baseline_current.json", {})
    summary = loaded.get("panel/brain4/shadow_candidate_outcome_baseline_summary_current.json", {})
    review = loaded.get("panel/brain4/shadow_candidate_promotion_review_current.json", {})

    if state.get("state_version") != "SHADOW_CANDIDATE_OUTCOME_BASELINE_STATE_v1_0":
        failures.append("state_version mismatch")
    if current.get("payload_version") != "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_v1_0":
        failures.append("current payload_version mismatch")
    if summary.get("summary_version") != "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_SUMMARY_v1_0":
        failures.append("summary_version mismatch")
    if review.get("payload_version") != "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_REVIEW_PACK_v1_0":
        failures.append("review pack payload_version mismatch")
    if not isinstance(review.get("review_rows"), list):
        failures.append("review_rows must be a list")
    if current.get("summary", {}).get("signal_authorized") is not False:
        failures.append("summary.signal_authorized must be false")
    if current.get("summary", {}).get("memory_promotion_authorized") is not False:
        failures.append("summary.memory_promotion_authorized must be false")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "validation_version": "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_VALIDATOR_v1_0",
        "required_files": REQUIRED_FILES,
        "failures": failures,
        "boundary_checked_flags": FORBIDDEN_TRUE_FLAGS,
        "boundary": {
            "display_only": True,
            "research_shadow_only": True,
            "signal_authorized": False,
            "memory_promotion_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }
    out = ROOT / "proofs" / "shadow_candidate_outcome_baseline_01_validation_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
