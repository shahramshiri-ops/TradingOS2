#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW_CANDIDATE_UNIVERSE_01

Research-only shadow candidate universe for TradingOS / SIG BRAIN.

Purpose:
- Increase live forward-observation density without promoting anything to active memory.
- Evaluate a bounded, pre-registered candidate bank against each live refresh.
- Register only active research candidates into the existing shadow-observation ledger so future H1 path observations can close.

Hard boundaries:
- NOT_SIGNAL
- NO_BUY_SELL
- NO_ENTRY_STOP_TARGET
- NO_POSITION_SIZE
- NO_BROKER_EXECUTION
- NO_AUTO_LEARNING
- NO_RULE_REWRITE
- NO_MEMORY_PROMOTION
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
import hashlib
import json
import math
import subprocess

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "config" / "shadow_candidate_universe_01_registry.json"
STATE_DIR = ROOT / "state" / "shadow_candidate_universe"
RUNTIME_DIR = ROOT / "runtime" / "sig_shadow_candidate_universe"
PANEL_DIR = ROOT / "panel" / "brain4"
OUTPUT_DIR = ROOT / "outputs" / "_shadow_candidate_universe_01"

VERSION = "SHADOW_CANDIDATE_UNIVERSE_01_v1_0"
STATE_VERSION = "SHADOW_CANDIDATE_UNIVERSE_STATE_v1_0"
AUTHORITY = "SHADOW_CANDIDATE_UNIVERSE_01|RESEARCH_SHADOW_ONLY|NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|NO_AUTO_LEARNING|NO_RULE_REWRITE"

BOUNDARY = {
    "display_only": True,
    "research_shadow_only": True,
    "active_memory_authorized": False,
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "entry_stop_target_authorized": False,
    "position_size_authorized": False,
    "profitability_claim_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "memory_promotion_authorized": False,
    "plain_language_fa": "این لایه فقط کاندیدهای پژوهشی shadow را برای observation ثبت می‌کند؛ memory فعال، سیگنال، خرید/فروش، ورود/خروج، حدضرر/هدف، سودآوری یا اجرای معامله نیست.",
}

MAX_REFRESH_HISTORY = 6000
MAX_EVALUATION_HISTORY = 12000
MAX_ACTIVE_EVENT_LEDGER = 5000
MAX_CONTEXT_SNAPSHOTS = 1500
MAX_EXAMPLES = 50


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def short_hash(text: str, n: int = 20) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return r.stdout.strip() if r.returncode == 0 else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def parse_utc(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def add_hours(ts: Any, hours: int) -> str:
    d = parse_utc(ts)
    if not d:
        return ""
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z") if hours == 0 else (d.replace(microsecond=0) + __import__('datetime').timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def norm(x: Any) -> str:
    return str(x).strip().upper() if x is not None else ""


def as_num(x: Any) -> Optional[float]:
    try:
        if x in (None, "", "UNKNOWN"):
            return None
        return float(x)
    except Exception:
        return None


def load_brain_context() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # Prefer panel payload because it usually has the newest committed static JSON.
    candidates = [
        ROOT / "runtime" / "sig_brain" / "sig_brain4_runtime_payload_current.json",
        ROOT / "panel" / "brain4" / "sig_brain4_runtime_payload_current.json",
    ]
    payload: Dict[str, Any] = {}
    for p in candidates:
        obj = read_json(p, {})
        if isinstance(obj, dict) and isinstance(obj.get("cards"), list):
            payload = obj
            break

    surfaces: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for card in payload.get("cards", []) or []:
        ctx = card.get("latest_context") or {}
        if not isinstance(ctx, dict):
            continue
        inst = norm(ctx.get("instrument") or card.get("instrument"))
        tf = norm(ctx.get("timeframe") or card.get("timeframe"))
        if not inst or not tf:
            continue
        # Merge duplicate cards for the same surface. Keep any non-empty fields.
        key = (inst, tf)
        existing = surfaces.get(key, {})
        merged = dict(existing)
        for k, v in ctx.items():
            if v not in (None, "", "UNKNOWN") or k not in merged:
                merged[k] = v
        merged.setdefault("instrument", inst)
        merged.setdefault("timeframe", tf)
        surfaces[key] = merged

    # Also read Brain5 surfaces as fallback/additional fields.
    brain5 = read_json(ROOT / "runtime" / "sig_brain" / "sig_brain5_derived_context_latest.json", {})
    for ctx in brain5.get("surfaces", []) or []:
        if not isinstance(ctx, dict):
            continue
        inst = norm(ctx.get("instrument"))
        tf = norm(ctx.get("timeframe"))
        if not inst or not tf:
            continue
        key = (inst, tf)
        existing = surfaces.get(key, {})
        merged = dict(ctx)
        merged.update(existing)  # Brain4/card fields win when present.
        surfaces[key] = merged

    return list(surfaces.values()), payload


def eval_clause(ctx: Dict[str, Any], clause: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    field = str(clause.get("field", ""))
    op = str(clause.get("op", "eq"))
    expected = clause.get("value")
    actual = ctx.get(field)
    detail = {"field": field, "op": op, "expected": expected, "actual": actual}

    if op != "exists" and field not in ctx:
        return False, f"MISSING_FIELD:{field}", detail

    ok = False
    if op == "exists":
        ok = field in ctx and ctx.get(field) not in (None, "", "UNKNOWN")
    elif op == "eq":
        ok = norm(actual) == norm(expected) if isinstance(expected, str) else actual == expected
    elif op == "neq":
        ok = norm(actual) != norm(expected) if isinstance(expected, str) else actual != expected
    elif op == "in":
        vals = [norm(v) for v in (expected or [])]
        ok = norm(actual) in vals
    elif op == "not_in":
        vals = [norm(v) for v in (expected or [])]
        ok = norm(actual) not in vals
    elif op == "contains":
        ok = norm(expected) in norm(actual)
    elif op == "truthy":
        ok = actual is True or norm(actual) in {"TRUE", "YES", "1", "Y"}
    elif op == "falsey":
        ok = actual is False or actual in (None, "", 0) or norm(actual) in {"FALSE", "NO", "0", "NONE", "UNKNOWN"}
    elif op in {"gt", "gte", "lt", "lte"}:
        a = as_num(actual)
        b = as_num(expected)
        ok = False if a is None or b is None else {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]
    elif op == "between":
        a = as_num(actual)
        lo = as_num((expected or [None, None])[0]) if isinstance(expected, list) else None
        hi = as_num((expected or [None, None])[1]) if isinstance(expected, list) else None
        ok = False if a is None or lo is None or hi is None else lo <= a <= hi
    else:
        return False, f"UNSUPPORTED_OP:{op}", detail

    return (ok, "PASS" if ok else f"CLAUSE_FAILED:{field}:{op}", detail)


def evaluate_candidate(spec: Dict[str, Any], surface_by_key: Dict[Tuple[str, str], Dict[str, Any]], created_utc: str, source_payload: Dict[str, Any]) -> Dict[str, Any]:
    inst = norm(spec.get("instrument"))
    tf = norm(spec.get("timeframe"))
    ctx = surface_by_key.get((inst, tf))
    clauses = spec.get("clauses") or []
    max_failed = int(spec.get("near_miss_max_failed_clauses") or max(1, math.ceil(len(clauses) * 0.25)))

    if not ctx:
        return {
            "evaluation_version": VERSION,
            "created_utc": created_utc,
            "candidate_id": spec.get("candidate_id"),
            "candidate_family": spec.get("candidate_family"),
            "instrument": inst,
            "timeframe": tf,
            "directional_bias": spec.get("directional_bias"),
            "evaluation_status": "INPUT_SURFACE_MISSING",
            "reason_codes": ["INPUT_SURFACE_MISSING"],
            "passed_clause_count": 0,
            "failed_clause_count": len(clauses),
            "missing_field_count": 0,
            "is_shadow_active": False,
            "is_near_miss": False,
            "boundary": BOUNDARY,
        }

    pass_details: List[Dict[str, Any]] = []
    fail_details: List[Dict[str, Any]] = []
    reason_codes: List[str] = []
    for cl in clauses:
        ok, code, detail = eval_clause(ctx, cl)
        if ok:
            pass_details.append(detail)
        else:
            fail_details.append(detail)
            reason_codes.append(code)

    missing_count = sum(1 for r in reason_codes if r.startswith("MISSING_FIELD:"))
    data_status = str(ctx.get("data_sufficiency_status", "UNKNOWN"))
    data_ok = data_status in {"OK", "PASS", "SUFFICIENT", "UNKNOWN"}  # UNKNOWN allowed only when no explicit field exists.
    if "data_sufficiency_status" in ctx and data_status not in {"OK", "PASS", "SUFFICIENT"}:
        status = "DATA_OR_CONTEXT_NOT_READY"
        active = False
        near = False
        reason_codes.append("DATA_OR_CONTEXT_NOT_READY:" + data_status)
    elif missing_count > 0:
        status = "INPUT_INSUFFICIENT"
        active = False
        near = False
    elif not fail_details:
        status = "SHADOW_CANDIDATE_ACTIVE"
        active = True
        near = False
    elif len(fail_details) <= max_failed:
        status = "SHADOW_CANDIDATE_NEAR_MISS"
        active = False
        near = True
    else:
        status = "NOT_TRIGGERED"
        active = False
        near = False

    trigger_bar = ctx.get("latest_h1_bar_open_ts_utc") or ctx.get("latest_bar_open_ts_utc") or source_payload.get("created_utc") or created_utc
    active_event_id = "SCU_EVT_" + short_hash("|".join([str(spec.get("candidate_id")), str(trigger_bar), str(spec.get("candidate_spec_version", ""))]), 24)

    reference_price = None
    for k in ["h1_close", "close", "latest_close", "bar_close"]:
        if ctx.get(k) not in (None, "", "UNKNOWN"):
            reference_price = ctx.get(k)
            break

    return {
        "evaluation_version": VERSION,
        "created_utc": created_utc,
        "candidate_id": spec.get("candidate_id"),
        "candidate_spec_version": spec.get("candidate_spec_version"),
        "candidate_family": spec.get("candidate_family"),
        "candidate_state": spec.get("candidate_state"),
        "instrument": inst,
        "timeframe": tf,
        "directional_bias": spec.get("directional_bias"),
        "candidate_contract_id": spec.get("candidate_contract_id"),
        "setup_cluster_id": spec.get("setup_cluster_id"),
        "score_not_probability": spec.get("score_not_probability"),
        "evaluation_status": status,
        "reason_codes": reason_codes[:20],
        "passed_clause_count": len(pass_details),
        "failed_clause_count": len(fail_details),
        "missing_field_count": missing_count,
        "total_clause_count": len(clauses),
        "is_shadow_active": active,
        "is_near_miss": near,
        "active_event_id": active_event_id if active else None,
        "trigger_bar_open_ts_utc": trigger_bar,
        "valid_until_utc": add_hours(trigger_bar, 8),
        "shadow_horizons": spec.get("shadow_horizons") or ["H1+1", "H1+2", "H1+4", "H1+8"],
        "observation_reference_price": reference_price,
        "observation_reference_price_policy": spec.get("observation_reference_price_policy"),
        "context_excerpt": {k: ctx.get(k) for k in [
            "instrument", "timeframe", "latest_bar_open_ts_utc", "latest_h1_bar_open_ts_utc", "session_bucket",
            "h1_bar_direction", "d1_trend_state", "h4_trend_state", "is_first_h1_bar_of_session",
            "last4_h1_contraction_flag", "current_h1_expansion_flag", "asian_high_breakout_continuation_by_closed_h1",
            "asian_high_swept_and_reclaimed_by_closed_h1", "london_low_swept_and_reclaimed_by_closed_h1",
            "weekly_open_reclaim_short_state", "h1_failed_breakout_or_session_sweep_state", "h1_close",
            "data_sufficiency_status", "context_builder_status"
        ] if k in ctx},
        "passed_clauses": pass_details[:20],
        "failed_clauses": fail_details[:20],
        "boundary": BOUNDARY,
        "forbidden_interpretation": spec.get("forbidden_interpretation"),
    }


def as_signal_intake_candidate(ev: Dict[str, Any], source_payload: Dict[str, Any]) -> Dict[str, Any]:
    cid = "SCUSHADOW_" + short_hash("|".join([str(ev.get("candidate_id")), str(ev.get("trigger_bar_open_ts_utc")), str(ev.get("active_event_id"))]), 22)
    return {
        "candidate_id": cid,
        "candidate_version": "SHADOW_CANDIDATE_UNIVERSE_01_INTAKE_v1_0",
        "candidate_state": "SHADOW_UNIVERSE_ACTIVE_PENDING_OBSERVATION_NOT_SIGNAL",
        "candidate_contract_id": ev.get("candidate_contract_id") or "SCU01_GENERIC_CONTRACT_v1_0",
        "setup_cluster_id": ev.get("setup_cluster_id") or "SCU01_UNKNOWN_CLUSTER",
        "source_memory_ids": [],
        "source_candidate_id": ev.get("candidate_id"),
        "source_shadow_event_id": ev.get("active_event_id"),
        "source_candidate_family": ev.get("candidate_family"),
        "source_type": "SHADOW_CANDIDATE_UNIVERSE_01_RESEARCH_ONLY",
        "instrument": ev.get("instrument"),
        "timeframe": ev.get("timeframe"),
        "directional_bias": ev.get("directional_bias"),
        "created_utc": ev.get("created_utc"),
        "trigger_bar_open_ts_utc": ev.get("trigger_bar_open_ts_utc"),
        "valid_until_utc": ev.get("valid_until_utc"),
        "shadow_horizons": ev.get("shadow_horizons") or ["H1+1", "H1+2", "H1+4", "H1+8"],
        "observation_reference_price": ev.get("observation_reference_price"),
        "observation_reference_price_policy": ev.get("observation_reference_price_policy") or "closed context price; observation-only, not entry",
        "source_payload_created_utc": source_payload.get("created_utc"),
        "source_payload_version": source_payload.get("payload_version"),
        "quality_band_not_probability": "PRE_REGISTERED_SHADOW_ONLY_NO_EDGE_CLAIM",
        "source_evidence": [{
            "source_candidate_id": ev.get("candidate_id"),
            "candidate_family": ev.get("candidate_family"),
            "evaluation_status": ev.get("evaluation_status"),
            "score_not_probability": ev.get("score_not_probability"),
            "passed_clause_count": ev.get("passed_clause_count"),
            "total_clause_count": ev.get("total_clause_count"),
            "evidence_grade": "NO_EDGE_CLAIM_FORWARD_OBSERVATION_ONLY",
        }],
        "latest_context_excerpt": ev.get("context_excerpt") or {},
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "forbidden_interpretation": "Research-only shadow candidate. Do not read as buy/sell/entry/stop/target/profitability/tradability/broker execution.",
    }


def empty_state(created_utc: str) -> Dict[str, Any]:
    return {
        "state_version": STATE_VERSION,
        "created_utc": created_utc,
        "updated_utc": created_utc,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "refresh_history": [],
        "evaluation_history": [],
        "active_event_ledger": [],
        "context_snapshots": [],
        "candidate_stats": {},
    }


def update_state(state: Dict[str, Any], evaluations: List[Dict[str, Any]], registry: Dict[str, Any], created_utc: str, source_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not state:
        state = empty_state(created_utc)
    state.setdefault("refresh_history", [])
    state.setdefault("evaluation_history", [])
    state.setdefault("active_event_ledger", [])
    state.setdefault("context_snapshots", [])
    state.setdefault("candidate_stats", {})

    active = [e for e in evaluations if e.get("is_shadow_active")]
    near = [e for e in evaluations if e.get("is_near_miss")]
    status_counts = Counter(e.get("evaluation_status", "UNKNOWN") for e in evaluations)
    family_counts = Counter(e.get("candidate_family", "UNKNOWN") for e in active)
    inst_counts = Counter(e.get("instrument", "UNKNOWN") for e in active)

    refresh_id = "SCU01_REFRESH_" + short_hash(str(created_utc) + "|" + str(source_payload.get("created_utc")), 18)
    refresh_row = {
        "refresh_id": refresh_id,
        "created_utc": created_utc,
        "source_payload_created_utc": source_payload.get("created_utc"),
        "source_payload_version": source_payload.get("payload_version"),
        "registry_version": registry.get("registry_version"),
        "candidate_spec_count": len(registry.get("candidates") or []),
        "active_shadow_candidate_count": len(active),
        "near_miss_count": len(near),
        "status_counts": dict(status_counts),
        "active_by_family": dict(family_counts),
        "active_by_instrument": dict(inst_counts),
        "git_sha": git_sha(),
        "boundary": BOUNDARY,
    }
    state["refresh_history"].append(refresh_row)
    state["refresh_history"] = state["refresh_history"][-MAX_REFRESH_HISTORY:]

    compact_rows = []
    for e in evaluations:
        compact_rows.append({
            "refresh_id": refresh_id,
            "created_utc": created_utc,
            "candidate_id": e.get("candidate_id"),
            "candidate_family": e.get("candidate_family"),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "directional_bias": e.get("directional_bias"),
            "evaluation_status": e.get("evaluation_status"),
            "reason_codes": e.get("reason_codes", [])[:8],
            "passed_clause_count": e.get("passed_clause_count"),
            "failed_clause_count": e.get("failed_clause_count"),
            "trigger_bar_open_ts_utc": e.get("trigger_bar_open_ts_utc"),
            "active_event_id": e.get("active_event_id"),
        })
    state["evaluation_history"].extend(compact_rows)
    state["evaluation_history"] = state["evaluation_history"][-MAX_EVALUATION_HISTORY:]

    existing_events = {r.get("active_event_id"): r for r in state.get("active_event_ledger", []) if r.get("active_event_id")}
    for e in active:
        eid = e.get("active_event_id")
        if not eid:
            continue
        row = existing_events.get(eid) or {
            "active_event_id": eid,
            "first_seen_utc": created_utc,
            "seen_refresh_count": 0,
        }
        row.update({
            "last_seen_utc": created_utc,
            "seen_refresh_count": int(row.get("seen_refresh_count") or 0) + 1,
            "candidate_id": e.get("candidate_id"),
            "candidate_family": e.get("candidate_family"),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "directional_bias": e.get("directional_bias"),
            "trigger_bar_open_ts_utc": e.get("trigger_bar_open_ts_utc"),
            "valid_until_utc": e.get("valid_until_utc"),
            "observation_reference_price": e.get("observation_reference_price"),
            "shadow_only": True,
            "signal_authorized": False,
            "broker_execution_authorized": False,
        })
        existing_events[eid] = row
        state["context_snapshots"].append({
            "active_event_id": eid,
            "created_utc": created_utc,
            "candidate_id": e.get("candidate_id"),
            "context_excerpt": e.get("context_excerpt") or {},
            "passed_clauses": e.get("passed_clauses", [])[:20],
            "failed_clauses": e.get("failed_clauses", [])[:20],
        })
    state["active_event_ledger"] = sorted(existing_events.values(), key=lambda x: (x.get("trigger_bar_open_ts_utc", ""), x.get("active_event_id", "")))[-MAX_ACTIVE_EVENT_LEDGER:]
    state["context_snapshots"] = state["context_snapshots"][-MAX_CONTEXT_SNAPSHOTS:]

    stats = state.setdefault("candidate_stats", {})
    for e in evaluations:
        cid = str(e.get("candidate_id"))
        st = stats.setdefault(cid, {
            "candidate_id": cid,
            "candidate_family": e.get("candidate_family"),
            "instrument": e.get("instrument"),
            "timeframe": e.get("timeframe"),
            "directional_bias": e.get("directional_bias"),
            "evaluation_count": 0,
            "active_count": 0,
            "near_miss_count": 0,
            "input_insufficient_count": 0,
            "last_status": None,
            "last_seen_utc": None,
            "last_active_utc": None,
        })
        st["evaluation_count"] += 1
        st["last_status"] = e.get("evaluation_status")
        st["last_seen_utc"] = created_utc
        if e.get("is_shadow_active"):
            st["active_count"] += 1
            st["last_active_utc"] = created_utc
        if e.get("is_near_miss"):
            st["near_miss_count"] += 1
        if e.get("evaluation_status") == "INPUT_INSUFFICIENT":
            st["input_insufficient_count"] += 1

    state["updated_utc"] = created_utc
    state["registry_version"] = registry.get("registry_version")
    state["candidate_spec_count"] = len(registry.get("candidates") or [])
    state["authority"] = AUTHORITY
    state["boundary"] = BOUNDARY
    return state


def build_review_pack(state: Dict[str, Any], current: Dict[str, Any], evaluations: List[Dict[str, Any]], created_utc: str) -> Dict[str, Any]:
    stats = list((state.get("candidate_stats") or {}).values())
    stats_sorted = sorted(stats, key=lambda x: (-int(x.get("active_count") or 0), -int(x.get("near_miss_count") or 0), str(x.get("candidate_id"))))
    never_active = [s for s in stats if int(s.get("active_count") or 0) == 0]
    noisy_or_frequent = [s for s in stats if int(s.get("active_count") or 0) >= 5]
    top_near = sorted(stats, key=lambda x: -int(x.get("near_miss_count") or 0))[:20]
    return {
        "review_pack_version": "SHADOW_CANDIDATE_UNIVERSE_01_REVIEW_PACK_v1_0",
        "created_utc": created_utc,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "interpretation_fa": "این بسته فقط برای review پژوهشی کاندیدهای shadow است. هیچ کاندیدی memory فعال یا سیگنال نیست.",
        "current_summary": current.get("summary"),
        "since_state_created_utc": state.get("created_utc"),
        "refresh_count_observed": len(state.get("refresh_history", []) or []),
        "candidate_count": state.get("candidate_spec_count"),
        "candidate_stats_top_active": stats_sorted[:30],
        "top_near_miss_candidates": top_near,
        "never_active_candidate_count": len(never_active),
        "never_active_examples": never_active[:30],
        "frequent_active_candidate_count": len(noisy_or_frequent),
        "frequent_active_examples": noisy_or_frequent[:30],
        "allowed_future_decisions_after_separate_review_only": [
            "KEEP_SHADOW_ONLY", "PARK_SHADOW_CANDIDATE", "REJECT_SHADOW_CANDIDATE", "RESPECIFY_AS_NEW_CANDIDATE_VERSION", "NOMINATE_FOR_CAVEATED_MEMORY_WATCH_REVIEW_ONLY"
        ],
        "forbidden_decisions_inside_this_pack": [
            "CREATE_SIGNAL", "AUTHORIZE_TRADE", "AUTO_PROMOTE_MEMORY", "CHANGE_RULE_AFTER_SEEING_OUTCOME", "OPEN_HOLDOUT_AUTOMATICALLY"
        ],
    }


def main() -> int:
    created = now_utc()
    registry = read_json(CONFIG_PATH, {})
    if not isinstance(registry, dict) or not isinstance(registry.get("candidates"), list):
        raise SystemExit(f"Missing or invalid registry: {CONFIG_PATH}")

    surfaces, source_payload = load_brain_context()
    surface_by_key = {(norm(s.get("instrument")), norm(s.get("timeframe"))): s for s in surfaces}
    evaluations = [evaluate_candidate(spec, surface_by_key, created, source_payload) for spec in registry.get("candidates", [])]
    active = [e for e in evaluations if e.get("is_shadow_active")]
    near = [e for e in evaluations if e.get("is_near_miss")]
    status_counts = Counter(e.get("evaluation_status", "UNKNOWN") for e in evaluations)
    family_counts = Counter(e.get("candidate_family", "UNKNOWN") for e in active)
    inst_counts = Counter(e.get("instrument", "UNKNOWN") for e in active)

    state_path = STATE_DIR / "shadow_candidate_universe_state_v1.json"
    state = read_json(state_path, {})
    state = update_state(state, evaluations, registry, created, source_payload)

    active_signal_candidates = [as_signal_intake_candidate(e, source_payload) for e in active]
    intake_status = "SHADOW_UNIVERSE_ACTIVE_CANDIDATES_READY_FOR_OBSERVATION" if active_signal_candidates else "EMPTY_SAFE_NO_SHADOW_CANDIDATE_ACTIVE"
    signal_intake = {
        "payload_version": "SHADOW_CANDIDATE_UNIVERSE_01_SIGNAL_INTAKE_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "intake_status": intake_status,
        "candidate_count": len(active_signal_candidates),
        "blocked_candidate_count": 0,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "source_brain4_payload": {
            "payload_version": source_payload.get("payload_version"),
            "created_utc": source_payload.get("created_utc"),
            "active_match_count": (source_payload.get("registry_summary") or {}).get("active_match_count"),
            "memory_count": (source_payload.get("registry_summary") or {}).get("memory_count"),
        },
        "candidates": active_signal_candidates,
        "blocked_candidates": [],
        "global_boundary": BOUNDARY,
    }

    current = {
        "payload_version": VERSION,
        "created_utc": created,
        "authority": AUTHORITY,
        "registry_version": registry.get("registry_version"),
        "source_payload_created_utc": source_payload.get("created_utc"),
        "source_payload_version": source_payload.get("payload_version"),
        "summary": {
            "candidate_spec_count": len(registry.get("candidates") or []),
            "surface_count": len(surfaces),
            "active_shadow_candidate_count": len(active),
            "near_miss_count": len(near),
            "status_counts": dict(status_counts),
            "active_by_family": dict(family_counts),
            "active_by_instrument": dict(inst_counts),
            "state_refresh_count": len(state.get("refresh_history", []) or []),
            "state_active_event_count": len(state.get("active_event_ledger", []) or []),
        },
        "active_candidates": active[:MAX_EXAMPLES],
        "near_miss_examples": near[:MAX_EXAMPLES],
        "boundary": BOUNDARY,
        "plain_language_fa": "کاندیدهای این فایل فقط برای افزایش observation پژوهشی هستند و در صفحه اصلی پنل نباید به عنوان event یا سیگنال دیده شوند.",
    }
    eval_payload = {
        "payload_version": "SHADOW_CANDIDATE_UNIVERSE_01_EVALUATIONS_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "row_count": len(evaluations),
        "rows": evaluations,
        "boundary": BOUNDARY,
    }
    summary = {
        "summary_version": "SHADOW_CANDIDATE_UNIVERSE_01_SUMMARY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "candidate_spec_count": len(registry.get("candidates") or []),
        "active_shadow_candidate_count": len(active),
        "near_miss_count": len(near),
        "status_counts": dict(status_counts),
        "active_candidate_ids": [e.get("candidate_id") for e in active],
        "near_miss_candidate_ids": [e.get("candidate_id") for e in near[:50]],
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "boundary": BOUNDARY,
    }
    review_pack = build_review_pack(state, current, evaluations, created)

    # State and runtime outputs.
    write_json(state_path, state)
    write_json(RUNTIME_DIR / "shadow_candidate_universe_current.json", current)
    write_json(RUNTIME_DIR / "shadow_candidate_universe_evaluations_current.json", eval_payload)
    write_json(RUNTIME_DIR / "shadow_candidate_universe_summary_current.json", summary)
    write_json(RUNTIME_DIR / "shadow_candidate_universe_signal_intake_current.json", signal_intake)
    write_json(RUNTIME_DIR / "shadow_candidate_universe_review_pack_current.json", review_pack)

    # Static panel/debug outputs. These are hidden from main UI unless a future debug panel reads them.
    write_json(PANEL_DIR / "shadow_candidate_universe_current.json", current)
    write_json(PANEL_DIR / "shadow_candidate_universe_evaluations_current.json", eval_payload)
    write_json(PANEL_DIR / "shadow_candidate_universe_summary_current.json", summary)
    write_json(PANEL_DIR / "shadow_candidate_universe_review_pack_current.json", review_pack)

    # Proof/report under outputs (not staged by safe commit, but useful locally/actions logs).
    write_json(OUTPUT_DIR / "shadow_candidate_universe_01_build_result.json", {
        "status": "SHADOW_CANDIDATE_UNIVERSE_01_BUILT",
        "created_utc": created,
        "candidate_spec_count": len(registry.get("candidates") or []),
        "active_shadow_candidate_count": len(active),
        "near_miss_count": len(near),
        "status_counts": dict(status_counts),
        "boundary": BOUNDARY,
    })

    print(json.dumps({
        "status": "SHADOW_CANDIDATE_UNIVERSE_01_BUILT",
        "candidate_spec_count": len(registry.get("candidates") or []),
        "active_shadow_candidate_count": len(active),
        "near_miss_count": len(near),
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
