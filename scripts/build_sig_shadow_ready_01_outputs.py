#!/usr/bin/env python3
"""
SHADOW-READY-01 builder.

Builds the readiness hardening layer around SHADOW-01B:
- near-miss diagnostics
- blocked/pre-candidate diagnostics
- cohort/version stamping
- health monitoring
- observation completion status
- daily/weekly summaries
- panel-safe status payload
- PMO review queue

Boundary:
- NOT a signal
- NO buy/sell
- NO entry/stop/target
- NO position sizing
- NO broker/execution
- NO automatic learning or rule rewrite
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

AUTHORITY = "SHADOW_READY_01|LIVE_SHADOW_READINESS_HARDENING|NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|NO_AUTO_LEARNING"
PATCH_VERSION = "SHADOW_READY_01_REPO_PATCH_v1_0"

CORE_MEMORY_MAP = {
  "EURUSD_H1_FAILED_BREAKOUT_TRAP_PRIOR_DAY_LOW_LONG_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
  "EURUSD_H1_LONDON_NY_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_LONG_D1UP_H4UP_CAVEATED_WATCH_v1_0": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
  "EURUSD_H1_TARGETED_LONDON_MORNING_LOW_FAILED_DOWNSIDE_LONG_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_EURUSD_H1_LOW_SWEEP_FAILED_BREAKOUT_LONG_v1_0",
  "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
  "EURUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
  "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
  "USDJPY_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
  "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_LONG_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
  "XAUUSD_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_SHORT_DIRECTIONAL_WATCH_v1_0": "SETUP_CLUSTER_H1_LONDON_NY_OVERLAP_SESSION_OPEN_TREND_v1_0",
}

OUT_OF_CORE_MEMORY_MAP = {
  "EURUSD_H1_LONDON_ASIAN_HIGH_SWEEP_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0": "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW",
  "XAUUSD_H1_WEEKLY_OPEN_RECLAIM_SHORT_DIRECTIONAL_WATCH_v1_0": "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW",
}

FORBIDDEN_TOP_LEVEL = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


def age_minutes(value: Any) -> float | None:
    d = parse_utc(value)
    if d is None:
        return None
    return round((dt.datetime.now(dt.timezone.utc) - d).total_seconds() / 60.0, 2)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def short_hash(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def summarize_counts(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        v = str(r.get(key) or "UNKNOWN")
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def failure_categories(card: Dict[str, Any]) -> List[str]:
    text = " | ".join([str(x) for x in safe_list(card.get("failed_conditions")) + safe_list(card.get("missing_inputs"))]).lower()
    cats = []
    checks = [
        ("MISSING_INPUT", ["missing", "input", "field"]),
        ("DATA_STALE_OR_INSUFFICIENT", ["stale", "sufficiency", "data_sufficiency", "unavailable"]),
        ("SESSION_OR_TIME_WINDOW", ["session", "overlap", "london", "new_york", "asian"]),
        ("D1_H4_REGIME_MISMATCH", ["d1", "h4", "trend", "context"]),
        ("REFERENCE_LEVEL_NOT_READY", ["prior day", "prior_day", "london low", "level", "reference"]),
        ("SWEEP_RECLAIM_NOT_CONFIRMED", ["sweep", "reclaim", "failed_breakout", "breakout", "rejection"]),
        ("DIRECTION_OR_CLOSE_CONFIRMATION_MISSING", ["direction", "close", "bar_direction", "bullish", "bearish"]),
        ("FIRST_BAR_OR_TRIGGER_TIMING", ["first", "trigger", "timing"]),
    ]
    for label, needles in checks:
        if any(n in text for n in needles):
            cats.append(label)
    return cats or ["CONDITION_MISMATCH_UNCLASSIFIED"]


def near_miss_strength(card: Dict[str, Any]) -> str:
    matched = len(safe_list(card.get("matched_conditions")))
    failed = len(safe_list(card.get("failed_conditions")))
    missing = len(safe_list(card.get("missing_inputs")))
    if bool(card.get("is_active_match")):
        return "MATCHED_NOT_NEAR_MISS"
    if missing:
        return "INPUT_INSUFFICIENT_DIAGNOSTIC"
    if matched >= 3 and failed <= 2:
        return "NEAR_MISS_HIGH"
    if matched >= 1:
        return "NEAR_MISS_MEDIUM"
    return "NON_MATCH_LOW_CONTEXT"


def build_near_miss_and_blockers(brain4: Dict[str, Any], candidate_payload: Dict[str, Any], blocked_ledger: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cards = safe_list(brain4.get("cards"))
    candidates = safe_list(candidate_payload.get("candidates"))
    candidate_memory_ids = set()
    for c in candidates:
        for mid in safe_list(c.get("source_memory_ids")):
            candidate_memory_ids.add(str(mid))

    rows: List[Dict[str, Any]] = []
    now = utc_now()
    for card in cards:
        mid = str(card.get("memory_id") or "")
        if mid not in CORE_MEMORY_MAP and mid not in OUT_OF_CORE_MEMORY_MAP:
            continue
        active_runtime = bool(card.get("active_in_runtime"))
        if not active_runtime and mid not in OUT_OF_CORE_MEMORY_MAP:
            continue
        cluster = CORE_MEMORY_MAP.get(mid) or "OUT_OF_CORE_OBSERVATION"
        is_match = bool(card.get("is_active_match"))
        strength = near_miss_strength(card)
        ctx = card.get("latest_context") if isinstance(card.get("latest_context"), dict) else {}
        row = {
            "near_miss_id": "NM_" + short_hash("|".join([mid, str(brain4.get("created_utc")), str(ctx.get("latest_bar_open_ts_utc") or ctx.get("bar_open_ts_utc")), strength])),
            "created_utc": now,
            "source_payload_created_utc": brain4.get("created_utc"),
            "memory_id": mid,
            "setup_cluster_id": cluster,
            "instrument": card.get("instrument"),
            "timeframe": card.get("timeframe"),
            "active_in_runtime": active_runtime,
            "is_active_match": is_match,
            "core_pilot_eligible": mid in CORE_MEMORY_MAP,
            "out_of_core_reason": OUT_OF_CORE_MEMORY_MAP.get(mid, ""),
            "candidate_payload_contains_memory": mid in candidate_memory_ids,
            "diagnostic_state": "ACTIVE_MATCH_REGISTERED_OR_SUPPRESSED" if is_match else strength,
            "near_miss_strength": strength,
            "matched_condition_count": len(safe_list(card.get("matched_conditions"))),
            "failed_condition_count": len(safe_list(card.get("failed_conditions"))),
            "missing_input_count": len(safe_list(card.get("missing_inputs"))),
            "failure_categories": failure_categories(card),
            "matched_conditions": safe_list(card.get("matched_conditions"))[:20],
            "failed_conditions": safe_list(card.get("failed_conditions"))[:20],
            "missing_inputs": safe_list(card.get("missing_inputs"))[:20],
            "brain_state": card.get("brain_state"),
            "status_badge": card.get("status_badge"),
            "latest_context_excerpt": {k: ctx.get(k) for k in sorted(ctx.keys())[:60]},
            **FORBIDDEN_TOP_LEVEL,
        }
        rows.append(row)

    near_miss_rows = [r for r in rows if r["diagnostic_state"] not in ("MATCHED_NOT_NEAR_MISS", "ACTIVE_MATCH_REGISTERED_OR_SUPPRESSED")]
    high_rows = [r for r in near_miss_rows if r.get("near_miss_strength") == "NEAR_MISS_HIGH"]

    near_miss_ledger = {
        "ledger_version": "SIG_SHADOW_READY_01_NEAR_MISS_LEDGER_v1_0",
        "created_utc": now,
        "updated_utc": now,
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "near_misses": rows,
        "summary": {
            "diagnostic_row_count": len(rows),
            "near_miss_count": len(near_miss_rows),
            "near_miss_high_count": len(high_rows),
            "by_diagnostic_state": summarize_counts(rows, "diagnostic_state"),
            "by_cluster": summarize_counts(rows, "setup_cluster_id"),
            "by_instrument": summarize_counts(rows, "instrument"),
            "purpose": "diagnostic_only_no_rule_change_no_signal",
        },
    }

    blocker_rows: List[Dict[str, Any]] = []
    for b in safe_list(blocked_ledger.get("blocked_candidates")):
        row = dict(b)
        row.update({
            "diagnostic_id": "BD_" + short_hash(str(b.get("blocked_candidate_id")) + str(b.get("blocked_at_utc"))),
            "diagnostic_source": "SHADOW_01B_BLOCKED_CANDIDATE_LEDGER",
            "diagnostic_type": "ACTUAL_BLOCKED_CANDIDATE",
            **FORBIDDEN_TOP_LEVEL,
        })
        blocker_rows.append(row)

    for r in near_miss_rows:
        cats = r.get("failure_categories") or []
        if r.get("missing_input_count") or any(c in cats for c in ["MISSING_INPUT", "DATA_STALE_OR_INSUFFICIENT", "REFERENCE_LEVEL_NOT_READY", "SWEEP_RECLAIM_NOT_CONFIRMED"]):
            blocker_rows.append({
                "diagnostic_id": "BD_" + short_hash(r["near_miss_id"]),
                "diagnostic_source": "NEAR_MISS_LEDGER",
                "diagnostic_type": "PRE_CANDIDATE_BLOCKER_OR_GATING_DIAGNOSTIC",
                "memory_id": r.get("memory_id"),
                "setup_cluster_id": r.get("setup_cluster_id"),
                "instrument": r.get("instrument"),
                "timeframe": r.get("timeframe"),
                "blocking_or_gating_categories": cats,
                "near_miss_strength": r.get("near_miss_strength"),
                "missing_inputs": r.get("missing_inputs"),
                "failed_conditions": r.get("failed_conditions"),
                "candidate_created": False,
                "reason": "diagnostic only; no candidate generated before all conditions cleared",
                **FORBIDDEN_TOP_LEVEL,
            })

    blocker_diag = {
        "ledger_version": "SIG_SHADOW_READY_01_BLOCKER_DIAGNOSTIC_LEDGER_v1_0",
        "created_utc": now,
        "updated_utc": now,
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "diagnostics": blocker_rows,
        "summary": {
            "diagnostic_count": len(blocker_rows),
            "actual_blocked_candidate_count": sum(1 for r in blocker_rows if r.get("diagnostic_type") == "ACTUAL_BLOCKED_CANDIDATE"),
            "pre_candidate_gating_diagnostic_count": sum(1 for r in blocker_rows if r.get("diagnostic_type") == "PRE_CANDIDATE_BLOCKER_OR_GATING_DIAGNOSTIC"),
            "by_diagnostic_type": summarize_counts(blocker_rows, "diagnostic_type"),
            "by_cluster": summarize_counts(blocker_rows, "setup_cluster_id"),
            "purpose": "diagnostic_only_no_rule_change_no_signal",
        },
    }
    return near_miss_ledger, blocker_diag


def build_cohort(registry: Dict[str, Any], policy: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    versions = {
        "memory_registry_version": registry.get("registry_version") or registry.get("version") or "UNKNOWN",
        "setup_contract_version": "SETUP_01_v1_0",
        "trigger_contract_version": "TRIG_01_v1_0",
        "blocker_policy_version": "BLOCK_01_v1_0",
        "qvec_version": "QVEC_01_v1_0",
        "sigcand_version": "SIGCAND_01_v1_0",
        "shadow_policy_version": "SHADOW_01_v1_0",
        "shadow_01b_runtime_version": "SHADOW_01B_INTEGRATED_SAFE_v1_0",
        "shadow_ready_version": PATCH_VERSION,
    }
    signature = short_hash(json.dumps(versions, sort_keys=True), 20)
    existing_sig = existing.get("version_signature") if isinstance(existing, dict) else None
    now = utc_now()
    started = existing.get("cohort_started_utc") if existing_sig == signature else now
    seq = int(existing.get("cohort_sequence") or 0)
    if existing_sig != signature:
        seq += 1
    return {
        "cohort_version": "SIG_SHADOW_COHORT_v1_0",
        "cohort_id": f"SHADOW_COHORT_{signature}",
        "cohort_sequence": seq,
        "cohort_started_utc": started,
        "updated_utc": now,
        "version_signature": signature,
        "version_change_detected_from_previous_run": bool(existing_sig and existing_sig != signature),
        "versions": versions,
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "cohort_policy": policy.get("cohort_policy", {}),
        "interpretation": "Events are comparable inside the same cohort signature. Rule changes create a new cohort instead of rewriting old evidence.",
    }


def build_observation_completion(observation_ledger: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    observations = safe_list(observation_ledger.get("observations"))
    rows = []
    for o in observations:
        horizons = o.get("horizons") if isinstance(o.get("horizons"), dict) else {}
        h_states = {k: (v.get("horizon_state") if isinstance(v, dict) else "UNKNOWN") for k, v in horizons.items()}
        rows.append({
            "candidate_id": o.get("candidate_id"),
            "instrument": o.get("instrument"),
            "timeframe": o.get("timeframe"),
            "directional_bias": o.get("directional_bias"),
            "trigger_bar_open_ts_utc": o.get("trigger_bar_open_ts_utc"),
            "observation_state": o.get("observation_state"),
            "horizon_states": h_states,
            "observed_horizon_count": sum(1 for s in h_states.values() if s == "OBSERVED"),
            "pending_horizon_count": sum(1 for s in h_states.values() if str(s).startswith("PENDING")),
            "error_horizon_count": sum(1 for s in h_states.values() if s not in ("OBSERVED", "PENDING_FUTURE_BARS")),
            **FORBIDDEN_TOP_LEVEL,
        })
    return {
        "ledger_version": "SIG_SHADOW_READY_01_OBSERVATION_COMPLETION_v1_0",
        "created_utc": now,
        "updated_utc": now,
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "observation_completion": rows,
        "summary": {
            "observation_count": len(rows),
            "by_observation_state": summarize_counts(rows, "observation_state"),
            "complete_count": sum(1 for r in rows if r.get("observation_state") == "OBSERVED_COMPLETE"),
            "pending_count": sum(1 for r in rows if r.get("observation_state") == "PENDING_OBSERVATION"),
            "error_or_unavailable_count": sum(1 for r in rows if r.get("observation_state") not in ("OBSERVED_COMPLETE", "PENDING_OBSERVATION")),
        },
    }


def date_key(ts: Any) -> str:
    s = str(ts or "")
    return s[:10] if len(s) >= 10 else "UNKNOWN_DATE"


def week_key(ts: Any) -> str:
    d = parse_utc(ts)
    if d is None:
        return "UNKNOWN_WEEK"
    iso = d.isocalendar()
    if hasattr(iso, "year"):
        iso_year = iso.year
        iso_week = iso.week
    else:
        iso_year = iso[0]
        iso_week = iso[1]
    return f"{iso_year}-W{iso_week:02d}"


def build_period_summaries(candidate_ledger: Dict[str, Any], observation_ledger: Dict[str, Any], near_miss: Dict[str, Any], blocker_diag: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    now = utc_now()
    candidates = safe_list(candidate_ledger.get("candidates"))
    observations = safe_list(observation_ledger.get("observations"))
    near_rows = safe_list(near_miss.get("near_misses"))
    block_rows = safe_list(blocker_diag.get("diagnostics"))

    def aggregate(period_func):
        buckets: Dict[str, Dict[str, Any]] = {}
        def bget(k):
            if k not in buckets:
                buckets[k] = {"period": k, "candidate_count": 0, "observation_count": 0, "near_miss_count": 0, "blocked_or_gating_diagnostic_count": 0, "by_cluster": {}, **FORBIDDEN_TOP_LEVEL}
            return buckets[k]
        for c in candidates:
            k = period_func(c.get("trigger_bar_open_ts_utc") or c.get("created_utc") or c.get("first_seen_utc"))
            b = bget(k); b["candidate_count"] += 1
            cl = c.get("setup_cluster_id") or "UNKNOWN"; b["by_cluster"][cl] = b["by_cluster"].get(cl, 0) + 1
        for o in observations:
            k = period_func(o.get("trigger_bar_open_ts_utc"))
            bget(k)["observation_count"] += 1
        for n in near_rows:
            k = period_func(n.get("source_payload_created_utc") or n.get("created_utc"))
            bget(k)["near_miss_count"] += 1
        for bd in block_rows:
            k = period_func(bd.get("blocked_at_utc") or bd.get("created_utc") or now)
            bget(k)["blocked_or_gating_diagnostic_count"] += 1
        return [buckets[k] for k in sorted(buckets)]

    daily_rows = aggregate(date_key)
    weekly_rows = aggregate(week_key)
    daily = {"summary_version": "SIG_SHADOW_READY_01_DAILY_SUMMARY_v1_0", "created_utc": now, "authority": AUTHORITY, **FORBIDDEN_TOP_LEVEL, "periods": daily_rows[-45:], "summary": {"period_count": len(daily_rows), "latest_period": daily_rows[-1]["period"] if daily_rows else None}}
    weekly = {"summary_version": "SIG_SHADOW_READY_01_WEEKLY_SUMMARY_v1_0", "created_utc": now, "authority": AUTHORITY, **FORBIDDEN_TOP_LEVEL, "periods": weekly_rows[-26:], "summary": {"period_count": len(weekly_rows), "latest_period": weekly_rows[-1]["period"] if weekly_rows else None}}
    return daily, weekly


def build_health(brain4: Dict[str, Any], candidate_payload: Dict[str, Any], candidate_ledger: Dict[str, Any], observation_ledger: Dict[str, Any], blocked_ledger: Dict[str, Any], shadow_summary: Dict[str, Any], proof_01b: Dict[str, Any], near_miss: Dict[str, Any], blocker_diag: Dict[str, Any], cohort: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    warnings: List[str] = []
    failures: List[str] = []

    brain4_age = age_minutes(brain4.get("created_utc"))
    if not brain4:
        failures.append("brain4_payload_missing")
    elif brain4_age is not None and brain4_age > 180:
        warnings.append(f"brain4_payload_stale_age_minutes={brain4_age}")

    if proof_01b.get("validation_status") not in ("PASS", None, ""):
        failures.append("shadow_01b_validation_not_pass")
    if not candidate_ledger:
        failures.append("candidate_ledger_missing")
    if not observation_ledger:
        failures.append("observation_ledger_missing")
    if cohort.get("version_change_detected_from_previous_run"):
        warnings.append("cohort_version_changed_new_segment_started")

    health_status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    return {
        "summary_version": "SIG_SHADOW_READY_01_HEALTH_SUMMARY_v1_0",
        "created_utc": now,
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "health_status": health_status,
        "failures": failures,
        "warnings": warnings,
        "freshness": {
            "brain4_payload_created_utc": brain4.get("created_utc"),
            "brain4_payload_age_minutes": brain4_age,
            "candidate_payload_created_utc": candidate_payload.get("created_utc"),
            "candidate_payload_age_minutes": age_minutes(candidate_payload.get("created_utc")),
            "candidate_ledger_updated_utc": candidate_ledger.get("updated_utc"),
            "candidate_ledger_age_minutes": age_minutes(candidate_ledger.get("updated_utc")),
            "shadow_summary_created_utc": shadow_summary.get("created_utc"),
        },
        "counts": {
            "brain4_memory_count": (brain4.get("registry_summary") or {}).get("memory_count"),
            "brain4_active_runtime_memory_count": (brain4.get("registry_summary") or {}).get("active_runtime_memory_count"),
            "brain4_active_match_count": (brain4.get("registry_summary") or {}).get("active_match_count"),
            "candidate_payload_count": len(safe_list(candidate_payload.get("candidates"))),
            "shadow_candidate_ledger_count": len(safe_list(candidate_ledger.get("candidates"))),
            "observation_count": len(safe_list(observation_ledger.get("observations"))),
            "blocked_candidate_count": len(safe_list(blocked_ledger.get("blocked_candidates"))),
            "near_miss_count": near_miss.get("summary", {}).get("near_miss_count"),
            "near_miss_high_count": near_miss.get("summary", {}).get("near_miss_high_count"),
            "blocker_diagnostic_count": blocker_diag.get("summary", {}).get("diagnostic_count"),
        },
        "cohort": {"cohort_id": cohort.get("cohort_id"), "cohort_started_utc": cohort.get("cohort_started_utc"), "version_signature": cohort.get("version_signature")},
        "plain_language_fa": "این health فقط سلامت ثبت و مشاهدهٔ shadow را نشان می‌دهد؛ سیگنال یا مجوز معامله نیست.",
        "plain_language_en": "This health payload only describes shadow logging/observation readiness; it is not a signal or trading authorization.",
    }


def build_panel_status(health: Dict[str, Any], candidate_ledger: Dict[str, Any], observation_completion: Dict[str, Any], near_miss: Dict[str, Any], cohort: Dict[str, Any]) -> Dict[str, Any]:
    counts = health.get("counts", {})
    recent_candidates = safe_list(candidate_ledger.get("candidates"))[-5:]
    return {
        "panel_payload_version": "SIG_SHADOW_READY_01_PANEL_STATUS_v1_0",
        "created_utc": utc_now(),
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "shadow_system_status": health.get("health_status"),
        "cohort_id": cohort.get("cohort_id"),
        "candidate_count": counts.get("shadow_candidate_ledger_count", 0),
        "candidate_count_last_payload": counts.get("candidate_payload_count", 0),
        "near_miss_count_last_run": counts.get("near_miss_count", 0),
        "near_miss_high_count_last_run": counts.get("near_miss_high_count", 0),
        "observation_count": counts.get("observation_count", 0),
        "observation_complete_count": observation_completion.get("summary", {}).get("complete_count", 0),
        "observation_pending_count": observation_completion.get("summary", {}).get("pending_count", 0),
        "recent_shadow_candidates_display_only": recent_candidates,
        "display_badge": "SHADOW READY / NOT A SIGNAL" if health.get("health_status") in ("PASS", "WARN") else "SHADOW HEALTH ISSUE / NOT A SIGNAL",
        "plain_language_fa": "سیستم فقط کاندیدهای فرضی shadow و near-missها را ثبت می‌کند. این سیگنال، ورود، حدضرر، تارگت یا اجرای معامله نیست.",
        "plain_language_en": "The system only logs shadow candidates and near-misses. This is not a signal, entry, stop, target, or execution layer.",
    }


def build_review_queue(candidate_ledger: Dict[str, Any], near_miss: Dict[str, Any], blocker_diag: Dict[str, Any], cohort: Dict[str, Any]) -> Dict[str, Any]:
    candidates = safe_list(candidate_ledger.get("candidates"))
    near_rows = safe_list(near_miss.get("near_misses"))
    block_rows = safe_list(blocker_diag.get("diagnostics"))
    by_cluster = summarize_counts(candidates, "setup_cluster_id")
    near_by_cluster = summarize_counts([r for r in near_rows if r.get("near_miss_strength") in ("NEAR_MISS_HIGH", "NEAR_MISS_MEDIUM")], "setup_cluster_id")
    review_items = []
    clusters = set(by_cluster) | set(near_by_cluster)
    for cl in sorted(clusters):
        ccount = by_cluster.get(cl, 0)
        ncount = near_by_cluster.get(cl, 0)
        if ccount >= 100:
            action = "PMO_REVIEW_ELIGIBLE_STRONG_SAMPLE_SHADOW_ONLY"
        elif ccount >= 50:
            action = "PMO_REVIEW_ELIGIBLE_MEDIUM_SAMPLE_SHADOW_ONLY"
        elif ccount >= 30:
            action = "PILOT_REVIEW_ELIGIBLE_SHADOW_ONLY"
        elif ccount < 10 and ncount >= 30:
            action = "NEAR_MISS_DIAGNOSTIC_REVIEW_RECOMMENDED_NO_RULE_CHANGE"
        else:
            action = "CONTINUE_OBSERVATION"
        review_items.append({
            "setup_cluster_id": cl,
            "candidate_count": ccount,
            "near_miss_medium_high_count": ncount,
            "blocker_or_gating_diagnostic_count": sum(1 for r in block_rows if r.get("setup_cluster_id") == cl),
            "recommended_pmo_action": action,
            "rule_change_authorized": False,
            "auto_learning_authorized": False,
        })
    return {
        "queue_version": "SIG_SHADOW_READY_01_REVIEW_QUEUE_v1_0",
        "created_utc": utc_now(),
        "authority": AUTHORITY,
        **FORBIDDEN_TOP_LEVEL,
        "cohort_id": cohort.get("cohort_id"),
        "review_items": review_items,
        "summary": {"review_item_count": len(review_items), "requires_manual_pmo_review": any(i["recommended_pmo_action"] != "CONTINUE_OBSERVATION" for i in review_items)},
        "boundary": "Queue items are prompts for manual PMO review only. No automatic rule updates are permitted.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain4-payload", default="runtime/sig_brain/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--candidate-payload", default="runtime/sig_signal_candidates/signal_candidate_payload_current.json")
    ap.add_argument("--candidate-ledger", default="runtime/sig_shadow/shadow_candidate_ledger_current.json")
    ap.add_argument("--observation-ledger", default="runtime/sig_shadow/shadow_observation_ledger_current.json")
    ap.add_argument("--blocked-ledger", default="runtime/sig_shadow/shadow_blocked_candidate_ledger_current.json")
    ap.add_argument("--shadow-summary", default="runtime/sig_shadow/shadow_summary_current.json")
    ap.add_argument("--shadow01b-proof", default="proofs/sig_shadow_01b_integrated_validation_result.json")
    ap.add_argument("--registry", default="sig_brain/brain_memory_registry_v1_0.json")
    ap.add_argument("--policy", default="sig_brain/shadow_ready_policy_v1_0.json")
    args = ap.parse_args()

    brain4 = load_json(Path(args.brain4_payload), {})
    candidate_payload = load_json(Path(args.candidate_payload), {"candidates": [], "blocked_candidates": []})
    candidate_ledger = load_json(Path(args.candidate_ledger), {"candidates": []})
    observation_ledger = load_json(Path(args.observation_ledger), {"observations": []})
    blocked_ledger = load_json(Path(args.blocked_ledger), {"blocked_candidates": []})
    shadow_summary = load_json(Path(args.shadow_summary), {})
    proof_01b = load_json(Path(args.shadow01b_proof), {})
    registry = load_json(Path(args.registry), {})
    policy = load_json(Path(args.policy), {})
    existing_cohort = load_json(Path("runtime/sig_shadow/shadow_cohort_current.json"), {})

    near_miss, blocker_diag = build_near_miss_and_blockers(brain4, candidate_payload, blocked_ledger)
    cohort = build_cohort(registry, policy, existing_cohort)
    observation_completion = build_observation_completion(observation_ledger)
    daily, weekly = build_period_summaries(candidate_ledger, observation_ledger, near_miss, blocker_diag)
    health = build_health(brain4, candidate_payload, candidate_ledger, observation_ledger, blocked_ledger, shadow_summary, proof_01b, near_miss, blocker_diag, cohort)
    panel_status = build_panel_status(health, candidate_ledger, observation_completion, near_miss, cohort)
    review_queue = build_review_queue(candidate_ledger, near_miss, blocker_diag, cohort)

    outputs = {
        "runtime/sig_shadow/near_miss_ledger_current.json": near_miss,
        "runtime/sig_shadow/blocker_diagnostic_ledger_current.json": blocker_diag,
        "runtime/sig_shadow/shadow_cohort_current.json": cohort,
        "runtime/sig_shadow/shadow_observation_completion_current.json": observation_completion,
        "runtime/sig_shadow/shadow_daily_summary_current.json": daily,
        "runtime/sig_shadow/shadow_weekly_summary_current.json": weekly,
        "runtime/sig_shadow/shadow_health_summary_current.json": health,
        "runtime/sig_shadow/shadow_panel_status_current.json": panel_status,
        "runtime/sig_shadow/shadow_review_queue_current.json": review_queue,
        "panel/brain4/shadow_panel_status_current.json": panel_status,
    }
    for p, obj in outputs.items():
        write_json(Path(p), obj)

    print(json.dumps({
        "status": "SHADOW_READY_01_OUTPUTS_BUILT",
        "health_status": health.get("health_status"),
        "near_miss_count": near_miss.get("summary", {}).get("near_miss_count"),
        "candidate_count": len(safe_list(candidate_ledger.get("candidates"))),
        "cohort_id": cohort.get("cohort_id"),
        **FORBIDDEN_TOP_LEVEL,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

