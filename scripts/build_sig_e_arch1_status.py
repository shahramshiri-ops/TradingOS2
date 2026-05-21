#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIG-E-ARCH1 status builder.

Builds a small static status payload declaring that the target architecture is E
while current runtime remains display-only / research / shadow / not-signal.

Boundary: contract/status only. No signal, no entry/stop/target, no broker/execution.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any, Dict

ROOT = Path.cwd()
CONTRACT = ROOT / "contracts" / "sig_e_architecture_contract_v1_0.json"
POLICY = ROOT / "config" / "target_architecture_e_policy.json"
OUT_RUNTIME = ROOT / "runtime" / "sig_e" / "sig_e_architecture_status_current.json"
OUT_PANEL = ROOT / "panel" / "brain4" / "sig_e_architecture_status_current.json"
OUT_DIR = ROOT / "outputs" / "_sig_e_arch1"
OUT_BUILD = OUT_DIR / "sig_e_arch1_build_result.json"

BOUNDARY_FALSE = [
    "current_runtime_signal_authorized",
    "current_runtime_trade_proposal_authorized",
    "current_runtime_entry_stop_target_authorized",
    "broker_integration_authorized",
    "auto_execution_authorized",
    "self_learning_deployment_authorized",
    "automatic_position_opening_authorized",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    contract = read_json(CONTRACT)
    policy = read_json(POLICY)
    boundary = policy.get("runtime_boundary", {})
    violations = [k for k in BOUNDARY_FALSE if boundary.get(k) is not False]
    if boundary.get("manual_review_required_for_any_future_trade_plan") is not True:
        violations.append("manual_review_required_for_any_future_trade_plan_not_true")
    if violations:
        raise SystemExit("SIG-E-ARCH1 boundary violations: " + ", ".join(violations))

    payload = {
        "status_id": "SIG_E_ARCHITECTURE_STATUS_CURRENT",
        "created_utc": now_utc(),
        "program": "SIG-E-ARCH1",
        "architecture_status": "TARGET_E_CONTRACT_ACTIVE_CURRENT_RUNTIME_NOT_SIGNAL",
        "target_architecture": policy.get("target_architecture"),
        "current_runtime_posture": policy.get("current_runtime_posture"),
        "contract_id": contract.get("contract_id"),
        "layer_count": len(contract.get("layers", [])),
        "phase_gate_sequence": policy.get("phase_gate_sequence", []),
        "non_authority_laws": policy.get("non_authority_laws", []),
        "boundary": boundary,
        "panel_policy": policy.get("panel_policy", {}),
        "next_recommended_gate": "SIG-E-SETUP1_SETUP_LAYER_NO_SIGNAL",
        "notes": [
            "This payload is metadata/research/debug only.",
            "No signal candidate runtime is active in ARCH1.",
            "No trade plan, entry, stop, target, risk sizing, broker integration, or execution is authorized."
        ]
    }
    write_json(OUT_RUNTIME, payload)
    write_json(OUT_PANEL, payload)
    build_result = {
        "status": "PASS",
        "created_utc": payload["created_utc"],
        "program": "SIG-E-ARCH1",
        "outputs": [OUT_RUNTIME.as_posix(), OUT_PANEL.as_posix()],
        "boundary": boundary,
    }
    write_json(OUT_BUILD, build_result)
    print(json.dumps(build_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
