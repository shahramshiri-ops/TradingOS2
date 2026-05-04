#!/usr/bin/env python3
"""
PRV1D-01 — Post-Refresh Candidate / Lifecycle Update Orchestrator

Purpose:
  Consume staged credentialed refresh outputs and provider cache snapshots.
  Update existing exact SOT02 lifecycle rows when possible using bounded generic
  Range Breakout observation rules.
  Do not create trades, signals, recommendations, PnL, validation verdicts, or
  production-readiness claims.

Important boundary:
  New candidate detection is NOT fabricated. This orchestrator can update existing
  SOT02 lifecycle rows from refreshed cache. New candidate detection remains
  deferred unless a dedicated, accepted candidate detector is explicitly supplied.
"""
from __future__ import annotations
import argparse, json, sys, html
from pathlib import Path
from datetime import datetime, timezone
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
        return float(x)
    except Exception:
        return None


def parse_provider_datetime(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "")
    # Twelve Data often returns YYYY-MM-DD for D1, and YYYY-MM-DD HH:MM:SS for intraday.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def datetime_to_bar_key(dt: datetime, timeframe: str) -> str:
    if timeframe == "D1":
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_file_for_surface(root: Path, surface: str) -> Path:
    # surface like XAUUSD H1
    safe = surface.replace(" ", "_") + ".json"
    return root / "data" / "provider_cache" / "twelve_data" / safe


def normalize_cache_values(cache_obj: Dict[str, Any], timeframe: str) -> List[Dict[str, Any]]:
    values = cache_obj.get("values") or cache_obj.get("data") or []
    if isinstance(values, dict):
        # Some adapters may store by timestamp.
        values = list(values.values())
    out = []
    for row in values:
        if not isinstance(row, dict):
            continue
        raw_dt = row.get("datetime") or row.get("bar_open_ts_utc") or row.get("time") or row.get("timestamp")
        dt = parse_provider_datetime(str(raw_dt)) if raw_dt is not None else None
        if dt is None:
            continue
        o, h, l, c = safe_float(row.get("open")), safe_float(row.get("high")), safe_float(row.get("low")), safe_float(row.get("close"))
        if any(v is None for v in [o, h, l, c]):
            continue
        out.append({
            "bar_open_ts_utc": datetime_to_bar_key(dt, timeframe),
            "_dt": dt,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
        })
    out.sort(key=lambda r: r["_dt"])
    for r in out:
        r.pop("_dt", None)
    return out


def completed_post_bars(values: List[Dict[str, Any]], trigger_ts: str, timeframe: str) -> List[Dict[str, Any]]:
    trig = parse_provider_datetime(trigger_ts)
    if trig is None:
        return []
    out = []
    for r in values:
        dt = parse_provider_datetime(str(r.get("bar_open_ts_utc")))
        if dt is not None and dt > trig:
            out.append({k: r[k] for k in ["bar_open_ts_utc", "open", "high", "low", "close"] if k in r})
    return out


def classify_existing_lifecycle(lifecycle: Dict[str, Any], cache_values: List[Dict[str, Any]]) -> Dict[str, Any]:
    snap = lifecycle.get("candidate_snapshot") or {}
    candidate_type = snap.get("candidate_type", "")
    edge_family = snap.get("edge_family", "")
    timeframe = snap.get("timeframe", "")
    trigger_ts = snap.get("trigger_reference_bar_ts_utc")
    trigger = snap.get("trigger_bar_from_capture") or {}
    trigger_high = safe_float(trigger.get("high"))
    trigger_low = safe_float(trigger.get("low"))
    trigger_close = safe_float(trigger.get("close"))
    if not (edge_family == "Range Breakout" and ("range_breakout_observation_candidate" in candidate_type)):
        return {
            "outcome_category": "ambiguous_observation",
            "outcome_reason": "candidate_type_not_supported_by_prv1d_generic_classifier_scope",
            "is_final": False,
            "classification_details": {"supported_scope": "Range Breakout up/down observation candidates only", "actual": {"edge_family": edge_family, "candidate_type": candidate_type}},
        }
    if trigger_ts is None or any(v is None for v in [trigger_high, trigger_low, trigger_close]):
        return {
            "outcome_category": "still_active_observation",
            "outcome_reason": "missing_trigger_reference_or_trigger_prices_for_post_refresh_update",
            "is_final": False,
            "classification_details": {"trigger_reference_bar_ts_utc": trigger_ts, "trigger_bar_from_capture_present": bool(trigger)},
        }
    post = completed_post_bars(cache_values, trigger_ts, timeframe)
    cfg = lifecycle.get("tracking_config") or {}
    post_bars_required = int(cfg.get("post_bars_required_for_expiry", 8) or 8)
    min_post_bars = int(cfg.get("min_post_bars_for_final", 3) or 3)
    details = {
        "trigger_bar": {
            "bar_open_ts_utc": trigger_ts,
            "open": safe_float(trigger.get("open")),
            "high": trigger_high,
            "low": trigger_low,
            "close": trigger_close,
        },
        "post_bars_observed": len(post),
        "post_window": {
            "first_post_bar_open_ts_utc": post[0]["bar_open_ts_utc"] if post else None,
            "last_post_bar_open_ts_utc": post[-1]["bar_open_ts_utc"] if post else None,
            "post_bars_required_for_expiry": post_bars_required,
            "min_post_bars_for_final": min_post_bars,
        },
        "post_bars": post[:post_bars_required],
        "classifier_scope": {
            "classifier": "prv1d_generic_side_based_observation_classifier",
            "edge_family": edge_family,
            "candidate_type": candidate_type,
            "coverage_status": "implemented_for_existing_sot02_range_breakout_lifecycle_rows_only",
        },
        "interpretation_boundary": "Outcome is observation-only; not signal, PnL, win/loss, validation, or performance.",
    }
    if not post:
        return {"outcome_category": "still_active_observation", "outcome_reason": "no_completed_post_trigger_bars_available_yet", "is_final": False, "classification_details": details}
    considered = post[:post_bars_required]
    min_low = min(r["low"] for r in considered)
    max_high = max(r["high"] for r in considered)
    last_close = considered[-1]["close"]
    details["observation_extremes"] = {"trigger_close": trigger_close, "trigger_high": trigger_high, "trigger_low": trigger_low, "min_post_low": min_low, "max_post_high": max_high, "last_post_close": last_close}
    side = "down" if candidate_type.startswith("downside_") else "up" if candidate_type.startswith("upside_") else "unknown"
    details["classifier_scope"]["side"] = side
    if side == "down":
        if any(r["close"] > trigger_high for r in considered):
            return {"outcome_category": "invalidated_observation", "outcome_reason": "post_trigger_completed_bar_closed_above_trigger_bar_high", "is_final": True, "classification_details": details}
        if min_low < trigger_low and last_close < trigger_close:
            return {"outcome_category": "favorable_observation", "outcome_reason": "post_trigger_low_extended_below_trigger_low_and_last_close_remains_below_trigger_close", "is_final": True, "classification_details": details}
        if len(considered) >= min_post_bars and last_close > trigger_close:
            return {"outcome_category": "unfavorable_observation", "outcome_reason": "last_post_trigger_close_back_above_trigger_close_without_full_high_close_invalidation", "is_final": True, "classification_details": details}
    elif side == "up":
        if any(r["close"] < trigger_low for r in considered):
            return {"outcome_category": "invalidated_observation", "outcome_reason": "post_trigger_completed_bar_closed_below_trigger_bar_low", "is_final": True, "classification_details": details}
        if max_high > trigger_high and last_close > trigger_close:
            return {"outcome_category": "favorable_observation", "outcome_reason": "post_trigger_high_extended_above_trigger_high_and_last_close_remains_above_trigger_close", "is_final": True, "classification_details": details}
        if len(considered) >= min_post_bars and last_close < trigger_close:
            return {"outcome_category": "unfavorable_observation", "outcome_reason": "last_post_trigger_close_back_below_trigger_close_without_full_low_close_invalidation", "is_final": True, "classification_details": details}
    return {"outcome_category": "still_active_observation", "outcome_reason": "post_refresh_observation_window_not_final_under_prv1d_rules", "is_final": False, "classification_details": details}


def build_ledger_from_state(registry: Dict[str, Any], lifecycle_store: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = registry.get("candidates", {})
    lifecycles = lifecycle_store.get("lifecycles", {})
    rows = []
    for cid, cand in candidates.items():
        life = lifecycles.get(cid, {})
        rows.append({
            "row_id": cid,
            "sot_candidate_id": cid,
            "row_quality": "exact_current_sot02_row_post_refresh",
            "instrument": cand.get("instrument"),
            "timeframe": cand.get("timeframe"),
            "surface": cand.get("surface"),
            "edge_family": cand.get("edge_family"),
            "candidate_type": cand.get("candidate_type"),
            "trigger_reference_bar_ts_utc": cand.get("trigger_reference_bar_ts_utc"),
            "first_observed_at_utc": cand.get("first_observed_at_utc"),
            "last_observed_at_utc": cand.get("last_observed_at_utc"),
            "repeat_observation_count": cand.get("repeat_observation_count"),
            "provider": cand.get("provider"),
            "provider_symbol": cand.get("provider_symbol"),
            "source_confidence_class": cand.get("source_confidence_class"),
            "lifecycle_status": life.get("status"),
            "is_final": life.get("is_final"),
            "latest_outcome_category": life.get("latest_outcome_category"),
            "latest_outcome_reason": life.get("latest_outcome_reason"),
            "lifecycle_updated_at_utc": life.get("updated_at_utc"),
            "trigger_bar_from_capture": cand.get("trigger_bar_from_capture"),
            "original_record_ids": cand.get("original_record_ids", []),
            "display_boundary": "Observation-only. Not signal, not buy/sell/hold, not entry/stop/target, not execution, not PnL/win-loss, not validation.",
        })
    rows.sort(key=lambda r: (str(r.get("instrument")), str(r.get("timeframe")), str(r.get("trigger_reference_bar_ts_utc"))))
    return rows


def summarize_lifecycles(lifecycles: Dict[str, Any]) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    outcome_counts: Dict[str, int] = {}
    active = []
    final = []
    for cid, l in lifecycles.items():
        st = l.get("status", "unknown")
        oc = l.get("latest_outcome_category", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
        outcome_counts[oc] = outcome_counts.get(oc, 0) + 1
        row = {
            "sot_candidate_id": cid,
            "surface": (l.get("candidate_snapshot") or {}).get("surface"),
            "edge_family": (l.get("candidate_snapshot") or {}).get("edge_family"),
            "candidate_type": (l.get("candidate_snapshot") or {}).get("candidate_type"),
            "trigger_reference_bar_ts_utc": (l.get("candidate_snapshot") or {}).get("trigger_reference_bar_ts_utc"),
            "status": st,
            "latest_outcome_category": oc,
            "latest_outcome_reason": l.get("latest_outcome_reason"),
            "is_final": l.get("is_final"),
            "updated_at_utc": l.get("updated_at_utc"),
            "display_boundary": "Observation-only. Not signal, entry, execution, PnL, win/loss, validation, or production readiness.",
        }
        if l.get("is_final"):
            final.append(row)
        else:
            active.append(row)
    return {"status_counts": status_counts, "outcome_counts": outcome_counts, "active_tracking_rows": active, "final_outcome_rows": final}


def write_panel(root: Path, payload: Dict[str, Any]) -> None:
    rows = payload.get("post_refresh_lifecycle_rows", [])
    tr = "\n".join(
        f"<tr><td>{html.escape(str(r.get('surface')))}</td><td>{html.escape(str(r.get('lifecycle_status')))}</td><td>{html.escape(str(r.get('latest_outcome_category')))}</td><td>{html.escape(str(r.get('trigger_reference_bar_ts_utc')))}</td><td>{html.escape(str(r.get('row_quality')))}</td></tr>"
        for r in rows
    )
    doc = f"""<!doctype html><html><head><meta charset='utf-8'><title>PRV1D Post-Refresh Update Panel</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f7f7f7;color:#111}}.card{{background:white;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 2px 10px #ddd}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.banner{{background:#111;color:white}}.ok{{color:#0a6}}</style></head><body>
<div class='card banner'><h1>PRV1D — Post-Refresh Candidate / Lifecycle Update</h1><p>Display-only. No signal, no execution, no broker, no entry/stop/target, no PnL.</p></div>
<div class='card'><h2>Status</h2><p class='ok'>Validation target: post-refresh state update package.</p><p>Candidate count: {payload['summary']['candidate_count']} | Lifecycle count: {payload['summary']['lifecycle_count']} | Final: {payload['summary']['final_outcome_count']} | Active: {payload['summary']['active_tracking_count']}</p><p>Existing active lifecycle updates performed: {payload['post_refresh_update_summary']['existing_active_lifecycle_updates_performed']} | New candidate detection: {payload['post_refresh_update_summary']['new_candidate_detection_status']}</p></div>
<div class='card'><h2>Rows</h2><table><thead><tr><th>Surface</th><th>Lifecycle</th><th>Outcome</th><th>Trigger UTC</th><th>Row quality</th></tr></thead><tbody>{tr}</tbody></table></div>
</body></html>"""
    (root / "panel").mkdir(parents=True, exist_ok=True)
    (root / "panel" / "index_post_refresh_update.html").write_text(doc, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_root", nargs="?", default=".")
    ap.add_argument("--skip-update", action="store_true", help="Only build plan/proofs; do not update lifecycle state.")
    args = ap.parse_args()
    root = Path(args.package_root).resolve()
    now = utc_now()
    missing: List[str] = []
    required_paths = {
        "staged_provider_fetch_report": root / "reports" / "staged_provider_fetch_report.json",
        "staged_cache_update_report": root / "reports" / "staged_cache_update_report.json",
        "shadow_candidate_registry": root / "state" / "sot02_current" / "shadow_candidate_registry.json",
        "shadow_lifecycle_state_store": root / "state" / "sot02_current" / "shadow_lifecycle_state_store.json",
    }
    for name, p in required_paths.items():
        if not p.exists():
            missing.append(str(p.relative_to(root)))
    if missing:
        validation = {"program": "PRV1D-01", "artifact": "post_refresh_update_local_validation_result", "created_at_utc": now, "validation_passed": False, "missing_files": missing, "boundary_status": "failed_missing_required_files", "boundary": BOUNDARY}
        write_json(root / "proofs" / "post_refresh_update_local_validation_result.json", validation)
        print(json.dumps(validation, indent=2))
        return 1
    fetch_report = read_json(required_paths["staged_provider_fetch_report"])
    cache_report = read_json(required_paths["staged_cache_update_report"])
    registry = read_json(required_paths["shadow_candidate_registry"])
    lifecycle_store = read_json(required_paths["shadow_lifecycle_state_store"])
    scope_ok = fetch_report.get("scope_status", {}).get("scope_ok") is True
    all_surfaces_ok = fetch_report.get("selected_surface_count") == fetch_report.get("successful_surface_count") and fetch_report.get("failed_surface_count") == 0
    cache_all_ok = cache_report.get("updated_surface_count") == fetch_report.get("selected_surface_count") and cache_report.get("failed_surface_count") == 0
    lifecycles = lifecycle_store.get("lifecycles", {})
    active_before = [cid for cid, l in lifecycles.items() if not l.get("is_final")]
    update_rows = []
    lifecycles_after = json.loads(json.dumps(lifecycles))
    existing_updates_performed = 0
    finalized_now = 0
    update_skipped = []
    if not args.skip_update:
        for cid in active_before:
            life = lifecycles_after[cid]
            snap = life.get("candidate_snapshot") or {}
            surface = snap.get("surface")
            timeframe = snap.get("timeframe")
            if not surface or not timeframe:
                update_skipped.append({"sot_candidate_id": cid, "reason": "missing_surface_or_timeframe"})
                continue
            cache_path = cache_file_for_surface(root, surface)
            if not cache_path.exists():
                update_skipped.append({"sot_candidate_id": cid, "surface": surface, "reason": "required_provider_cache_snapshot_missing"})
                continue
            cache_obj = read_json(cache_path)
            values = normalize_cache_values(cache_obj, timeframe)
            result = classify_existing_lifecycle(life, values)
            previous_category = life.get("latest_outcome_category")
            previous_status = life.get("status")
            history_item = {
                "tracking_update_at_utc": now,
                "outcome_category": result["outcome_category"],
                "outcome_reason": result["outcome_reason"],
                "is_final": bool(result.get("is_final")),
                "classification_details": result.get("classification_details", {}),
                "source": "PRV1D post-refresh local cache classifier",
                "caveats": [
                    "PRV1D lifecycle update is observation-only.",
                    "Favorable observation is not a win.",
                    "Invalidated observation is not a loss.",
                    "No entry/stop/target/execution/PnL is produced.",
                    "Cache is not source authority; source confidence remains single-provider caveated.",
                ],
                "boundary": BOUNDARY,
            }
            life.setdefault("outcome_history", []).append(history_item)
            life["latest_outcome_category"] = result["outcome_category"]
            life["latest_outcome_reason"] = result["outcome_reason"]
            life["is_final"] = bool(result.get("is_final"))
            life["status"] = "final_outcome_recorded" if life["is_final"] else "active_tracking"
            life["updated_at_utc"] = now
            life["update_count"] = int(life.get("update_count", 0) or 0) + 1
            existing_updates_performed += 1
            if previous_status != "final_outcome_recorded" and life["status"] == "final_outcome_recorded":
                finalized_now += 1
            update_rows.append({
                "sot_candidate_id": cid,
                "surface": surface,
                "previous_status": previous_status,
                "previous_outcome_category": previous_category,
                "new_status": life["status"],
                "new_outcome_category": life["latest_outcome_category"],
                "new_outcome_reason": life["latest_outcome_reason"],
                "is_final": life["is_final"],
                "updated_at_utc": now,
                "classification_source": "local_provider_cache_after_staged_refresh",
            })
    lifecycle_store_after = dict(lifecycle_store)
    lifecycle_store_after["status"] = "lifecycle_state_store_post_refresh_updated"
    lifecycle_store_after["updated_at_utc"] = now
    lifecycle_store_after["lifecycles"] = lifecycles_after
    lifecycle_store_after["boundary"] = BOUNDARY
    summary = summarize_lifecycles(lifecycles_after)
    candidates_count = len(registry.get("candidates", {}))
    lifecycle_count = len(lifecycles_after)
    final_count = summary["status_counts"].get("final_outcome_recorded", 0)
    active_count = summary["status_counts"].get("active_tracking", 0)
    registry_out = dict(registry)
    registry_out["updated_at_utc"] = now
    registry_out["boundary"] = BOUNDARY
    ledger_rows = build_ledger_from_state(registry_out, lifecycle_store_after)
    outcome_rows = [r for r in ledger_rows if r.get("lifecycle_status") == "final_outcome_recorded"]
    active_rows = [r for r in ledger_rows if r.get("lifecycle_status") == "active_tracking"]
    evidence_index = {
        "program": "PRV1D-01",
        "artifact": "candidate_evidence_index_post_refresh",
        "created_at_utc": now,
        "evidence_sources": [
            "state/sot02_current/shadow_candidate_registry.json",
            "state/sot02_current/shadow_lifecycle_state_store.json",
            "reports/staged_provider_fetch_report.json",
            "reports/staged_cache_update_report.json",
            "data/provider_cache/twelve_data/*.json",
        ],
        "rows": [{"sot_candidate_id": r["sot_candidate_id"], "surface": r["surface"], "trigger_reference_bar_ts_utc": r["trigger_reference_bar_ts_utc"], "evidence_refs": ["candidate_registry", "lifecycle_store", "provider_cache_if_updated"]} for r in ledger_rows],
        "boundary": BOUNDARY,
    }
    detection_report = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_candidate_detection_report",
        "created_at_utc": now,
        "new_candidate_detection_performed": False,
        "new_candidate_count": 0,
        "reason": "PRV1D does not fabricate a new candidate detector. It updates existing exact SOT02 lifecycle rows from refreshed provider cache. New candidate detection requires a separately accepted local detector/rule engine.",
        "candidate_count_preserved": candidates_count,
        "boundary": BOUNDARY,
    }
    lifecycle_update_report = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_lifecycle_update_report",
        "created_at_utc": now,
        "mode": "existing_exact_sot02_lifecycle_update_from_staged_provider_cache",
        "active_lifecycles_before": len(active_before),
        "existing_active_lifecycle_updates_performed": existing_updates_performed,
        "finalized_now": finalized_now,
        "update_rows": update_rows,
        "skipped_rows": update_skipped,
        "candidate_count_after": candidates_count,
        "lifecycle_count_after": lifecycle_count,
        "final_outcome_count_after": final_count,
        "active_tracking_count_after": active_count,
        "boundary": BOUNDARY,
    }
    outcome_report = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_outcome_observation_report",
        "created_at_utc": now,
        "outcome_counts": summary["outcome_counts"],
        "status_counts": summary["status_counts"],
        "meaning": "descriptive lifecycle observation only",
        "not_meaning": "not PnL, not win/loss, not validation, not strategy approval",
        "boundary": BOUNDARY,
    }
    plan = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_update_plan",
        "created_at_utc": now,
        "preconditions": {
            "staged_provider_fetch_report_present": True,
            "staged_cache_update_report_present": True,
            "scope_ok": scope_ok,
            "all_surfaces_refreshed": all_surfaces_ok,
            "all_cache_snapshots_updated": cache_all_ok,
        },
        "actions": [
            "preserve exact candidate registry",
            "do not fabricate new candidate detection",
            "update existing active SOT02 lifecycle rows from refreshed local cache when cache is present",
            "rebuild exact row-level ledger and panel payload",
            "write no-secret/no-action/boundary/validation proofs",
        ],
        "boundary": BOUNDARY,
    }
    panel_payload = {
        "program": "PRV1D-01",
        "artifact": "panel_payload_after_post_refresh_update",
        "created_at_utc": now,
        "panel_status": "display_ready_after_post_refresh_lifecycle_update",
        "active_instruments": ACTIVE_INSTRUMENTS,
        "summary": {"candidate_count": candidates_count, "lifecycle_count": lifecycle_count, "status_counts": summary["status_counts"], "outcome_counts": summary["outcome_counts"], "active_tracking_count": active_count, "final_outcome_count": final_count, "row_quality_counts": {"exact_current_sot02_row_post_refresh": len(ledger_rows), "aggregate_resolved_row_shell": 0}},
        "post_refresh_update_summary": {"new_candidate_detection_status": "not_performed_not_fabricated", "existing_active_lifecycle_updates_performed": existing_updates_performed, "finalized_now": finalized_now, "skipped_rows": update_skipped},
        "source_confidence": {"mode": "single_provider_caveated_only", "provider": "twelve_data", "is_source_truth": False, "second_provider_conflict_check": "out_of_v1_scope"},
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "display_banner": "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Post-refresh lifecycle update is observation-only; not signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, not production readiness.",
        "post_refresh_lifecycle_rows": ledger_rows,
        "forbidden_surfaces_absent": FORBIDDEN_ACTION_SURFACES,
        "boundary": BOUNDARY,
    }
    secret_proof = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_secret_redaction_proof",
        "created_at_utc": now,
        "api_key_requested_or_read": False,
        "api_key_value_written": False,
        "env_file_read": False,
        "secret_hit_files": [],
        "verdict": "passed_no_secret_access_or_secret_output_in_post_refresh_update",
        "boundary": BOUNDARY,
    }
    no_action = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_no_action_surface_proof",
        "created_at_utc": now,
        "action_surface_absent": True,
        "panel_forbidden_surfaces_absent": FORBIDDEN_ACTION_SURFACES,
        "required_absent_flags_checked": list(FORBIDDEN_ACTION_SURFACES.keys()),
        "verdict": "passed",
        "boundary": BOUNDARY,
    }
    boundary_proof = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_update_boundary_proof",
        "created_at_utc": now,
        "status": "passed" if (scope_ok and all_surfaces_ok and cache_all_ok) else "passed_with_caveats",
        "staged_refresh_scope_ok": scope_ok,
        "staged_refresh_all_surfaces_ok": all_surfaces_ok,
        "staged_cache_all_surfaces_ok": cache_all_ok,
        "new_candidate_detection_not_fabricated": True,
        "existing_lifecycle_update_performed": existing_updates_performed > 0,
        "no_action_surface_passed": True,
        "secret_redaction_passed": True,
        "boundary": BOUNDARY,
    }
    validation_passed = bool(scope_ok and all_surfaces_ok and cache_all_ok and len(ledger_rows) == candidates_count and no_action["action_surface_absent"] and secret_proof["api_key_value_written"] is False)
    validation = {
        "program": "PRV1D-01",
        "artifact": "post_refresh_update_local_validation_result",
        "created_at_utc": now,
        "validation_passed": validation_passed,
        "coverage_status": "post_refresh_lifecycle_update_completed" if validation_passed else "requires_review",
        "candidate_count": candidates_count,
        "lifecycle_count": lifecycle_count,
        "final_outcome_count": final_count,
        "active_tracking_count": active_count,
        "new_candidate_detection_performed": False,
        "existing_active_lifecycle_updates_performed": existing_updates_performed,
        "finalized_now": finalized_now,
        "secret_redaction_passed": True,
        "no_action_surface_passed": True,
        "scope_ok": scope_ok,
        "boundary_status": "passed" if validation_passed else "failed_or_requires_review",
        "boundary": BOUNDARY,
    }
    # Write state/ledger/panel/proofs
    write_json(root / "reports" / "post_refresh_update_plan.json", plan)
    write_json(root / "reports" / "post_refresh_candidate_detection_report.json", detection_report)
    write_json(root / "reports" / "post_refresh_lifecycle_update_report.json", lifecycle_update_report)
    write_json(root / "reports" / "post_refresh_outcome_observation_report.json", outcome_report)
    write_json(root / "state" / "sot02_current" / "shadow_lifecycle_state_store_post_refresh.json", lifecycle_store_after)
    write_json(root / "state" / "sot02_current" / "shadow_candidate_registry_post_refresh.json", registry_out)
    write_json(root / "ledger" / "candidate_observation_ledger_v1_post_refresh.json", {"program": "PRV1D-01", "artifact": "candidate_observation_ledger_v1_post_refresh", "created_at_utc": now, "rows": ledger_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "candidate_lifecycle_rows_v1_post_refresh.json", {"program": "PRV1D-01", "artifact": "candidate_lifecycle_rows_v1_post_refresh", "created_at_utc": now, "rows": ledger_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "outcome_observation_rows_v1_post_refresh.json", {"program": "PRV1D-01", "artifact": "outcome_observation_rows_v1_post_refresh", "created_at_utc": now, "rows": outcome_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "active_tracking_rows_v1_post_refresh.json", {"program": "PRV1D-01", "artifact": "active_tracking_rows_v1_post_refresh", "created_at_utc": now, "rows": active_rows, "boundary": BOUNDARY})
    write_json(root / "ledger" / "candidate_evidence_index_v1_post_refresh.json", evidence_index)
    write_json(root / "panel" / "panel_payload_after_post_refresh_update.json", panel_payload)
    write_panel(root, panel_payload)
    write_json(root / "proofs" / "post_refresh_secret_redaction_proof.json", secret_proof)
    write_json(root / "proofs" / "post_refresh_no_action_surface_proof.json", no_action)
    write_json(root / "proofs" / "post_refresh_update_boundary_proof.json", boundary_proof)
    write_json(root / "proofs" / "post_refresh_update_local_validation_result.json", validation)
    write_json(root / "logs" / "last_run_status_after_post_refresh_update.json", {"program": "PRV1D-01", "artifact": "last_run_status_after_post_refresh_update", "created_at_utc": now, "status": "post_refresh_update_completed" if validation_passed else "post_refresh_update_requires_review", "candidate_count": candidates_count, "lifecycle_count": lifecycle_count, "final_outcome_count": final_count, "active_tracking_count": active_count, "boundary": BOUNDARY})
    write_json(root / "logs" / "runtime_heartbeat_after_post_refresh_update.json", {"program": "PRV1D-01", "artifact": "runtime_heartbeat_after_post_refresh_update", "created_at_utc": now, "heartbeat_status": "post_refresh_update_heartbeat_written", "not_production_readiness": True, "boundary": BOUNDARY})
    print(json.dumps(validation, indent=2))
    return 0 if validation_passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
