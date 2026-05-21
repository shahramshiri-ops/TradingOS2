#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRADINGOS_SHADOW_CANDIDATE_OUTCOME_BASELINE_01

Builds a research-only outcome/baseline layer for SHADOW_CANDIDATE_UNIVERSE_01.

Purpose:
- Convert shadow-only candidate activations into stable forward-observation subjects.
- Close H1+1/H1+2/H1+4/H1+8 outcomes when future closed H1 bars are available.
- Build same-instrument / same-session / same-direction control baselines from closed H1 bars.
- Maintain denominators for all shadow candidates: evaluated, active, near-miss, not-triggered, input-insufficient/data-blocked.
- Produce conservative promotion-review readiness reports without promoting anything automatically.

Hard boundaries:
DISPLAY_ONLY / RESEARCH_SHADOW_ONLY / NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET /
NO_POSITION_SIZE / NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE / NO_MEMORY_PROMOTION.

This script does not create memories, signals, orders, PnL, targets, stops, or broker actions.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Tuple
import csv
import gzip
import hashlib
import json
import math
import os
import subprocess

VERSION = "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_v1_0"
STATE_VERSION = "SHADOW_CANDIDATE_OUTCOME_BASELINE_STATE_v1_0"
ROOT = Path.cwd()
PANEL = ROOT / "panel" / "brain4"
STATE_DIR = ROOT / "state" / "shadow_candidate_outcome_baseline"
RUNTIME_DIR = ROOT / "runtime" / "sig_shadow_candidate_outcome_baseline"
OUTPUT_DIR = ROOT / "outputs" / "_shadow_candidate_outcome_baseline_01"
PROOFS = ROOT / "proofs"

HORIZON_STEPS = [1, 2, 4, 8]
HORIZONS = [f"H1+{h}" for h in HORIZON_STEPS]
MAX_REFRESH_HISTORY = 5000
MAX_SUBJECTS = 10000
MAX_BASELINE_EXAMPLES = 20
MAX_SEEN_REFRESHES = 10000

BOUNDARY = {
    "display_only": True,
    "research_shadow_only": True,
    "active_memory_authorized": False,
    "memory_promotion_authorized": False,
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "buy_sell_recommendation_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "entry_stop_target_authorized": False,
    "position_size_authorized": False,
    "profitability_claim_authorized": False,
    "pnl_claim_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "plain_language_fa": (
        "این لایه فقط outcome و baseline پژوهشی برای کاندیدهای shadow-only ثبت می‌کند؛ memory رسمی، سیگنال، "
        "خرید/فروش، ورود/خروج، حدضرر/هدف، سودآوری، PnL، اجرای معامله یا تغییر خودکار قانون نیست."
    ),
}

AUTHORITY = (
    "SHADOW_CANDIDATE_OUTCOME_BASELINE_01|RESEARCH_SHADOW_ONLY|OUTCOME_BASELINE_OBSERVATION|"
    "NOT_SIGNAL|NO_BUY_SELL|NO_ENTRY_STOP_TARGET|NO_POSITION_SIZE|NO_BROKER_EXECUTION|"
    "NO_AUTO_LEARNING|NO_RULE_REWRITE|NO_MEMORY_PROMOTION"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(x: Any) -> Optional[datetime]:
    if x in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def ts_out(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(*parts: Any, length: int = 20) -> str:
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


def fnum(x: Any) -> Optional[float]:
    try:
        if x in (None, ""):
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def run_git(args: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(["git"] + args, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def bar_ts(row: Dict[str, Any]) -> str:
    for k in (
        "bar_open_ts_utc", "timestamp_utc", "ts_utc", "datetime_utc", "time_utc",
        "timestamp", "datetime", "time", "date",
    ):
        if row.get(k):
            return str(row.get(k))
    return ""


def price(row: Dict[str, Any], key: str) -> Optional[float]:
    candidates = [
        key, key.lower(), key.upper(),
        f"h1_{key.lower()}", f"H1_{key.upper()}",
        {"open": "o", "high": "h", "low": "l", "close": "c"}.get(key.lower(), key),
    ]
    for k in candidates:
        if k and k in row:
            v = fnum(row.get(k))
            if v is not None:
                return v
    return None


def read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix == ".gz":
        fh = gzip.open(path, "rt", encoding="utf-8", errors="ignore", newline="")
    else:
        fh = path.open("r", encoding="utf-8-sig", errors="ignore", newline="")
    with fh:
        return list(csv.DictReader(fh))


def read_h1_bars(instrument: str) -> List[Dict[str, Any]]:
    inst = str(instrument or "").upper()
    candidates = [
        ROOT / "runtime" / "sig_shadow" / "price_bridge_h1" / f"{inst}_H1.csv",
        ROOT / "runtime" / "sig_shadow" / "price_bridge_h1" / f"{inst}_H1.csv.gz",
        ROOT / "data" / "live_resampled" / f"{inst}_H1_from_M5.csv.gz",
        ROOT / "data" / "live_resampled" / f"{inst}_H1.csv.gz",
        ROOT / "data" / "live_resampled" / f"{inst}_H1_from_M5.csv",
        ROOT / "data" / "live_resampled" / f"{inst}_H1.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return []
    raw = read_csv_rows(path)
    parsed: List[Tuple[datetime, Dict[str, Any]]] = []
    for r in raw:
        t = parse_ts(bar_ts(r))
        if t is None:
            continue
        # Keep only rows with at least close; open/high/low fallback later if missing.
        if price(r, "close") is None:
            continue
        parsed.append((t, r))
    parsed.sort(key=lambda x: x[0])
    return [r for _, r in parsed]


def session_bucket_from_ts(ts: Any) -> str:
    dt = parse_ts(ts)
    if dt is None:
        return "UNKNOWN_SESSION"
    h = dt.hour
    if 0 <= h <= 6:
        return "ASIA"
    if 7 <= h <= 11:
        return "LONDON"
    if 12 <= h <= 15:
        return "LONDON_NY_OVERLAP"
    if 16 <= h <= 20:
        return "NEW_YORK"
    return "ROLLOVER_THIN_LIQUIDITY"


def neutral_pct_threshold(instrument: str) -> float:
    # Research-only neutral band to avoid counting a microscopic close change as meaningful.
    inst = str(instrument or "").upper()
    if inst == "XAUUSD":
        return 0.0025
    return 0.0015


def direction_side(direction: str) -> str:
    d = str(direction or "").upper()
    if d.startswith("LONG") or d in {"BUY", "BULLISH"}:
        return "LONG"
    if d.startswith("SHORT") or d in {"SELL", "BEARISH"}:
        return "SHORT"
    return "UNKNOWN"


def compute_path_from_anchor(
    *,
    instrument: str,
    direction: str,
    ref_price: Optional[float],
    future_rows: List[Dict[str, Any]],
    horizon_steps: Iterable[int] = HORIZON_STEPS,
) -> Dict[str, Dict[str, Any]]:
    side = direction_side(direction)
    out: Dict[str, Dict[str, Any]] = {}
    if ref_price is None or ref_price == 0:
        for h in horizon_steps:
            out[f"H1+{h}"] = {"completion_status": "NOT_OBSERVABLE", "reason_code": "REFERENCE_PRICE_UNAVAILABLE"}
        return out

    eps_pct = neutral_pct_threshold(instrument)
    for h in horizon_steps:
        hz = f"H1+{h}"
        if len(future_rows) < h:
            out[hz] = {
                "completion_status": "PENDING",
                "reason_code": "PENDING_FUTURE_H1_BARS",
                "available_future_h1_bars": len(future_rows),
                "required_future_h1_bars": h,
            }
            continue
        rows = future_rows[:h]
        highs = [price(r, "high") for r in rows]
        lows = [price(r, "low") for r in rows]
        closes = [price(r, "close") for r in rows]
        highs = [x for x in highs if x is not None]
        lows = [x for x in lows if x is not None]
        closes = [x for x in closes if x is not None]
        if not highs or not lows or not closes:
            out[hz] = {"completion_status": "NOT_OBSERVABLE", "reason_code": "PRICE_DATA_INCOMPLETE"}
            continue

        if side == "LONG":
            favorable = max(highs) - ref_price
            adverse = ref_price - min(lows)
            close_move = closes[-1] - ref_price
        elif side == "SHORT":
            favorable = ref_price - min(lows)
            adverse = max(highs) - ref_price
            close_move = ref_price - closes[-1]
        else:
            favorable = None
            adverse = None
            close_move = None

        pct = (close_move / ref_price * 100.0) if close_move is not None and ref_price else None
        if pct is None:
            label = "UNKNOWN_DIRECTION"
        elif pct > eps_pct:
            label = "FAVORABLE_CLOSE_MOVE"
        elif pct < -eps_pct:
            label = "ADVERSE_CLOSE_MOVE"
        else:
            label = "NEUTRAL_CLOSE_MOVE"

        end_ts = bar_ts(rows[-1])
        out[hz] = {
            "completion_status": "COMPLETE",
            "reference_price_observation_only": ref_price,
            "horizon_end_bar_open_ts_utc": end_ts,
            "future_h1_bar_count": h,
            "max_favorable_excursion_price_units": favorable,
            "max_adverse_excursion_price_units": adverse,
            "directional_close_move_price_units": close_move,
            "directional_close_move_pct": pct,
            "directional_outcome_label": label,
            "metrics_are_pnl": False,
            "pnl_claim": False,
            "profitability_claim": False,
        }
    return out


def future_rows_after(bars: List[Dict[str, Any]], trigger_ts: Any) -> List[Dict[str, Any]]:
    t0 = parse_ts(trigger_ts)
    if t0 is None:
        return []
    out = []
    for r in bars:
        t = parse_ts(bar_ts(r))
        if t is not None and t > t0:
            out.append(r)
    return out


def find_trigger_close(bars: List[Dict[str, Any]], trigger_ts: Any) -> Optional[float]:
    t0 = parse_ts(trigger_ts)
    if t0 is None:
        return None
    for r in bars:
        t = parse_ts(bar_ts(r))
        if t == t0:
            return price(r, "close")
    return None


def compute_baseline_controls(
    *,
    instrument: str,
    direction: str,
    session_bucket: str,
    bars: List[Dict[str, Any]],
    exclude_trigger_ts: Any = None,
) -> Dict[str, Any]:
    side = direction_side(direction)
    if not bars:
        return {
            "baseline_status": "BASELINE_DATA_UNAVAILABLE",
            "baseline_method": "same_instrument_same_session_same_direction_closed_H1_controls",
            "control_anchor_count": 0,
            "horizons": {},
            "metrics_are_pnl": False,
        }

    exclude_dt = parse_ts(exclude_trigger_ts)
    controls_by_h: Dict[str, List[Dict[str, Any]]] = {f"H1+{h}": [] for h in HORIZON_STEPS}
    parsed = [(parse_ts(bar_ts(r)), r) for r in bars]
    parsed = [(t, r) for t, r in parsed if t is not None]
    for idx, (t, r) in enumerate(parsed):
        if exclude_dt is not None and t == exclude_dt:
            continue
        if session_bucket != "UNKNOWN_SESSION" and session_bucket_from_ts(ts_out(t)) != session_bucket:
            continue
        ref = price(r, "close")
        if ref is None:
            continue
        future = [rr for _, rr in parsed[idx + 1:]]
        path = compute_path_from_anchor(instrument=instrument, direction=side, ref_price=ref, future_rows=future)
        for hz, hr in path.items():
            if hr.get("completion_status") == "COMPLETE":
                controls_by_h[hz].append(hr)

    horizon_summary: Dict[str, Any] = {}
    all_anchor_count = 0
    for hz, rows in controls_by_h.items():
        all_anchor_count = max(all_anchor_count, len(rows))
        counts = Counter(str(x.get("directional_outcome_label") or "UNKNOWN") for x in rows)
        moves = [fnum(x.get("directional_close_move_pct")) for x in rows]
        moves = [x for x in moves if x is not None]
        n = len(rows)
        horizon_summary[hz] = {
            "control_count": n,
            "favorable_rate": (counts.get("FAVORABLE_CLOSE_MOVE", 0) / n) if n else None,
            "adverse_rate": (counts.get("ADVERSE_CLOSE_MOVE", 0) / n) if n else None,
            "neutral_rate": (counts.get("NEUTRAL_CLOSE_MOVE", 0) / n) if n else None,
            "median_directional_close_move_pct": median(moves) if moves else None,
            "avg_directional_close_move_pct": mean(moves) if moves else None,
            "outcome_counts": dict(counts),
            "baseline_pnl_claim": False,
            "baseline_signal_claim": False,
        }

    if all_anchor_count == 0:
        status = "BASELINE_NO_MATCHING_CONTROL_ANCHORS"
    elif all_anchor_count < 20:
        status = "BASELINE_UNDERPOWERED_CONTROL_SAMPLE"
    else:
        status = "BASELINE_READY_FOR_RESEARCH_COMPARISON"

    return {
        "baseline_status": status,
        "baseline_method": "same_instrument_same_session_same_direction_closed_H1_controls",
        "instrument": instrument,
        "direction_side": side,
        "session_bucket": session_bucket,
        "control_anchor_count": all_anchor_count,
        "horizons": horizon_summary,
        "metrics_are_pnl": False,
        "profitability_claim": False,
    }


def initialize_state(created: str) -> Dict[str, Any]:
    return {
        "state_version": STATE_VERSION,
        "created_utc": created,
        "updated_utc": created,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "processed_evaluation_refreshes": [],
        "refresh_history": [],
        "candidate_denominator_rollup": {},
        "subjects": {},
        "candidate_outcome_rollup": {},
        "candidate_review_status": {},
        "baseline_method": "same_instrument_same_session_same_direction_closed_H1_controls",
    }


def load_state(created: str) -> Dict[str, Any]:
    state = read_json(STATE_DIR / "shadow_candidate_outcome_baseline_state_v1.json", None)
    if not isinstance(state, dict) or state.get("state_version") != STATE_VERSION:
        return initialize_state(created)
    state.setdefault("boundary", BOUNDARY)
    state.setdefault("processed_evaluation_refreshes", [])
    state.setdefault("refresh_history", [])
    state.setdefault("candidate_denominator_rollup", {})
    state.setdefault("subjects", {})
    state.setdefault("candidate_outcome_rollup", {})
    state.setdefault("candidate_review_status", {})
    return state


def status_bucket_from_eval(row: Dict[str, Any]) -> str:
    st = str(row.get("evaluation_status") or "UNKNOWN")
    if row.get("is_shadow_active") or st == "SHADOW_CANDIDATE_ACTIVE":
        return "ACTIVE"
    if row.get("is_near_miss") or st == "SHADOW_CANDIDATE_NEAR_MISS":
        return "NEAR_MISS"
    if int(row.get("missing_field_count") or 0) > 0:
        return "INPUT_INSUFFICIENT"
    if st in {"DATA_STALE", "DATA_OR_CONTEXT_NOT_READY"}:
        return "DATA_QUALITY_BLOCKED"
    if st == "NOT_TRIGGERED":
        return "NOT_TRIGGERED"
    return st


def update_denominators(state: Dict[str, Any], eval_payload: Dict[str, Any], created: str) -> Dict[str, Any]:
    eval_created = eval_payload.get("created_utc") or created
    rows = as_list(eval_payload.get("rows"))
    already = eval_created in set(as_list(state.get("processed_evaluation_refreshes")))
    status_counts = Counter()
    if not already:
        for row in rows:
            cid = str(row.get("candidate_id") or "UNKNOWN_CANDIDATE")
            bucket = status_bucket_from_eval(row)
            status_counts[bucket] += 1
            rec = state["candidate_denominator_rollup"].setdefault(cid, {
                "source_candidate_id": cid,
                "candidate_family": row.get("candidate_family"),
                "instrument": row.get("instrument"),
                "timeframe": row.get("timeframe"),
                "directional_bias": row.get("directional_bias"),
                "evaluated_refresh_count": 0,
                "active_refresh_count": 0,
                "near_miss_refresh_count": 0,
                "not_triggered_refresh_count": 0,
                "input_insufficient_refresh_count": 0,
                "data_quality_blocked_refresh_count": 0,
                "status_counts": {},
                "first_seen_utc": eval_created,
                "last_seen_utc": eval_created,
            })
            rec["last_seen_utc"] = eval_created
            rec["evaluated_refresh_count"] = int(rec.get("evaluated_refresh_count") or 0) + 1
            if bucket == "ACTIVE":
                rec["active_refresh_count"] = int(rec.get("active_refresh_count") or 0) + 1
            elif bucket == "NEAR_MISS":
                rec["near_miss_refresh_count"] = int(rec.get("near_miss_refresh_count") or 0) + 1
            elif bucket == "NOT_TRIGGERED":
                rec["not_triggered_refresh_count"] = int(rec.get("not_triggered_refresh_count") or 0) + 1
            elif bucket == "INPUT_INSUFFICIENT":
                rec["input_insufficient_refresh_count"] = int(rec.get("input_insufficient_refresh_count") or 0) + 1
            elif bucket == "DATA_QUALITY_BLOCKED":
                rec["data_quality_blocked_refresh_count"] = int(rec.get("data_quality_blocked_refresh_count") or 0) + 1
            sc = rec.setdefault("status_counts", {})
            sc[bucket] = int(sc.get(bucket) or 0) + 1
        processed = as_list(state.get("processed_evaluation_refreshes"))
        processed.append(eval_created)
        state["processed_evaluation_refreshes"] = processed[-MAX_SEEN_REFRESHES:]
    else:
        for row in rows:
            status_counts[status_bucket_from_eval(row)] += 1
    return {"already_processed": already, "status_counts": dict(status_counts), "row_count": len(rows), "eval_created_utc": eval_created}


def build_subject_from_intake(c: Dict[str, Any], bars: List[Dict[str, Any]], created: str) -> Dict[str, Any]:
    source_cid = c.get("source_candidate_id") or c.get("candidate_id")
    runtime_cid = c.get("candidate_id")
    trigger_ts = c.get("trigger_bar_open_ts_utc")
    event_id = c.get("source_shadow_event_id") or "SCOB_EVT_" + stable_hash(source_cid, trigger_ts, runtime_cid)
    ctx = as_dict(c.get("latest_context_excerpt"))
    session = ctx.get("session_bucket") or session_bucket_from_ts(trigger_ts)
    inst = str(c.get("instrument") or ctx.get("instrument") or "UNKNOWN").upper()
    direction = c.get("directional_bias") or c.get("direction_side") or "UNKNOWN"
    ref = fnum(c.get("observation_reference_price"))
    if ref is None:
        ref = fnum(ctx.get("h1_close"))
    if ref is None:
        ref = find_trigger_close(bars, trigger_ts)
    future = future_rows_after(bars, trigger_ts)
    horizons = compute_path_from_anchor(instrument=inst, direction=direction, ref_price=ref, future_rows=future)
    baseline = compute_baseline_controls(
        instrument=inst,
        direction=direction,
        session_bucket=str(session or "UNKNOWN_SESSION"),
        bars=bars,
        exclude_trigger_ts=trigger_ts,
    )
    complete_count = sum(1 for x in horizons.values() if x.get("completion_status") == "COMPLETE")
    pending_count = sum(1 for x in horizons.values() if x.get("completion_status") == "PENDING")
    not_obs_count = sum(1 for x in horizons.values() if x.get("completion_status") == "NOT_OBSERVABLE")
    if complete_count == len(HORIZONS):
        subject_status = "OUTCOME_COMPLETE"
    elif complete_count > 0 or pending_count > 0:
        subject_status = "OUTCOME_PARTIAL_OR_PENDING"
    else:
        subject_status = "OUTCOME_NOT_OBSERVABLE"
    return {
        "subject_id": event_id,
        "runtime_candidate_id": runtime_cid,
        "source_candidate_id": source_cid,
        "source_candidate_family": c.get("source_candidate_family") or c.get("candidate_family"),
        "candidate_contract_id": c.get("candidate_contract_id"),
        "setup_cluster_id": c.get("setup_cluster_id"),
        "instrument": inst,
        "timeframe": c.get("timeframe") or "H1",
        "directional_bias": direction,
        "direction_side": direction_side(direction),
        "trigger_bar_open_ts_utc": trigger_ts,
        "valid_until_utc": c.get("valid_until_utc"),
        "first_seen_utc": created,
        "last_seen_utc": created,
        "reference_price_observation_only": ref,
        "observation_reference_price_policy": c.get("observation_reference_price_policy"),
        "session_bucket": session,
        "source_payload_created_utc": c.get("source_payload_created_utc"),
        "source_payload_version": c.get("source_payload_version"),
        "context_excerpt": ctx,
        "horizon_results": horizons,
        "baseline_control_snapshot": baseline,
        "subject_status": subject_status,
        "complete_horizon_count": complete_count,
        "pending_horizon_count": pending_count,
        "not_observable_horizon_count": not_obs_count,
        "available_future_h1_bars": len(future),
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
    }


def merge_subject(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> Dict[str, Any]:
    if not prev:
        return cur
    out = dict(prev)
    # Preserve first_seen, update latest context/status. Complete horizons are sticky unless new complete exists.
    out["last_seen_utc"] = cur.get("last_seen_utc")
    out["available_future_h1_bars"] = cur.get("available_future_h1_bars")
    out["subject_status"] = cur.get("subject_status")
    out["pending_horizon_count"] = cur.get("pending_horizon_count")
    out["complete_horizon_count"] = max(int(prev.get("complete_horizon_count") or 0), int(cur.get("complete_horizon_count") or 0))
    out["not_observable_horizon_count"] = cur.get("not_observable_horizon_count")
    out["context_excerpt"] = cur.get("context_excerpt") or prev.get("context_excerpt")
    out["baseline_control_snapshot"] = cur.get("baseline_control_snapshot") or prev.get("baseline_control_snapshot")
    hrs = dict(prev.get("horizon_results") or {})
    for hz, hr in (cur.get("horizon_results") or {}).items():
        if hr.get("completion_status") == "COMPLETE":
            hrs[hz] = hr
        elif hz not in hrs or hrs[hz].get("completion_status") != "COMPLETE":
            hrs[hz] = hr
    out["horizon_results"] = hrs
    complete_count = sum(1 for x in hrs.values() if x.get("completion_status") == "COMPLETE")
    pending_count = sum(1 for x in hrs.values() if x.get("completion_status") == "PENDING")
    out["complete_horizon_count"] = complete_count
    out["pending_horizon_count"] = pending_count
    if complete_count == len(HORIZONS):
        out["subject_status"] = "OUTCOME_COMPLETE"
    elif complete_count > 0 or pending_count > 0:
        out["subject_status"] = "OUTCOME_PARTIAL_OR_PENDING"
    else:
        out["subject_status"] = "OUTCOME_NOT_OBSERVABLE"
    return out


def build_rollups(state: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    subjects = as_dict(state.get("subjects"))
    denom = as_dict(state.get("candidate_denominator_rollup"))
    rollup: Dict[str, Any] = {}
    review: Dict[str, Any] = {}
    rows: List[Dict[str, Any]] = []

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for subj in subjects.values():
        cid = subj.get("source_candidate_id") or "UNKNOWN_CANDIDATE"
        grouped[cid].append(subj)

    all_cids = sorted(set(denom.keys()) | set(grouped.keys()))
    for cid in all_cids:
        ds = denom.get(cid, {})
        subs = grouped.get(cid, [])
        horizon_stats: Dict[str, Any] = {}
        for hz in HORIZONS:
            completed = []
            for s in subs:
                hr = as_dict(as_dict(s.get("horizon_results")).get(hz))
                if hr.get("completion_status") == "COMPLETE":
                    completed.append(hr)
            counts = Counter(str(x.get("directional_outcome_label") or "UNKNOWN") for x in completed)
            n = len(completed)
            base_rates = []
            for s in subs:
                b = as_dict(s.get("baseline_control_snapshot"))
                hzb = as_dict(as_dict(b.get("horizons")).get(hz))
                br = fnum(hzb.get("favorable_rate"))
                if br is not None:
                    base_rates.append(br)
            baseline_fav = mean(base_rates) if base_rates else None
            cand_fav = counts.get("FAVORABLE_CLOSE_MOVE", 0) / n if n else None
            delta = (cand_fav - baseline_fav) if cand_fav is not None and baseline_fav is not None else None
            horizon_stats[hz] = {
                "closed_subject_count": n,
                "favorable_count": counts.get("FAVORABLE_CLOSE_MOVE", 0),
                "adverse_count": counts.get("ADVERSE_CLOSE_MOVE", 0),
                "neutral_count": counts.get("NEUTRAL_CLOSE_MOVE", 0),
                "candidate_favorable_rate": cand_fav,
                "avg_baseline_favorable_rate": baseline_fav,
                "delta_vs_baseline_favorable_rate": delta,
                "outcome_counts": dict(counts),
            }

        closed_h4 = int(horizon_stats.get("H1+4", {}).get("closed_subject_count") or 0)
        closed_h8 = int(horizon_stats.get("H1+8", {}).get("closed_subject_count") or 0)
        active_events = len(subs)
        evaluated = int(ds.get("evaluated_refresh_count") or 0)
        active_refreshes = int(ds.get("active_refresh_count") or 0)
        near_miss_refreshes = int(ds.get("near_miss_refresh_count") or 0)
        data_blocked = int(ds.get("data_quality_blocked_refresh_count") or 0) + int(ds.get("input_insufficient_refresh_count") or 0)
        active_rate = active_refreshes / evaluated if evaluated else None
        near_miss_rate = near_miss_refreshes / evaluated if evaluated else None

        h4_delta = horizon_stats.get("H1+4", {}).get("delta_vs_baseline_favorable_rate")
        h8_delta = horizon_stats.get("H1+8", {}).get("delta_vs_baseline_favorable_rate")
        avg_delta_parts = [x for x in [h4_delta, h8_delta] if x is not None]
        avg_delta = mean(avg_delta_parts) if avg_delta_parts else None

        if active_events == 0:
            review_status = "NO_LIVE_OCCURRENCE_YET"
        elif data_blocked and evaluated and (data_blocked / evaluated) > 0.5:
            review_status = "DATA_QUALITY_BLOCKED"
        elif max(closed_h4, closed_h8) < 10:
            review_status = "UNDERPOWERED_CONTINUE"
        elif avg_delta is not None and avg_delta >= 0.05 and max(closed_h4, closed_h8) >= 20:
            review_status = "PROMOTION_REVIEW_READY_NOT_AUTO_PROMOTED"
        elif active_rate is not None and active_rate > 0.30 and avg_delta is not None and avg_delta < -0.03:
            review_status = "TOO_NOISY_DEMOTE_REVIEW"
        else:
            review_status = "CONTINUE_SHADOW"

        rec = {
            "source_candidate_id": cid,
            "candidate_family": ds.get("candidate_family") or (subs[0].get("source_candidate_family") if subs else None),
            "instrument": ds.get("instrument") or (subs[0].get("instrument") if subs else None),
            "timeframe": ds.get("timeframe") or (subs[0].get("timeframe") if subs else None),
            "directional_bias": ds.get("directional_bias") or (subs[0].get("directional_bias") if subs else None),
            "evaluated_refresh_count": evaluated,
            "active_refresh_count": active_refreshes,
            "near_miss_refresh_count": near_miss_refreshes,
            "not_triggered_refresh_count": int(ds.get("not_triggered_refresh_count") or 0),
            "input_or_data_blocked_refresh_count": data_blocked,
            "active_rate_per_evaluated_refresh": active_rate,
            "near_miss_rate_per_evaluated_refresh": near_miss_rate,
            "unique_active_subject_count": active_events,
            "closed_h1_plus_4_subject_count": closed_h4,
            "closed_h1_plus_8_subject_count": closed_h8,
            "avg_delta_vs_baseline_h1_plus_4_h1_plus_8": avg_delta,
            "horizon_stats": horizon_stats,
            "review_status": review_status,
            "auto_promotion_authorized": False,
            "signal_authorized": False,
            "boundary": BOUNDARY,
        }
        rollup[cid] = rec
        review[cid] = {
            "source_candidate_id": cid,
            "review_status": review_status,
            "reason_summary": {
                "unique_active_subject_count": active_events,
                "closed_h1_plus_4_subject_count": closed_h4,
                "closed_h1_plus_8_subject_count": closed_h8,
                "avg_delta_vs_baseline_h1_plus_4_h1_plus_8": avg_delta,
                "evaluated_refresh_count": evaluated,
                "active_rate_per_evaluated_refresh": active_rate,
            },
            "allowed_next_action": "HUMAN_REVIEW_ONLY_NO_AUTO_PROMOTION",
            "auto_promotion_authorized": False,
            "memory_creation_authorized": False,
            "signal_authorized": False,
        }
        rows.append({k: rec.get(k) for k in [
            "source_candidate_id", "candidate_family", "instrument", "timeframe", "directional_bias",
            "evaluated_refresh_count", "active_refresh_count", "near_miss_refresh_count",
            "unique_active_subject_count", "closed_h1_plus_4_subject_count", "closed_h1_plus_8_subject_count",
            "avg_delta_vs_baseline_h1_plus_4_h1_plus_8", "review_status",
        ]})

    rows.sort(key=lambda r: (str(r.get("review_status")), str(r.get("source_candidate_id"))))
    return rollup, review, rows


def main() -> int:
    created = now_utc()
    state = load_state(created)
    state["updated_utc"] = created
    state["authority"] = AUTHORITY
    state["boundary"] = BOUNDARY

    eval_payload = read_json(PANEL / "shadow_candidate_universe_evaluations_current.json", {})
    if not isinstance(eval_payload, dict) or not eval_payload.get("rows"):
        eval_payload = read_json(RUNTIME_DIR.parent / "sig_shadow_candidate_universe" / "shadow_candidate_universe_evaluations_current.json", {})
    intake_payload = read_json(ROOT / "runtime" / "sig_shadow_candidate_universe" / "shadow_candidate_universe_signal_intake_current.json", {})
    current_payload = read_json(PANEL / "shadow_candidate_universe_current.json", {})

    denom_info = update_denominators(state, eval_payload if isinstance(eval_payload, dict) else {}, created)

    active_candidates = as_list(as_dict(intake_payload).get("candidates"))
    bar_cache: Dict[str, List[Dict[str, Any]]] = {}
    current_subject_ids = []
    data_status_by_inst: Dict[str, Any] = {}
    for c in active_candidates:
        inst = str(c.get("instrument") or "UNKNOWN").upper()
        if inst not in bar_cache:
            bar_cache[inst] = read_h1_bars(inst)
            if bar_cache[inst]:
                data_status_by_inst[inst] = {
                    "h1_bar_count": len(bar_cache[inst]),
                    "first_bar_open_ts_utc": bar_ts(bar_cache[inst][0]),
                    "last_bar_open_ts_utc": bar_ts(bar_cache[inst][-1]),
                    "status": "H1_BARS_AVAILABLE",
                }
            else:
                data_status_by_inst[inst] = {"h1_bar_count": 0, "status": "H1_BARS_UNAVAILABLE"}
        subj = build_subject_from_intake(c, bar_cache[inst], created)
        sid = subj["subject_id"]
        current_subject_ids.append(sid)
        prev = as_dict(state.get("subjects")).get(sid)
        state["subjects"][sid] = merge_subject(prev, subj)

    # Prune very old subjects only if excessive; preserve newest by last_seen/trigger.
    subjects = as_dict(state.get("subjects"))
    if len(subjects) > MAX_SUBJECTS:
        items = sorted(subjects.items(), key=lambda kv: (kv[1].get("last_seen_utc") or "", kv[1].get("trigger_bar_open_ts_utc") or ""))
        state["subjects"] = dict(items[-MAX_SUBJECTS:])

    rollup, review, review_rows = build_rollups(state)
    state["candidate_outcome_rollup"] = rollup
    state["candidate_review_status"] = review

    refresh_record = {
        "refresh_id": "SCOB01_REFRESH_" + stable_hash(created, denom_info.get("eval_created_utc"), len(active_candidates)),
        "created_utc": created,
        "eval_created_utc": denom_info.get("eval_created_utc"),
        "evaluation_row_count": denom_info.get("row_count"),
        "evaluation_status_counts": denom_info.get("status_counts"),
        "evaluation_already_processed": denom_info.get("already_processed"),
        "active_candidate_count_current": len(active_candidates),
        "current_subject_ids": current_subject_ids[:50],
        "h1_data_status_by_instrument": data_status_by_inst,
        "git_sha": run_git(["rev-parse", "--short", "HEAD"]),
        "boundary": BOUNDARY,
    }
    state["refresh_history"] = (as_list(state.get("refresh_history")) + [refresh_record])[-MAX_REFRESH_HISTORY:]

    total_subjects = len(as_dict(state.get("subjects")))
    complete_subjects = sum(1 for s in as_dict(state.get("subjects")).values() if s.get("subject_status") == "OUTCOME_COMPLETE")
    partial_subjects = sum(1 for s in as_dict(state.get("subjects")).values() if s.get("subject_status") == "OUTCOME_PARTIAL_OR_PENDING")
    not_obs_subjects = sum(1 for s in as_dict(state.get("subjects")).values() if s.get("subject_status") == "OUTCOME_NOT_OBSERVABLE")
    review_counts = Counter(str(x.get("review_status")) for x in rollup.values())

    summary = {
        "summary_version": "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_SUMMARY_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "candidate_count_with_denominator": len(state.get("candidate_denominator_rollup", {})),
        "current_active_shadow_candidate_count": len(active_candidates),
        "total_unique_shadow_candidate_subjects": total_subjects,
        "outcome_complete_subject_count": complete_subjects,
        "outcome_partial_or_pending_subject_count": partial_subjects,
        "outcome_not_observable_subject_count": not_obs_subjects,
        "review_status_counts": dict(review_counts.most_common()),
        "h1_data_status_by_instrument": data_status_by_inst,
        "baseline_method": state.get("baseline_method"),
        "signal_authorized": False,
        "memory_promotion_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "boundary": BOUNDARY,
        "plain_language_fa": (
            "این خلاصه نشان می‌دهد کاندیدهای shadow-only بعد از فعال شدن چه outcome پژوهشی گرفته‌اند و baseline کنترلی چیست. "
            "این خروجی memory رسمی یا سیگنال نیست."
        ),
    }

    current_payload_out = {
        "payload_version": VERSION,
        "created_utc": created,
        "authority": AUTHORITY,
        "source_universe_payload_version": current_payload.get("payload_version"),
        "source_universe_created_utc": current_payload.get("created_utc"),
        "summary": summary,
        "current_refresh": refresh_record,
        "current_active_subjects": [state["subjects"][sid] for sid in current_subject_ids if sid in state["subjects"]],
        "candidate_rollup": rollup,
        "boundary": BOUNDARY,
    }

    review_pack = {
        "payload_version": "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_REVIEW_PACK_v1_0",
        "created_utc": created,
        "authority": AUTHORITY,
        "summary": summary,
        "review_rows": review_rows,
        "review_status_by_candidate": review,
        "decision_boundary": {
            "human_review_required": True,
            "auto_promotion_authorized": False,
            "memory_creation_authorized": False,
            "signal_authorized": False,
            "broker_execution_authorized": False,
            "entry_stop_target_authorized": False,
        },
        "recommended_use_fa": (
            "بعد از چند هفته/ماه، این review pack را برای تصمیم انسانی درباره ادامه shadow، park، demote یا طراحی برنامه promotion review استفاده کن. "
            "هیچ کاندیدی خودکار به memory یا signal تبدیل نمی‌شود."
        ),
        "boundary": BOUNDARY,
    }

    # Write persistent state and current payloads.
    write_json(STATE_DIR / "shadow_candidate_outcome_baseline_state_v1.json", state)
    write_json(RUNTIME_DIR / "shadow_candidate_outcome_baseline_current.json", current_payload_out)
    write_json(RUNTIME_DIR / "shadow_candidate_outcome_baseline_summary_current.json", summary)
    write_json(RUNTIME_DIR / "shadow_candidate_promotion_review_current.json", review_pack)
    write_json(PANEL / "shadow_candidate_outcome_baseline_summary_current.json", summary)
    write_json(PANEL / "shadow_candidate_outcome_baseline_current.json", current_payload_out)
    write_json(PANEL / "shadow_candidate_promotion_review_current.json", review_pack)
    write_json(PANEL / "shadow_candidate_outcome_baseline_research_pack_current.json", review_pack)
    write_json(OUTPUT_DIR / "shadow_candidate_outcome_baseline_01_build_result.json", {
        "status": "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_BUILT",
        "created_utc": created,
        "summary": summary,
        "boundary": BOUNDARY,
    })

    print(json.dumps({
        "status": "SHADOW_CANDIDATE_OUTCOME_BASELINE_01_BUILT",
        "current_active_shadow_candidate_count": len(active_candidates),
        "total_unique_shadow_candidate_subjects": total_subjects,
        "outcome_complete_subject_count": complete_subjects,
        "review_status_counts": dict(review_counts.most_common()),
        "signal_authorized": False,
        "memory_promotion_authorized": False,
        "broker_execution_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
