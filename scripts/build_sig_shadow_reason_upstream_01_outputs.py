#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
REASON-UPSTREAM-01 / DIAG-02

Purpose:
- Replace vague UNKNOWN_NEAR_MISS_REASON with explicit, auditable reason codes where possible.
- Distinguish exact reasons from inferred reasons and low-confidence "upstream did not emit reason".
- Update Shadow OPS panel payload so the UI no longer hides the reason-quality problem.

Boundary:
NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_POSITION_SIZE /
NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
from collections import Counter
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
    "REASON_UPSTREAM_01|DIAG_02_NEAR_MISS_REASON_QUALITY|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|"
    "NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"
)

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

CORE_FAMILY_BY_MEMORY = {
    "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0": "EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG",
    "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_CAVEATED_WATCH_v1_0": "EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG",
    "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0": "EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG",
    "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
    "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
    "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
    "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
    "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
    "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "H1_LONDON_NY_SESSION_OPEN_TREND",
}

# Inputs
NEAR_REASON_ENRICHED = RUNTIME_SHADOW / "near_miss_reason_enriched_current.json"
NEAR_DETAIL = RUNTIME_SHADOW / "near_miss_detail_ledger_current.json"
ELIG_DIAG = RUNTIME_SHADOW / "eligibility_diagnostic_current.json"
ELIG_STATUS = RUNTIME_SHADOW / "eligibility_status_current.json"
BLOCKER_BREAKDOWN = RUNTIME_SHADOW / "blocker_reason_breakdown_current.json"
CAND_PAYLOAD = RUNTIME_CAND / "signal_candidate_payload_current.json"
EVENT_HISTORY = RUNTIME_BRAIN / "sig_brain4_event_history_current.json"
OPS_STATUS_RUNTIME = RUNTIME_SHADOW / "shadow_ops_status_current.json"
OPS_STATUS_PANEL = PANEL / "shadow_ops_status_current.json"

# Outputs
OUT_REASON_SOURCE = RUNTIME_SHADOW / "near_miss_reason_source_current.json"
OUT_REASON_QUALITY = RUNTIME_SHADOW / "near_miss_reason_quality_current.json"
OUT_REASON_ENRICHED = RUNTIME_SHADOW / "near_miss_reason_enriched_current.json"
OUT_VALIDATION = PROOFS / "sig_shadow_reason_upstream_01_validation_result.json"


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


def as_list(payload: Any, keys: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in keys:
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def text_blob(row: Dict[str, Any]) -> str:
    pieces = []
    for k in [
        "reason", "plain_language_fa", "plain_language_en", "normalized_reason",
        "stage_failed", "reason_code", "eligibility_status", "blocker_reason_code",
        "status", "event_status", "source", "memory_id",
    ]:
        if row.get(k) is not None:
            pieces.append(str(row.get(k)))
    return " | ".join(pieces).lower()


def normalize_existing_code(code: Any) -> str:
    c = str(code or "").strip()
    if not c:
        return "UNKNOWN_NEAR_MISS_REASON"
    upper = c.upper()
    if upper in {"UNKNOWN", "UNKNOWN_REASON", "UNKNOWN_NEAR_MISS_REASON", "NONE", "NULL"}:
        return "UNKNOWN_NEAR_MISS_REASON"
    return upper


def stage_for_reason(reason_code: str) -> str:
    mapping = {
        "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT": "ELIGIBILITY_OUT_OF_CORE",
        "EXTENDED_ONLY_NOT_CORE": "ELIGIBILITY_OUT_OF_CORE",
        "NON_CORE_MEMORY": "ELIGIBILITY_NON_CORE",
        "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE": "ELIGIBILITY_NON_CORE",
        "EXPIRED_BEFORE_CANDIDATE": "LIFECYCLE_EXPIRED",
        "DISPLAY_EXPIRY": "LIFECYCLE_EXPIRED",
        "INVALIDATED_BEFORE_CANDIDATE": "LIFECYCLE_INVALIDATED",
        "CONTEXT_INVALIDATION": "LIFECYCLE_INVALIDATED",
        "CORE_ACTIVE_AWAITING_CANDIDATE_INTAKE": "CANDIDATE_INTAKE_PENDING",
        "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED": "CANDIDATE_INTAKE_PENDING",
        "BLOCKER_OR_POLICY_VETO": "BLOCKER_OR_POLICY",
        "UPSTREAM_REASON_NOT_EMITTED": "UPSTREAM_INSTRUMENTATION_GAP",
        "UPSTREAM_STAGE_REASON_NOT_EMITTED": "UPSTREAM_INSTRUMENTATION_GAP",
        "MISSING_REQUIRED_FIELD": "INPUT_DATA",
        "DATA_STALE": "INPUT_DATA",
        "TRIGGER_NOT_CONFIRMED": "TRIGGER",
        "SETUP_PARTIAL_ONLY": "SETUP",
        "SESSION_NOT_IN_SCOPE": "SESSION_SCOPE",
    }
    return mapping.get(reason_code, reason_code)


def infer_reason(row: Dict[str, Any]) -> Tuple[str, str, str, bool]:
    """
    Returns:
    - reason_code
    - reason_confidence: HIGH/MEDIUM/LOW
    - reason_basis
    - needs_upstream_instrumentation
    """
    mid = str(row.get("memory_id") or row.get("source_memory_id") or "")
    eligibility = str(row.get("eligibility_status") or "")
    status = str(row.get("status") or row.get("event_status") or "").upper()
    existing = normalize_existing_code(row.get("reason_code") or row.get("stage_failed") or row.get("blocker_reason_code"))
    blob = text_blob(row)

    # Keep explicit non-unknown reasons.
    if existing != "UNKNOWN_NEAR_MISS_REASON":
        return existing, "HIGH", "explicit_reason_code_or_stage_failed_present", False

    # Exact structural reasons.
    if mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        return "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT", "HIGH", "memory_id_in_extended_observation_only_registry", False

    if eligibility == "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY":
        return "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT", "HIGH", "eligibility_status_extended_observation_only", False

    if mid and mid not in CORE_SHADOW_MEMORY_IDS and mid not in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        return "NON_CORE_MEMORY", "HIGH", "memory_id_not_in_core_shadow_registry", False

    if eligibility in {"ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE", "NON_CORE_LIFECYCLE_RECORD"}:
        return "NON_CORE_MEMORY", "HIGH", "eligibility_status_non_core", False

    if eligibility == "CORE_WATCH_EXPIRED_BEFORE_CANDIDATE" or status == "EXPIRED" or "expired" in blob:
        return "EXPIRED_BEFORE_CANDIDATE", "HIGH", "event_lifecycle_expired", False

    if eligibility == "CORE_WATCH_INVALIDATED_BEFORE_CANDIDATE" or status == "INVALIDATED" or "invalidated" in blob:
        return "INVALIDATED_BEFORE_CANDIDATE", "HIGH", "event_lifecycle_invalidated", False

    if eligibility == "ACTIVE_WATCH_CORE_ELIGIBLE":
        return "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED", "MEDIUM", "active_core_eligible_watch_but_candidate_payload_empty_or_not_linked", True

    # Textual hints.
    if "split-stability" in blob or "split stability" in blob or "extended observation" in blob or "out-of-core" in blob:
        return "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT", "HIGH", "text_hint_out_of_core_or_split_stability", False

    if "non-core" in blob or "not in core" in blob:
        return "NON_CORE_MEMORY", "HIGH", "text_hint_non_core", False

    if "block" in blob or "veto" in blob:
        return "BLOCKER_OR_POLICY_VETO", "MEDIUM", "text_hint_blocker_or_veto", False

    if "missing" in blob or "required field" in blob or "input insufficient" in blob:
        return "MISSING_REQUIRED_FIELD", "MEDIUM", "text_hint_missing_required_field", False

    if "stale" in blob:
        return "DATA_STALE", "MEDIUM", "text_hint_stale_data", False

    if "trigger" in blob:
        return "TRIGGER_NOT_CONFIRMED", "MEDIUM", "text_hint_trigger_not_confirmed", False

    if "setup" in blob or "partial" in blob:
        return "SETUP_PARTIAL_ONLY", "MEDIUM", "text_hint_setup_partial", False

    if "session" in blob and ("scope" in blob or "not in" in blob):
        return "SESSION_NOT_IN_SCOPE", "MEDIUM", "text_hint_session_scope", False

    # Honest fallback: not "unknown", but an instrumentation problem.
    return "UPSTREAM_REASON_NOT_EMITTED", "LOW", "no_explicit_stage_or_reason_emitted_by_upstream", True


def merge_records() -> List[Dict[str, Any]]:
    """
    Merge all possible near-miss/eligibility records. De-duplicate by diagnostic/event/memory/reason-ish id.
    """
    sources = [
        ("near_miss_reason_enriched_current", load_json(NEAR_REASON_ENRICHED, {}), ["records"]),
        ("near_miss_detail_ledger_current", load_json(NEAR_DETAIL, {}), ["records", "near_misses", "items"]),
        ("eligibility_diagnostic_current", load_json(ELIG_DIAG, {}), ["event_diagnostics", "records"]),
        ("eligibility_status_current", load_json(ELIG_STATUS, {}), ["event_diagnostics", "records"]),
        ("blocker_reason_breakdown_current", load_json(BLOCKER_BREAKDOWN, {}), ["records", "blocked_candidates", "blockers"]),
        ("signal_candidate_payload_current_blocked", load_json(CAND_PAYLOAD, {}), ["blocked_candidates"]),
        ("event_history_current", load_json(EVENT_HISTORY, {}), ["active_events", "events"]),
    ]

    merged: Dict[str, Dict[str, Any]] = {}

    for source_name, payload, keys in sources:
        for idx, row in enumerate(as_list(payload, keys)):
            if not isinstance(row, dict):
                continue

            # We focus on near-miss / blocked / eligibility-not-candidate / event lifecycle rows.
            record = dict(row)
            record["source_payload"] = source_name

            did = (
                record.get("diagnostic_id")
                or record.get("blocker_diagnostic_id")
                or record.get("event_id")
                or record.get("candidate_id")
                or stable_id([
                    source_name, idx, record.get("memory_id"), record.get("source_memory_id"),
                    record.get("eligibility_status"), record.get("stage_failed"), record.get("status")
                ])
            )

            # Avoid duplicated event_history full list overwhelming with expired records unless useful.
            if source_name == "event_history_current":
                status = str(record.get("status") or "").upper()
                mid = str(record.get("memory_id") or "")
                if status not in {"ACTIVE", "EXPIRED", "INVALIDATED"}:
                    continue
                if mid not in CORE_SHADOW_MEMORY_IDS and mid not in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
                    # Keep non-core active only, skip old non-core lifecycle noise.
                    if status != "ACTIVE":
                        continue

            merged[str(did)] = record

    return list(merged.values())


def enrich(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for idx, r in enumerate(records):
        mid = str(r.get("memory_id") or r.get("source_memory_id") or "")
        reason_code, confidence, basis, needs_inst = infer_reason(r)
        canonical_stage = stage_for_reason(reason_code)

        out = dict(r)
        out["reason_source_id"] = str(r.get("diagnostic_id") or r.get("event_id") or r.get("candidate_id") or "RS_" + stable_id([idx, mid, reason_code]))
        out["memory_id"] = mid or r.get("memory_id")
        out["setup_cluster_id"] = r.get("setup_cluster_id") or CORE_FAMILY_BY_MEMORY.get(mid, "UNKNOWN_CLUSTER")
        out["original_reason_code"] = normalize_existing_code(r.get("reason_code") or r.get("stage_failed") or r.get("blocker_reason_code"))
        out["upstream_reason_code"] = reason_code
        out["reason_code"] = reason_code
        out["canonical_stage"] = canonical_stage
        out["normalized_stage"] = canonical_stage
        out["reason_confidence"] = confidence
        out["reason_basis"] = basis
        out["needs_upstream_instrumentation"] = bool(needs_inst)
        out["core_shadow_memory"] = mid in CORE_SHADOW_MEMORY_IDS
        out["extended_observation_only"] = mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS
        out["candidate_eligible_after_reason"] = bool(reason_code in {"CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED"})
        out["review_priority"] = (
            "HIGH" if reason_code in {"CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED", "UPSTREAM_REASON_NOT_EMITTED"}
            else "MEDIUM" if confidence == "MEDIUM"
            else "LOW"
        )
        out["forbidden"] = "NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"
        enriched.append(out)

    # De-duplicate by reason_source_id.
    dedup = {}
    for r in enriched:
        dedup[str(r["reason_source_id"])] = r
    return list(dedup.values())


def count_by(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    c = Counter(str(r.get(key) or "UNKNOWN") for r in rows)
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def update_ops_status(enriched: List[Dict[str, Any]], created: str) -> None:
    reason_breakdown = count_by(enriched, "upstream_reason_code")
    stage_breakdown = count_by(enriched, "canonical_stage")
    confidence_breakdown = count_by(enriched, "reason_confidence")
    low_confidence_count = sum(1 for r in enriched if r.get("reason_confidence") == "LOW")
    instrumentation_gap_count = sum(1 for r in enriched if r.get("needs_upstream_instrumentation"))
    unresolved_unknown_after = sum(1 for r in enriched if r.get("upstream_reason_code") == "UNKNOWN_NEAR_MISS_REASON")

    for path in [OPS_STATUS_RUNTIME, OPS_STATUS_PANEL]:
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            payload = {}

        payload["reason_upstream_version"] = "REASON_UPSTREAM_01_v1_0"
        payload["reason_upstream_created_utc"] = created
        payload["top_reason_breakdown"] = list(reason_breakdown.items())[:8]
        payload["top_stage_breakdown"] = list(stage_breakdown.items())[:8]
        payload["reason_confidence_breakdown"] = confidence_breakdown
        payload["low_confidence_reason_count"] = low_confidence_count
        payload["instrumentation_gap_count"] = instrumentation_gap_count
        payload["unresolved_unknown_reason_count_after_reason_upstream"] = unresolved_unknown_after
        payload["plain_language_fa"] = (
            "این کارت وضعیت عملیاتی shadow را نشان می‌دهد. reason-upstream تلاش کرده علت near-missها را صریح‌تر کند. "
            "موارد LOW confidence به معنی نیاز به instrument کردن دقیق‌تر setup/trigger/blocker است. این سیگنال یا دستور معامله نیست."
        )
        payload.setdefault("boundary", {})
        payload["boundary"].update({
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        })
        # Keep old top-level flags safe if they exist.
        for flag in [
            "signal_authorized", "trade_instruction_authorized", "broker_execution_authorized",
            "action_surface_authorized", "auto_learning_authorized", "rule_rewrite_authorized",
        ]:
            if flag in payload:
                payload[flag] = False

        write_json(path, payload)


def main() -> None:
    created = now_utc()
    records = merge_records()
    enriched = enrich(records)

    reason_breakdown = count_by(enriched, "upstream_reason_code")
    stage_breakdown = count_by(enriched, "canonical_stage")
    confidence_breakdown = count_by(enriched, "reason_confidence")
    original_breakdown = count_by(enriched, "original_reason_code")
    memory_breakdown = count_by(enriched, "memory_id")
    cluster_breakdown = count_by(enriched, "setup_cluster_id")

    unknown_before = sum(1 for r in enriched if r.get("original_reason_code") == "UNKNOWN_NEAR_MISS_REASON")
    unknown_after = sum(1 for r in enriched if r.get("upstream_reason_code") == "UNKNOWN_NEAR_MISS_REASON")
    instrumentation_gap = sum(1 for r in enriched if r.get("needs_upstream_instrumentation"))
    low_conf = sum(1 for r in enriched if r.get("reason_confidence") == "LOW")

    source_payload = {
        "payload_version": "REASON_UPSTREAM_01_SOURCE_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "record_count": len(enriched),
        "unknown_reason_count_before": unknown_before,
        "unknown_reason_count_after": unknown_after,
        "instrumentation_gap_count": instrumentation_gap,
        "low_confidence_reason_count": low_conf,
        "reason_breakdown": reason_breakdown,
        "stage_breakdown": stage_breakdown,
        "reason_confidence_breakdown": confidence_breakdown,
        "original_reason_breakdown": original_breakdown,
        "memory_breakdown": memory_breakdown,
        "cluster_breakdown": cluster_breakdown,
        "records": enriched,
        "plain_language_fa": (
            "این فایل دلیل‌های near-miss / blocked / eligibility را با کدهای صریح‌تر ثبت می‌کند. "
            "LOW confidence یعنی upstream هنوز stage/reason دقیق تولید نکرده و باید در پچ‌های بعدی در همان setup/trigger/blocker instrument شود."
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    quality_payload = {
        "payload_version": "REASON_UPSTREAM_01_QUALITY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "quality_status": "PASS" if unknown_after == 0 else "WARN",
        "record_count": len(enriched),
        "unknown_reason_count_before": unknown_before,
        "unknown_reason_count_after": unknown_after,
        "instrumentation_gap_count": instrumentation_gap,
        "low_confidence_reason_count": low_conf,
        "high_confidence_count": confidence_breakdown.get("HIGH", 0),
        "medium_confidence_count": confidence_breakdown.get("MEDIUM", 0),
        "reason_breakdown": reason_breakdown,
        "stage_breakdown": stage_breakdown,
        "recommended_next_action": (
            "Instrument setup/trigger/blocker upstream to emit reason_code directly"
            if instrumentation_gap or low_conf else
            "Continue live observation; reason quality acceptable"
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    # Keep compatibility: overwrite existing enriched near-miss file with better reason fields.
    compat_payload = {
        "payload_version": "REASON_UPSTREAM_01_COMPAT_NEAR_MISS_REASON_ENRICHED_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "near_miss_count": len(enriched),
        "near_miss_high_count": sum(1 for r in enriched if r.get("review_priority") == "HIGH"),
        "reason_breakdown": reason_breakdown,
        "stage_breakdown": stage_breakdown,
        "reason_confidence_breakdown": confidence_breakdown,
        "records": enriched,
        "plain_language_fa": "reason-upstream این فایل را با reason_codeهای دقیق‌تر بازنویسی کرده است. این سیگنال نیست.",
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    write_json(OUT_REASON_SOURCE, source_payload)
    write_json(OUT_REASON_QUALITY, quality_payload)
    write_json(OUT_REASON_ENRICHED, compat_payload)
    update_ops_status(enriched, created)

    print(json.dumps({
        "status": "REASON_UPSTREAM_01_OUTPUTS_BUILT",
        "record_count": len(enriched),
        "unknown_reason_count_before": unknown_before,
        "unknown_reason_count_after": unknown_after,
        "instrumentation_gap_count": instrumentation_gap,
        "low_confidence_reason_count": low_conf,
        "top_reason_breakdown": list(reason_breakdown.items())[:5],
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
