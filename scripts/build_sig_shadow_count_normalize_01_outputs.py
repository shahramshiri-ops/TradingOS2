#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COUNT-NORMALIZE-01 / SHADOW-SEMANTICS-01

Purpose:
- Stop confusing "near-miss count" with actual market opportunities.
- Separate diagnostic records, unique market near-miss events, blocker diagnostics,
  eligibility/lifecycle records, instrumentation gaps, active watches, and candidates.
- Produce panel-safe count semantics for the unified Shadow panel.

Boundary:
NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_POSITION_SIZE /
NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import json
import hashlib

ROOT = Path.cwd()

RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
RUNTIME_BRAIN = ROOT / "runtime" / "sig_brain"
RUNTIME_CAND = ROOT / "runtime" / "sig_signal_candidates"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"

for p in [RUNTIME_SHADOW, RUNTIME_BRAIN, RUNTIME_CAND, PANEL, PROOFS]:
    p.mkdir(parents=True, exist_ok=True)

AUTHORITY = (
    "COUNT_NORMALIZE_01|SHADOW_COUNT_SEMANTICS|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|"
    "NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"
)

# Inputs
REASON_SOURCE = RUNTIME_SHADOW / "near_miss_reason_source_current.json"
REASON_ENRICHED = RUNTIME_SHADOW / "near_miss_reason_enriched_current.json"
REASON_QUALITY = RUNTIME_SHADOW / "near_miss_reason_quality_current.json"
OPS_STATUS_RUNTIME = RUNTIME_SHADOW / "shadow_ops_status_current.json"
OPS_STATUS_PANEL = PANEL / "shadow_ops_status_current.json"
SHADOW_STATUS_RUNTIME = RUNTIME_SHADOW / "shadow_panel_status_current.json"
SHADOW_STATUS_PANEL = PANEL / "shadow_panel_status_current.json"
EVENT_HISTORY = RUNTIME_BRAIN / "sig_brain4_event_history_current.json"
CAND_PAYLOAD = RUNTIME_CAND / "signal_candidate_payload_current.json"
BLOCKER_BREAKDOWN = RUNTIME_SHADOW / "blocker_reason_breakdown_current.json"

# Outputs
OUT_SEMANTICS_RUNTIME = RUNTIME_SHADOW / "shadow_count_semantics_current.json"
OUT_SEMANTICS_PANEL = PANEL / "shadow_count_semantics_current.json"
OUT_VALIDATION = PROOFS / "sig_shadow_count_normalize_01_validation_result.json"

CORE_SHADOW_MEMORY_IDS = {
    "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_CAVEATED_WATCH_v1_0",
    "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0",
    "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0",
    "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0",
    "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0",
    "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0",
    "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0",
}

EXTENDED_OBSERVATION_ONLY_MEMORY_IDS = {
    "EURUSD_H1_LONDON_ASIAN_HIGH_SWEEP_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0",
    "XAUUSD_H1_WEEKLY_OPEN_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0",
}

MARKET_NEAR_MISS_REASON_CODES = {
    "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED",
    "CORE_ACTIVE_AWAITING_CANDIDATE_INTAKE",
    "TRIGGER_NOT_CONFIRMED",
    "SETUP_PARTIAL_ONLY",
    "MISSING_REQUIRED_FIELD",
    "SESSION_NOT_IN_SCOPE",
    "DATA_STALE",
}

BLOCKER_REASON_CODES = {
    "BLOCKER_OR_POLICY_VETO",
    "BLOCKER_LEDGER_REASON_UNKNOWN",
}

ELIGIBILITY_REASON_CODES = {
    "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT",
    "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW",
    "EXTENDED_ONLY_NOT_CORE",
    "NON_CORE_MEMORY",
    "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE",
}

LIFECYCLE_REASON_CODES = {
    "EXPIRED_BEFORE_CANDIDATE",
    "INVALIDATED_BEFORE_CANDIDATE",
    "DISPLAY_EXPIRY",
    "CONTEXT_INVALIDATION",
}

INSTRUMENTATION_GAP_REASON_CODES = {
    "UPSTREAM_REASON_NOT_EMITTED",
    "UPSTREAM_STAGE_REASON_NOT_EMITTED",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def stable_id(parts: List[Any]) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def first_non_null(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def as_list(payload: Any, keys: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in keys:
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def record_id(row: Dict[str, Any], idx: int) -> str:
    return str(
        row.get("reason_source_id")
        or row.get("diagnostic_id")
        or row.get("event_id")
        or row.get("candidate_id")
        or stable_id([idx, row.get("memory_id"), row.get("reason_code"), row.get("source_payload")])
    )


def event_like_key(row: Dict[str, Any], idx: int) -> str:
    """A conservative unique market-event key."""
    return str(
        row.get("event_id")
        or row.get("source_event_id")
        or stable_id([
            row.get("instrument"),
            row.get("timeframe"),
            row.get("memory_id") or row.get("source_memory_id"),
            row.get("source_bar_open_ts_utc"),
            row.get("activated_at_utc"),
            row.get("reason_code"),
            idx,
        ])
    )


def normalize_reason(row: Dict[str, Any]) -> str:
    for k in ["upstream_reason_code", "reason_code", "stage_failed", "blocker_reason_code", "original_reason_code"]:
        v = row.get(k)
        if v:
            s = str(v).upper().strip()
            if s not in {"UNKNOWN", "UNKNOWN_REASON", "UNKNOWN_NEAR_MISS_REASON", "NONE", "NULL"}:
                return s
    return "UNKNOWN_NEAR_MISS_REASON"


def classify_record(row: Dict[str, Any]) -> str:
    reason = normalize_reason(row)
    stage = str(row.get("canonical_stage") or row.get("normalized_stage") or row.get("stage_failed") or "").upper()
    source = str(row.get("source_payload") or row.get("source") or "").upper()
    mid = str(row.get("memory_id") or row.get("source_memory_id") or "")
    eligibility = str(row.get("eligibility_status") or "").upper()

    if reason in MARKET_NEAR_MISS_REASON_CODES or row.get("candidate_eligible_after_reason") or row.get("one_step_from_candidate"):
        return "MARKET_NEAR_MISS_EVENT"

    if reason in INSTRUMENTATION_GAP_REASON_CODES or stage == "UPSTREAM_INSTRUMENTATION_GAP":
        return "INSTRUMENTATION_GAP_RECORD"

    if reason in BLOCKER_REASON_CODES or "BLOCKER" in reason or "BLOCKER" in source or "BLOCKER" in stage:
        return "BLOCKER_DIAGNOSTIC_RECORD"

    if reason in ELIGIBILITY_REASON_CODES or "ELIGIBILITY" in stage or eligibility in {"ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY", "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE"}:
        return "ELIGIBILITY_RECORD"

    if reason in LIFECYCLE_REASON_CODES or "LIFECYCLE" in stage or eligibility in {"CORE_WATCH_EXPIRED_BEFORE_CANDIDATE", "CORE_WATCH_INVALIDATED_BEFORE_CANDIDATE"}:
        return "LIFECYCLE_RECORD"

    if mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        return "ELIGIBILITY_RECORD"

    if mid and mid not in CORE_SHADOW_MEMORY_IDS and source != "SIGNAL_CANDIDATE_PAYLOAD_CURRENT_BLOCKED":
        return "ELIGIBILITY_RECORD"

    return "DIAGNOSTIC_RECORD_UNCLASSIFIED"


def dedup_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = {}
    for idx, r in enumerate(records):
        out[record_id(r, idx)] = r
    return list(out.values())


def collect_records() -> List[Dict[str, Any]]:
    sources = [
        ("near_miss_reason_source_current", load_json(REASON_SOURCE, {}), ["records"]),
        ("near_miss_reason_enriched_current", load_json(REASON_ENRICHED, {}), ["records"]),
        ("blocker_reason_breakdown_current", load_json(BLOCKER_BREAKDOWN, {}), ["records", "blocked_candidates", "blockers"]),
    ]
    all_rows: List[Dict[str, Any]] = []
    for source_name, payload, keys in sources:
        for row in as_list(payload, keys):
            r = dict(row)
            r.setdefault("source_payload", source_name)
            all_rows.append(r)
    return dedup_records(all_rows)


def count_by(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    c = Counter(str(r.get(key) or "UNKNOWN") for r in rows)
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def active_watch_counts(event_history: Dict[str, Any]) -> Dict[str, int]:
    active_events = as_list(event_history, ["active_events"])
    counts = {
        "active_watch_count": len(active_events),
        "active_core_eligible_watch_count": 0,
        "active_extended_only_watch_count": 0,
        "active_non_core_watch_count": 0,
    }
    for e in active_events:
        mid = str(e.get("memory_id") or "")
        if mid in CORE_SHADOW_MEMORY_IDS:
            counts["active_core_eligible_watch_count"] += 1
        elif mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
            counts["active_extended_only_watch_count"] += 1
        else:
            counts["active_non_core_watch_count"] += 1
    return counts


def update_panel_ops(semantics: Dict[str, Any]) -> None:
    for path in [OPS_STATUS_RUNTIME, OPS_STATUS_PANEL]:
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            payload = {}

        payload["count_semantics_version"] = "COUNT_NORMALIZE_01_v1_0"
        payload["count_semantics_created_utc"] = semantics["created_utc"]
        payload["diagnostic_record_count_last_run"] = semantics["diagnostic_record_count_last_run"]
        payload["unique_market_near_miss_event_count_last_run"] = semantics["unique_market_near_miss_event_count_last_run"]
        payload["unique_memory_involved_count_last_run"] = semantics["unique_memory_involved_count_last_run"]
        payload["blocker_diagnostic_record_count_last_run"] = semantics["blocker_diagnostic_record_count_last_run"]
        payload["eligibility_record_count_last_run"] = semantics["eligibility_record_count_last_run"]
        payload["instrumentation_gap_record_count_last_run"] = semantics["instrumentation_gap_record_count_last_run"]
        payload["active_watch_count"] = semantics["active_watch_count"]
        payload["active_core_eligible_watch_count"] = semantics["active_core_eligible_watch_count"]
        payload["active_extended_only_watch_count"] = semantics["active_extended_only_watch_count"]
        payload["active_non_core_watch_count"] = semantics["active_non_core_watch_count"]
        payload["near_miss_count_label"] = "DIAGNOSTIC_RECORD_COUNT_NOT_MARKET_OPPORTUNITY_COUNT"
        payload["plain_language_fa"] = (
            "عدد near-miss در این پنل به معنی فرصت معاملاتی نیست. "
            "COUNT-NORMALIZE-01 آن را به diagnostic records، unique market near-miss events، blocker diagnostics، eligibility/lifecycle records و instrumentation gaps تفکیک می‌کند. "
            "این سیگنال یا دستور معامله نیست."
        )
        payload["top_count_class_breakdown"] = list(semantics["record_class_breakdown"].items())[:8]
        payload.setdefault("boundary", {})
        payload["boundary"].update({
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        })
        for flag in [
            "signal_authorized", "trade_instruction_authorized", "broker_execution_authorized",
            "action_surface_authorized", "auto_learning_authorized", "rule_rewrite_authorized",
        ]:
            if flag in payload:
                payload[flag] = False
        write_json(path, payload)


def main() -> None:
    created = now_utc()

    records = collect_records()
    event_history = load_json(EVENT_HISTORY, {})
    cand_payload = load_json(CAND_PAYLOAD, {})
    ops = load_json(OPS_STATUS_RUNTIME, {})
    shadow = load_json(SHADOW_STATUS_RUNTIME, {})

    classified = []
    market_event_keys = set()
    memory_ids = set()

    for idx, r in enumerate(records):
        rr = dict(r)
        rr["count_record_id"] = record_id(rr, idx)
        rr["count_class"] = classify_record(rr)
        rr["reason_code"] = normalize_reason(rr)
        rr["count_semantics_note"] = (
            "This is a diagnostic row, not automatically a unique market opportunity."
        )
        mid = str(rr.get("memory_id") or rr.get("source_memory_id") or "")
        if mid:
            memory_ids.add(mid)
        if rr["count_class"] == "MARKET_NEAR_MISS_EVENT":
            market_event_keys.add(event_like_key(rr, idx))
        classified.append(rr)

    record_class_breakdown = count_by(classified, "count_class")
    reason_breakdown = count_by(classified, "reason_code")
    source_breakdown = count_by(classified, "source_payload")
    memory_breakdown = count_by(classified, "memory_id")

    candidates = as_list(cand_payload, ["candidates"])
    blocked_candidates = as_list(cand_payload, ["blocked_candidates"])
    active_counts = active_watch_counts(event_history)

    semantics = {
        "payload_version": "COUNT_NORMALIZE_01_SHADOW_COUNT_SEMANTICS_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "count_policy": {
            "near_miss_is_not_trade_opportunity": True,
            "near_miss_panel_label_should_be": "diagnostic records",
            "candidate_definition": "A core-eligible memory that passes setup/trigger/blocker policy and is logged for shadow observation.",
            "market_near_miss_event_definition": "A unique live/runtime market state that appears one step from a candidate or fails a setup/trigger/input/session condition.",
            "diagnostic_record_definition": "Any row explaining why a watch/blocker/eligibility/lifecycle item did not become a candidate.",
        },
        "candidate_count": len(candidates),
        "blocked_candidate_count_from_payload": len(blocked_candidates),
        "raw_near_miss_count_from_ops": first_non_null(ops.get("near_miss_count_last_run"), shadow.get("near_miss_count_last_run")),
        "raw_near_miss_high_count_from_ops": first_non_null(ops.get("near_miss_high_count_last_run"), shadow.get("near_miss_high_count_last_run")),
        "raw_near_miss_count_from_shadow_status": shadow.get("near_miss_count_last_run"),
        "diagnostic_record_count_last_run": len(classified),
        "unique_market_near_miss_event_count_last_run": len(market_event_keys),
        "unique_memory_involved_count_last_run": len(memory_ids),
        "blocker_diagnostic_record_count_last_run": record_class_breakdown.get("BLOCKER_DIAGNOSTIC_RECORD", 0),
        "eligibility_record_count_last_run": record_class_breakdown.get("ELIGIBILITY_RECORD", 0),
        "lifecycle_record_count_last_run": record_class_breakdown.get("LIFECYCLE_RECORD", 0),
        "instrumentation_gap_record_count_last_run": record_class_breakdown.get("INSTRUMENTATION_GAP_RECORD", 0),
        "unclassified_diagnostic_record_count_last_run": record_class_breakdown.get("DIAGNOSTIC_RECORD_UNCLASSIFIED", 0),
        **active_counts,
        "record_class_breakdown": record_class_breakdown,
        "reason_breakdown": reason_breakdown,
        "source_breakdown": source_breakdown,
        "memory_breakdown": memory_breakdown,
        "records": classified,
        "plain_language_fa": (
            "این فایل معنای شمارش‌های Shadow را اصلاح می‌کند. "
            "near-miss خام لزوماً فرصت بازار نیست؛ در اینجا به diagnostic records، unique market near-miss events، blocker diagnostics، eligibility/lifecycle records و instrumentation gaps تفکیک شده است."
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    write_json(OUT_SEMANTICS_RUNTIME, semantics)
    write_json(OUT_SEMANTICS_PANEL, semantics)
    update_panel_ops(semantics)

    print(json.dumps({
        "status": "COUNT_NORMALIZE_01_OUTPUTS_BUILT",
        "candidate_count": semantics["candidate_count"],
        "raw_near_miss_count_from_ops": semantics["raw_near_miss_count_from_ops"],
        "diagnostic_record_count_last_run": semantics["diagnostic_record_count_last_run"],
        "unique_market_near_miss_event_count_last_run": semantics["unique_market_near_miss_event_count_last_run"],
        "unique_memory_involved_count_last_run": semantics["unique_memory_involved_count_last_run"],
        "instrumentation_gap_record_count_last_run": semantics["instrumentation_gap_record_count_last_run"],
        "active_watch_count": semantics["active_watch_count"],
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
