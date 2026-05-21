#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-OPS-01 — Combined Shadow Operations Hardening

Combines:
- DIAG-01B: stage-specific near-miss reason enrichment
- ELIG-01: watch/core/extended/candidate eligibility clarity
- LEDGER-01: last-run / daily / weekly / cohort rollups
- HEALTH-01: end-to-end freshness / pipeline health
- lightweight REVIEW queue

Boundary:
NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_POSITION_SIZE /
NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json
import hashlib
from collections import Counter, defaultdict

ROOT = Path.cwd()

RUNTIME_BRAIN = ROOT / "runtime" / "sig_brain"
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
RUNTIME_CAND = ROOT / "runtime" / "sig_signal_candidates"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"
REPORTS = ROOT / "reports"

for p in [RUNTIME_SHADOW, RUNTIME_CAND, PANEL, PROOFS, REPORTS]:
    p.mkdir(parents=True, exist_ok=True)

AUTHORITY = (
    "SHADOW_OPS_01|DIAG_ELIG_LEDGER_HEALTH_REVIEW|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|"
    "NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"
)

# Input files
REFRESH_STATUS = RUNTIME_BRAIN / "sig_live_refresh_status_latest.json"
BRAIN4_PAYLOAD = RUNTIME_BRAIN / "sig_brain4_runtime_payload_current.json"
EVENT_HISTORY = RUNTIME_BRAIN / "sig_brain4_event_history_current.json"
CAND_PAYLOAD = RUNTIME_CAND / "signal_candidate_payload_current.json"
CAND_SUMMARY = RUNTIME_CAND / "signal_candidate_summary_current.json"
SHADOW_PANEL = RUNTIME_SHADOW / "shadow_panel_status_current.json"
SHADOW_SUMMARY = RUNTIME_SHADOW / "shadow_summary_current.json"
READY_VALIDATION = PROOFS / "sig_shadow_ready_01_validation_result.json"
DIAG_VALIDATION = PROOFS / "sig_shadow_diag_01_validation_result.json"
DIAG_NEAR_MISS = RUNTIME_SHADOW / "near_miss_detail_ledger_current.json"
DIAG_BLOCKER = RUNTIME_SHADOW / "blocker_reason_breakdown_current.json"
DIAG_ELIG = RUNTIME_SHADOW / "eligibility_diagnostic_current.json"

# Output files
OUT_REASON_ENRICHED = RUNTIME_SHADOW / "near_miss_reason_enriched_current.json"
OUT_ELIG_STATUS = RUNTIME_SHADOW / "eligibility_status_current.json"
OUT_LAST_RUN = RUNTIME_SHADOW / "shadow_last_run_summary_current.json"
OUT_HISTORY = RUNTIME_SHADOW / "shadow_ops_run_history_current.json"
OUT_DAILY = RUNTIME_SHADOW / "shadow_daily_rollup_current.json"
OUT_WEEKLY = RUNTIME_SHADOW / "shadow_weekly_rollup_current.json"
OUT_COHORT = RUNTIME_SHADOW / "shadow_cohort_rollup_current.json"
OUT_HEALTH = RUNTIME_SHADOW / "shadow_pipeline_health_current.json"
OUT_REVIEW_QUEUE = RUNTIME_SHADOW / "shadow_review_queue_current.json"
OUT_PANEL_OPS = PANEL / "shadow_ops_status_current.json"
OUT_REPORT_TEMPLATE = REPORTS / "shadow_weekly_review_template.md"
OUT_VALIDATION = PROOFS / "sig_shadow_ops_01_validation_result.json"

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


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_now() -> str:
    return utc_now_dt().isoformat().replace("+00:00", "Z")


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


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value)
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def age_minutes(value: Any, now: Optional[datetime] = None) -> Optional[float]:
    dt = parse_ts(value)
    if not dt:
        return None
    n = now or utc_now_dt()
    return round((n - dt).total_seconds() / 60.0, 2)


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


def count_by(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    c = Counter(str(r.get(key) or "UNKNOWN") for r in rows)
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def event_key(e: Dict[str, Any]) -> str:
    return str(e.get("event_id") or e.get("candidate_id") or stable_id([
        e.get("memory_id"), e.get("instrument"), e.get("timeframe"),
        e.get("source_bar_open_ts_utc"), e.get("activated_at_utc"), e.get("status")
    ]))


def infer_stage_reason(row: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return stage_failed, reason_code, normalized_reason."""
    stage = str(row.get("stage_failed") or row.get("reason_code") or "").strip()
    reason = str(row.get("reason") or row.get("plain_language_fa") or "").strip()
    eligibility = str(row.get("eligibility_status") or "").strip()

    if stage and stage != "UNKNOWN_NEAR_MISS_REASON":
        code = stage
    elif eligibility == "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY":
        code = "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT"
    elif eligibility == "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE":
        code = "NON_CORE_MEMORY"
    elif eligibility == "CORE_WATCH_EXPIRED_BEFORE_CANDIDATE":
        code = "EXPIRED_BEFORE_CANDIDATE"
    elif eligibility == "CORE_WATCH_INVALIDATED_BEFORE_CANDIDATE":
        code = "INVALIDATED_BEFORE_CANDIDATE"
    elif eligibility == "ACTIVE_WATCH_CORE_ELIGIBLE":
        code = "CORE_ELIGIBLE_AWAITING_CANDIDATE_INTAKE"
    elif "out-of-core" in reason.lower() or "split-stability" in reason.lower():
        code = "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT"
    elif "expired" in reason.lower():
        code = "EXPIRED_BEFORE_CANDIDATE"
    elif "invalidated" in reason.lower():
        code = "INVALIDATED_BEFORE_CANDIDATE"
    elif "trigger" in reason.lower():
        code = "TRIGGER_NOT_CONFIRMED"
    elif "missing" in reason.lower() or "field" in reason.lower():
        code = "MISSING_REQUIRED_FIELD"
    elif "block" in reason.lower() or "veto" in reason.lower():
        code = "BLOCKER_OR_POLICY_VETO"
    else:
        code = "UNKNOWN_NEAR_MISS_REASON"

    stage_map = {
        "OUT_OF_CORE_SPLIT_STABILITY_CAVEAT": "ELIGIBILITY_OUT_OF_CORE",
        "NON_CORE_MEMORY": "ELIGIBILITY_NON_CORE",
        "EXPIRED_BEFORE_CANDIDATE": "LIFECYCLE_EXPIRED",
        "INVALIDATED_BEFORE_CANDIDATE": "LIFECYCLE_INVALIDATED",
        "CORE_ELIGIBLE_AWAITING_CANDIDATE_INTAKE": "CANDIDATE_INTAKE_PENDING",
        "TRIGGER_NOT_CONFIRMED": "TRIGGER",
        "MISSING_REQUIRED_FIELD": "INPUT_DATA",
        "BLOCKER_OR_POLICY_VETO": "BLOCKER_OR_POLICY",
        "UNKNOWN_NEAR_MISS_REASON": "UNKNOWN",
    }
    normalized_stage = stage_map.get(code, code)
    return normalized_stage, code, reason or code


def classify_event(e: Dict[str, Any]) -> Dict[str, Any]:
    mid = str(e.get("memory_id") or "")
    status = str(e.get("status") or "").upper()
    if not mid:
        eligibility = "UNKNOWN_MEMORY_ID"
        reason = "event has no memory_id"
    elif bool(e.get("no_trade", False)):
        eligibility = "NOT_CANDIDATE_NO_TRADE_CONTEXT"
        reason = "no-trade/context memory is not directional candidate"
    elif mid in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS:
        eligibility = "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY" if status == "ACTIVE" else "EXTENDED_OBSERVATION_LIFECYCLE_RECORD"
        reason = "memory is displayable but excluded from core shadow because of split-stability caveat"
    elif mid in CORE_SHADOW_MEMORY_IDS:
        if status == "ACTIVE":
            eligibility = "ACTIVE_WATCH_CORE_ELIGIBLE"
            reason = "core memory active; candidate intake should evaluate setup/trigger/blocker"
        elif status == "EXPIRED":
            eligibility = "CORE_WATCH_EXPIRED_BEFORE_CANDIDATE"
            reason = "core memory display lifecycle expired before current candidate intake"
        elif status == "INVALIDATED":
            eligibility = "CORE_WATCH_INVALIDATED_BEFORE_CANDIDATE"
            reason = "core memory context invalidated in lifecycle"
        else:
            eligibility = "CORE_WATCH_NON_ACTIVE"
            reason = f"core memory status is {status or 'UNKNOWN'}"
    else:
        eligibility = "ACTIVE_WATCH_NOT_SHADOW_ELIGIBLE" if status == "ACTIVE" else "NON_CORE_LIFECYCLE_RECORD"
        reason = "memory is not in core shadow pilot"

    stage, code, _ = infer_stage_reason({"eligibility_status": eligibility, "reason": reason})
    severity = "HIGH" if eligibility in {"ACTIVE_WATCH_CORE_ELIGIBLE", "ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY"} else "LOW"
    return {
        "event_id": event_key(e),
        "memory_id": mid,
        "instrument": e.get("instrument"),
        "timeframe": e.get("timeframe"),
        "status": status,
        "direction_side": e.get("direction_side"),
        "session_bucket": e.get("session_bucket"),
        "source_bar_open_ts_utc": e.get("source_bar_open_ts_utc"),
        "activated_at_utc": e.get("activated_at_utc"),
        "setup_cluster_id": CORE_FAMILY_BY_MEMORY.get(mid, "OUT_OF_CORE_OR_UNKNOWN"),
        "eligibility_status": eligibility,
        "normalized_stage": stage,
        "reason_code": code,
        "reason": reason,
        "severity": severity,
        "one_step_from_candidate": eligibility == "ACTIVE_WATCH_CORE_ELIGIBLE",
    }


def enrich_near_misses(diag_near: Dict[str, Any], event_diag_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = as_list(diag_near, ["records", "near_misses", "items"])
    out: Dict[str, Dict[str, Any]] = {}

    for idx, r in enumerate(records):
        stage, code, normalized = infer_stage_reason(r)
        mid = r.get("memory_id")
        enriched = dict(r)
        enriched["diagnostic_id"] = str(r.get("diagnostic_id") or "OPS_NM_" + stable_id([idx, mid, code, r.get("event_id")]))
        enriched["normalized_stage"] = stage
        enriched["reason_code"] = code
        enriched["normalized_reason"] = normalized
        enriched["setup_cluster_id"] = r.get("setup_cluster_id") or CORE_FAMILY_BY_MEMORY.get(str(mid), "UNKNOWN_CLUSTER")
        enriched["core_shadow_memory"] = str(mid) in CORE_SHADOW_MEMORY_IDS
        enriched["extended_observation_only"] = str(mid) in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS
        enriched["candidate_eligible_after_diagnostic"] = bool(enriched.get("eligibility_status") == "ACTIVE_WATCH_CORE_ELIGIBLE")
        enriched["forbidden"] = "NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|NO_AUTO_LEARNING"
        out[enriched["diagnostic_id"]] = enriched

    # Add event-based rows that might not be in previous detail file.
    for e in event_diag_rows:
        if e["eligibility_status"] == "SHADOW_CANDIDATE_LOGGED":
            continue
        did = "OPS_EVT_" + stable_id([e.get("event_id"), e.get("memory_id"), e.get("eligibility_status")])
        out.setdefault(did, {
            "diagnostic_id": did,
            "source": "event_history_ops_eligibility",
            "event_id": e.get("event_id"),
            "memory_id": e.get("memory_id"),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "setup_cluster_id": e.get("setup_cluster_id"),
            "eligibility_status": e.get("eligibility_status"),
            "normalized_stage": e.get("normalized_stage"),
            "reason_code": e.get("reason_code"),
            "normalized_reason": e.get("reason"),
            "severity": e.get("severity"),
            "one_step_from_candidate": e.get("one_step_from_candidate"),
            "core_shadow_memory": str(e.get("memory_id")) in CORE_SHADOW_MEMORY_IDS,
            "extended_observation_only": str(e.get("memory_id")) in EXTENDED_OBSERVATION_ONLY_MEMORY_IDS,
            "forbidden": "NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|NO_AUTO_LEARNING",
        })
    return list(out.values())


def build_health(now_dt: datetime, inputs: Dict[str, Dict[str, Any]], ready_validation: Dict[str, Any], diag_validation: Dict[str, Any]) -> Dict[str, Any]:
    failures: List[str] = []
    warnings: List[str] = []

    refresh = inputs.get("refresh", {})
    brain4 = inputs.get("brain4", {})
    cand = inputs.get("candidate", {})
    shadow_panel = inputs.get("shadow_panel", {})

    refresh_created = refresh.get("created_utc") or refresh.get("payload_created_utc")
    brain4_created = brain4.get("created_utc")
    cand_created = cand.get("created_utc")
    shadow_created = shadow_panel.get("created_utc")

    age_refresh = age_minutes(refresh_created, now_dt)
    age_brain4 = age_minutes(brain4_created, now_dt)
    age_cand = age_minutes(cand_created, now_dt)
    age_shadow = age_minutes(shadow_created, now_dt)

    # Conservative freshness: local test may use old files, so old age is WARN, not FAIL.
    if age_refresh is None:
        warnings.append("refresh_status_timestamp_missing")
    elif age_refresh > 180:
        warnings.append(f"refresh_status_age_gt_180min:{age_refresh}")

    if age_brain4 is None:
        warnings.append("brain4_payload_timestamp_missing")
    elif age_brain4 > 180:
        warnings.append(f"brain4_payload_age_gt_180min:{age_brain4}")

    if age_cand is None:
        warnings.append("candidate_payload_timestamp_missing")
    if age_shadow is None:
        warnings.append("shadow_panel_timestamp_missing")

    if ready_validation.get("validation_status") not in {None, "PASS"}:
        failures.append("shadow_ready_validation_not_pass")
    if diag_validation.get("validation_status") not in {None, "PASS"}:
        warnings.append("diag01_previous_validation_not_pass_or_missing")

    # Boundary checks
    joined = json.dumps([refresh, brain4, cand, shadow_panel], ensure_ascii=False)
    for token in [
        '"signal_authorized": true',
        '"trade_instruction_authorized": true',
        '"broker_execution_authorized": true',
        '"auto_learning_authorized": true',
        '"rule_rewrite_authorized": true',
    ]:
        if token in joined:
            failures.append(f"forbidden_boundary_flag:{token}")

    # Pipeline order sanity if timestamps available
    b4dt = parse_ts(brain4_created)
    cdt = parse_ts(cand_created)
    if b4dt and cdt and cdt < b4dt - timedelta(minutes=15):
        warnings.append("candidate_payload_older_than_brain4_by_gt_15min")

    health_status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    return {
        "payload_version": "SHADOW_OPS_01_PIPELINE_HEALTH_v1_0",
        "created_utc": now_dt.isoformat().replace("+00:00", "Z"),
        "authority": AUTHORITY,
        "health_status": health_status,
        "failures": failures,
        "warnings": warnings,
        "freshness_minutes": {
            "refresh_status": age_refresh,
            "brain4_payload": age_brain4,
            "candidate_payload": age_cand,
            "shadow_panel_status": age_shadow,
        },
        "source_timestamps": {
            "refresh_created_utc": refresh_created,
            "brain4_created_utc": brain4_created,
            "candidate_created_utc": cand_created,
            "shadow_panel_status_created_utc": shadow_created,
        },
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }


def period_key_day(ts: str) -> str:
    dt = parse_ts(ts)
    return dt.date().isoformat() if dt else "UNKNOWN_DAY"


def period_key_week(ts: str) -> str:
    dt = parse_ts(ts)
    if not dt:
        return "UNKNOWN_WEEK"
    iso = dt.isocalendar()
    if hasattr(iso, "year"):
        return f"{iso.year}-W{iso.week:02d}"
    return f"{iso[0]}-W{iso[1]:02d}"


def append_history(run_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    current = load_json(OUT_HISTORY, {})
    rows = []
    if isinstance(current, dict) and isinstance(current.get("runs"), list):
        rows = [r for r in current["runs"] if isinstance(r, dict)]
    rows.append(run_row)
    # Keep bounded history in repo.
    rows = rows[-1500:]
    return rows


def rollup(rows: List[Dict[str, Any]], period_func) -> List[Dict[str, Any]]:
    bucket: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = period_func(r.get("created_utc"))
        if key not in bucket:
            bucket[key] = {
                "period": key,
                "run_count": 0,
                "candidate_count": 0,
                "near_miss_count": 0,
                "near_miss_high_count": 0,
                "blocked_candidate_count": 0,
                "active_watch_core_eligible_count": 0,
                "active_watch_extended_observation_only_count": 0,
                "health_fail_count": 0,
                "health_warn_count": 0,
            }
        b = bucket[key]
        b["run_count"] += 1
        for metric in [
            "candidate_count", "near_miss_count", "near_miss_high_count",
            "blocked_candidate_count", "active_watch_core_eligible_count",
            "active_watch_extended_observation_only_count",
        ]:
            b[metric] += int(r.get(metric) or 0)
        hs = str(r.get("health_status") or "")
        if hs == "FAIL":
            b["health_fail_count"] += 1
        elif hs == "WARN":
            b["health_warn_count"] += 1
    return [bucket[k] for k in sorted(bucket.keys())]


def build_review_queue(run: Dict[str, Any], enriched: List[Dict[str, Any]], health: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    if run.get("candidate_count", 0) == 0 and run.get("near_miss_high_count", 0) > 0:
        items.append({
            "review_id": "REV_" + stable_id([run.get("created_utc"), "HIGH_NEAR_MISS_NO_CANDIDATE"]),
            "priority": "HIGH",
            "review_type": "HIGH_NEAR_MISS_WITH_ZERO_CANDIDATES",
            "reason": "There are high-severity near-misses but no shadow candidate. Review gating / eligibility reasons.",
            "suggested_action": "Inspect near_miss_reason_enriched_current.json; do not loosen rules without PMO review.",
        })
    if run.get("active_watch_extended_observation_only_count", 0) > 0:
        items.append({
            "review_id": "REV_" + stable_id([run.get("created_utc"), "EXTENDED_ACTIVE"]),
            "priority": "MEDIUM",
            "review_type": "ACTIVE_EXTENDED_OBSERVATION_ONLY_WATCH",
            "reason": "An active watch is not core-shadow eligible because it remains extended-observation-only.",
            "suggested_action": "Keep out of candidate path until split-stability review is formally accepted.",
        })
    if str(health.get("health_status")) in {"WARN", "FAIL"}:
        items.append({
            "review_id": "REV_" + stable_id([run.get("created_utc"), "HEALTH_" + str(health.get("health_status"))]),
            "priority": "HIGH" if health.get("health_status") == "FAIL" else "MEDIUM",
            "review_type": "PIPELINE_HEALTH_" + str(health.get("health_status")),
            "reason": "Pipeline health has warning/failure diagnostics.",
            "suggested_action": "Review shadow_pipeline_health_current.json before interpreting candidate/near-miss counts.",
        })
    # Unknown reasons are still important.
    unknown_count = sum(1 for x in enriched if x.get("reason_code") == "UNKNOWN_NEAR_MISS_REASON")
    if unknown_count:
        items.append({
            "review_id": "REV_" + stable_id([run.get("created_utc"), "UNKNOWN_NEAR_MISS", unknown_count]),
            "priority": "MEDIUM",
            "review_type": "UNKNOWN_NEAR_MISS_REASON_REMAINS",
            "reason": f"{unknown_count} near-miss records still have unknown reason after enrichment.",
            "suggested_action": "Upstream setup/trigger/blocker scripts should emit stage_failed/reason_code.",
        })
    return {
        "payload_version": "SHADOW_OPS_01_REVIEW_QUEUE_v1_0",
        "created_utc": run.get("created_utc"),
        "authority": AUTHORITY,
        "review_item_count": len(items),
        "items": items,
        "boundary": {
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
            "signal_authorized": False,
            "broker_execution_authorized": False,
        },
    }


def write_review_template() -> None:
    if OUT_REPORT_TEMPLATE.exists():
        return
    OUT_REPORT_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT_TEMPLATE.write_text(
        """# Shadow Weekly Review Template

## Boundary

NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_BROKER_EXECUTION / NO_AUTO_LEARNING

## 1. Pipeline Health

- Health status:
- Stale-data warnings:
- Workflow cadence issues:

## 2. Candidate / Near-Miss / Blocked Counts

- Candidates:
- High near-misses:
- Blocked:
- Observations pending/complete:

## 3. Top Near-Miss Reasons

- Reason 1:
- Reason 2:
- Unknown reasons:

## 4. Core vs Extended Eligibility

- Core-eligible active watches:
- Extended-only active watches:
- Non-core active watches:

## 5. PMO Decision

- Continue:
- Instrumentation patch required:
- Trigger/blocker review required:
- No rule changes without versioned PMO approval.
""",
        encoding="utf-8",
    )


def main() -> None:
    now_dt = utc_now_dt()
    created = now_dt.isoformat().replace("+00:00", "Z")

    refresh = load_json(REFRESH_STATUS, {})
    brain4 = load_json(BRAIN4_PAYLOAD, {})
    event_history = load_json(EVENT_HISTORY, {})
    cand_payload = load_json(CAND_PAYLOAD, {})
    cand_summary = load_json(CAND_SUMMARY, {})
    shadow_panel = load_json(SHADOW_PANEL, {})
    shadow_summary = load_json(SHADOW_SUMMARY, {})
    ready_validation = load_json(READY_VALIDATION, {})
    diag_validation = load_json(DIAG_VALIDATION, {})
    diag_near = load_json(DIAG_NEAR_MISS, {})
    diag_blocker = load_json(DIAG_BLOCKER, {})
    diag_elig = load_json(DIAG_ELIG, {})

    events = as_list(event_history, ["active_events", "events"])
    event_diag_rows = [classify_event(e) for e in events]
    enriched = enrich_near_misses(diag_near, event_diag_rows)

    candidates = as_list(cand_payload, ["candidates"])
    blocked_candidates = as_list(cand_payload, ["blocked_candidates"])
    blocker_records = as_list(diag_blocker, ["records", "blocked_candidates", "blockers"])
    blocked_count = max(len(blocked_candidates), int((diag_blocker or {}).get("blocked_candidate_count") or 0), len(blocker_records))

    elig_status_breakdown = count_by(event_diag_rows, "eligibility_status")
    active_core = elig_status_breakdown.get("ACTIVE_WATCH_CORE_ELIGIBLE", 0)
    active_extended = elig_status_breakdown.get("ACTIVE_WATCH_EXTENDED_OBSERVATION_ONLY", 0)
    candidate_logged = elig_status_breakdown.get("SHADOW_CANDIDATE_LOGGED", 0)

    health = build_health(
        now_dt,
        {"refresh": refresh, "brain4": brain4, "candidate": cand_payload, "shadow_panel": shadow_panel},
        ready_validation,
        diag_validation,
    )

    reason_breakdown = count_by(enriched, "reason_code")
    stage_breakdown = count_by(enriched, "normalized_stage")
    memory_breakdown = count_by(enriched, "memory_id")
    cluster_breakdown = count_by(enriched, "setup_cluster_id")
    severity_breakdown = count_by(enriched, "severity")
    high_count = sum(1 for r in enriched if str(r.get("severity")).upper() in {"HIGH", "CRITICAL"})

    last_run = {
        "payload_version": "SHADOW_OPS_01_LAST_RUN_SUMMARY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "candidate_count": len(candidates),
        "near_miss_count": len(enriched),
        "near_miss_high_count": high_count,
        "blocked_candidate_count": blocked_count,
        "active_watch_core_eligible_count": active_core,
        "active_watch_extended_observation_only_count": active_extended,
        "shadow_candidate_logged_count": candidate_logged,
        "top_reason_breakdown": list(reason_breakdown.items())[:8],
        "top_stage_breakdown": list(stage_breakdown.items())[:8],
        "health_status": health.get("health_status"),
        "health_warnings": health.get("warnings", []),
        "health_failures": health.get("failures", []),
        "source_created_utc": {
            "refresh": refresh.get("created_utc") or refresh.get("payload_created_utc"),
            "brain4": brain4.get("created_utc"),
            "candidate": cand_payload.get("created_utc"),
            "shadow_panel": shadow_panel.get("created_utc"),
        },
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    # Persist history and rollups.
    run_row = {
        "created_utc": created,
        "candidate_count": len(candidates),
        "near_miss_count": len(enriched),
        "near_miss_high_count": high_count,
        "blocked_candidate_count": blocked_count,
        "active_watch_core_eligible_count": active_core,
        "active_watch_extended_observation_only_count": active_extended,
        "health_status": health.get("health_status"),
    }
    history_rows = append_history(run_row)

    cohort_id = shadow_panel.get("cohort_id") or "SHADOW_COHORT_UNKNOWN"
    history_payload = {
        "payload_version": "SHADOW_OPS_01_RUN_HISTORY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "cohort_id": cohort_id,
        "run_count": len(history_rows),
        "runs": history_rows,
        "boundary": {
            "signal_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    daily = {
        "payload_version": "SHADOW_OPS_01_DAILY_ROLLUP_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "rollups": rollup(history_rows, period_key_day),
        "boundary": {"signal_authorized": False, "broker_execution_authorized": False},
    }
    weekly = {
        "payload_version": "SHADOW_OPS_01_WEEKLY_ROLLUP_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "rollups": rollup(history_rows, period_key_week),
        "boundary": {"signal_authorized": False, "broker_execution_authorized": False},
    }
    cohort = {
        "payload_version": "SHADOW_OPS_01_COHORT_ROLLUP_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "cohort_id": cohort_id,
        "run_count": len(history_rows),
        "candidate_count": sum(int(r.get("candidate_count") or 0) for r in history_rows),
        "near_miss_count": sum(int(r.get("near_miss_count") or 0) for r in history_rows),
        "near_miss_high_count": sum(int(r.get("near_miss_high_count") or 0) for r in history_rows),
        "blocked_candidate_count": sum(int(r.get("blocked_candidate_count") or 0) for r in history_rows),
        "active_watch_core_eligible_count": sum(int(r.get("active_watch_core_eligible_count") or 0) for r in history_rows),
        "active_watch_extended_observation_only_count": sum(int(r.get("active_watch_extended_observation_only_count") or 0) for r in history_rows),
        "health_fail_count": sum(1 for r in history_rows if r.get("health_status") == "FAIL"),
        "health_warn_count": sum(1 for r in history_rows if r.get("health_status") == "WARN"),
        "boundary": {"signal_authorized": False, "broker_execution_authorized": False, "auto_learning_authorized": False},
    }

    review_queue = build_review_queue(run_row, enriched, health)

    eligibility_status = {
        "payload_version": "SHADOW_OPS_01_ELIGIBILITY_STATUS_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "eligibility_status_breakdown": elig_status_breakdown,
        "active_watch_core_eligible_count": active_core,
        "active_watch_extended_observation_only_count": active_extended,
        "shadow_candidate_logged_count": candidate_logged,
        "event_diagnostics": event_diag_rows,
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    reason_enriched_payload = {
        "payload_version": "SHADOW_OPS_01_NEAR_MISS_REASON_ENRICHED_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "near_miss_count": len(enriched),
        "near_miss_high_count": high_count,
        "reason_breakdown": reason_breakdown,
        "stage_breakdown": stage_breakdown,
        "severity_breakdown": severity_breakdown,
        "memory_breakdown": memory_breakdown,
        "cluster_breakdown": cluster_breakdown,
        "records": enriched,
        "plain_language_fa": "این فایل توضیح می‌دهد چرا موارد نزدیک به setup/candidate به shadow candidate کامل تبدیل نشده‌اند.",
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    panel_ops = {
        "panel_payload_version": "SHADOW_OPS_01_PANEL_STATUS_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "display_badge": "SHADOW OPS / NOT A SIGNAL",
        "health_status": health.get("health_status"),
        "candidate_count": len(candidates),
        "near_miss_count_last_run": len(enriched),
        "near_miss_high_count_last_run": high_count,
        "blocked_candidate_count_last_run": blocked_count,
        "active_watch_core_eligible_count": active_core,
        "active_watch_extended_observation_only_count": active_extended,
        "top_reason_breakdown": list(reason_breakdown.items())[:5],
        "top_stage_breakdown": list(stage_breakdown.items())[:5],
        "daily_rollup_latest": daily["rollups"][-1] if daily["rollups"] else None,
        "weekly_rollup_latest": weekly["rollups"][-1] if weekly["rollups"] else None,
        "cohort_rollup": {
            "cohort_id": cohort_id,
            "run_count": cohort["run_count"],
            "candidate_count": cohort["candidate_count"],
            "near_miss_count": cohort["near_miss_count"],
            "near_miss_high_count": cohort["near_miss_high_count"],
            "blocked_candidate_count": cohort["blocked_candidate_count"],
        },
        "review_item_count": review_queue["review_item_count"],
        "plain_language_fa": (
            "این وضعیت عملیاتی shadow است: علت near-missها، eligibility، rollup و سلامت pipeline را نشان می‌دهد. "
            "این سیگنال، ورود، حدضرر، تارگت، اجرای معامله یا یادگیری خودکار نیست."
        ),
        "boundary": {
            "signal_authorized": False,
            "trade_instruction_authorized": False,
            "broker_execution_authorized": False,
            "auto_learning_authorized": False,
            "rule_rewrite_authorized": False,
        },
    }

    # Write outputs.
    write_json(OUT_REASON_ENRICHED, reason_enriched_payload)
    write_json(OUT_ELIG_STATUS, eligibility_status)
    write_json(OUT_LAST_RUN, last_run)
    write_json(OUT_HISTORY, history_payload)
    write_json(OUT_DAILY, daily)
    write_json(OUT_WEEKLY, weekly)
    write_json(OUT_COHORT, cohort)
    write_json(OUT_HEALTH, health)
    write_json(OUT_REVIEW_QUEUE, review_queue)
    write_json(OUT_PANEL_OPS, panel_ops)
    write_review_template()

    print(json.dumps({
        "status": "SHADOW_OPS_01_OUTPUTS_BUILT",
        "health_status": health.get("health_status"),
        "candidate_count": len(candidates),
        "near_miss_count": len(enriched),
        "near_miss_high_count": high_count,
        "blocked_candidate_count": blocked_count,
        "review_item_count": review_queue["review_item_count"],
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
