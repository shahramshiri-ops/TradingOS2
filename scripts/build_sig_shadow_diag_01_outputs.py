#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-DIAG-01 — Near-Miss / Blocker / Eligibility Diagnostic Hardening

Purpose:
- Convert raw near-miss/blocker/candidate status into explainable diagnostics.
- Distinguish active watch, core-shadow eligibility, extended-observation-only,
  blocked pre-candidate, and candidate logged.
- Produce last-run diagnostic ledgers and panel-safe summaries.

Boundary:
- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import json
import hashlib
import os
from collections import Counter, defaultdict

ROOT = Path.cwd()

RUNTIME_SIG_BRAIN = ROOT / "runtime" / "sig_brain"
RUNTIME_SIG_SHADOW = ROOT / "runtime" / "sig_shadow"
RUNTIME_SIG_CANDIDATES = ROOT / "runtime" / "sig_signal_candidates"
PANEL_BRAIN4 = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"

for p in [RUNTIME_SIG_SHADOW, RUNTIME_SIG_CANDIDATES, PANEL_BRAIN4, PROOFS]:
    p.mkdir(parents=True, exist_ok=True)

POLICY_PATH = ROOT / "sig_brain" / "shadow_diag_policy_v1_0.json"
READY_POLICY_PATH = ROOT / "sig_brain" / "shadow_ready_policy_v1_0.json"
COHORT_POLICY_PATH = ROOT / "sig_brain" / "shadow_cohort_policy_v1_0.json"

EVENT_HISTORY_PATH = RUNTIME_SIG_BRAIN / "sig_brain4_event_history_current.json"
BRAIN4_PAYLOAD_PATH = RUNTIME_SIG_BRAIN / "sig_brain4_runtime_payload_current.json"
CANDIDATE_PAYLOAD_PATH = RUNTIME_SIG_CANDIDATES / "signal_candidate_payload_current.json"
CANDIDATE_SUMMARY_PATH = RUNTIME_SIG_CANDIDATES / "signal_candidate_summary_current.json"
SHADOW_PANEL_STATUS_PATH = RUNTIME_SIG_SHADOW / "shadow_panel_status_current.json"
NEAR_MISS_LEDGER_PATH = RUNTIME_SIG_SHADOW / "near_miss_ledger_current.json"
BLOCKER_LEDGER_PATH = RUNTIME_SIG_SHADOW / "blocker_diagnostic_ledger_current.json"
SHADOW_SUMMARY_PATH = RUNTIME_SIG_SHADOW / "shadow_summary_current.json"

OUT_NEAR_MISS_DETAIL = RUNTIME_SIG_SHADOW / "near_miss_detail_ledger_current.json"
OUT_BLOCKER_BREAKDOWN = RUNTIME_SIG_SHADOW / "blocker_reason_breakdown_current.json"
OUT_ELIGIBILITY = RUNTIME_SIG_SHADOW / "eligibility_diagnostic_current.json"
OUT_PANEL_SUMMARY_RUNTIME = RUNTIME_SIG_SHADOW / "shadow_near_miss_summary_current.json"
OUT_PANEL_SUMMARY_PANEL = PANEL_BRAIN4 / "shadow_near_miss_summary_current.json"
OUT_VALIDATION = PROOFS / "sig_shadow_diag_01_validation_result.json"

AUTHORITY = (
    "SHADOW_DIAG_01|NEAR_MISS_BLOCKER_ELIGIBILITY_DIAGNOSTICS|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|"
    "NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"
)

# 9 core pilot memories selected by MEM-AUDIT-01D / SETUP-01 / SIGCAND-01.
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

# Out-of-core active memories retained only for observation until split-stability review.
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


def utc_now() -> str:
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


def as_list_from_payload(payload: Any, candidate_keys: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in candidate_keys:
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def event_key(e: Dict[str, Any]) -> str:
    return str(e.get("event_id") or e.get("candidate_id") or e.get("memory_id") or stable_id([
        e.get("memory_id"), e.get("instrument"), e.get("timeframe"), e.get("source_bar_open_ts_utc"),
        e.get("activated_at_utc"), e.get("status")
    ]))


def classify_event_eligibility(e: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Return eligibility_status, stage_failed, severity, reason."""
    mid = str(e.get("memory_id") or "")
    status = str(e.get("status") or e.get("event_status") or "").upper()
    no_trade = bool(e.get("no_trade", False))

    if not mid:
        return "UNKNOWN_MEMORY_ID", "MEMORY_ID_MISSING", "MEDIUM", "event has no memory_id"

    if no_trade:
        return "NOT_CANDIDATE_NO_TRADE_CONTEXT", "NO_TRADE_CONTEXT", "LOW", "no-trade/context memory is not directional candidate"

    if mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        return (
            "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY",
            "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT",
            "HIGH" if status == "ACTIVE" else "MEDIUM",
            "memory is active/displayable but excluded from core shadow because of split-stability caveat",
        )

    if mid not in CORE_SHADOW_MEMORY_IDS:
        return (
            "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE",
            "NON_CORE_MEMORY",
            "MEDIUM" if status == "ACTIVE" else "LOW",
            "memory is not in the 9 core setup/trigger pilot memories",
        )

    if status == "ACTIVE":
        return (
            "ACTIVE_WATCH_CORE_ELIGIBLE",
            "CANDIDATE_INTAKE_REQUIRED",
            "HIGH",
            "core memory is active; should be reviewed by signal-candidate intake",
        )

    if status == "EXPIRED":
        return (
            "CORE_WATCH_EXPIRED_BEFORE_CANDIDATE",
            "DISPLAY_EXPIRY",
            "LOW",
            "core memory was present in history but display window expired",
        )

    if status == "INVALIDATED":
        return (
            "CORE_WATCH_INVALIDATED_BEFORE_CANDIDATE",
            "CONTEXT_INVALIDATION",
            "LOW",
            "core memory context was invalidated before/after display lifecycle",
        )

    return (
        "CORE_WATCH_NON_ACTIVE",
        "NOT_ACTIVE_NOW",
        "LOW",
        f"core memory status is {status or 'UNKNOWN'}, not active for candidate intake",
    )


def normalize_near_miss(raw: Dict[str, Any], source: str, idx: int) -> Dict[str, Any]:
    mid = raw.get("memory_id") or raw.get("source_memory_id") or raw.get("candidate_memory_id")
    e = dict(raw)
    if not e.get("diagnostic_id"):
        e["diagnostic_id"] = "NM_" + stable_id([source, idx, mid, raw.get("event_id"), raw.get("stage_failed"), raw.get("created_utc")])
    e["source"] = source
    e["memory_id"] = mid or e.get("memory_id")
    e.setdefault("instrument", raw.get("instrument"))
    e.setdefault("timeframe", raw.get("timeframe"))
    e.setdefault("setup_cluster_id", CORE_FAMILY_BY_MEMORY.get(str(mid), raw.get("setup_cluster_id", "UNKNOWN_CLUSTER")))
    e.setdefault("stage_failed", raw.get("stage_failed") or raw.get("reason_code") or raw.get("diagnostic_reason") or "UNKNOWN_NEAR_MISS_REASON")
    e.setdefault("severity", raw.get("severity") or raw.get("near_miss_strength") or "MEDIUM")
    e.setdefault("candidate_eligible", False)
    e.setdefault("plain_language_fa", raw.get("plain_language_fa") or "این مورد near-miss است؛ یعنی به کاندید shadow نزدیک بوده اما کامل نشده است.")
    return e


def build_from_existing_near_misses(existing: Any) -> List[Dict[str, Any]]:
    records = []
    if isinstance(existing, dict):
        raw_list = []
        for key in ["near_misses", "items", "events", "records", "diagnostics"]:
            if isinstance(existing.get(key), list):
                raw_list.extend(existing[key])
        # Some earlier patch may only store summaries; no detailed list.
        for idx, raw in enumerate(raw_list):
            if isinstance(raw, dict):
                records.append(normalize_near_miss(raw, "near_miss_ledger_current", idx))
    elif isinstance(existing, list):
        for idx, raw in enumerate(existing):
            if isinstance(raw, dict):
                records.append(normalize_near_miss(raw, "near_miss_ledger_current", idx))
    return records


def build_event_diagnostics(event_history: Dict[str, Any], candidate_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = as_list_from_payload(event_history, ["active_events", "events"])
    active_events = as_list_from_payload(event_history, ["active_events"])
    candidates = as_list_from_payload(candidate_payload, ["candidates"])
    candidate_source_ids = set(str(c.get("source_event_id") or c.get("event_id") or c.get("source_memory_id") or c.get("memory_id")) for c in candidates)

    diagnostics = []
    # Prefer active_events; include recent events too for lifecycle explanation.
    dedup: Dict[str, Dict[str, Any]] = {}
    for e in events + active_events:
        if not isinstance(e, dict):
            continue
        dedup[event_key(e)] = e

    for ekey, e in dedup.items():
        mid = str(e.get("memory_id") or "")
        eligibility, stage_failed, severity, reason = classify_event_eligibility(e)
        is_candidate_logged = (
            ekey in candidate_source_ids
            or mid in candidate_source_ids
            or any(str(c.get("source_memory_id") or c.get("memory_id")) == mid for c in candidates)
        )
        if is_candidate_logged:
            eligibility = "SHADOW_CANDIDATE_LOGGED"
            stage_failed = "NONE"
            severity = "INFO"
            reason = "event/memory has corresponding shadow candidate"

        # We include only active/high-signal diagnostics prominently; expired/invalidated remain low severity.
        diagnostics.append({
            "diagnostic_id": "ELIG_" + stable_id([ekey, mid, e.get("status"), eligibility]),
            "event_id": ekey,
            "memory_id": mid,
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "session_bucket": e.get("session_bucket"),
            "direction_side": e.get("direction_side"),
            "source_bar_open_ts_utc": e.get("source_bar_open_ts_utc"),
            "source_bar_close_ts_utc": e.get("source_bar_close_ts_utc"),
            "activated_at_utc": e.get("activated_at_utc"),
            "last_seen_utc": e.get("last_seen_utc"),
            "expires_at_utc": e.get("expires_at_utc"),
            "event_status": e.get("status"),
            "setup_cluster_id": CORE_FAMILY_BY_MEMORY.get(mid, "OUT_OF_CORE_OR_UNKNOWN"),
            "eligibility_status": eligibility,
            "stage_failed": stage_failed,
            "severity": severity,
            "candidate_logged": is_candidate_logged,
            "reason": reason,
            "one_step_from_candidate": bool(severity == "HIGH" and eligibility in {
                "ACTIVE_WATCH_CORE_ELIGIBLE",
                "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY",
            }),
            "forbidden": "NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION",
        })

    return diagnostics


def build_blocker_breakdown(candidate_payload: Dict[str, Any], blocker_ledger: Any) -> List[Dict[str, Any]]:
    blocked = as_list_from_payload(candidate_payload, ["blocked_candidates"])
    records = []

    for idx, b in enumerate(blocked):
        reason = b.get("block_reason") or b.get("blocked_reason") or b.get("reason_code") or b.get("intake_status") or "BLOCKED_UNKNOWN_REASON"
        records.append({
            "blocker_diagnostic_id": "BLK_" + stable_id(["candidate_payload", idx, b.get("candidate_id"), b.get("memory_id"), reason]),
            "source": "signal_candidate_payload_current",
            "candidate_id": b.get("candidate_id"),
            "memory_id": b.get("memory_id") or b.get("source_memory_id"),
            "instrument": b.get("instrument"),
            "timeframe": b.get("timeframe"),
            "setup_cluster_id": b.get("setup_cluster_id") or CORE_FAMILY_BY_MEMORY.get(str(b.get("memory_id") or b.get("source_memory_id")), "UNKNOWN_CLUSTER"),
            "blocker_reason_code": reason,
            "blocker_family": b.get("blocker_family") or b.get("stage_failed") or "INTAKE_OR_POLICY_BLOCK",
            "severity": b.get("severity") or "MEDIUM",
            "plain_language_fa": b.get("plain_language_fa") or "این مورد به دلیل سیاست/بلوک‌کننده وارد candidate نشده است.",
        })

    # Existing blocker ledger may have more details.
    existing_list = []
    if isinstance(blocker_ledger, dict):
        for key in ["blocked_candidates", "blockers", "records", "items", "diagnostics"]:
            if isinstance(blocker_ledger.get(key), list):
                existing_list.extend(blocker_ledger[key])
    elif isinstance(blocker_ledger, list):
        existing_list = blocker_ledger

    for idx, b in enumerate(existing_list):
        if not isinstance(b, dict):
            continue
        reason = b.get("blocker_reason_code") or b.get("reason_code") or b.get("blocked_reason") or b.get("block_reason") or "BLOCKER_LEDGER_REASON_UNKNOWN"
        records.append({
            "blocker_diagnostic_id": b.get("blocker_diagnostic_id") or "BLKLED_" + stable_id(["blocker_ledger", idx, b.get("candidate_id"), b.get("memory_id"), reason]),
            "source": "blocker_diagnostic_ledger_current",
            "candidate_id": b.get("candidate_id"),
            "memory_id": b.get("memory_id") or b.get("source_memory_id"),
            "instrument": b.get("instrument"),
            "timeframe": b.get("timeframe"),
            "setup_cluster_id": b.get("setup_cluster_id") or CORE_FAMILY_BY_MEMORY.get(str(b.get("memory_id") or b.get("source_memory_id")), "UNKNOWN_CLUSTER"),
            "blocker_reason_code": reason,
            "blocker_family": b.get("blocker_family") or b.get("stage_failed") or "BLOCKER_LEDGER",
            "severity": b.get("severity") or "MEDIUM",
            "plain_language_fa": b.get("plain_language_fa") or "این مورد در لاگ blocker ثبت شده است.",
        })
    return records


def count_by(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    c = Counter(str(r.get(key) or "UNKNOWN") for r in rows)
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def main() -> None:
    created = utc_now()

    event_history = load_json(EVENT_HISTORY_PATH, {})
    brain4_payload = load_json(BRAIN4_PAYLOAD_PATH, {})
    candidate_payload = load_json(CANDIDATE_PAYLOAD_PATH, {})
    candidate_summary = load_json(CANDIDATE_SUMMARY_PATH, {})
    shadow_panel_status = load_json(SHADOW_PANEL_STATUS_PATH, {})
    existing_near_miss = load_json(NEAR_MISS_LEDGER_PATH, {})
    existing_blocker = load_json(BLOCKER_LEDGER_PATH, {})
    shadow_summary = load_json(SHADOW_SUMMARY_PATH, {})

    existing_nm = build_from_existing_near_misses(existing_near_miss)
    event_diags = build_event_diagnostics(event_history, candidate_payload)
    blocker_records = build_blocker_breakdown(candidate_payload, existing_blocker)

    # Convert eligibility diagnostics that are not candidate logged into near-miss/explainability rows.
    eligibility_as_near_miss = []
    for d in event_diags:
        if d.get("eligibility_status") == "SHADOW_CANDIDATE_LOGGED":
            continue
        if d.get("event_status") not in {"ACTIVE", "EXPIRED", "INVALIDATED"}:
            continue
        # Keep active + high severity + all core/out-of-core explanations; expired/invalidated are lower severity lifecycle diagnostics.
        eligibility_as_near_miss.append({
            "diagnostic_id": "NM_FROM_" + d["diagnostic_id"],
            "source": "event_history_eligibility_diagnostic",
            "event_id": d.get("event_id"),
            "memory_id": d.get("memory_id"),
            "instrument": d.get("instrument"),
            "timeframe": d.get("timeframe"),
            "setup_cluster_id": d.get("setup_cluster_id"),
            "stage_failed": d.get("stage_failed"),
            "severity": d.get("severity"),
            "eligibility_status": d.get("eligibility_status"),
            "one_step_from_candidate": d.get("one_step_from_candidate"),
            "reason": d.get("reason"),
            "plain_language_fa": (
                "این watch فعال/اخیر به candidate تبدیل نشده است. "
                f"دلیل: {d.get('reason')}"
            ),
            "forbidden": "NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION",
        })

    # Merge and de-duplicate by diagnostic_id.
    merged = {}
    for row in existing_nm + eligibility_as_near_miss:
        merged[str(row.get("diagnostic_id") or stable_id([row.get("source"), row.get("memory_id"), row.get("stage_failed")]))] = row
    near_miss_details = list(merged.values())

    # Severity normalization and high count.
    for r in near_miss_details:
        sev = str(r.get("severity") or "MEDIUM").upper()
        if sev not in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            # Older payload may use numeric-like or words.
            if "HIGH" in sev or "STRONG" in sev:
                sev = "HIGH"
            elif "LOW" in sev:
                sev = "LOW"
            else:
                sev = "MEDIUM"
        r["severity"] = sev

    high_near_miss_count = sum(1 for r in near_miss_details if str(r.get("severity")).upper() in {"HIGH", "CRITICAL"})
    last_run_near_miss_count = len(near_miss_details)

    candidates = as_list_from_payload(candidate_payload, ["candidates"])
    blocked_candidates = as_list_from_payload(candidate_payload, ["blocked_candidates"])

    # Eligibility summary.
    eligibility_summary = {
        "payload_version": "SHADOW_DIAG_01_ELIGIBILITY_DIAGNOSTIC_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "source_files": {
            "event_history": str(EVENT_HISTORY_PATH).replace("\\", "/"),
            "brain4_payload": str(BRAIN4_PAYLOAD_PATH).replace("\\", "/"),
            "candidate_payload": str(CANDIDATE_PAYLOAD_PATH).replace("\\", "/"),
            "near_miss_ledger": str(NEAR_MISS_LEDGER_PATH).replace("\\", "/"),
            "blocker_ledger": str(BLOCKER_LEDGER_PATH).replace("\\", "/"),
        },
        "brain4_payload_created_utc": brain4_payload.get("created_utc"),
        "candidate_payload_created_utc": candidate_payload.get("created_utc"),
        "shadow_panel_status_created_utc": shadow_panel_status.get("created_utc"),
        "active_event_count": (event_history.get("summary") or {}).get("active_event_count"),
        "event_count": (event_history.get("summary") or {}).get("event_count"),
        "candidate_count": len(candidates),
        "blocked_candidate_count": len(blocked_candidates) or len(blocker_records),
        "near_miss_detail_count": last_run_near_miss_count,
        "near_miss_high_count": high_near_miss_count,
        "eligibility_status_breakdown": count_by(event_diags, "eligibility_status"),
        "stage_failed_breakdown": count_by(near_miss_details, "stage_failed"),
        "severity_breakdown": count_by(near_miss_details, "severity"),
        "memory_breakdown": count_by(near_miss_details, "memory_id"),
        "cluster_breakdown": count_by(near_miss_details, "setup_cluster_id"),
        "event_diagnostics": event_diags,
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    blocker_breakdown = {
        "payload_version": "SHADOW_DIAG_01_BLOCKER_REASON_BREAKDOWN_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "blocked_candidate_count": len(blocker_records),
        "reason_breakdown": count_by(blocker_records, "blocker_reason_code"),
        "family_breakdown": count_by(blocker_records, "blocker_family"),
        "memory_breakdown": count_by(blocker_records, "memory_id"),
        "records": blocker_records,
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    near_miss_detail_payload = {
        "payload_version": "SHADOW_DIAG_01_NEAR_MISS_DETAIL_LEDGER_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "near_miss_detail_count": last_run_near_miss_count,
        "near_miss_high_count": high_near_miss_count,
        "stage_failed_breakdown": eligibility_summary["stage_failed_breakdown"],
        "severity_breakdown": eligibility_summary["severity_breakdown"],
        "memory_breakdown": eligibility_summary["memory_breakdown"],
        "cluster_breakdown": eligibility_summary["cluster_breakdown"],
        "records": near_miss_details,
        "plain_language_fa": (
            "این فایل توضیح می‌دهد چرا watchها یا وضعیت‌های نزدیک به setup به shadow candidate تبدیل نشده‌اند. "
            "این سیگنال یا دستور معامله نیست."
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    panel_summary = {
        "panel_payload_version": "SHADOW_DIAG_01_NEAR_MISS_PANEL_SUMMARY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "shadow_system_status": shadow_panel_status.get("shadow_system_status", "UNKNOWN"),
        "candidate_count": len(candidates),
        "near_miss_detail_count_last_run": last_run_near_miss_count,
        "near_miss_high_count_last_run": high_near_miss_count,
        "blocked_candidate_count": len(blocker_records),
        "top_stage_failed": list(eligibility_summary["stage_failed_breakdown"].items())[:5],
        "top_memory_breakdown": list(eligibility_summary["memory_breakdown"].items())[:5],
        "top_blocker_reasons": list(blocker_breakdown["reason_breakdown"].items())[:5],
        "active_watch_core_eligible_count": eligibility_summary["eligibility_status_breakdown"].get("ACTIVE_WATCH_CORE_ELIGIBLE", 0),
        "active_watch_extended_observation_only_count": eligibility_summary["eligibility_status_breakdown"].get("ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY", 0),
        "shadow_candidate_logged_count": eligibility_summary["eligibility_status_breakdown"].get("SHADOW_CANDIDATE_LOGGED", 0),
        "display_badge": "SHADOW DIAGNOSTICS / NOT A SIGNAL",
        "plain_language_fa": (
            "این کارت توضیح می‌دهد چرا وضعیت‌های نزدیک به setup/candidate هنوز به shadow candidate کامل تبدیل نشده‌اند. "
            "این سیگنال، ورود، حدضرر، تارگت یا اجرای معامله نیست."
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    write_json(OUT_NEAR_MISS_DETAIL, near_miss_detail_payload)
    write_json(OUT_BLOCKER_BREAKDOWN, blocker_breakdown)
    write_json(OUT_ELIGIBILITY, eligibility_summary)
    write_json(OUT_PANEL_SUMMARY_RUNTIME, panel_summary)
    write_json(OUT_PANEL_SUMMARY_PANEL, panel_summary)

    print(json.dumps({
        "status": "SHADOW_DIAG_01_OUTPUTS_BUILT",
        "candidate_count": len(candidates),
        "near_miss_detail_count": last_run_near_miss_count,
        "near_miss_high_count": high_near_miss_count,
        "blocked_candidate_count": len(blocker_records),
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
