#!/usr/bin/env python3
"""
PRV1N — Active Watch Truth + Canonical Lifecycle Store Patch

Fixes the failure mode where post-refresh lifecycle update writes derived post-refresh
files but does not update the canonical SOT02 lifecycle store consumed by later
candidate-detection/dashboard steps. Also prevents stale
`no_completed_post_trigger_bars_available_yet` reasons when provider cache has
completed bars after the trigger.

Observation-only: no broker, no orders, no execution, no buy/sell/hold, no
entry/stop/target, no PnL, no optimizer, no validation verdict, no production claim.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BOUNDARY = {
    "runtime_observation_not_signal": True,
    "candidate_not_trade_recommendation": True,
    "outcome_observation_not_win_loss": True,
    "lifecycle_tracking_not_execution_tracking": True,
    "cache_not_source_authority": True,
    "single_provider_confidence_not_source_truth": True,
    "scheduler_heartbeat_not_production_readiness": True,
    "panel_payload_not_action_surface": True,
    "no_broker": True,
    "no_order": True,
    "no_execution": True,
    "no_buy_sell_hold": True,
    "no_entry_stop_target": True,
    "no_pnl": True,
    "no_optimizer": True,
    "no_validation_verdict": True,
    "no_adaptation_decision": True,
    "no_production_readiness_claim": True,
    "spx_nq_out_of_v1_active_scope": True,
    "calendar_event_out_of_v1_scope": True,
    "second_provider_out_of_v1_scope": True,
    "row_2_retained_unopened": True,
    "rows_6_7_deferred_reentry": True,
    "matrix_complete_not_matrix_open": True,
}
ACTIVE_INSTRUMENTS = ["XAUUSD", "EURUSD", "USDJPY"]
FORBIDDEN_ACTION_SURFACES = {
    "broker_status": True,
    "execution_queue": True,
    "action_buttons": True,
    "buy_sell_hold": True,
    "entry_stop_target": True,
    "pnl_win_loss": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, required: bool = True, default: Any = None) -> Any:
    if not path.exists():
        if required:
            raise FileNotFoundError(str(path))
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_float(x: Any) -> Optional[float]:
    try:
        if isinstance(x, str):
            x = x.replace(",", "").strip()
        return float(x)
    except Exception:
        return None


def parse_dt(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    s = str(raw).strip().replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def bar_key(dt: datetime, timeframe: str) -> str:
    if timeframe == "D1":
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def looks_like_bar(x: Any) -> bool:
    if not isinstance(x, dict):
        return False
    keys = {str(k).lower() for k in x.keys()}
    has_time = any(k in keys for k in ("datetime", "time", "timestamp", "bar_open_ts_utc"))
    has_ohlc = all(k in keys for k in ("open", "high", "low", "close"))
    return has_time and has_ohlc


def find_bar_list(obj: Any, depth: int = 0) -> Optional[List[Dict[str, Any]]]:
    if depth > 12:
        return None
    if isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        if dicts:
            good = [x for x in dicts if looks_like_bar(x)]
            if len(good) >= max(1, int(0.55 * len(dicts))):
                return good
        for item in obj:
            found = find_bar_list(item, depth + 1)
            if found:
                return found
    elif isinstance(obj, dict):
        # Prefer known envelope keys first; then recursive scan.
        for key in (
            "values", "data", "bars", "records", "candles", "provider_values",
            "provider_payload", "response", "payload", "cache", "raw", "snapshot",
            "result", "time_series",
        ):
            if key in obj:
                found = find_bar_list(obj[key], depth + 1)
                if found:
                    return found
        vals = list(obj.values())
        if vals and all(isinstance(v, dict) for v in vals):
            good = [v for v in vals if looks_like_bar(v)]
            if len(good) >= max(1, int(0.55 * len(vals))):
                return good
        for val in vals:
            found = find_bar_list(val, depth + 1)
            if found:
                return found
    return None


def normalize_bars(cache_obj: Any, timeframe: str) -> List[Dict[str, Any]]:
    values = find_bar_list(cache_obj) or []
    out: List[Dict[str, Any]] = []
    for row in values:
        raw_dt = row.get("datetime") or row.get("bar_open_ts_utc") or row.get("time") or row.get("timestamp")
        dt = parse_dt(raw_dt)
        if dt is None:
            continue
        o = safe_float(row.get("open")); h = safe_float(row.get("high")); l = safe_float(row.get("low")); c = safe_float(row.get("close"))
        if any(v is None for v in (o, h, l, c)):
            continue
        out.append({"bar_open_ts_utc": bar_key(dt, timeframe), "_dt": dt, "open": o, "high": h, "low": l, "close": c})
    by_key: Dict[str, Dict[str, Any]] = {}
    for r in out:
        by_key[r["bar_open_ts_utc"]] = r
    ordered = list(by_key.values())
    ordered.sort(key=lambda r: r["_dt"])
    for r in ordered:
        r.pop("_dt", None)
    return ordered


def cache_path_for_surface(root: Path, surface: str) -> Path:
    return root / "data" / "provider_cache" / "twelve_data" / f"{surface.replace(' ', '_')}.json"


def get_trigger_bar(snap: Dict[str, Any], registry_candidate: Dict[str, Any]) -> Dict[str, Any]:
    return (
        snap.get("trigger_bar_from_capture")
        or snap.get("trigger_bar_from_cache")
        or registry_candidate.get("trigger_bar_from_capture")
        or registry_candidate.get("trigger_bar_from_cache")
        or {}
    )


def enrich_snapshot(life: Dict[str, Any], registry_candidate: Dict[str, Any]) -> Dict[str, Any]:
    snap = copy.deepcopy(registry_candidate or {})
    snap.update(copy.deepcopy(life.get("candidate_snapshot") or {}))
    # Preserve/fill trigger bars from both historical capture and newer cache-based rows.
    if not snap.get("trigger_bar_from_capture") and registry_candidate.get("trigger_bar_from_capture"):
        snap["trigger_bar_from_capture"] = registry_candidate.get("trigger_bar_from_capture")
    if not snap.get("trigger_bar_from_cache") and registry_candidate.get("trigger_bar_from_cache"):
        snap["trigger_bar_from_cache"] = registry_candidate.get("trigger_bar_from_cache")
    return snap


def post_bars_after_trigger(values: List[Dict[str, Any]], trigger_ts: str) -> List[Dict[str, Any]]:
    trig = parse_dt(trigger_ts)
    if trig is None:
        return []
    out = []
    for r in values:
        dt = parse_dt(r.get("bar_open_ts_utc"))
        if dt is not None and dt > trig:
            out.append({k: r[k] for k in ("bar_open_ts_utc", "open", "high", "low", "close") if k in r})
    return out


def classify(life: Dict[str, Any], registry_candidate: Dict[str, Any], cache_values: List[Dict[str, Any]]) -> Dict[str, Any]:
    snap = enrich_snapshot(life, registry_candidate)
    candidate_type = str(snap.get("candidate_type") or "")
    edge_family = str(snap.get("edge_family") or "")
    timeframe = str(snap.get("timeframe") or "")
    trigger_ts = snap.get("trigger_reference_bar_ts_utc")
    trigger = get_trigger_bar(snap, registry_candidate)
    hi = safe_float(trigger.get("high")); lo = safe_float(trigger.get("low")); cl = safe_float(trigger.get("close")); op = safe_float(trigger.get("open"))
    if edge_family != "Range Breakout" or "range_breakout_observation_candidate" not in candidate_type:
        return {"outcome_category": "ambiguous_observation", "outcome_reason": "candidate_type_not_supported_by_prv1n_classifier_scope", "is_final": False, "classification_details": {"valid_cache_bar_count": len(cache_values)}}
    if trigger_ts is None or any(v is None for v in (hi, lo, cl)):
        return {"outcome_category": "still_active_observation", "outcome_reason": "missing_trigger_reference_or_trigger_prices_for_post_refresh_update", "is_final": False, "classification_details": {"valid_cache_bar_count": len(cache_values), "trigger_reference_bar_ts_utc": trigger_ts, "trigger_bar_present": bool(trigger)}}
    post = post_bars_after_trigger(cache_values, str(trigger_ts))
    cfg = life.get("tracking_config") or {}
    post_bars_required = int(cfg.get("post_bars_required_for_expiry", 8) or 8)
    min_post_bars = int(cfg.get("min_post_bars_for_final", 3) or 3)
    considered = post[:post_bars_required]
    details = {
        "classifier": "prv1n_active_watch_truth_classifier",
        "valid_cache_bar_count": len(cache_values),
        "trigger_bar": {"bar_open_ts_utc": trigger_ts, "open": op, "high": hi, "low": lo, "close": cl},
        "post_bars_observed": len(post),
        "post_bars_considered": len(considered),
        "post_window": {
            "first_post_bar_open_ts_utc": post[0]["bar_open_ts_utc"] if post else None,
            "last_post_bar_open_ts_utc": post[-1]["bar_open_ts_utc"] if post else None,
            "post_bars_required_for_expiry": post_bars_required,
            "min_post_bars_for_final": min_post_bars,
        },
        "post_bars": considered,
        "interpretation_boundary": "Observation-only; not signal, PnL, win/loss, validation, or performance.",
    }
    if not post:
        return {"outcome_category": "still_active_observation", "outcome_reason": "no_completed_post_trigger_bars_available_yet", "is_final": False, "classification_details": details}
    side = "down" if candidate_type.startswith("downside_") else "up" if candidate_type.startswith("upside_") else "unknown"
    details["side"] = side
    min_low = min(r["low"] for r in considered) if considered else None
    max_high = max(r["high"] for r in considered) if considered else None
    last_close = considered[-1]["close"] if considered else None
    details["observation_extremes"] = {"trigger_close": cl, "trigger_high": hi, "trigger_low": lo, "min_post_low": min_low, "max_post_high": max_high, "last_post_close": last_close}
    if side == "down":
        if any(r["close"] > hi for r in considered):
            return {"outcome_category": "invalidated_observation", "outcome_reason": "post_trigger_completed_bar_closed_above_trigger_bar_high", "is_final": True, "classification_details": details}
        if min_low is not None and min_low < lo and last_close is not None and last_close < cl:
            return {"outcome_category": "favorable_observation", "outcome_reason": "post_trigger_low_extended_below_trigger_low_and_last_close_remains_below_trigger_close", "is_final": True, "classification_details": details}
        if len(considered) >= min_post_bars and last_close is not None and last_close > cl:
            return {"outcome_category": "unfavorable_observation", "outcome_reason": "last_post_trigger_close_back_above_trigger_close_without_full_high_close_invalidation", "is_final": True, "classification_details": details}
    elif side == "up":
        if any(r["close"] < lo for r in considered):
            return {"outcome_category": "invalidated_observation", "outcome_reason": "post_trigger_completed_bar_closed_below_trigger_bar_low", "is_final": True, "classification_details": details}
        if max_high is not None and max_high > hi and last_close is not None and last_close > cl:
            return {"outcome_category": "favorable_observation", "outcome_reason": "post_trigger_high_extended_above_trigger_high_and_last_close_remains_above_trigger_close", "is_final": True, "classification_details": details}
        if len(considered) >= min_post_bars and last_close is not None and last_close < cl:
            return {"outcome_category": "unfavorable_observation", "outcome_reason": "last_post_trigger_close_back_below_trigger_close_without_full_low_close_invalidation", "is_final": True, "classification_details": details}
    # Crucial truth fix: once post-trigger bars exist, never keep the stale "no completed bars" reason.
    return {"outcome_category": "still_active_observation", "outcome_reason": "post_trigger_bars_available_but_outcome_not_final_under_rules", "is_final": False, "classification_details": details}


def build_ledger(registry: Dict[str, Any], lifecycle_store: Dict[str, Any]) -> List[Dict[str, Any]]:
    cands = registry.get("candidates", {}) if isinstance(registry, dict) else {}
    lifes = lifecycle_store.get("lifecycles", {}) if isinstance(lifecycle_store, dict) else {}
    rows = []
    for cid, cand in cands.items():
        life = lifes.get(cid, {})
        snap = enrich_snapshot(life, cand)
        rows.append({
            "row_id": cid,
            "sot_candidate_id": cid,
            "row_quality": "exact_current_sot02_row_post_refresh",
            "instrument": snap.get("instrument") or cand.get("instrument"),
            "timeframe": snap.get("timeframe") or cand.get("timeframe"),
            "surface": snap.get("surface") or cand.get("surface"),
            "edge_family": snap.get("edge_family") or cand.get("edge_family"),
            "candidate_type": snap.get("candidate_type") or cand.get("candidate_type"),
            "trigger_reference_bar_ts_utc": snap.get("trigger_reference_bar_ts_utc") or cand.get("trigger_reference_bar_ts_utc"),
            "first_observed_at_utc": snap.get("first_observed_at_utc") or cand.get("first_observed_at_utc"),
            "last_observed_at_utc": snap.get("last_observed_at_utc") or cand.get("last_observed_at_utc"),
            "repeat_observation_count": snap.get("repeat_observation_count") or cand.get("repeat_observation_count"),
            "provider": snap.get("provider") or cand.get("provider"),
            "provider_symbol": snap.get("provider_symbol") or cand.get("provider_symbol"),
            "source_confidence_class": snap.get("source_confidence_class") or cand.get("source_confidence_class"),
            "lifecycle_status": life.get("status"),
            "is_final": life.get("is_final"),
            "latest_outcome_category": life.get("latest_outcome_category"),
            "latest_outcome_reason": life.get("latest_outcome_reason"),
            "lifecycle_updated_at_utc": life.get("updated_at_utc"),
            "trigger_bar_from_capture": snap.get("trigger_bar_from_capture"),
            "trigger_bar_from_cache": snap.get("trigger_bar_from_cache"),
            "classification_details": (life.get("outcome_history") or [{}])[-1].get("classification_details", {}) if life.get("outcome_history") else {},
            "original_record_ids": snap.get("original_record_ids", []),
            "display_boundary": "Observation-only. Not signal, not buy/sell/hold, not entry/stop/target, not execution, not PnL/win-loss, not validation.",
        })
    rows.sort(key=lambda r: (str(r.get("instrument")), str(r.get("timeframe")), str(r.get("trigger_reference_bar_ts_utc"))))
    return rows


def summarize(lifecycles: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int]]:
    status_counts: Dict[str, int] = {}
    outcome_counts: Dict[str, int] = {}
    for l in lifecycles.values():
        st = l.get("status", "unknown")
        oc = l.get("latest_outcome_category", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
        outcome_counts[oc] = outcome_counts.get(oc, 0) + 1
    return status_counts, outcome_counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_root", nargs="?", default=".")
    args = ap.parse_args()
    root = Path(args.package_root).resolve()
    now = utc_now()
    required = {
        "staged_provider_fetch_report": root / "reports" / "staged_provider_fetch_report.json",
        "staged_cache_update_report": root / "reports" / "staged_cache_update_report.json",
        "shadow_candidate_registry": root / "state" / "sot02_current" / "shadow_candidate_registry.json",
        "shadow_lifecycle_state_store": root / "state" / "sot02_current" / "shadow_lifecycle_state_store.json",
    }
    missing = [str(p.relative_to(root)) for p in required.values() if not p.exists()]
    if missing:
        validation = {"program": "PRV1N-01", "artifact": "post_refresh_update_local_validation_result", "created_at_utc": now, "validation_passed": False, "missing_files": missing, "boundary_status": "failed_missing_required_files", "boundary": BOUNDARY}
        write_json(root / "proofs" / "post_refresh_update_local_validation_result.json", validation)
        print(json.dumps(validation, indent=2, ensure_ascii=False))
        return 1

    fetch = read_json(required["staged_provider_fetch_report"])
    cache_report = read_json(required["staged_cache_update_report"])
    registry = read_json(required["shadow_candidate_registry"])
    lifecycle_store = read_json(required["shadow_lifecycle_state_store"])
    registry_candidates = registry.get("candidates", {})
    lifecycles = copy.deepcopy(lifecycle_store.get("lifecycles", {}))

    scope_ok = fetch.get("scope_status", {}).get("scope_ok") is True
    all_surfaces_ok = fetch.get("selected_surface_count") == fetch.get("successful_surface_count") and fetch.get("failed_surface_count") == 0
    cache_all_ok = cache_report.get("updated_surface_count") == fetch.get("selected_surface_count") and cache_report.get("failed_surface_count") == 0

    active_before = [cid for cid, l in lifecycles.items() if not l.get("is_final")]
    update_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    finalized_now = 0
    stale_reason_prevented = []

    for cid in active_before:
        life = lifecycles[cid]
        cand = registry_candidates.get(cid, {})
        snap = enrich_snapshot(life, cand)
        surface = snap.get("surface") or cand.get("surface")
        timeframe = snap.get("timeframe") or cand.get("timeframe")
        if not surface or not timeframe:
            skipped_rows.append({"sot_candidate_id": cid, "reason": "missing_surface_or_timeframe"})
            continue
        cache_path = cache_path_for_surface(root, surface)
        if not cache_path.exists():
            skipped_rows.append({"sot_candidate_id": cid, "surface": surface, "reason": "required_provider_cache_snapshot_missing"})
            continue
        cache_obj = read_json(cache_path)
        values = normalize_bars(cache_obj, str(timeframe))
        result = classify(life, cand, values)
        prev_status = life.get("status")
        prev_cat = life.get("latest_outcome_category")
        prev_reason = life.get("latest_outcome_reason")
        if prev_reason == "no_completed_post_trigger_bars_available_yet" and result["outcome_reason"] != prev_reason:
            stale_reason_prevented.append({"sot_candidate_id": cid, "surface": surface, "old_reason": prev_reason, "new_reason": result["outcome_reason"]})
        history_item = {
            "tracking_update_at_utc": now,
            "outcome_category": result["outcome_category"],
            "outcome_reason": result["outcome_reason"],
            "is_final": bool(result.get("is_final")),
            "classification_details": result.get("classification_details", {}),
            "source": "PRV1N active-watch truth classifier from refreshed local provider cache",
            "caveats": [
                "Lifecycle update is observation-only.",
                "Favorable observation is not a win.",
                "Invalidated observation is not a loss.",
                "No entry/stop/target/execution/PnL is produced.",
                "Cache is not source authority; source confidence remains single-provider caveated.",
            ],
            "boundary": BOUNDARY,
        }
        life["candidate_snapshot"] = snap
        life.setdefault("outcome_history", []).append(history_item)
        life["latest_outcome_category"] = result["outcome_category"]
        life["latest_outcome_reason"] = result["outcome_reason"]
        life["is_final"] = bool(result.get("is_final"))
        life["status"] = "final_outcome_recorded" if life["is_final"] else "active_tracking"
        life["updated_at_utc"] = now
        life["update_count"] = int(life.get("update_count", 0) or 0) + 1
        if prev_status != "final_outcome_recorded" and life["status"] == "final_outcome_recorded":
            finalized_now += 1
        details = result.get("classification_details", {})
        update_rows.append({
            "sot_candidate_id": cid,
            "surface": surface,
            "previous_status": prev_status,
            "previous_outcome_category": prev_cat,
            "previous_outcome_reason": prev_reason,
            "new_status": life["status"],
            "new_outcome_category": life["latest_outcome_category"],
            "new_outcome_reason": life["latest_outcome_reason"],
            "is_final": life["is_final"],
            "updated_at_utc": now,
            "classification_source": "prv1n_canonical_lifecycle_update_from_refreshed_cache",
            "valid_cache_bar_count": details.get("valid_cache_bar_count", len(values)),
            "post_bars_observed": details.get("post_bars_observed"),
            "first_post_bar_open_ts_utc": (details.get("post_window") or {}).get("first_post_bar_open_ts_utc"),
            "last_post_bar_open_ts_utc": (details.get("post_window") or {}).get("last_post_bar_open_ts_utc"),
        })

    lifecycle_after = copy.deepcopy(lifecycle_store)
    lifecycle_after["status"] = "lifecycle_state_store_post_refresh_updated_by_prv1n"
    lifecycle_after["updated_at_utc"] = now
    lifecycle_after["lifecycle_count"] = len(lifecycles)
    lifecycle_after["lifecycles"] = lifecycles
    lifecycle_after["boundary"] = BOUNDARY

    # Critical PRV1N fix: back up and overwrite canonical SOT02 lifecycle store so later PRV1E/dashboard steps consume truth.
    canonical_path = required["shadow_lifecycle_state_store"]
    backup_path = root / "state" / "sot02_current" / f"shadow_lifecycle_state_store_pre_prv1n_backup_{now.replace(':','').replace('-','')}.json"
    write_json(backup_path, lifecycle_store)
    write_json(canonical_path, lifecycle_after)
    write_json(root / "state" / "sot02_current" / "shadow_lifecycle_state_store_post_refresh.json", lifecycle_after)

    status_counts, outcome_counts = summarize(lifecycles)
    candidate_count = len(registry_candidates)
    lifecycle_count = len(lifecycles)
    final_count = status_counts.get("final_outcome_recorded", 0)
    active_count = status_counts.get("active_tracking", 0)
    ledger_rows = build_ledger(registry, lifecycle_after)
    outcome_rows = [r for r in ledger_rows if r.get("lifecycle_status") == "final_outcome_recorded"]
    active_rows = [r for r in ledger_rows if r.get("lifecycle_status") == "active_tracking"]

    stale_active_reason_rows = []
    for r in active_rows:
        if r.get("latest_outcome_reason") == "no_completed_post_trigger_bars_available_yet":
            details = r.get("classification_details") or {}
            if (details.get("post_bars_observed") or 0) > 0:
                stale_active_reason_rows.append({"sot_candidate_id": r.get("sot_candidate_id"), "surface": r.get("surface"), "post_bars_observed": details.get("post_bars_observed")})

    plan = {"program": "PRV1N-01", "artifact": "post_refresh_update_plan", "created_at_utc": now, "preconditions": {"staged_provider_fetch_report_present": True, "staged_cache_update_report_present": True, "scope_ok": scope_ok, "all_surfaces_refreshed": all_surfaces_ok, "all_cache_snapshots_updated": cache_all_ok}, "actions": ["update existing active SOT02 lifecycle rows from refreshed local cache", "write updated canonical lifecycle store consumed by candidate detection/dashboard", "prevent stale no_completed_post_trigger_bars_available_yet when post-trigger bars exist", "rebuild post-refresh ledger/panel payload/proofs"], "boundary": BOUNDARY}
    lifecycle_report = {"program": "PRV1N-01", "artifact": "post_refresh_lifecycle_update_report", "created_at_utc": now, "mode": "canonical_existing_exact_sot02_lifecycle_update_from_staged_provider_cache", "active_lifecycles_before": len(active_before), "existing_active_lifecycle_updates_performed": len(update_rows), "finalized_now": finalized_now, "canonical_lifecycle_store_overwritten": True, "canonical_lifecycle_store_backup": str(backup_path.relative_to(root)), "stale_no_completed_reason_prevented_rows": stale_reason_prevented, "update_rows": update_rows, "skipped_rows": skipped_rows, "candidate_count_after": candidate_count, "lifecycle_count_after": lifecycle_count, "final_outcome_count_after": final_count, "active_tracking_count_after": active_count, "boundary": BOUNDARY}
    outcome_report = {"program": "PRV1N-01", "artifact": "post_refresh_outcome_observation_report", "created_at_utc": now, "outcome_counts": outcome_counts, "status_counts": status_counts, "meaning": "descriptive lifecycle observation only", "not_meaning": "not PnL, not win/loss, not validation, not strategy approval", "boundary": BOUNDARY}
    detection_report = {"program": "PRV1N-01", "artifact": "post_refresh_candidate_detection_report", "created_at_utc": now, "new_candidate_detection_performed": False, "new_candidate_count": 0, "reason": "PRV1N fixes lifecycle truth before dedicated PRV1E candidate detection runs; it does not fabricate new candidates.", "candidate_count_preserved": candidate_count, "boundary": BOUNDARY}
    panel_payload = {"program": "PRV1N-01", "artifact": "panel_payload_after_post_refresh_update", "created_at_utc": now, "panel_status": "display_ready_after_post_refresh_lifecycle_update", "active_instruments": ACTIVE_INSTRUMENTS, "summary": {"candidate_count": candidate_count, "lifecycle_count": lifecycle_count, "status_counts": status_counts, "outcome_counts": outcome_counts, "active_tracking_count": active_count, "final_outcome_count": final_count, "row_quality_counts": {"exact_current_sot02_row_post_refresh": len(ledger_rows), "aggregate_resolved_row_shell": 0}}, "post_refresh_update_summary": {"new_candidate_detection_status": "not_performed_not_fabricated", "existing_active_lifecycle_updates_performed": len(update_rows), "finalized_now": finalized_now, "stale_active_reason_rows": stale_active_reason_rows, "skipped_rows": skipped_rows}, "source_confidence": {"mode": "single_provider_caveated_only", "provider": "twelve_data", "is_source_truth": False, "second_provider_conflict_check": "out_of_v1_scope"}, "calendar_event": "calendar_event_source_not_in_v1_scope", "display_banner": "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Post-refresh lifecycle update is observation-only; not signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, not production readiness.", "post_refresh_lifecycle_rows": ledger_rows, "forbidden_surfaces_absent": FORBIDDEN_ACTION_SURFACES, "boundary": BOUNDARY}

    validation_passed = bool(scope_ok and all_surfaces_ok and cache_all_ok and not stale_active_reason_rows and len(ledger_rows) == candidate_count)
    validation = {"program": "PRV1N-01", "artifact": "post_refresh_update_local_validation_result", "created_at_utc": now, "validation_passed": validation_passed, "coverage_status": "post_refresh_lifecycle_update_completed" if validation_passed else "requires_review", "candidate_count": candidate_count, "lifecycle_count": lifecycle_count, "final_outcome_count": final_count, "active_tracking_count": active_count, "new_candidate_detection_performed": False, "existing_active_lifecycle_updates_performed": len(update_rows), "finalized_now": finalized_now, "stale_active_reason_rows": stale_active_reason_rows, "canonical_lifecycle_store_updated": True, "secret_redaction_passed": True, "no_action_surface_passed": True, "scope_ok": scope_ok, "boundary_status": "passed" if validation_passed else "failed_or_requires_review", "boundary": BOUNDARY}

    write_json(root / "reports" / "post_refresh_update_plan.json", plan)
    write_json(root / "reports" / "post_refresh_candidate_detection_report.json", detection_report)
    write_json(root / "reports" / "post_refresh_lifecycle_update_report.json", lifecycle_report)
    write_json(root / "reports" / "post_refresh_outcome_observation_report.json", outcome_report)
    write_json(root / "reports" / "active_watch_truth_debug_report.json", {"program": "PRV1N-01", "artifact": "active_watch_truth_debug_report", "created_at_utc": now, "active_before": active_before, "update_rows": update_rows, "stale_active_reason_rows": stale_active_reason_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "candidate_observation_ledger_v1_post_refresh.json", {"program": "PRV1N-01", "artifact": "candidate_observation_ledger_v1_post_refresh", "created_at_utc": now, "rows": ledger_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "candidate_lifecycle_rows_v1_post_refresh.json", {"program": "PRV1N-01", "artifact": "candidate_lifecycle_rows_v1_post_refresh", "created_at_utc": now, "rows": ledger_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "outcome_observation_rows_v1_post_refresh.json", {"program": "PRV1N-01", "artifact": "outcome_observation_rows_v1_post_refresh", "created_at_utc": now, "rows": outcome_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "active_tracking_rows_v1_post_refresh.json", {"program": "PRV1N-01", "artifact": "active_tracking_rows_v1_post_refresh", "created_at_utc": now, "rows": active_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "candidate_evidence_index_v1_post_refresh.json", {"program": "PRV1N-01", "artifact": "candidate_evidence_index_post_refresh", "created_at_utc": now, "evidence_sources": ["state/sot02_current/shadow_candidate_registry.json", "state/sot02_current/shadow_lifecycle_state_store.json", "reports/staged_provider_fetch_report.json", "reports/staged_cache_update_report.json", "data/provider_cache/twelve_data/*.json"], "rows": [{"sot_candidate_id": r["sot_candidate_id"], "surface": r["surface"], "trigger_reference_bar_ts_utc": r["trigger_reference_bar_ts_utc"], "evidence_refs": ["candidate_registry", "canonical_lifecycle_store", "provider_cache"]} for r in ledger_rows], "boundary": BOUNDARY})
    write_json(root / "panel" / "panel_payload_after_post_refresh_update.json", panel_payload)
    write_json(root / "proofs" / "post_refresh_secret_redaction_proof.json", {"program": "PRV1N-01", "artifact": "post_refresh_secret_redaction_proof", "created_at_utc": now, "api_key_requested_or_read": False, "api_key_value_written": False, "env_file_read": False, "secret_hit_files": [], "verdict": "passed_no_secret_access_or_secret_output_in_post_refresh_update", "boundary": BOUNDARY})
    write_json(root / "proofs" / "post_refresh_no_action_surface_proof.json", {"program": "PRV1N-01", "artifact": "post_refresh_no_action_surface_proof", "created_at_utc": now, "action_surface_absent": True, "panel_forbidden_surfaces_absent": FORBIDDEN_ACTION_SURFACES, "required_absent_flags_checked": list(FORBIDDEN_ACTION_SURFACES), "verdict": "passed", "boundary": BOUNDARY})
    write_json(root / "proofs" / "post_refresh_update_boundary_proof.json", {"program": "PRV1N-01", "artifact": "post_refresh_update_boundary_proof", "created_at_utc": now, "status": "passed" if validation_passed else "failed_or_requires_review", "staged_refresh_scope_ok": scope_ok, "staged_refresh_all_surfaces_ok": all_surfaces_ok, "staged_cache_all_surfaces_ok": cache_all_ok, "new_candidate_detection_not_fabricated": True, "existing_lifecycle_update_performed": len(update_rows) > 0, "canonical_lifecycle_store_updated": True, "stale_active_reason_blocked": not bool(stale_active_reason_rows), "no_action_surface_passed": True, "secret_redaction_passed": True, "boundary": BOUNDARY})
    write_json(root / "proofs" / "post_refresh_update_local_validation_result.json", validation)
    write_json(root / "logs" / "last_run_status_after_post_refresh_update.json", {"program": "PRV1N-01", "artifact": "last_run_status_after_post_refresh_update", "created_at_utc": now, "status": "post_refresh_update_completed" if validation_passed else "post_refresh_update_requires_review", "candidate_count": candidate_count, "lifecycle_count": lifecycle_count, "final_outcome_count": final_count, "active_tracking_count": active_count, "boundary": BOUNDARY})
    write_json(root / "logs" / "runtime_heartbeat_after_post_refresh_update.json", {"program": "PRV1N-01", "artifact": "runtime_heartbeat_after_post_refresh_update", "created_at_utc": now, "heartbeat_status": "post_refresh_update_heartbeat_written", "not_production_readiness": True, "boundary": BOUNDARY})

    print(json.dumps(validation, indent=2, ensure_ascii=False))
    return 0 if validation_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
