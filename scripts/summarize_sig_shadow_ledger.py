#!/usr/bin/env python3
"""
SHADOW-01B summary builder.
Creates runtime and panel summary for shadow-only candidates and observations.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict

AUTHORITY = "SIG_SHADOW_01B_SUMMARY_BUILDER_v1_0|SHADOW_ONLY|NOT_SIGNAL|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-ledger", default="runtime/sig_shadow/shadow_candidate_ledger_current.json")
    ap.add_argument("--observation-ledger", default="runtime/sig_shadow/shadow_observation_ledger_current.json")
    ap.add_argument("--blocked-ledger", default="runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json")
    ap.add_argument("--out", default="runtime/sig_shadow/shadow_summary_current.json")
    ap.add_argument("--panel-out", default="panel/brain4/sig_shadow_summary_current.json")
    args = ap.parse_args()

    cand = load_json(Path(args.candidate_ledger), {"candidates": [], "summary": {}})
    obs = load_json(Path(args.observation_ledger), {"observations": [], "summary": {}})
    blocked = load_json(Path(args.blocked_ledger), {"blocked_candidates": [], "summary": {}})

    candidates = cand.get("candidates", []) or []
    observations = obs.get("observations", []) or []
    blocked_rows = blocked.get("blocked_candidates", []) or []

    by_cluster = {}
    by_instrument = {}
    for c in candidates:
        by_cluster[c.get("setup_cluster_id", "UNKNOWN")] = by_cluster.get(c.get("setup_cluster_id", "UNKNOWN"), 0) + 1
        by_instrument[c.get("instrument", "UNKNOWN")] = by_instrument.get(c.get("instrument", "UNKNOWN"), 0) + 1

    observation_states = {}
    for o in observations:
        st = o.get("observation_state", "UNKNOWN")
        observation_states[st] = observation_states.get(st, 0) + 1

    summary = {
        "summary_version": "SIG_SHADOW_01B_SUMMARY_v1_0",
        "created_utc": utc_now(),
        "authority": AUTHORITY,
        "shadow_status": cand.get("summary", {}).get("ledger_status", "UNKNOWN"),
        "candidate_count": len(candidates),
        "blocked_candidate_count": len(blocked_rows),
        "observation_count": len(observations),
        "observed_complete_count": obs.get("summary", {}).get("observed_complete_count", 0),
        "pending_observation_count": obs.get("summary", {}).get("pending_observation_count", 0),
        "by_cluster": by_cluster,
        "by_instrument": by_instrument,
        "observation_states": observation_states,
        "recent_candidates": candidates[-10:],
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "plain_language_fa": "این فقط دفتر ثبت و مشاهدهٔ shadow است؛ سیگنال، ورود/خروج یا اجرای معامله نیست.",
        "plain_language_en": "This is a forward-shadow logging and observation layer only; not a signal, entry/exit, or execution layer.",
    }

    write_json(Path(args.out), summary)
    write_json(Path(args.panel_out), summary)
    print(json.dumps({
        "status": "SIG_SHADOW_01B_SUMMARY_BUILT",
        "candidate_count": len(candidates),
        "observation_count": len(observations),
        "signal_authorized": False,
        "broker_execution_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
