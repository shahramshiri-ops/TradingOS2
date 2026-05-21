#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRADINGOS_LIVE_OBSERVATION_MAX_VALUE_01

Builds a compact, persistent forward-observation evidence layer for SIG BRAIN live operation.

This script is intentionally DISPLAY_ONLY / NOT_SIGNAL. It does not create, modify, promote,
reject, or trade any memory. It converts each live refresh into audit-ready evidence:
- current memory evaluation rows for all memory cards
- official active/expired event ledger snapshot
- near-miss and blocker rollups
- provider/data-health rollups
- baseline/control exposure denominators (not performance proof)
- outcome observer rollups from existing shadow outcome artifacts
- daily/weekly/monthly review summaries

No broker, no execution, no entry/stop/target, no PnL, no auto-learning, no rule rewrite.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
import hashlib
import json
import os
import subprocess

VERSION = "LIVE_OBSERVATION_MAX_VALUE_01_v1_0"
STATE_VERSION = "LIVE_OBSERVATION_STATE_v1_0"
ROOT = Path.cwd()
PANEL_DIR = ROOT / "panel" / "brain4"
STATE_DIR = ROOT / "state" / "live_observation"
RUNTIME_DIR = ROOT / "runtime" / "sig_live_observation"
OUTPUT_DIR = ROOT / "outputs" / "_live_observation_max_value_01"

BOUNDARY = {
    "display_only": True,
    "personal_research_posture": True,
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "action_surface_authorized": False,
    "broker_execution_authorized": False,
    "entry_stop_target_authorized": False,
    "position_size_authorized": False,
    "profitability_claim_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "plain_language_fa": "این لایه فقط شواهد زندهٔ پژوهشی را ثبت می‌کند؛ سیگنال، توصیه خرید/فروش، ورود/خروج، حدضرر/هدف، سودآوری یا اجرای معامله نیست.",
}

FORBIDDEN_PURPOSES = [
    "NO_SIGNAL",
    "NO_BUY_SELL",
    "NO_ENTRY_STOP_TARGET",
    "NO_POSITION_SIZE",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_LEARNING",
    "NO_RULE_REWRITE",
]

MAX_REFRESH_HISTORY = 5000
MAX_EVENT_LEDGER = 5000
MAX_CONTEXT_SNAPSHOTS = 1500
MAX_CURRENT_SUBJECTS_BY_MEMORY = 5000
MAX_EXAMPLE_ROWS = 25


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def date_key(ts: str) -> str:
    dt = parse_utc(ts) or datetime.now(timezone.utc)
    return dt.date().isoformat()


def week_key(ts: str) -> str:
    dt = parse_utc(ts) or datetime.now(timezone.utc)
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def month_key(ts: str) -> str:
    dt = parse_utc(ts) or datetime.now(timezone.utc)
    return f"{dt.year}-{dt.month:02d}"


def stable_hash(*parts: Any, length: int = 16) -> str:
    raw = "||".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": path.as_posix(), "_default_used": True}
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False), encoding="utf-8")
    tmp.replace(path)


def run_git(args: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(["git"] + args, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def inc_nested(d: Dict[str, Any], key: str, amount: int = 1) -> None:
    d[key] = int(d.get(key, 0) or 0) + amount


def top_counter(counter_like: Dict[str, int], n: int = 20) -> List[List[Any]]:
    return [[k, v] for k, v in Counter(counter_like).most_common(n)]


def normalize_condition_label(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for k in ("field", "reason", "reason_code", "condition", "name", "type", "label"):
            v = item.get(k)
            if v:
                return str(v)
        return stable_hash(json.dumps(item, sort_keys=True, ensure_ascii=False), length=10)
    return str(item)


def status_from_card(card: Dict[str, Any], near_miss_memory_counts: Dict[str, int]) -> Tuple[str, List[str]]:
    memory_id = card.get("memory_id") or "UNKNOWN_MEMORY"
    active_in_runtime = bool(card.get("active_in_runtime"))
    is_active_match = bool(card.get("is_active_match"))
    missing_inputs = as_list(card.get("missing_inputs"))
    failed_conditions = as_list(card.get("failed_conditions"))
    latest_context = as_dict(card.get("latest_context"))
    data_status = latest_context.get("data_sufficiency_status") or card.get("data_sufficiency_status")

    reasons: List[str] = []
    if not active_in_runtime:
        reasons.append("MEMORY_NOT_ACTIVE_IN_RUNTIME")
        return "NOT_RUNTIME_ACTIVE", reasons
    if data_status and str(data_status).upper() not in {"OK", "PASS", "READY"}:
        reasons.append(f"DATA_SUFFICIENCY_{data_status}")
        return "DATA_OR_CONTEXT_NOT_READY", reasons
    if missing_inputs:
        reasons.append("MISSING_REQUIRED_INPUTS")
        reasons.extend(["missing:" + normalize_condition_label(x) for x in missing_inputs[:10]])
        return "INPUT_INSUFFICIENT", reasons
    if is_active_match:
        reasons.append("ALL_RUNTIME_MATCH_CONDITIONS_PASSED")
        return "MATCHED_ACTIVE", reasons
    if int(near_miss_memory_counts.get(memory_id, 0) or 0) > 0:
        reasons.append("SHADOW_NEAR_MISS_REPORTED")
        return "NEAR_MISS", reasons
    if failed_conditions:
        reasons.append("MATCH_CONDITION_FAILED")
        reasons.extend(["failed:" + normalize_condition_label(x) for x in failed_conditions[:10]])
        return "NOT_MATCHED", reasons
    reasons.append("NOT_MATCHED_NO_ACTIVE_TRIGGER")
    return "NOT_MATCHED", reasons


def limited_context_snapshot(card: Dict[str, Any], event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = as_dict(card.get("latest_context"))
    keys = [
        "instrument", "timeframe", "latest_bar_open_ts_utc", "latest_bar_close_ts_utc",
        "session_bucket", "data_sufficiency_status", "context_builder_status",
        "h1_dir", "h4_dir", "d1_trend_state", "h4_trend_state", "h1_bar_direction",
        "m15_dir", "m15_range_ratio_12", "conflict_severity",
        "weekly_open", "prior_day_high", "prior_day_low", "asian_session_high", "asian_session_low",
        "reference_level_field", "reference_level_value",
        "upside_sweep_flag", "downside_sweep_flag",
        "sweep_then_reject_back_inside_up_flag", "sweep_then_reject_back_inside_down_flag",
        "asian_high_swept_and_reclaimed_by_closed_h1", "asian_low_swept_and_reclaimed_by_closed_h1",
    ]
    out = {k: ctx.get(k) for k in keys if k in ctx}
    if event:
        for k in ("reference_level_field", "reference_level_value", "source_bar_open_ts_utc", "source_bar_close_ts_utc"):
            if k in event and k not in out:
                out[k] = event.get(k)
    return out


def find_card_by_memory(cards_by_id: Dict[str, Dict[str, Any]], memory_id: Optional[str]) -> Dict[str, Any]:
    if not memory_id:
        return {}
    return cards_by_id.get(memory_id, {})


def initialize_state(created: str) -> Dict[str, Any]:
    return {
        "state_version": STATE_VERSION,
        "created_utc": created,
        "updated_utc": created,
        "builder_version": VERSION,
        "boundary": BOUNDARY,
        "purpose_limits": FORBIDDEN_PURPOSES,
        "cumulative": {
            "refresh_count": 0,
            "memory_evaluation_count": 0,
            "matched_active_count": 0,
            "near_miss_count": 0,
            "input_insufficient_count": 0,
            "not_matched_count": 0,
            "not_runtime_active_count": 0,
            "data_or_context_not_ready_count": 0,
            "official_event_count_seen": 0,
            "unique_official_event_count": 0,
        },
        "daily": {},
        "weekly": {},
        "monthly": {},
        "memory_rollup": {},
        "event_ledger": {},
        "context_snapshots_by_event_id": {},
        "near_miss_rollup": {},
        "provider_health_rollup": {},
        "baseline_exposure_rollup": {},
        "outcome_subject_rollup": {},
        "refresh_history": [],
    }


def ensure_bucket(container: Dict[str, Any], key: str) -> Dict[str, Any]:
    if key not in container or not isinstance(container[key], dict):
        container[key] = {
            "refresh_count": 0,
            "memory_evaluation_count": 0,
            "matched_active_count": 0,
            "near_miss_count": 0,
            "input_insufficient_count": 0,
            "not_matched_count": 0,
            "not_runtime_active_count": 0,
            "data_or_context_not_ready_count": 0,
            "official_event_count_seen": 0,
            "unique_official_event_count_seen": 0,
            "provider_status_counts": {},
            "baseline_exposure_counts": {},
            "memories_triggered": {},
            "memories_near_miss": {},
            "last_refresh_utc": None,
        }
    return container[key]


def update_bucket(bucket: Dict[str, Any], field: str, amount: int = 1) -> None:
    bucket[field] = int(bucket.get(field, 0) or 0) + amount


def compact_dict(d: Dict[str, Any], max_items: int) -> Dict[str, Any]:
    if len(d) <= max_items:
        return d
    # Preserve newest-ish entries when values contain last_seen_utc/updated_utc.
    def key_fn(item: Tuple[str, Any]) -> str:
        v = item[1] if isinstance(item[1], dict) else {}
        return str(v.get("last_seen_utc") or v.get("updated_utc") or v.get("created_utc") or "")
    items = sorted(d.items(), key=key_fn, reverse=True)[:max_items]
    return dict(items)


def summarize_provider_health(refresh_status: Dict[str, Any]) -> Dict[str, Any]:
    provider_rows = as_list(as_dict(refresh_status.get("provider_m5")).get("by_instrument"))
    surfaces = as_list(as_dict(refresh_status.get("brain_context")).get("surfaces"))
    lag_diag = as_dict(refresh_status.get("lag_diagnostic"))
    status_counts = Counter(str(row.get("status", "UNKNOWN")) for row in provider_rows if isinstance(row, dict))
    context_status_counts = Counter(str(row.get("data_sufficiency_status", "UNKNOWN")) for row in surfaces if isinstance(row, dict))
    return {
        "provider_rows": provider_rows,
        "provider_status_counts": dict(status_counts),
        "brain_context_surface_count": len(surfaces),
        "context_status_counts": dict(context_status_counts),
        "lag_diagnostic": lag_diag,
        "provider_max_latest_bar_open_ts_utc": as_dict(refresh_status.get("provider_m5")).get("max_latest_bar_open_ts_utc"),
        "last_successful_refresh_utc": refresh_status.get("last_successful_refresh_utc"),
    }


def summarize_baseline_exposures(refresh_status: Dict[str, Any]) -> List[Dict[str, Any]]:
    surfaces = as_list(as_dict(refresh_status.get("brain_context")).get("surfaces"))
    rows: List[Dict[str, Any]] = []
    for row in surfaces:
        if not isinstance(row, dict):
            continue
        instrument = row.get("instrument") or "UNKNOWN"
        timeframe = row.get("timeframe") or "UNKNOWN"
        session = row.get("session_bucket") or "UNKNOWN_SESSION"
        key = f"{instrument}|{timeframe}|{session}"
        rows.append({
            "baseline_exposure_key": key,
            "instrument": instrument,
            "timeframe": timeframe,
            "session_bucket": session,
            "latest_bar_open_ts_utc": row.get("latest_bar_open_ts_utc"),
            "latest_bar_close_ts_utc": row.get("latest_bar_close_ts_utc"),
            "data_sufficiency_status": row.get("data_sufficiency_status"),
            "scope": "DENOMINATOR_ONLY_NOT_PERFORMANCE_BASELINE",
        })
    return rows


def summarize_outcomes(completion_state: Dict[str, Any]) -> Dict[str, Any]:
    subjects = as_dict(completion_state.get("subjects"))
    by_memory: Dict[str, Dict[str, Any]] = {}
    for subject in subjects.values():
        if not isinstance(subject, dict):
            continue
        memory_id = subject.get("memory_id") or "UNKNOWN_MEMORY"
        bucket = by_memory.setdefault(memory_id, {
            "subject_count": 0,
            "status_counts": {},
            "directional_outcome_counts": {},
            "latest_seen_utc": None,
            "example_subject_ids": [],
        })
        bucket["subject_count"] += 1
        status = str(subject.get("latest_observation_status") or "UNKNOWN")
        inc_nested(bucket["status_counts"], status)
        # Some subjects may carry horizon outcomes. Count only labels, not performance claims.
        horizons = as_dict(subject.get("horizons"))
        for hrow in horizons.values():
            if isinstance(hrow, dict):
                outcome = hrow.get("directional_outcome") or hrow.get("outcome_status") or hrow.get("status")
                if outcome:
                    inc_nested(bucket["directional_outcome_counts"], str(outcome))
        last_seen = subject.get("last_seen_utc") or subject.get("first_seen_utc")
        if last_seen and (not bucket["latest_seen_utc"] or last_seen > bucket["latest_seen_utc"]):
            bucket["latest_seen_utc"] = last_seen
        if len(bucket["example_subject_ids"]) < 5:
            bucket["example_subject_ids"].append(subject.get("stable_subject_key") or subject.get("subject_id"))
    return {
        "payload_version": completion_state.get("payload_version"),
        "created_utc": completion_state.get("created_utc"),
        "raw_subject_count_current": completion_state.get("raw_subject_count_current"),
        "unique_subject_count_current": completion_state.get("unique_subject_count_current"),
        "current_complete_horizon_rows": completion_state.get("current_complete_horizon_rows"),
        "current_pending_horizon_rows": completion_state.get("current_pending_horizon_rows"),
        "horizon_completion_ladder": completion_state.get("horizon_completion_ladder"),
        "directional_outcome_breakdown_carry_forward": completion_state.get("directional_outcome_breakdown_carry_forward"),
        "by_memory": dict(list(by_memory.items())[:MAX_CURRENT_SUBJECTS_BY_MEMORY]),
        "boundary_note": "Outcome rows are path observations only; not PnL, not trade results, not signal proof.",
    }


def merge_state_and_current(
    state: Dict[str, Any],
    refresh_id: str,
    created: str,
    evaluation_rows: List[Dict[str, Any]],
    event_rows: List[Dict[str, Any]],
    event_snapshots: Dict[str, Dict[str, Any]],
    near_miss_summary: Dict[str, Any],
    provider_health: Dict[str, Any],
    baseline_exposures: List[Dict[str, Any]],
    outcome_summary: Dict[str, Any],
) -> None:
    state["updated_utc"] = created
    state["builder_version"] = VERSION
    cumulative = state.setdefault("cumulative", {})
    daily = ensure_bucket(state.setdefault("daily", {}), date_key(created))
    weekly = ensure_bucket(state.setdefault("weekly", {}), week_key(created))
    monthly = ensure_bucket(state.setdefault("monthly", {}), month_key(created))
    buckets = [daily, weekly, monthly]

    inc_nested(cumulative, "refresh_count")
    for b in buckets:
        update_bucket(b, "refresh_count")
        b["last_refresh_utc"] = created

    status_counts = Counter(row.get("evaluation_status", "UNKNOWN") for row in evaluation_rows)
    count_mapping = {
        "MATCHED_ACTIVE": "matched_active_count",
        "NEAR_MISS": "near_miss_count",
        "INPUT_INSUFFICIENT": "input_insufficient_count",
        "NOT_MATCHED": "not_matched_count",
        "NOT_RUNTIME_ACTIVE": "not_runtime_active_count",
        "DATA_OR_CONTEXT_NOT_READY": "data_or_context_not_ready_count",
    }
    inc_nested(cumulative, "memory_evaluation_count", len(evaluation_rows))
    for b in buckets:
        update_bucket(b, "memory_evaluation_count", len(evaluation_rows))
    for status, count in status_counts.items():
        field = count_mapping.get(status)
        if field:
            inc_nested(cumulative, field, count)
            for b in buckets:
                update_bucket(b, field, count)

    # Per-memory rollup.
    memory_rollup = state.setdefault("memory_rollup", {})
    for row in evaluation_rows:
        mid = row.get("memory_id") or "UNKNOWN_MEMORY"
        mr = memory_rollup.setdefault(mid, {
            "memory_id": mid,
            "instrument": row.get("instrument"),
            "timeframe": row.get("timeframe"),
            "active_in_runtime": row.get("active_in_runtime"),
            "first_seen_utc": created,
            "last_seen_utc": created,
            "evaluation_counts": {},
            "reason_code_counts": {},
            "active_event_count": 0,
            "near_miss_count": 0,
            "input_insufficient_count": 0,
            "latest_status": None,
            "latest_reason_codes": [],
            "latest_score_not_probability": row.get("score_not_probability"),
            "latest_band": row.get("band"),
        })
        mr["last_seen_utc"] = created
        mr["active_in_runtime"] = row.get("active_in_runtime")
        mr["instrument"] = row.get("instrument") or mr.get("instrument")
        mr["timeframe"] = row.get("timeframe") or mr.get("timeframe")
        status = row.get("evaluation_status", "UNKNOWN")
        inc_nested(mr.setdefault("evaluation_counts", {}), status)
        for rc in as_list(row.get("reason_codes")):
            inc_nested(mr.setdefault("reason_code_counts", {}), str(rc))
        if status == "MATCHED_ACTIVE":
            inc_nested(mr, "active_event_count")
            for b in buckets:
                inc_nested(b.setdefault("memories_triggered", {}), mid)
        if status == "NEAR_MISS":
            inc_nested(mr, "near_miss_count")
            for b in buckets:
                inc_nested(b.setdefault("memories_near_miss", {}), mid)
        if status == "INPUT_INSUFFICIENT":
            inc_nested(mr, "input_insufficient_count")
        mr["latest_status"] = status
        mr["latest_reason_codes"] = as_list(row.get("reason_codes"))[:20]
        mr["latest_score_not_probability"] = row.get("score_not_probability")
        mr["latest_band"] = row.get("band")

    # Event ledger.
    event_ledger = state.setdefault("event_ledger", {})
    seen_this_run = set()
    for ev in event_rows:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("event_id") or stable_hash(ev.get("memory_id"), ev.get("activated_at_utc"), ev.get("source_bar_open_ts_utc"))
        seen_this_run.add(eid)
        existing = event_ledger.get(eid, {})
        merged = dict(existing)
        keep_keys = [
            "event_id", "memory_id", "instrument", "timeframe", "event_type", "direction_side",
            "activated_at_utc", "first_seen_utc", "last_seen_utc", "expires_at_utc",
            "source_bar_open_ts_utc", "source_bar_close_ts_utc", "reference_level_field", "reference_level_value",
            "expiry_label_fa", "expiry_is_invalidation", "status", "display_status",
        ]
        for k in keep_keys:
            if k in ev:
                merged[k] = ev.get(k)
        merged.setdefault("event_id", eid)
        merged["last_observed_in_live_observation_utc"] = created
        merged["observation_refresh_count"] = int(existing.get("observation_refresh_count", 0) or 0) + 1
        merged["boundary"] = {
            "display_only": True,
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
        }
        event_ledger[eid] = merged
        mid = merged.get("memory_id")
        if mid and mid in memory_rollup:
            memory_rollup[mid]["last_event_id"] = eid
        if eid in event_snapshots:
            state.setdefault("context_snapshots_by_event_id", {})[eid] = event_snapshots[eid]

    inc_nested(cumulative, "official_event_count_seen", len(event_rows))
    cumulative["unique_official_event_count"] = len(event_ledger)
    for b in buckets:
        update_bucket(b, "official_event_count_seen", len(event_rows))
        b["unique_official_event_count_seen"] = len(event_ledger)

    state["event_ledger"] = compact_dict(event_ledger, MAX_EVENT_LEDGER)
    state["context_snapshots_by_event_id"] = compact_dict(state.setdefault("context_snapshots_by_event_id", {}), MAX_CONTEXT_SNAPSHOTS)

    # Near-miss rollup.
    nmr = state.setdefault("near_miss_rollup", {})
    for item in as_list(near_miss_summary.get("top_memory_breakdown")):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            mid, count = str(item[0]), int(item[1] or 0)
            row = nmr.setdefault(mid, {"memory_id": mid, "count": 0, "first_seen_utc": created, "last_seen_utc": created})
            row["count"] += count
            row["last_seen_utc"] = created
    for item in as_list(near_miss_summary.get("top_blocker_reasons")):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            reason, count = str(item[0]), int(item[1] or 0)
            row = nmr.setdefault(f"BLOCKER_REASON::{reason}", {"reason_code": reason, "count": 0, "first_seen_utc": created, "last_seen_utc": created})
            row["count"] += count
            row["last_seen_utc"] = created

    # Provider health rollup.
    phr = state.setdefault("provider_health_rollup", {})
    for status, count in as_dict(provider_health.get("provider_status_counts")).items():
        inc_nested(phr, f"provider_status::{status}", int(count or 0))
        for b in buckets:
            inc_nested(b.setdefault("provider_status_counts", {}), str(status), int(count or 0))
    for status, count in as_dict(provider_health.get("context_status_counts")).items():
        inc_nested(phr, f"context_status::{status}", int(count or 0))

    # Baseline/control denominator exposure rollup.
    ber = state.setdefault("baseline_exposure_rollup", {})
    for exposure in baseline_exposures:
        key = exposure.get("baseline_exposure_key") or "UNKNOWN"
        row = ber.setdefault(key, {
            "baseline_exposure_key": key,
            "instrument": exposure.get("instrument"),
            "timeframe": exposure.get("timeframe"),
            "session_bucket": exposure.get("session_bucket"),
            "scope": "DENOMINATOR_ONLY_NOT_PERFORMANCE_BASELINE",
            "count": 0,
            "first_seen_utc": created,
            "last_seen_utc": created,
        })
        row["count"] += 1
        row["last_seen_utc"] = created
        for b in buckets:
            inc_nested(b.setdefault("baseline_exposure_counts", {}), key)

    # Outcome subject rollup.
    osr = state.setdefault("outcome_subject_rollup", {})
    for mid, summary in as_dict(outcome_summary.get("by_memory")).items():
        row = osr.setdefault(mid, {
            "memory_id": mid,
            "subject_count_seen_cumulative_proxy": 0,
            "status_counts": {},
            "directional_outcome_counts": {},
            "last_seen_utc": created,
            "boundary_note": "Path observations only; not PnL and not signal proof.",
        })
        row["last_seen_utc"] = created
        row["subject_count_seen_cumulative_proxy"] += int(summary.get("subject_count", 0) or 0)
        for status, count in as_dict(summary.get("status_counts")).items():
            inc_nested(row.setdefault("status_counts", {}), str(status), int(count or 0))
        for outcome, count in as_dict(summary.get("directional_outcome_counts")).items():
            inc_nested(row.setdefault("directional_outcome_counts", {}), str(outcome), int(count or 0))

    # Refresh history compact.
    state.setdefault("refresh_history", []).append({
        "refresh_id": refresh_id,
        "created_utc": created,
        "memory_evaluation_count": len(evaluation_rows),
        "evaluation_status_counts": dict(status_counts),
        "official_event_rows_seen": len(event_rows),
        "near_miss_detail_count_last_run": near_miss_summary.get("near_miss_detail_count_last_run"),
        "candidate_count": near_miss_summary.get("candidate_count"),
        "provider_max_latest_bar_open_ts_utc": provider_health.get("provider_max_latest_bar_open_ts_utc"),
    })
    state["refresh_history"] = state["refresh_history"][-MAX_REFRESH_HISTORY:]


def classify_memory_for_review(memory_row: Dict[str, Any]) -> Dict[str, Any]:
    eval_counts = as_dict(memory_row.get("evaluation_counts"))
    active_in_runtime = bool(memory_row.get("active_in_runtime"))
    matched = int(eval_counts.get("MATCHED_ACTIVE", 0) or 0)
    near = int(eval_counts.get("NEAR_MISS", 0) or 0)
    insuff = int(eval_counts.get("INPUT_INSUFFICIENT", 0) or 0)
    total = sum(int(v or 0) for v in eval_counts.values())
    if not active_in_runtime:
        cls = "ARCHIVE_NO_RUNTIME_USE_OR_INACTIVE"
        next_action = "No live improvement action; keep archived unless separately reviewed."
    elif matched > 0:
        cls = "FORWARD_OBSERVATION_ACCUMULATING"
        next_action = "Keep observing until enough closed outcomes exist; no promotion from count alone."
    elif near >= max(5, total * 0.20):
        cls = "RECURRING_NEAR_MISS_RESEARCH_REVIEW_CANDIDATE"
        next_action = "Possible future research question; do not change live rule automatically."
    elif insuff >= max(5, total * 0.20):
        cls = "INPUT_OR_CONTEXT_COVERAGE_REPAIR_CANDIDATE"
        next_action = "Review missing fields/context builder; memory rule unchanged."
    else:
        cls = "NO_LIVE_TRIGGER_YET"
        next_action = "Continue observation; low/no activation alone is not failure."
    return {
        "memory_id": memory_row.get("memory_id"),
        "instrument": memory_row.get("instrument"),
        "timeframe": memory_row.get("timeframe"),
        "review_classification": cls,
        "next_action_guardrail": next_action,
        "evaluation_counts": eval_counts,
        "active_event_count": memory_row.get("active_event_count", 0),
        "near_miss_count": memory_row.get("near_miss_count", 0),
        "input_insufficient_count": memory_row.get("input_insufficient_count", 0),
        "latest_status": memory_row.get("latest_status"),
        "latest_reason_codes": memory_row.get("latest_reason_codes", []),
    }


def main() -> None:
    created = now_utc()
    git_sha = run_git(["rev-parse", "--short", "HEAD"])
    git_branch = run_git(["branch", "--show-current"])

    payload = read_json(PANEL_DIR / "sig_brain4_runtime_payload_current.json", {})
    event_history = read_json(PANEL_DIR / "sig_brain4_event_history_current.json", {})
    refresh_status = read_json(PANEL_DIR / "sig_live_refresh_status_latest.json", {})
    near_miss_summary = read_json(PANEL_DIR / "shadow_near_miss_summary_current.json", {})
    shadow_ops = read_json(PANEL_DIR / "shadow_ops_status_current.json", {})
    candidate_summary = read_json(PANEL_DIR / "sig_signal_candidate_summary_current.json", {})
    outcome_completion = read_json(PANEL_DIR / "shadow_outcome_completion_state_current.json", {})

    cards = as_list(payload.get("cards"))
    cards_by_id = {str(c.get("memory_id")): c for c in cards if isinstance(c, dict) and c.get("memory_id")}
    near_miss_memory_counts = {
        str(item[0]): int(item[1] or 0)
        for item in as_list(near_miss_summary.get("top_memory_breakdown"))
        if isinstance(item, (list, tuple)) and len(item) >= 2
    }

    payload_created = payload.get("created_utc") or refresh_status.get("created_utc") or created
    refresh_id = stable_hash(VERSION, payload_created, refresh_status.get("last_successful_refresh_utc"), git_sha, length=20)

    evaluation_rows: List[Dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        status, reason_codes = status_from_card(card, near_miss_memory_counts)
        ctx = as_dict(card.get("latest_context"))
        row = {
            "row_version": "LIVE_MEMORY_EVALUATION_ROW_v1_0",
            "refresh_id": refresh_id,
            "created_utc": created,
            "source_payload_created_utc": payload_created,
            "memory_id": card.get("memory_id"),
            "instrument": card.get("instrument") or ctx.get("instrument"),
            "timeframe": card.get("timeframe") or ctx.get("timeframe"),
            "memory_class": card.get("memory_class"),
            "candidate_type": card.get("candidate_type"),
            "active_in_runtime": bool(card.get("active_in_runtime")),
            "is_active_match": bool(card.get("is_active_match")),
            "evaluation_status": status,
            "reason_codes": reason_codes,
            "missing_input_count": len(as_list(card.get("missing_inputs"))),
            "failed_condition_count": len(as_list(card.get("failed_conditions"))),
            "near_miss_reported_count": int(near_miss_memory_counts.get(str(card.get("memory_id")), 0) or 0),
            "score_not_probability": card.get("score_not_probability"),
            "band": card.get("band"),
            "status_badge": card.get("status_badge"),
            "session_bucket": ctx.get("session_bucket"),
            "latest_bar_open_ts_utc": ctx.get("latest_bar_open_ts_utc"),
            "latest_bar_close_ts_utc": ctx.get("latest_bar_close_ts_utc"),
            "data_sufficiency_status": ctx.get("data_sufficiency_status"),
            "context_builder_status": ctx.get("context_builder_status"),
            "boundary": {
                "display_only": True,
                "signal_authorized": False,
                "trade_instruction_authorized": False,
                "broker_execution_authorized": False,
            },
        }
        evaluation_rows.append(row)

    event_rows: List[Dict[str, Any]] = []
    for collection_name in ("active_events", "events"):
        for ev in as_list(event_history.get(collection_name)):
            if isinstance(ev, dict):
                row = dict(ev)
                row["source_collection"] = collection_name
                # Current status is explicit for active_events; for events infer if not provided.
                row.setdefault("display_status", "ACTIVE" if collection_name == "active_events" else "HISTORICAL_OR_EXPIRED")
                event_rows.append(row)

    # Deduplicate events by event_id.
    deduped_events: Dict[str, Dict[str, Any]] = {}
    for ev in event_rows:
        eid = ev.get("event_id") or stable_hash(ev.get("memory_id"), ev.get("activated_at_utc"), ev.get("source_bar_open_ts_utc"), length=20)
        ev["event_id"] = eid
        deduped_events[eid] = {**deduped_events.get(eid, {}), **ev}
    event_rows = list(deduped_events.values())

    event_snapshots: Dict[str, Dict[str, Any]] = {}
    for ev in event_rows:
        mid = ev.get("memory_id")
        card = find_card_by_memory(cards_by_id, mid)
        eid = ev.get("event_id")
        if not eid:
            continue
        event_snapshots[eid] = {
            "snapshot_version": "LIVE_EVENT_CONTEXT_SNAPSHOT_v1_0",
            "event_id": eid,
            "memory_id": mid,
            "snapshot_created_utc": created,
            "source_payload_created_utc": payload_created,
            "context": limited_context_snapshot(card, ev),
            "matched_conditions_count": len(as_list(card.get("matched_conditions"))) if card else None,
            "failed_conditions_count": len(as_list(card.get("failed_conditions"))) if card else None,
            "missing_inputs_count": len(as_list(card.get("missing_inputs"))) if card else None,
            "panel_visible_summary_fa": (card.get("plain_language_summary_fa") or card.get("headline_fa")) if card else ev.get("meaning_fa"),
            "boundary": BOUNDARY,
        }

    provider_health = summarize_provider_health(refresh_status)
    baseline_exposures = summarize_baseline_exposures(refresh_status)
    outcome_summary = summarize_outcomes(outcome_completion)

    state = read_json(STATE_DIR / "live_observation_state_v1.json", None)
    if not isinstance(state, dict) or state.get("state_version") != STATE_VERSION:
        state = initialize_state(created)

    merge_state_and_current(
        state=state,
        refresh_id=refresh_id,
        created=created,
        evaluation_rows=evaluation_rows,
        event_rows=event_rows,
        event_snapshots=event_snapshots,
        near_miss_summary=near_miss_summary if isinstance(near_miss_summary, dict) else {},
        provider_health=provider_health,
        baseline_exposures=baseline_exposures,
        outcome_summary=outcome_summary,
    )

    day = date_key(created)
    week = week_key(created)
    month = month_key(created)
    current_status_counts = Counter(row.get("evaluation_status", "UNKNOWN") for row in evaluation_rows)
    active_event_rows = [ev for ev in event_rows if ev.get("source_collection") == "active_events" or str(ev.get("display_status", "")).upper() == "ACTIVE"]

    current_summary = {
        "payload_version": VERSION,
        "created_utc": created,
        "refresh_id": refresh_id,
        "git": {"branch": git_branch, "sha": git_sha},
        "authority": "LIVE_OBSERVATION_MAX_VALUE_01|DISPLAY_ONLY_FORWARD_EVIDENCE|NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE",
        "boundary": BOUNDARY,
        "source_files": {
            "runtime_payload": "panel/brain4/sig_brain4_runtime_payload_current.json",
            "event_history": "panel/brain4/sig_brain4_event_history_current.json",
            "refresh_status": "panel/brain4/sig_live_refresh_status_latest.json",
            "near_miss_summary": "panel/brain4/shadow_near_miss_summary_current.json",
            "outcome_completion_state": "panel/brain4/shadow_outcome_completion_state_current.json",
        },
        "current_refresh_summary": {
            "memory_count": len(evaluation_rows),
            "evaluation_status_counts": dict(current_status_counts),
            "official_event_rows_seen": len(event_rows),
            "active_event_rows_seen": len(active_event_rows),
            "near_miss_detail_count_last_run": near_miss_summary.get("near_miss_detail_count_last_run") if isinstance(near_miss_summary, dict) else None,
            "candidate_count": candidate_summary.get("candidate_count") if isinstance(candidate_summary, dict) else None,
            "blocked_candidate_count": candidate_summary.get("blocked_candidate_count") if isinstance(candidate_summary, dict) else None,
            "shadow_ops_status": shadow_ops.get("shadow_ops_status") or shadow_ops.get("status") if isinstance(shadow_ops, dict) else None,
        },
        "provider_health_current": provider_health,
        "baseline_exposure_current": {
            "scope": "DENOMINATOR_ONLY_NOT_PERFORMANCE_BASELINE",
            "plain_language_fa": "این بخش فقط تعداد مواجهه‌های زمینه‌ای instrument/timeframe/session را ثبت می‌کند تا بعداً denominator داشته باشیم؛ هنوز baseline عملکردی یا اثبات برتری نیست.",
            "rows": baseline_exposures,
        },
        "outcome_observer_current": outcome_summary,
        "cumulative_summary": state.get("cumulative", {}),
        "review_guardrail_fa": "بعد از چند هفته/ماه، این فایل برای review استفاده می‌شود؛ هیچ rule یا memory به صورت خودکار تغییر نمی‌کند.",
    }

    daily_summary = {
        "summary_version": "LIVE_OBSERVATION_DAILY_SUMMARY_v1_0",
        "created_utc": created,
        "date_key": day,
        "boundary": BOUNDARY,
        "summary": state.get("daily", {}).get(day, {}),
        "top_memory_statuses": [classify_memory_for_review(v) for v in list(as_dict(state.get("memory_rollup")).values())[:MAX_EXAMPLE_ROWS]],
    }
    weekly_summary = {
        "summary_version": "LIVE_OBSERVATION_WEEKLY_SUMMARY_v1_0",
        "created_utc": created,
        "week_key": week,
        "boundary": BOUNDARY,
        "summary": state.get("weekly", {}).get(week, {}),
        "review_note_fa": "این summary برای audit هفتگی است؛ تصمیم ارتقا/حذف memory نیازمند review جداگانه است.",
    }
    monthly_review_rows = [classify_memory_for_review(v) for v in as_dict(state.get("memory_rollup")).values()]
    monthly_review_rows = sorted(monthly_review_rows, key=lambda x: (x.get("review_classification", ""), x.get("memory_id", "")))
    monthly_pack = {
        "review_pack_version": "LIVE_OBSERVATION_MONTHLY_REVIEW_PACK_v1_0",
        "created_utc": created,
        "month_key": month,
        "boundary": BOUNDARY,
        "summary": state.get("monthly", {}).get(month, {}),
        "memory_review_rows": monthly_review_rows,
        "decision_options_allowed_after_review_only": [
            "KEEP_AS_DISPLAY_CONTEXT",
            "KEEP_AS_CAVEATED_WATCH",
            "PROMOTE_TO_SETUP_TRIGGER_PILOT_REVIEW_ONLY",
            "DEMOTE_TO_EXTENDED_OBSERVATION",
            "PARK_NO_RUNTIME_USE",
            "REJECT_OR_ARCHIVE",
            "NEEDS_RESEARCH_RESPEC",
        ],
        "forbidden_automatic_actions": FORBIDDEN_PURPOSES,
    }

    event_ledger_current = {
        "ledger_version": "LIVE_OBSERVATION_EVENT_LEDGER_CURRENT_v1_0",
        "created_utc": created,
        "boundary": BOUNDARY,
        "event_count": len(as_dict(state.get("event_ledger"))),
        "events": sorted(as_dict(state.get("event_ledger")).values(), key=lambda x: str(x.get("last_observed_in_live_observation_utc") or ""), reverse=True)[:500],
    }

    memory_eval_current = {
        "ledger_version": "LIVE_MEMORY_EVALUATION_CURRENT_v1_0",
        "created_utc": created,
        "refresh_id": refresh_id,
        "boundary": BOUNDARY,
        "row_count": len(evaluation_rows),
        "status_counts": dict(current_status_counts),
        "rows": evaluation_rows,
    }

    # Write outputs. State is compact/persistent; panel files are current summaries for review/download.
    write_json(STATE_DIR / "live_observation_state_v1.json", state)
    write_json(RUNTIME_DIR / "live_observation_state_current.json", state)
    write_json(PANEL_DIR / "live_observation_current.json", current_summary)
    write_json(PANEL_DIR / "live_memory_evaluation_current.json", memory_eval_current)
    write_json(PANEL_DIR / "live_event_ledger_current.json", event_ledger_current)
    write_json(PANEL_DIR / "live_observation_daily_summary_current.json", daily_summary)
    write_json(PANEL_DIR / "live_observation_weekly_summary_current.json", weekly_summary)
    write_json(PANEL_DIR / "live_observation_monthly_review_pack_current.json", monthly_pack)
    write_json(STATE_DIR / "live_observation_monthly_review_pack_current.json", monthly_pack)

    result = {
        "status": "LIVE_OBSERVATION_MAX_VALUE_01_BUILD_OK",
        "created_utc": created,
        "version": VERSION,
        "refresh_id": refresh_id,
        "files_written": [
            "state/live_observation/live_observation_state_v1.json",
            "runtime/sig_live_observation/live_observation_state_current.json",
            "panel/brain4/live_observation_current.json",
            "panel/brain4/live_memory_evaluation_current.json",
            "panel/brain4/live_event_ledger_current.json",
            "panel/brain4/live_observation_daily_summary_current.json",
            "panel/brain4/live_observation_weekly_summary_current.json",
            "panel/brain4/live_observation_monthly_review_pack_current.json",
            "state/live_observation/live_observation_monthly_review_pack_current.json",
        ],
        "current_status_counts": dict(current_status_counts),
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_DIR / "live_observation_max_value_01_build_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
