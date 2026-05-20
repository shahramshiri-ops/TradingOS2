#!/usr/bin/env python3
"""
SHADOW-01B shadow candidate ledger updater.

Append/update shadow-only signal-candidate records from
runtime/sig_signal_candidates/signal_candidate_payload_current.json into
runtime/sig_shadow/shadow_candidate_ledger_current.json.

Boundary:
- NOT a live signal
- NO buy/sell command
- NO entry/stop/target
- NO position sizing
- NO broker/execution
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

AUTHORITY = "SIG_SHADOW_01B_LEDGER_BUILDER_v1_0|FORWARD_SHADOW_ONLY|NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION"

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def empty_candidate_ledger() -> Dict[str, Any]:
    return {
        "ledger_version": "SIG_SHADOW_CANDIDATE_LEDGER_v1_0",
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "candidates": [],
        "summary": {
            "candidate_count": 0,
            "new_candidate_count_last_run": 0,
            "updated_candidate_count_last_run": 0,
            "ledger_status": "EMPTY_SAFE_INITIALIZED"
        }
    }

def empty_blocked_ledger() -> Dict[str, Any]:
    return {
        "ledger_version": "SIG_SHADOW_BLOCKED_CANDIDATE_LEDGER_v1_0",
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "authority": "SIG_SHADOW_01B_BLOCKED_CANDIDATE_LEDGER|NOT_SIGNAL|NO_BROKER_EXECUTION",
        "blocked_candidates": [],
        "summary": {
            "blocked_candidate_count": 0,
            "new_blocked_candidate_count_last_run": 0
        }
    }

def sanitize_candidate(c: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(c)
    out["shadow_ledger_state"] = out.get("shadow_ledger_state") or "SHADOW_REGISTERED_PENDING_OBSERVATION"
    out["first_seen_utc"] = out.get("first_seen_utc") or utc_now()
    out["last_seen_utc"] = utc_now()
    out["seen_refresh_count"] = int(out.get("seen_refresh_count") or 0) + 1
    out["signal_authorized"] = False
    out["trade_instruction_authorized"] = False
    out["broker_execution_authorized"] = False
    out["action_surface_authorized"] = False
    out["ledger_authority"] = AUTHORITY
    return out

def update_candidate_ledger(existing: Dict[str, Any], intake: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    candidates = existing.get("candidates", [])
    by_id = {str(c.get("candidate_id")): c for c in candidates if c.get("candidate_id")}

    new_count = 0
    updated_count = 0
    for c in intake.get("candidates", []) or []:
        cid = str(c.get("candidate_id", ""))
        if not cid:
            continue
        if cid in by_id:
            preserved = dict(by_id[cid])
            preserved.update(c)
            preserved["first_seen_utc"] = by_id[cid].get("first_seen_utc") or c.get("created_utc") or now
            preserved["seen_refresh_count"] = int(by_id[cid].get("seen_refresh_count") or 1) + 1
            by_id[cid] = sanitize_candidate(preserved)
            updated_count += 1
        else:
            by_id[cid] = sanitize_candidate(c)
            new_count += 1

    out_candidates = sorted(by_id.values(), key=lambda x: (x.get("trigger_bar_open_ts_utc", ""), x.get("candidate_id", "")))
    status = "UPDATED"
    if not out_candidates and intake.get("intake_status", "").startswith("EMPTY_SAFE"):
        status = intake.get("intake_status")
    elif not out_candidates:
        status = "EMPTY_SAFE_NO_CANDIDATES"

    existing.update({
        "ledger_version": "SIG_SHADOW_CANDIDATE_LEDGER_v1_0",
        "updated_utc": now,
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "candidates": out_candidates,
        "summary": {
            "candidate_count": len(out_candidates),
            "new_candidate_count_last_run": new_count,
            "updated_candidate_count_last_run": updated_count,
            "ledger_status": status,
            "source_intake_status": intake.get("intake_status"),
            "source_intake_candidate_count": intake.get("candidate_count"),
            "source_intake_created_utc": intake.get("created_utc")
        }
    })
    return existing

def update_blocked_ledger(existing: Dict[str, Any], intake: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    rows = existing.get("blocked_candidates", [])
    by_id = {str(b.get("blocked_candidate_id")): b for b in rows if b.get("blocked_candidate_id")}
    new_count = 0
    for b in intake.get("blocked_candidates", []) or []:
        bid = str(b.get("blocked_candidate_id", ""))
        if not bid:
            continue
        if bid not in by_id:
            row = dict(b)
            row["first_seen_utc"] = now
            row["signal_authorized"] = False
            row["broker_execution_authorized"] = False
            by_id[bid] = row
            new_count += 1
    out_rows = sorted(by_id.values(), key=lambda x: (x.get("blocked_at_utc", ""), x.get("blocked_candidate_id", "")))
    existing.update({
        "ledger_version": "SIG_SHADOW_BLOCKED_CANDIDATE_LEDGER_v1_0",
        "updated_utc": now,
        "authority": "SIG_SHADOW_01B_BLOCKED_CANDIDATE_LEDGER|NOT_SIGNAL|NO_BROKER_EXECUTION",
        "blocked_candidates": out_rows,
        "summary": {
            "blocked_candidate_count": len(out_rows),
            "new_blocked_candidate_count_last_run": new_count,
            "source_blocked_candidate_count": intake.get("blocked_candidate_count"),
        }
    })
    return existing

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake", default="runtime/sig_signal_candidates/signal_candidate_payload_current.json")
    ap.add_argument("--ledger", default="runtime/sig_shadow/shadow_candidate_ledger_current.json")
    ap.add_argument("--blocked-ledger", default="runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json")
    args = ap.parse_args()

    intake = load_json(Path(args.intake), {"candidates": [], "blocked_candidates": [], "intake_status": "MISSING_INTAKE_EMPTY_SAFE"})
    ledger = load_json(Path(args.ledger), empty_candidate_ledger())
    blocked_ledger = load_json(Path(args.blocked_ledger), empty_blocked_ledger())

    ledger = update_candidate_ledger(ledger, intake)
    blocked_ledger = update_blocked_ledger(blocked_ledger, intake)

    write_json(Path(args.ledger), ledger)
    write_json(Path(args.blocked_ledger), blocked_ledger)

    print(json.dumps({
        "status": "SIG_SHADOW_01B_LEDGER_UPDATED",
        "candidate_count": ledger.get("summary", {}).get("candidate_count"),
        "new_candidate_count_last_run": ledger.get("summary", {}).get("new_candidate_count_last_run"),
        "blocked_candidate_count": blocked_ledger.get("summary", {}).get("blocked_candidate_count"),
        "signal_authorized": False,
        "broker_execution_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
