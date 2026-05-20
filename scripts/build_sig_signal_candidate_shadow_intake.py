#!/usr/bin/env python3
"""
SHADOW-01B integrated signal-candidate shadow intake.

Reads the current Brain4 runtime payload and converts only active, core memory
matches into shadow-only signal-candidate records.

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
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

AUTHORITY = "SIG_SIGNAL_CANDIDATE_SHADOW_INTAKE_v1_0|SHADOW_ONLY|NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION"

CORE_MEMORY_MAP = {
  "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
    "candidate_contract": "SIGCAND_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "CAVEATED"
  },
  "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_CAVEATED_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
    "candidate_contract": "SIGCAND_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "ADEQUATE"
  },
  "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
    "candidate_contract": "SIGCAND_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "ADEQUATE"
  },
  "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "ADEQUATE"
  },
  "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "SHORT_BIAS",
    "sample_grade": "STRONG"
  },
  "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "STRONG"
  },
  "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "SHORT_BIAS",
    "sample_grade": "STRONG"
  },
  "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "LONG_BIAS",
    "sample_grade": "STRONG"
  },
  "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": {
    "cluster": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
    "candidate_contract": "SIGCAND_H1_LONDON_NY_SESSION_OPEN_TREND_DIRECTIONAL_CANDIDATE_v1_0",
    "direction": "SHORT_BIAS",
    "sample_grade": "STRONG"
  }
}

EXCLUDED_MEMORY_MAP = {
  "EURUSD_H1_LONDON_ASIAN_HIGH_SWEEP_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0": "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW",
  "XAUUSD_H1_WEEKLY_OPEN_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0": "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW"
}

HORIZONS_H1 = [1, 2, 4, 8]

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def short_hash(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]

def iso_add_hours(ts: str, hours: int) -> str:
    try:
        d = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        return (d + dt.timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""

def get_trigger_bar(card: Dict[str, Any], payload: Dict[str, Any]) -> str:
    ctx = card.get("latest_context") or {}
    return (
        ctx.get("latest_h1_bar_open_ts_utc")
        or ctx.get("latest_bar_open_ts_utc")
        or payload.get("created_utc")
        or utc_now()
    )

def reference_price(card: Dict[str, Any]) -> Any:
    ctx = card.get("latest_context") or {}
    for key in ("h1_close", "close", "latest_close", "bar_close"):
        if key in ctx and ctx.get(key) not in (None, "", "UNKNOWN"):
            return ctx.get(key)
    return None

def group_key_for_card(card: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    mid = str(card.get("memory_id", ""))
    meta = CORE_MEMORY_MAP[mid]
    return (
        meta["cluster"],
        str(card.get("instrument", "")).upper(),
        str(card.get("timeframe", "")).upper(),
        meta["direction"],
        str(get_trigger_bar(card, payload)),
    )

def candidate_from_group(cards: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
    first = cards[0]
    mid = str(first.get("memory_id", ""))
    meta = CORE_MEMORY_MAP[mid]
    trigger_bar = str(get_trigger_bar(first, payload))
    instrument = str(first.get("instrument", "")).upper()
    timeframe = str(first.get("timeframe", "")).upper()
    directional_bias = meta["direction"]
    cluster = meta["cluster"]
    contract = meta["candidate_contract"]
    source_ids = sorted({str(c.get("memory_id", "")) for c in cards})
    raw_id = "|".join([cluster, instrument, timeframe, directional_bias, trigger_bar] + source_ids)
    candidate_id = "SHADOWCAND_" + short_hash(raw_id, 20)
    created = payload.get("created_utc") or utc_now()

    evidence = []
    grades = []
    for c in cards:
        memid = str(c.get("memory_id", ""))
        mmeta = CORE_MEMORY_MAP.get(memid, {})
        grades.append(mmeta.get("sample_grade", "CAVEATED"))
        evidence.append({
            "memory_id": memid,
            "brain_state": c.get("brain_state"),
            "matched_conditions": c.get("matched_conditions", []),
            "evidence_summary": c.get("evidence_summary", {}),
            "sample_grade": mmeta.get("sample_grade", "CAVEATED"),
            "status_badge": c.get("status_badge"),
        })

    quality_band = "CAVEATED"
    if grades and all(g == "STRONG" for g in grades):
        quality_band = "STRONG_SAMPLE_SUPPORT_CAVEATED_RUNTIME"
    elif grades and any(g in ("STRONG", "ADEQUATE") for g in grades):
        quality_band = "ADEQUATE_SAMPLE_SUPPORT_CAVEATED_RUNTIME"

    return {
        "candidate_id": candidate_id,
        "candidate_version": "SIGCAND_SHADOW_INTAKE_v1_0",
        "candidate_state": "SHADOW_INTAKE_READY_NOT_SIGNAL",
        "candidate_contract_id": contract,
        "setup_cluster_id": cluster,
        "source_memory_ids": source_ids,
        "source_memory_count": len(source_ids),
        "instrument": instrument,
        "timeframe": timeframe,
        "directional_bias": directional_bias,
        "created_utc": created,
        "trigger_bar_open_ts_utc": trigger_bar,
        "valid_until_utc": iso_add_hours(trigger_bar, 8),
        "shadow_horizons": [f"H1+{h}" for h in HORIZONS_H1],
        "observation_reference_price": reference_price(first),
        "observation_reference_price_policy": "closed H1 context close; observation-only, not entry",
        "source_payload_created_utc": payload.get("created_utc"),
        "source_payload_version": payload.get("payload_version"),
        "quality_band_not_probability": quality_band,
        "source_evidence": evidence,
        "latest_context_excerpt": {
            k: (first.get("latest_context") or {}).get(k)
            for k in [
                "instrument", "timeframe", "latest_bar_open_ts_utc", "latest_h1_bar_open_ts_utc",
                "session_bucket", "prior_h1_session", "is_first_h1_bar_of_session",
                "h1_bar_direction", "session_open_trend_trigger_state", "d1_trend_state",
                "h4_trend_state", "d1_trend_safe", "h4_trend_safe", "h1_open", "h1_high",
                "h1_low", "h1_close", "data_sufficiency_status", "context_builder_status"
            ]
            if k in (first.get("latest_context") or {})
        },
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "forbidden_interpretation": "Do not read this as buy/sell/entry/stop/target/profitability/tradability/broker execution.",
    }

def build(payload: Dict[str, Any]) -> Dict[str, Any]:
    cards = payload.get("cards", []) if isinstance(payload.get("cards"), list) else []
    active_core_cards = []
    active_excluded_cards = []
    active_non_core_cards = []
    for c in cards:
        if c.get("is_active_match") is not True:
            continue
        mid = str(c.get("memory_id", ""))
        if mid in CORE_MEMORY_MAP:
            active_core_cards.append(c)
        elif mid in EXCLUDED_MEMORY_MAP:
            active_excluded_cards.append(c)
        else:
            active_non_core_cards.append(c)

    groups: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for c in active_core_cards:
        groups.setdefault(group_key_for_card(c, payload), []).append(c)

    candidates = [candidate_from_group(v, payload) for v in groups.values()]
    candidates.sort(key=lambda x: (x["instrument"], x["timeframe"], x["setup_cluster_id"], x["directional_bias"], x["trigger_bar_open_ts_utc"]))

    blocked = []
    for c in active_excluded_cards:
        mid = str(c.get("memory_id", ""))
        blocked.append({
            "blocked_candidate_id": "BLOCKED_SHADOWCAND_" + short_hash(mid + "|" + str(get_trigger_bar(c, payload)), 20),
            "source_memory_id": mid,
            "instrument": c.get("instrument"),
            "timeframe": c.get("timeframe"),
            "blocked_reason": EXCLUDED_MEMORY_MAP.get(mid, "NOT_CORE_FOR_SHADOW_01B"),
            "blocked_at_utc": payload.get("created_utc") or utc_now(),
            "authority": "BLOCKED_SHADOW_INTAKE_NOT_SIGNAL",
        })
    for c in active_non_core_cards:
        mid = str(c.get("memory_id", ""))
        blocked.append({
            "blocked_candidate_id": "BLOCKED_SHADOWCAND_" + short_hash(mid + "|" + str(get_trigger_bar(c, payload)), 20),
            "source_memory_id": mid,
            "instrument": c.get("instrument"),
            "timeframe": c.get("timeframe"),
            "blocked_reason": "ACTIVE_MEMORY_NOT_IN_CORE_SHADOW_01B_MAP",
            "blocked_at_utc": payload.get("created_utc") or utc_now(),
            "authority": "BLOCKED_SHADOW_INTAKE_NOT_SIGNAL",
        })

    if candidates:
        intake_status = "CANDIDATE_INTAKE_READY_SHADOW_ONLY"
    elif active_excluded_cards or active_non_core_cards:
        intake_status = "EMPTY_SAFE_ACTIVE_NON_CORE_ONLY"
    else:
        intake_status = "EMPTY_SAFE_NO_ACTIVE_CORE_MATCH"

    return {
        "payload_version": "SIG_SIGNAL_CANDIDATE_SHADOW_INTAKE_PAYLOAD_v1_0",
        "created_utc": utc_now(),
        "authority": AUTHORITY,
        "intake_status": intake_status,
        "candidate_count": len(candidates),
        "blocked_candidate_count": len(blocked),
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "source_brain4_payload": {
            "payload_version": payload.get("payload_version"),
            "created_utc": payload.get("created_utc"),
            "active_match_count": (payload.get("registry_summary") or {}).get("active_match_count"),
            "memory_count": (payload.get("registry_summary") or {}).get("memory_count"),
        },
        "candidates": candidates,
        "blocked_candidates": blocked,
        "global_boundary": {
            "plain_language_en": "These are shadow-only candidate records derived from active Brain4 memory matches. They are not trading signals.",
            "plain_language_fa": "این رکوردها فقط کاندیدهای فرضی برای ثبت در shadow هستند و سیگنال معامله نیستند.",
            "no_entry_stop_target": True,
            "no_broker_execution": True,
        }
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain-payload", default="runtime/sig_brain/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--out", default="runtime/sig_signal_candidates/signal_candidate_payload_current.json")
    ap.add_argument("--summary-out", default="runtime/sig_signal_candidates/signal_candidate_summary_current.json")
    ap.add_argument("--panel-summary-out", default="panel/brain4/sig_signal_candidate_summary_current.json")
    ap.add_argument("--panel-payload-out", default="panel/brain4/sig_signal_candidate_payload_current.json")
    args = ap.parse_args()

    payload = load_json(Path(args.brain_payload), default={})
    out = build(payload)

    write_json(Path(args.out), out)
    summary = {
        "summary_version": "SIG_SIGNAL_CANDIDATE_SHADOW_INTAKE_SUMMARY_v1_0",
        "created_utc": out["created_utc"],
        "authority": AUTHORITY,
        "intake_status": out["intake_status"],
        "candidate_count": out["candidate_count"],
        "blocked_candidate_count": out["blocked_candidate_count"],
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "candidate_ids": [c["candidate_id"] for c in out.get("candidates", [])],
        "blocked_candidate_ids": [b["blocked_candidate_id"] for b in out.get("blocked_candidates", [])],
    }
    write_json(Path(args.summary_out), summary)
    write_json(Path(args.panel_summary_out), summary)
    write_json(Path(args.panel_payload_out), out)

    print(json.dumps({
        "status": "SIG_SIGNAL_CANDIDATE_SHADOW_INTAKE_BUILT",
        "intake_status": out["intake_status"],
        "candidate_count": out["candidate_count"],
        "blocked_candidate_count": out["blocked_candidate_count"],
        "signal_authorized": False,
        "broker_execution_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
