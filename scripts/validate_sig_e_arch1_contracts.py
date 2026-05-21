#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate SIG-E-ARCH1 contracts.

This validator intentionally checks governance boundaries more than market logic.
It should fail if the ARCH1 contract accidentally authorizes signals, trade plans,
entry/stop/target, position sizing, broker integration, auto-execution, or self-learning deployment.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any, Dict, List

ROOT = Path.cwd()
CONTRACTS = [
    ROOT / "contracts" / "sig_e_architecture_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_setup_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_trigger_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_blocker_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_quality_vector_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_signal_candidate_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_trade_plan_draft_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_risk_model_contract_v1_0.json",
    ROOT / "contracts" / "sig_e_forward_shadow_trade_plan_contract_v1_0.json",
]
POLICY_FILES = [
    ROOT / "config" / "target_architecture_e_policy.json",
    ROOT / "sig_brain" / "sig_e_target_architecture_policy_v1_0.json",
]
DOCS = [
    ROOT / "docs" / "SIG_E_ARCH1_MANUAL_SEMI_AUTOMATED_DECISION_ARCHITECTURE_FA.md",
    ROOT / "docs" / "SIG_E_ARCH1_RUNTIME_BOUNDARY_FA.md",
]
PROOF = ROOT / "proofs" / "sig_e_arch1_validation_result.json"
OUT_DIR = ROOT / "outputs" / "_sig_e_arch1"
OUT_VALIDATION = OUT_DIR / "sig_e_arch1_validation_result.json"

MUST_BE_FALSE_KEYS = {
    "current_runtime_signal_authorized",
    "current_runtime_trade_proposal_authorized",
    "current_runtime_entry_stop_target_authorized",
    "broker_integration_authorized",
    "auto_execution_authorized",
    "self_learning_deployment_authorized",
    "automatic_position_opening_authorized",
    "signal_authorized",
    "trade_plan_authorized",
    "broker_execution_authorized",
    "execution_authorized",
    "current_runtime_authorized",
    "position_sizing_execution_authorized",
    "profitability_claim_authorized",
}
MUST_BE_TRUE_KEYS = {
    "manual_review_required_for_any_future_trade_plan",
    "human_final_decision_required",
    "not_live_profitability_claim",
    "manual_review_required",
    "setup_is_not_a_trade",
    "trigger_alone_is_not_a_trade",
    "signal_candidate_is_not_execution",
    "trade_plan_is_draft_only",
    "quality_vector_is_not_probability",
}
FORBIDDEN_ACTIVE_WORDS = [
    "auto_execution_authorized\": true",
    "broker_execution_authorized\": true",
    "automatic_position_opening_authorized\": true",
    "current_runtime_signal_authorized\": true",
    "current_runtime_trade_proposal_authorized\": true",
    "current_runtime_entry_stop_target_authorized\": true",
]
REQUIRED_NON_AUTHORITY = [
    "memory_is_not_a_trade",
    "setup_is_not_a_trade",
    "trigger_alone_is_not_a_trade",
    "signal_candidate_is_not_execution",
    "trade_plan_draft_requires_manual_review",
    "no_auto_execution",
    "no_broker_integration",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_values(obj: Any, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield p, k, v
            yield from walk_values(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            yield p, None, v
            yield from walk_values(v, p)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    failures: List[str] = []
    loaded: Dict[str, Dict[str, Any]] = {}

    for path in CONTRACTS + POLICY_FILES:
        if not path.exists():
            failures.append(f"missing_file:{path.as_posix()}")
            continue
        try:
            loaded[path.as_posix()] = read_json(path)
        except Exception as e:
            failures.append(f"invalid_json:{path.as_posix()}:{e}")

    for path in DOCS:
        if not path.exists():
            failures.append(f"missing_doc:{path.as_posix()}")

    for path, obj in loaded.items():
        raw = json.dumps(obj, ensure_ascii=False).lower()
        for marker in FORBIDDEN_ACTIVE_WORDS:
            if marker.lower() in raw:
                failures.append(f"forbidden_true_marker:{path}:{marker}")
        for full_path, key, value in walk_values(obj):
            if key in MUST_BE_FALSE_KEYS and value is not False:
                failures.append(f"boundary_key_not_false:{path}:{full_path}={value!r}")
            if key in MUST_BE_TRUE_KEYS and value is not True:
                failures.append(f"required_key_not_true:{path}:{full_path}={value!r}")

    arch = loaded.get((ROOT / "contracts" / "sig_e_architecture_contract_v1_0.json").as_posix(), {})
    if arch.get("target_architecture") != "E_MANUAL_SEMI_AUTOMATED_TRADING_DECISION_SYSTEM":
        failures.append("target_architecture_not_E")
    layers = arch.get("layers", [])
    if len(layers) < 10:
        failures.append("architecture_layer_count_lt_10")
    for layer in layers:
        if layer.get("may_authorize_trade") is not False:
            failures.append(f"layer_may_authorize_trade_not_false:{layer.get('name')}")
        if layer.get("name") == "broker_execution" and layer.get("authorized") is not False:
            failures.append("broker_execution_layer_authorized_not_false")

    policy = loaded.get((ROOT / "config" / "target_architecture_e_policy.json").as_posix(), {})
    laws = policy.get("non_authority_laws", [])
    for required in REQUIRED_NON_AUTHORITY:
        if required not in laws:
            failures.append(f"missing_non_authority_law:{required}")
    phases = policy.get("phase_gate_sequence", [])
    if not phases or phases[0] != "SIG_E_ARCH1_CONTRACT_ONLY":
        failures.append("phase_gate_sequence_missing_ARCH1_first")
    if "SIG_E_TP1_TRADE_PLAN_DRAFT_MANUAL_REVIEW_ONLY" not in phases:
        failures.append("phase_gate_sequence_missing_TP1")
    if "SIG_E_RISK1_RISK_POSITION_SIZE_DRAFT_NO_EXECUTION" not in phases:
        failures.append("phase_gate_sequence_missing_RISK1")

    result = {
        "status": "FAIL" if failures else "PASS",
        "created_utc": now_utc(),
        "program": "SIG-E-ARCH1",
        "validated_contracts": [p.as_posix() for p in CONTRACTS],
        "validated_policies": [p.as_posix() for p in POLICY_FILES],
        "validated_docs": [p.as_posix() for p in DOCS],
        "failures": failures,
        "boundary": {
            "current_runtime_signal_authorized": False,
            "current_runtime_trade_proposal_authorized": False,
            "current_runtime_entry_stop_target_authorized": False,
            "broker_integration_authorized": False,
            "auto_execution_authorized": False,
            "manual_review_required_for_any_future_trade_plan": True,
        },
    }
    write_json(OUT_VALIDATION, result)
    write_json(PROOF, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
