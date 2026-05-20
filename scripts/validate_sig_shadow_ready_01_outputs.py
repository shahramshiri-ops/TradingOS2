#!/usr/bin/env python3
"""Validate SHADOW-READY-01 outputs."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List

REQUIRED = [
    "runtime/sig_shadow/near_miss_ledger_current.json",
    "runtime/sig_shadow/blocker_diagnostic_ledger_current.json",
    "runtime/sig_shadow/shadow_cohort_current.json",
    "runtime/sig_shadow/shadow_observation_completion_current.json",
    "runtime/sig_shadow/shadow_daily_summary_current.json",
    "runtime/sig_shadow/shadow_weekly_summary_current.json",
    "runtime/sig_shadow/shadow_health_summary_current.json",
    "runtime/sig_shadow/shadow_panel_status_current.json",
    "runtime/sig_shadow/shadow_review_queue_current.json",
    "panel/brain4/shadow_panel_status_current.json",
]
AUTH_FALSE_KEYS = ["signal_authorized", "trade_instruction_authorized", "broker_execution_authorized", "action_surface_authorized", "auto_learning_authorized", "rule_rewrite_authorized"]
FORBIDDEN_KEYS = {"entry", "entry_price", "stop", "stop_loss", "target", "take_profit", "position_size", "order", "broker_order", "buy", "sell"}

def load(path: Path) -> Dict[str, Any]:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}

def walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from walk(v)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proof-out", default="proofs/sig_shadow_ready_01_validation_result.json")
    args = ap.parse_args()
    failures: List[str] = []
    warnings: List[str] = []
    loaded = {}
    for rel in REQUIRED:
        p = Path(rel)
        obj = load(p)
        loaded[rel] = obj
        if not obj:
            failures.append(f"missing_or_invalid_json:{rel}")
            continue
        for node in walk(obj):
            for k in AUTH_FALSE_KEYS:
                if k in node and node.get(k) is not False:
                    failures.append(f"{rel}: {k} must be false")
            bad = FORBIDDEN_KEYS.intersection(set(node.keys()))
            if bad:
                failures.append(f"{rel}: forbidden trading keys present {sorted(bad)}")
    health = loaded.get("runtime/sig_shadow/shadow_health_summary_current.json", {})
    if health.get("health_status") == "FAIL":
        failures.append("shadow_health_summary reports FAIL")
    elif health.get("health_status") == "WARN":
        warnings.extend(health.get("warnings") or [])
    panel = loaded.get("runtime/sig_shadow/shadow_panel_status_current.json", {})
    badge = str(panel.get("display_badge", ""))
    if "SIGNAL" in badge and "NOT A SIGNAL" not in badge:
        failures.append("panel display badge must not imply signal")
    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "required_file_count": len(REQUIRED),
        "near_miss_count": (loaded.get("runtime/sig_shadow/near_miss_ledger_current.json", {}).get("summary", {}) or {}).get("near_miss_count"),
        "health_status": health.get("health_status"),
        "cohort_id": (loaded.get("runtime/sig_shadow/shadow_cohort_current.json", {}) or {}).get("cohort_id"),
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }
    out = Path(args.proof_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
