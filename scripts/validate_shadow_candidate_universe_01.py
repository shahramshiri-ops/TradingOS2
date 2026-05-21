#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate SHADOW_CANDIDATE_UNIVERSE_01 outputs and non-authority boundaries."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

ROOT = Path.cwd()
REQUIRED_FILES = [
    "config/shadow_candidate_universe_01_registry.json",
    "state/shadow_candidate_universe/shadow_candidate_universe_state_v1.json",
    "runtime/sig_shadow_candidate_universe/shadow_candidate_universe_current.json",
    "runtime/sig_shadow_candidate_universe/shadow_candidate_universe_evaluations_current.json",
    "runtime/sig_shadow_candidate_universe/shadow_candidate_universe_summary_current.json",
    "runtime/sig_shadow_candidate_universe/shadow_candidate_universe_signal_intake_current.json",
    "panel/brain4/shadow_candidate_universe_current.json",
    "panel/brain4/shadow_candidate_universe_summary_current.json",
    "panel/brain4/shadow_candidate_universe_review_pack_current.json",
]
FORBIDDEN_TRUE_FLAGS = {
    "signal_authorized",
    "trade_instruction_authorized",
    "broker_execution_authorized",
    "action_surface_authorized",
    "entry_stop_target_authorized",
    "position_size_authorized",
    "profitability_claim_authorized",
    "auto_learning_authorized",
    "rule_rewrite_authorized",
    "active_memory_authorized",
    "memory_promotion_authorized",
}
FORBIDDEN_KEYS = {"entry", "entry_price", "stop", "stop_loss", "target", "take_profit", "position_size", "order", "broker_order"}


def read_json(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def scan(obj: Any, path: str, failures: List[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_TRUE_FLAGS and v is True:
                failures.append(f"{path}.{k} is true")
            if k in FORBIDDEN_KEYS:
                failures.append(f"{path}.{k} forbidden trading key present")
            scan(v, f"{path}.{k}", failures)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:5000]):
            scan(item, f"{path}[{i}]", failures)


def main() -> int:
    failures: List[str] = []
    warnings: List[str] = []
    loaded: Dict[str, Any] = {}
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if not p.exists():
            failures.append(f"missing required file: {rel}")
            continue
        try:
            data = read_json(rel)
            loaded[rel] = data
            scan(data, rel, failures)
        except Exception as exc:
            failures.append(f"invalid json {rel}: {exc}")

    reg = loaded.get("config/shadow_candidate_universe_01_registry.json", {})
    cur = loaded.get("runtime/sig_shadow_candidate_universe/shadow_candidate_universe_current.json", {})
    evals = loaded.get("runtime/sig_shadow_candidate_universe/shadow_candidate_universe_evaluations_current.json", {})
    intake = loaded.get("runtime/sig_shadow_candidate_universe/shadow_candidate_universe_signal_intake_current.json", {})
    state = loaded.get("state/shadow_candidate_universe/shadow_candidate_universe_state_v1.json", {})

    candidates = reg.get("candidates", []) if isinstance(reg, dict) else []
    if reg.get("registry_version") != "SHADOW_CANDIDATE_UNIVERSE_01_REGISTRY_v1_0":
        failures.append("registry_version mismatch")
    if len(candidates) < 20:
        warnings.append("candidate registry has fewer than 20 candidates")
    ids = [c.get("candidate_id") for c in candidates]
    if len(ids) != len(set(ids)):
        failures.append("candidate_id values are not unique")
    for i, c in enumerate(candidates):
        for k in ["candidate_id", "candidate_state", "instrument", "timeframe", "directional_bias", "clauses"]:
            if k not in c:
                failures.append(f"registry.candidates[{i}] missing {k}")
        if c.get("candidate_state") != "SHADOW_ONLY_RESEARCH_CANDIDATE_NOT_MEMORY":
            failures.append(f"registry.candidates[{i}] candidate_state must be SHADOW_ONLY_RESEARCH_CANDIDATE_NOT_MEMORY")

    if cur.get("payload_version") != "SHADOW_CANDIDATE_UNIVERSE_01_v1_0":
        failures.append("current payload_version mismatch")
    if evals.get("row_count") != len(evals.get("rows", []) or []):
        failures.append("evaluations row_count mismatch")
    if evals.get("row_count") != len(candidates):
        failures.append("evaluations row_count does not match registry candidate count")
    if state.get("state_version") != "SHADOW_CANDIDATE_UNIVERSE_STATE_v1_0":
        failures.append("state_version mismatch")
    if not isinstance(state.get("refresh_history"), list) or not state.get("refresh_history"):
        failures.append("state.refresh_history missing/empty")

    intake_candidates = intake.get("candidates", []) if isinstance(intake, dict) else []
    for i, c in enumerate(intake_candidates):
        for k in ["candidate_id", "candidate_state", "candidate_contract_id", "setup_cluster_id", "instrument", "timeframe", "directional_bias", "trigger_bar_open_ts_utc"]:
            if k not in c:
                failures.append(f"signal_intake.candidates[{i}] missing {k}")
        if c.get("source_type") != "SHADOW_CANDIDATE_UNIVERSE_01_RESEARCH_ONLY":
            failures.append(f"signal_intake.candidates[{i}] source_type mismatch")
        if c.get("signal_authorized") is not False:
            failures.append(f"signal_intake.candidates[{i}] signal_authorized must be false")

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "candidate_spec_count": len(candidates),
        "evaluation_row_count": evals.get("row_count"),
        "active_shadow_candidate_count": (cur.get("summary") or {}).get("active_shadow_candidate_count"),
        "near_miss_count": (cur.get("summary") or {}).get("near_miss_count"),
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }
    out = ROOT / "outputs" / "_shadow_candidate_universe_01" / "shadow_candidate_universe_01_validation_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
