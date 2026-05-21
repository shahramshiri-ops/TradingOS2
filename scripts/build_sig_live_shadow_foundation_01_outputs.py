#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LIVE-SHADOW-FOUNDATION-01

Purpose:
- Make multi-month live observation useful.
- Add append-only daily JSONL logs for context snapshots, memory watches,
  setup-shadow skeleton, trigger-shadow skeleton, blocker diagnostics,
  candidate snapshots, and diagnostic records.
- Do NOT create signals, entries, stops, targets, PnL, execution, or auto-learning.

Boundary:
NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_POSITION_SIZE /
NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE / NO_OUTCOME_YET
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Set
from collections import Counter
import json
import hashlib
import os

ROOT = Path.cwd()

RUNTIME_BRAIN = ROOT / "runtime" / "sig_brain"
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
RUNTIME_CAND = ROOT / "runtime" / "sig_signal_candidates"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"

for p in [RUNTIME_BRAIN, RUNTIME_SHADOW, RUNTIME_CAND, PANEL, PROOFS]:
    p.mkdir(parents=True, exist_ok=True)

AUTHORITY = (
    "LIVE_SHADOW_FOUNDATION_01|APPEND_ONLY_SETUP_TRIGGER_CONTEXT_LOGGING|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|"
    "NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE|NO_OUTCOME_YET"
)

# Inputs
BRAIN4_PAYLOAD = RUNTIME_BRAIN / "sig_brain4_runtime_payload_current.json"
EVENT_HISTORY = RUNTIME_BRAIN / "sig_brain4_event_history_current.json"
COUNT_SEMANTICS = RUNTIME_SHADOW / "shadow_count_semantics_current.json"
OPS_STATUS = RUNTIME_SHADOW / "shadow_ops_status_current.json"
SHADOW_STATUS = RUNTIME_SHADOW / "shadow_panel_status_current.json"
REASON_SOURCE = RUNTIME_SHADOW / "near_miss_reason_source_current.json"
REASON_ENRICHED = RUNTIME_SHADOW / "near_miss_reason_enriched_current.json"
BLOCKER_BREAKDOWN = RUNTIME_SHADOW / "blocker_reason_breakdown_current.json"
CAND_PAYLOAD = RUNTIME_CAND / "signal_candidate_payload_current.json"
CAND_SUMMARY = RUNTIME_CAND / "signal_candidate_summary_current.json"

# Outputs
OUT_STATUS_RUNTIME = RUNTIME_SHADOW / "live_shadow_foundation_status_current.json"
OUT_STATUS_PANEL = PANEL / "live_shadow_foundation_status_current.json"
OUT_VALIDATION = PROOFS / "sig_live_shadow_foundation_01_validation_result.json"

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

SETUP_LIKE_CLASSES = {
    "MARKET_NEAR_MISS_EVENT",
    "ELIGIBILITY_RECORD",
    "LIFECYCLE_RECORD",
}

TRIGGER_LIKE_REASON_CODES = {
    "TRIGGER_NOT_CONFIRMED",
    "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED",
    "BLOCKER_OR_POLICY_VETO",
    "BLOCKER_LEDGER_REASON_UNKNOWN",
}

NO_SIGNAL_BOUNDARY = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "outcome_observation_authorized": False,
}


def now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def now_utc() -> str:
    return now_dt().isoformat().replace("+00:00", "Z")


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


def as_list(payload: Any, keys: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in keys:
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def day_key(created_utc: str) -> str:
    return created_utc[:10]


def log_dir_for_day(day: str) -> Path:
    return RUNTIME_SHADOW / "live_logs" / day


def read_existing_hashes(path: Path) -> Set[str]:
    hashes: Set[str] = set()
    if not path.exists():
        return hashes
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                h = item.get("record_hash")
                if h:
                    hashes.add(str(h))
            except Exception:
                continue
    except Exception:
        return hashes
    return hashes


def append_jsonl_dedup(path: Path, records: List[Dict[str, Any]]) -> Dict[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_existing_hashes(path)
    written = 0
    skipped = 0
    with path.open("a", encoding="utf-8") as f:
        for r in records:
            rr = dict(r)
            rr.setdefault("schema_version", "LIVE_SHADOW_FOUNDATION_01_RECORD_v1_0")
            rr.setdefault("authority", AUTHORITY)
            rr.setdefault("boundary", NO_SIGNAL_BOUNDARY)
            h = rr.get("record_hash") or stable_hash({k: v for k, v in rr.items() if k != "record_hash"})
            rr["record_hash"] = h
            if h in existing:
                skipped += 1
                continue
            f.write(json.dumps(rr, ensure_ascii=False, sort_keys=True) + "\n")
            existing.add(h)
            written += 1
    return {"written": written, "skipped": skipped, "path": str(path).replace("\\", "/")}


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:
        return 0


def event_id_from(row: Dict[str, Any], prefix: str) -> str:
    seed = [
        row.get("event_id"),
        row.get("candidate_id"),
        row.get("diagnostic_id"),
        row.get("reason_source_id"),
        row.get("memory_id") or row.get("source_memory_id"),
        row.get("instrument"),
        row.get("timeframe"),
        row.get("source_bar_open_ts_utc"),
        row.get("activated_at_utc"),
        row.get("reason_code") or row.get("upstream_reason_code"),
    ]
    return prefix + "_" + stable_hash(seed)[:20]


def normalize_reason(row: Dict[str, Any]) -> str:
    for k in ["reason_code", "upstream_reason_code", "canonical_stage", "count_class", "stage_failed", "blocker_reason_code"]:
        v = row.get(k)
        if v:
            return str(v)
    return "UNKNOWN_REASON"


def memory_class(mid: str) -> str:
    if mid in CORE_SHADOW_MEMORY_IDS:
        return "CORE_SHADOW_MEMORY"
    if mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        return "EXTENDED_OBSERVATION_ONLY_MEMORY"
    return "NON_CORE_OR_UNKNOWN_MEMORY"


def build_context_snapshot(created: str, payloads: Dict[str, Any]) -> Dict[str, Any]:
    brain4 = payloads.get("brain4") or {}
    count = payloads.get("count") or {}
    ops = payloads.get("ops") or {}
    shadow = payloads.get("shadow") or {}
    cand = payloads.get("candidate") or {}

    # Keep this small/panel-safe; do not dump entire bars.
    return {
        "record_type": "CONTEXT_SNAPSHOT",
        "created_utc": created,
        "snapshot_id": "CTX_" + stable_hash([created, brain4.get("created_utc"), count.get("created_utc"), ops.get("created_utc")])[:20],
        "brain4_created_utc": brain4.get("created_utc"),
        "count_semantics_created_utc": count.get("created_utc"),
        "ops_created_utc": ops.get("created_utc"),
        "shadow_status_created_utc": shadow.get("created_utc"),
        "candidate_payload_created_utc": cand.get("created_utc"),
        "instrument_count": len(brain4.get("instruments") or []) if isinstance(brain4, dict) else None,
        "candidate_count": count.get("candidate_count", cand.get("candidate_count")),
        "diagnostic_record_count": count.get("diagnostic_record_count_last_run"),
        "unique_market_near_miss_event_count": count.get("unique_market_near_miss_event_count_last_run"),
        "instrumentation_gap_count": count.get("instrumentation_gap_record_count_last_run"),
        "active_watch_count": count.get("active_watch_count"),
        "health_status": ops.get("health_status") or shadow.get("shadow_system_status"),
        "plain_language_fa": "Snapshot دوره‌ای برای استفاده چندماهه؛ سیگنال یا دستور معامله نیست.",
    }


def build_memory_watch_records(created: str, event_history: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = []
    events = as_list(event_history, ["active_events", "events"])
    for e in events:
        mid = str(e.get("memory_id") or "")
        status = str(e.get("status") or e.get("event_status") or "UNKNOWN")
        records.append({
            "record_type": "MEMORY_WATCH",
            "created_utc": created,
            "watch_record_id": event_id_from(e, "WATCH"),
            "event_id": e.get("event_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "session_bucket": e.get("session_bucket"),
            "direction_side": e.get("direction_side"),
            "event_status": status,
            "source_bar_open_ts_utc": e.get("source_bar_open_ts_utc"),
            "activated_at_utc": e.get("activated_at_utc"),
            "expires_at_utc": e.get("expires_at_utc"),
            "shadow_candidate_allowed": mid in CORE_SHADOW_MEMORY_IDS,
            "plain_language_fa": "ثبت append-only وضعیت memory/watch برای تحلیل چندماهه؛ نه سیگنال.",
        })
    return records


def build_setup_shadow_records(created: str, reason_records: List[Dict[str, Any]], event_history: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = []

    # Reason/count records: these are diagnostic setup-forming skeletons unless explicitly blocker-only.
    for r in reason_records:
        count_class = str(r.get("count_class") or "")
        reason = normalize_reason(r)
        mid = str(r.get("memory_id") or r.get("source_memory_id") or "")
        if count_class not in SETUP_LIKE_CLASSES and reason not in {
            "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED",
            "UPSTREAM_REASON_NOT_EMITTED",
            "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT",
            "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW",
        }:
            continue

        setup_stage = "SETUP_DIAGNOSTIC_ONLY"
        if count_class == "MARKET_NEAR_MISS_EVENT":
            setup_stage = "SETUP_FORMING_OR_NEAR_CANDIDATE"
        elif reason in {"OUT_OF_CORE_SPLIT_STABILITY_CAVEAT", "EXTENDED_OBSERVATION_ONLY_NOT_CORE_UNTIL_SPLIT_REVIEW"}:
            setup_stage = "SETUP_OBSERVED_BUT_EXTENDED_ONLY"
        elif reason == "UPSTREAM_REASON_NOT_EMITTED":
            setup_stage = "SETUP_OR_DIAGNOSTIC_REASON_NOT_EMITTED"

        records.append({
            "record_type": "SETUP_SHADOW",
            "created_utc": created,
            "setup_shadow_id": event_id_from(r, "SETUP"),
            "source_record_id": r.get("count_record_id") or r.get("reason_source_id") or r.get("diagnostic_id") or r.get("event_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": r.get("instrument"),
            "timeframe": r.get("timeframe"),
            "setup_stage": setup_stage,
            "reason_code": reason,
            "count_class": count_class or None,
            "candidate_counted": False,
            "outcome_authorized": False,
            "plain_language_fa": "Setup shadow skeleton: فقط مسیر شکل‌گیری/نزدیک‌شدن setup را ثبت می‌کند؛ سیگنال نیست.",
        })

    # Active events are also setup/watch states.
    for e in as_list(event_history, ["active_events"]):
        mid = str(e.get("memory_id") or "")
        records.append({
            "record_type": "SETUP_SHADOW",
            "created_utc": created,
            "setup_shadow_id": event_id_from(e, "SETUP_ACTIVE"),
            "source_record_id": e.get("event_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "setup_stage": "ACTIVE_WATCH_AS_SETUP_CONTEXT",
            "reason_code": "ACTIVE_MEMORY_WATCH",
            "candidate_counted": False,
            "outcome_authorized": False,
            "plain_language_fa": "Memory فعال به عنوان setup context ثبت شد؛ سیگنال یا candidate نیست.",
        })

    return records


def build_trigger_shadow_records(created: str, reason_records: List[Dict[str, Any]], candidates: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []

    for r in reason_records:
        reason = normalize_reason(r)
        if reason not in TRIGGER_LIKE_REASON_CODES and str(r.get("count_class")) not in {"MARKET_NEAR_MISS_EVENT", "BLOCKER_DIAGNOSTIC_RECORD"}:
            continue
        mid = str(r.get("memory_id") or r.get("source_memory_id") or "")
        trigger_stage = "TRIGGER_DIAGNOSTIC_ONLY"
        if reason == "TRIGGER_NOT_CONFIRMED":
            trigger_stage = "TRIGGER_NOT_CONFIRMED"
        elif reason in {"BLOCKER_OR_POLICY_VETO", "BLOCKER_LEDGER_REASON_UNKNOWN"}:
            trigger_stage = "TRIGGER_OR_CANDIDATE_BLOCKED"
        elif reason == "CORE_ELIGIBLE_BUT_NO_CANDIDATE_EMITTED":
            trigger_stage = "CORE_ELIGIBLE_CANDIDATE_INTAKE_GAP"

        records.append({
            "record_type": "TRIGGER_SHADOW",
            "created_utc": created,
            "trigger_shadow_id": event_id_from(r, "TRIGGER"),
            "source_record_id": r.get("count_record_id") or r.get("reason_source_id") or r.get("diagnostic_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": r.get("instrument"),
            "timeframe": r.get("timeframe"),
            "trigger_stage": trigger_stage,
            "reason_code": reason,
            "candidate_counted": False,
            "outcome_authorized": False,
            "plain_language_fa": "Trigger shadow skeleton: تلاش/شبه‌trigger یا علت fail شدن را ثبت می‌کند؛ سیگنال نیست.",
        })

    for c in candidates:
        mid = str(c.get("memory_id") or c.get("source_memory_id") or "")
        records.append({
            "record_type": "TRIGGER_SHADOW",
            "created_utc": created,
            "trigger_shadow_id": event_id_from(c, "TRIGGER_CAND"),
            "source_record_id": c.get("candidate_id") or c.get("event_id"),
            "candidate_id": c.get("candidate_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": c.get("instrument"),
            "timeframe": c.get("timeframe"),
            "trigger_stage": "TRIGGER_ACCEPTED_AS_SHADOW_CANDIDATE",
            "reason_code": "SHADOW_CANDIDATE_LOGGED",
            "candidate_counted": True,
            "outcome_authorized": False,
            "plain_language_fa": "Candidate ثبت شده اما هنوز outcome یا معامله نیست.",
        })

    return records


def build_blocker_shadow_records(created: str, blockers: List[Dict[str, Any]], reason_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []

    merged = []
    merged.extend(blockers)
    for r in reason_records:
        if str(r.get("count_class")) == "BLOCKER_DIAGNOSTIC_RECORD" or "BLOCKER" in normalize_reason(r):
            merged.append(r)

    for b in merged:
        mid = str(b.get("memory_id") or b.get("source_memory_id") or "")
        records.append({
            "record_type": "BLOCKER_SHADOW",
            "created_utc": created,
            "blocker_shadow_id": event_id_from(b, "BLOCKER"),
            "source_record_id": b.get("candidate_id") or b.get("diagnostic_id") or b.get("reason_source_id"),
            "candidate_id": b.get("candidate_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": b.get("instrument"),
            "timeframe": b.get("timeframe"),
            "blocker_reason_code": normalize_reason(b),
            "blocker_family": b.get("blocker_family") or b.get("canonical_stage") or b.get("normalized_stage"),
            "outcome_authorized": False,
            "plain_language_fa": "Blocker diagnostic ثبت شد؛ برای review آینده، نه سیگنال.",
        })

    return records


def build_candidate_records(created: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for c in candidates:
        mid = str(c.get("memory_id") or c.get("source_memory_id") or "")
        records.append({
            "record_type": "SHADOW_CANDIDATE_SNAPSHOT",
            "created_utc": created,
            "candidate_snapshot_id": event_id_from(c, "CAND"),
            "candidate_id": c.get("candidate_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": c.get("instrument"),
            "timeframe": c.get("timeframe"),
            "session_bucket": c.get("session_bucket"),
            "source_bar_open_ts_utc": c.get("source_bar_open_ts_utc"),
            "direction_side": c.get("direction_side"),
            "outcome_authorized": False,
            "plain_language_fa": "Candidate snapshot فقط برای shadow observation آینده ذخیره شد؛ معامله نیست.",
        })
    return records


def build_diagnostic_records(created: str, reason_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for r in reason_records:
        mid = str(r.get("memory_id") or r.get("source_memory_id") or "")
        records.append({
            "record_type": "DIAGNOSTIC_RECORD",
            "created_utc": created,
            "diagnostic_log_id": event_id_from(r, "DIAG"),
            "source_record_id": r.get("count_record_id") or r.get("reason_source_id") or r.get("diagnostic_id") or r.get("event_id"),
            "memory_id": mid,
            "memory_class": memory_class(mid),
            "instrument": r.get("instrument"),
            "timeframe": r.get("timeframe"),
            "count_class": r.get("count_class"),
            "reason_code": normalize_reason(r),
            "reason_confidence": r.get("reason_confidence"),
            "needs_upstream_instrumentation": bool(r.get("needs_upstream_instrumentation")),
            "outcome_authorized": False,
            "plain_language_fa": "Diagnostic record append-only؛ برای فهم علت candidate نشدن.",
        })
    return records


def latest_tail(path: Path, limit: int = 5) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []


def main() -> None:
    created = now_utc()
    day = day_key(created)
    ldir = log_dir_for_day(day)
    ldir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "brain4": load_json(BRAIN4_PAYLOAD, {}),
        "event_history": load_json(EVENT_HISTORY, {}),
        "count": load_json(COUNT_SEMANTICS, {}),
        "ops": load_json(OPS_STATUS, {}),
        "shadow": load_json(SHADOW_STATUS, {}),
        "reason_source": load_json(REASON_SOURCE, {}),
        "reason_enriched": load_json(REASON_ENRICHED, {}),
        "blockers": load_json(BLOCKER_BREAKDOWN, {}),
        "candidate": load_json(CAND_PAYLOAD, {}),
        "candidate_summary": load_json(CAND_SUMMARY, {}),
    }

    # Prefer count-semantics records because they already normalize classes.
    reason_records = as_list(payloads["count"], ["records"])
    if not reason_records:
        reason_records = as_list(payloads["reason_source"], ["records"]) + as_list(payloads["reason_enriched"], ["records"])

    candidates = as_list(payloads["candidate"], ["candidates"])
    blockers = as_list(payloads["candidate"], ["blocked_candidates"]) + as_list(payloads["blockers"], ["records", "blocked_candidates", "blockers"])

    context_records = [build_context_snapshot(created, payloads)]
    watch_records = build_memory_watch_records(created, payloads["event_history"])
    setup_records = build_setup_shadow_records(created, reason_records, payloads["event_history"])
    trigger_records = build_trigger_shadow_records(created, reason_records, candidates, blockers)
    blocker_records = build_blocker_shadow_records(created, blockers, reason_records)
    candidate_records = build_candidate_records(created, candidates)
    diagnostic_records = build_diagnostic_records(created, reason_records)

    files = {
        "context_snapshot": ldir / ("context_snapshot_log_" + day + ".jsonl"),
        "memory_watch": ldir / ("memory_watch_log_" + day + ".jsonl"),
        "setup_shadow": ldir / ("setup_shadow_log_" + day + ".jsonl"),
        "trigger_shadow": ldir / ("trigger_shadow_log_" + day + ".jsonl"),
        "blocker_shadow": ldir / ("blocker_shadow_log_" + day + ".jsonl"),
        "candidate_shadow": ldir / ("candidate_shadow_log_" + day + ".jsonl"),
        "diagnostic_record": ldir / ("diagnostic_record_log_" + day + ".jsonl"),
    }

    append_results = {
        "context_snapshot": append_jsonl_dedup(files["context_snapshot"], context_records),
        "memory_watch": append_jsonl_dedup(files["memory_watch"], watch_records),
        "setup_shadow": append_jsonl_dedup(files["setup_shadow"], setup_records),
        "trigger_shadow": append_jsonl_dedup(files["trigger_shadow"], trigger_records),
        "blocker_shadow": append_jsonl_dedup(files["blocker_shadow"], blocker_records),
        "candidate_shadow": append_jsonl_dedup(files["candidate_shadow"], candidate_records),
        "diagnostic_record": append_jsonl_dedup(files["diagnostic_record"], diagnostic_records),
    }

    today_counts = {name + "_count_today": count_jsonl(path) for name, path in files.items()}

    class_counts = Counter(str(r.get("count_class") or "UNKNOWN") for r in reason_records)
    reason_counts = Counter(normalize_reason(r) for r in reason_records)

    status = {
        "payload_version": "LIVE_SHADOW_FOUNDATION_01_STATUS_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "day": day,
        "log_directory": str(ldir).replace("\\", "/"),
        "append_results": append_results,
        **today_counts,
        "current_run_counts": {
            "context_snapshot_records_built": len(context_records),
            "memory_watch_records_built": len(watch_records),
            "setup_shadow_records_built": len(setup_records),
            "trigger_shadow_records_built": len(trigger_records),
            "blocker_shadow_records_built": len(blocker_records),
            "candidate_shadow_records_built": len(candidate_records),
            "diagnostic_records_built": len(diagnostic_records),
            "candidate_count": len(candidates),
            "reason_record_count": len(reason_records),
        },
        "count_semantics": {
            "candidate_count": payloads["count"].get("candidate_count"),
            "diagnostic_record_count_last_run": payloads["count"].get("diagnostic_record_count_last_run"),
            "unique_market_near_miss_event_count_last_run": payloads["count"].get("unique_market_near_miss_event_count_last_run"),
            "instrumentation_gap_record_count_last_run": payloads["count"].get("instrumentation_gap_record_count_last_run"),
            "active_watch_count": payloads["count"].get("active_watch_count"),
        },
        "record_class_breakdown_last_run": dict(class_counts.most_common()),
        "reason_breakdown_last_run": dict(reason_counts.most_common()),
        "recent_setup_shadow_records": latest_tail(files["setup_shadow"], 5),
        "recent_trigger_shadow_records": latest_tail(files["trigger_shadow"], 5),
        "recent_candidate_shadow_records": latest_tail(files["candidate_shadow"], 5),
        "display_badge": "LIVE SHADOW FOUNDATION / NOT A SIGNAL",
        "plain_language_fa": (
            "این وضعیت نشان می‌دهد داده زنده به شکل append-only برای context، memory watch، setup shadow، trigger shadow، blocker و candidate snapshot ذخیره می‌شود. "
            "این outcome، سیگنال، ورود، حدضرر، تارگت یا اجرای معامله نیست."
        ),
        "boundary": NO_SIGNAL_BOUNDARY,
    }

    write_json(OUT_STATUS_RUNTIME, status)
    write_json(OUT_STATUS_PANEL, status)

    print(json.dumps({
        "status": "LIVE_SHADOW_FOUNDATION_01_OUTPUTS_BUILT",
        "day": day,
        "context_snapshot_count_today": status["context_snapshot_count_today"],
        "setup_shadow_count_today": status["setup_shadow_count_today"],
        "trigger_shadow_count_today": status["trigger_shadow_count_today"],
        "candidate_shadow_count_today": status["candidate_shadow_count_today"],
        "diagnostic_record_count_today": status["diagnostic_record_count_today"],
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "outcome_observation_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
