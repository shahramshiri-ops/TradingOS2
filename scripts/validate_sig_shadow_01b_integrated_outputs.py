#!/usr/bin/env python3
"""
SHADOW-01B integrated output validator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

def load(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def no_auth_failures(obj: Dict[str, Any], label: str) -> List[str]:
    failures = []
    for k in ["signal_authorized", "trade_instruction_authorized", "broker_execution_authorized", "action_surface_authorized"]:
        if k in obj and obj.get(k) is not False:
            failures.append(f"{label}: {k} must be false")
    return failures

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-payload", default="runtime/sig_signal_candidates/signal_candidate_payload_current.json")
    ap.add_argument("--candidate-ledger", default="runtime/sig_shadow/shadow_candidate_ledger_current.json")
    ap.add_argument("--observation-ledger", default="runtime/sig_shadow/shadow_observation_ledger_current.json")
    ap.add_argument("--blocked-ledger", default="runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json")
    ap.add_argument("--summary", default="runtime/sig_shadow/shadow_summary_current.json")
    ap.add_argument("--proof-out", default="proofs/sig_shadow_01b_integrated_validation_result.json")
    args = ap.parse_args()

    payload = load(args.candidate_payload)
    cand = load(args.candidate_ledger)
    obs = load(args.observation_ledger)
    blocked = load(args.blocked_ledger)
    summary = load(args.summary)

    failures: List[str] = []
    warnings: List[str] = []

    for label, obj in [
        ("candidate_payload", payload),
        ("candidate_ledger", cand),
        ("observation_ledger", obs),
        ("blocked_ledger", blocked),
        ("summary", summary),
    ]:
        if not obj:
            failures.append(f"{label} missing or empty JSON")
        failures.extend(no_auth_failures(obj, label))

    if "candidates" not in payload or not isinstance(payload.get("candidates"), list):
        failures.append("candidate_payload.candidates must be a list")
    if "candidates" not in cand or not isinstance(cand.get("candidates"), list):
        failures.append("candidate_ledger.candidates must be a list")
    if "observations" not in obs or not isinstance(obs.get("observations"), list):
        failures.append("observation_ledger.observations must be a list")
    if "blocked_candidates" not in blocked or not isinstance(blocked.get("blocked_candidates"), list):
        failures.append("blocked_ledger.blocked_candidates must be a list")

    for i, c in enumerate(payload.get("candidates", []) or []):
        for k in ["candidate_id", "candidate_state", "candidate_contract_id", "setup_cluster_id", "source_memory_ids", "instrument", "timeframe", "directional_bias"]:
            if k not in c:
                failures.append(f"candidate_payload.candidates[{i}] missing {k}")
        if c.get("signal_authorized") is not False:
            failures.append(f"candidate_payload.candidates[{i}] signal_authorized must be false")
        if c.get("trade_instruction_authorized") is not False:
            failures.append(f"candidate_payload.candidates[{i}] trade_instruction_authorized must be false")
        if c.get("broker_execution_authorized") is not False:
            failures.append(f"candidate_payload.candidates[{i}] broker_execution_authorized must be false")
        forbidden_keys = {"entry", "entry_price", "stop", "stop_loss", "target", "take_profit", "position_size", "order", "broker_order"}
        bad = forbidden_keys.intersection(set(c.keys()))
        if bad:
            failures.append(f"candidate_payload.candidates[{i}] forbidden trading keys present: {sorted(bad)}")

    for i, o in enumerate(obs.get("observations", []) or []):
        if o.get("metrics_are_pnl") is not False:
            failures.append(f"observation[{i}] metrics_are_pnl must be false")

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "candidate_payload_count": len(payload.get("candidates", []) or []),
        "candidate_ledger_count": len(cand.get("candidates", []) or []),
        "observation_count": len(obs.get("observations", []) or []),
        "blocked_candidate_count": len(blocked.get("blocked_candidates", []) or []),
        "summary_candidate_count": summary.get("candidate_count"),
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
    }
    out = Path(args.proof_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
