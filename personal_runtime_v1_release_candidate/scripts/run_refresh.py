#!/usr/bin/env python3
"""
PRV1-01 Personal Runtime V1 — run/refresh dry-run entrypoint.

This script deliberately performs a cache-first, display-only runtime refresh from
packaged state files. It does NOT fetch live data, read API secrets, connect to a
broker, create orders, generate signals, compute PnL, or claim production readiness.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

ACTIVE_REQUIRED = ["XAUUSD", "EURUSD", "USDJPY"]
FORBIDDEN_ACTIVE = {"SPX", "NQ"}
FORBIDDEN_OUTPUT_TERMS = [
    "buy", "sell", "hold", "entry", "stop", "target", "order", "broker",
    "execution", "pnl", "win_loss", "optimizer", "validation_verdict",
    "adaptation_decision", "production_ready", "production-readiness"
]
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
CAVEAT_BANNER = (
    "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Not a signal, not buy/sell/hold, "
    "not entry/stop/target, not broker/order/execution, not PnL or win/loss, "
    "not optimizer, not validation verdict, not adaptation decision, not production readiness. "
    "SPX/NQ out of V1 active scope. Calendar/event and second-provider checks out of V1 scope. "
    "Row 2 retained unopened; Rows 6–7 deferred re-entry; matrix-complete ≠ matrix-open."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def package_root_from_arg(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    here = Path(__file__).resolve()
    # scripts/run_refresh.py -> package root
    return here.parent.parent.resolve()


def validate_scope(active_config: Dict[str, Any]) -> Dict[str, Any]:
    active = [row.get("instrument") for row in active_config.get("active_instruments", [])]
    forbidden_present = sorted([x for x in active if x in FORBIDDEN_ACTIVE])
    return {
        "active_instruments": active,
        "required_active_match": active == ACTIVE_REQUIRED,
        "forbidden_active_present": forbidden_present,
        "scope_ok": active == ACTIVE_REQUIRED and not forbidden_present,
        "removed_from_active_v1": active_config.get("removed_from_active_v1", {}),
    }


def build_cache_status(cache_plan: Dict[str, Any], created_at: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = cache_plan.get("surface_rows", [])
    surfaces = [r.get("surface") for r in rows]
    status_counts: Dict[str, int] = {}
    for r in rows:
        status = r.get("refresh_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "program": "PRV1-01",
        "artifact": "cache_status",
        "created_at_utc": created_at,
        "mode": "cache_first_dry_run_from_packaged_state",
        "surface_count": len(rows),
        "surfaces": surfaces,
        "refresh_status_counts": status_counts,
        "xauusd_m5_caveat": "XAUUSD M5 is not fabricated into RSP cache feed plan if absent.",
        "cache_first_behavior": {
            "new_live_fetch_performed": False,
            "full_refetch_performed": False,
            "credential_read": False,
            "network_access_attempted": False,
            "provider_adapter_called": False,
            "used_existing_cache_plan_only": True,
        },
        "boundary": {
            "cache_not_source_authority": True,
            "cache_status_not_signal": True,
            "cache_status_not_validation_or_readiness": True,
        },
    }


def build_heartbeat(created_at: str, scope_status: Dict[str, Any], cache_status: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "program": "PRV1-01",
        "artifact": "runtime_heartbeat",
        "created_at_utc": created_at,
        "heartbeat_status": "dry_run_heartbeat_written_from_local_package_state",
        "runtime_mode": "local_display_only_cache_first_dry_run",
        "scope_ok": scope_status.get("scope_ok", False),
        "active_instruments": scope_status.get("active_instruments", []),
        "cache_surface_count": cache_status.get("surface_count"),
        "last_refresh_mode": "dry_run_no_live_fetch",
        "scheduler_claim": "heartbeat_file_written_only_no_background_scheduler_claimed",
        "not_production_readiness": True,
        "boundary": BOUNDARY,
    }


def build_last_run(created_at: str, runtime_state: Dict[str, Any], scope_status: Dict[str, Any]) -> Dict[str, Any]:
    latest = runtime_state.get("latest_state", {})
    return {
        "program": "PRV1-01",
        "artifact": "last_run_status",
        "created_at_utc": created_at,
        "status": "dry_run_completed_from_existing_packaged_state",
        "mode": "cache_first_display_only_no_live_fetch",
        "active_instruments": scope_status.get("active_instruments", []),
        "candidate_count": latest.get("candidate_count"),
        "lifecycle_count": latest.get("lifecycle_count"),
        "active_tracking_count": latest.get("active_tracking_count"),
        "final_outcome_count": latest.get("final_outcome_count"),
        "source_confidence": "single_provider_caveated_only_not_source_truth",
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "execution_summary": {
            "new_live_fetch_performed": False,
            "api_key_requested_or_read": False,
            "env_file_read": False,
            "broker_connection_attempted": False,
            "orders_created": False,
            "signals_generated": False,
            "panel_payload_generated": True,
        },
        "caveat_banner": CAVEAT_BANNER,
        "boundary": BOUNDARY,
    }


def build_panel_payload(package_root: Path, created_at: str) -> Dict[str, Any]:
    runtime_state = read_json(package_root / "state" / "runtime_state_v1.json")
    candidate_state = read_json(package_root / "state" / "candidate_lifecycle_state_v1.json")
    outcome_state = read_json(package_root / "state" / "outcome_observation_state_v1.json")
    source_conf = read_json(package_root / "config" / "single_provider_source_confidence_config.json")
    heartbeat_path = package_root / "logs" / "runtime_heartbeat.json"
    last_run_path = package_root / "logs" / "last_run_status.json"
    heartbeat = read_json(heartbeat_path) if heartbeat_path.exists() else {}
    last_run = read_json(last_run_path) if last_run_path.exists() else {}
    return {
        "program": "PRV1-01",
        "artifact": "panel_payload_generated_stage3",
        "created_at_utc": created_at,
        "panel_mode": "simple_display_ready_payload_dry_run",
        "active_instruments": runtime_state.get("active_instruments", ACTIVE_REQUIRED),
        "latest_state": runtime_state.get("latest_state", {}),
        "candidate_lifecycle_state": {
            "candidate_count": candidate_state.get("candidate_count"),
            "lifecycle_count": candidate_state.get("lifecycle_count"),
            "active_tracking_count": candidate_state.get("active_tracking_count"),
            "final_outcome_count": candidate_state.get("final_outcome_count"),
            "display_rule": candidate_state.get("display_rule"),
        },
        "outcome_observation_state": {
            "final_outcome_recorded": outcome_state.get("final_outcome_recorded"),
            "active_tracking": outcome_state.get("active_tracking"),
            "outcome_counts": outcome_state.get("outcome_counts", {}),
        },
        "source_confidence": {
            "mode": source_conf.get("mode"),
            "provider": source_conf.get("provider"),
            "meaning": source_conf.get("source_confidence_meaning"),
            "not_meaning": source_conf.get("source_confidence_not_meaning", []),
        },
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "last_refresh": {
            "heartbeat_created_at_utc": heartbeat.get("created_at_utc"),
            "last_run_created_at_utc": last_run.get("created_at_utc"),
            "last_run_status": last_run.get("status"),
        },
        "caveat_banner": CAVEAT_BANNER,
        "forbidden_surfaces_absent": {
            "broker_status": True,
            "execution_queue": True,
            "action_buttons": True,
            "buy_sell_hold": True,
            "entry_stop_target": True,
            "pnl_win_loss": True,
        },
        "boundary": BOUNDARY,
    }


def check_forbidden_text(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight text scan. It allows boundary descriptions but verifies no action surface keys exist."""
    forbidden_action_keys = [
        "buy", "sell", "hold", "entry", "stop", "target", "position_size", "allocation", "order_ticket",
        "execution_queue", "broker_status", "pnl", "win_loss"
    ]
    present_keys: List[str] = []
    def walk(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                # Keys under forbidden_surfaces_absent are explicit absence flags, not action surfaces.
                if lk in forbidden_action_keys and not prefix.startswith("forbidden_surfaces_absent."):
                    present_keys.append(prefix + str(k))
                walk(v, prefix + str(k) + ".")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, prefix + str(i) + ".")
    walk(payload)
    return {
        "forbidden_action_surface_keys_present": sorted(set(present_keys)),
        "action_surface_absent": not present_keys,
        "note": "Boundary phrases may mention forbidden concepts only to negate them; this check flags action-surface keys, not caveat wording.",
    }


def run(package_root: Path) -> Dict[str, Any]:
    created_at = utc_now()
    active_config = read_json(package_root / "config" / "active_instrument_config.json")
    runtime_state = read_json(package_root / "state" / "runtime_state_v1.json")
    cache_plan = read_json(package_root / "data" / "cache" / "cache_first_feed_plan_v1.json")

    scope_status = validate_scope(active_config)
    cache_status = build_cache_status(cache_plan, created_at)
    heartbeat = build_heartbeat(created_at, scope_status, cache_status)
    last_run = build_last_run(created_at, runtime_state, scope_status)

    write_json(package_root / "reports" / "cache_status.json", cache_status)
    write_json(package_root / "logs" / "runtime_heartbeat.json", heartbeat)
    write_json(package_root / "logs" / "last_run_status.json", last_run)

    panel_payload = build_panel_payload(package_root, created_at)
    write_json(package_root / "panel" / "panel_payload_generated_stage3.json", panel_payload)

    boundary_scan = check_forbidden_text(panel_payload)
    refresh_report = {
        "program": "PRV1-01",
        "artifact": "refresh_report",
        "created_at_utc": created_at,
        "refresh_mode": "dry_run_cache_first_existing_state_only",
        "result": "completed_without_live_fetch_or_secret_access",
        "scope_status": scope_status,
        "files_written": [
            "logs/runtime_heartbeat.json",
            "logs/last_run_status.json",
            "reports/cache_status.json",
            "panel/panel_payload_generated_stage3.json",
            "reports/refresh_report.json",
            "proofs/refresh_dry_run_proof.json",
        ],
        "not_performed": [
            "live_fetch",
            "api_key_read",
            "env_file_read",
            "broker_connection",
            "order_creation",
            "execution",
            "signal_generation",
            "PnL_or_win_loss_calculation",
            "optimizer_run",
            "validation_verdict",
            "adaptation_decision",
            "production_readiness_claim",
            "calendar_event_logic",
            "second_provider_conflict_check",
        ],
        "cache_status_summary": {
            "surface_count": cache_status["surface_count"],
            "refresh_status_counts": cache_status["refresh_status_counts"],
        },
        "panel_boundary_scan": boundary_scan,
        "caveat_banner": CAVEAT_BANNER,
        "boundary": BOUNDARY,
    }
    dry_run_proof = {
        "program": "PRV1-01",
        "artifact": "refresh_dry_run_proof",
        "created_at_utc": created_at,
        "verdict": "dry_run_completed_no_live_fetch_no_secret_no_broker_no_signal",
        "package_root": str(package_root),
        "read_files": [
            "config/active_instrument_config.json",
            "state/runtime_state_v1.json",
            "state/candidate_lifecycle_state_v1.json",
            "state/outcome_observation_state_v1.json",
            "config/single_provider_source_confidence_config.json",
            "data/cache/cache_first_feed_plan_v1.json",
        ],
        "written_files": refresh_report["files_written"],
        "scope_status": scope_status,
        "cache_first_behavior_preserved": True,
        "repeated_full_fetch_prevented": True,
        "credential_policy_observed": {
            "api_key_requested_in_chat": False,
            "api_key_read_by_script": False,
            ".env_read_by_script": False,
            "secrets_written_to_outputs": False,
        },
        "boundary_scan": boundary_scan,
        "boundary": BOUNDARY,
    }
    write_json(package_root / "reports" / "refresh_report.json", refresh_report)
    write_json(package_root / "proofs" / "refresh_dry_run_proof.json", dry_run_proof)
    return refresh_report


def main() -> int:
    parser = argparse.ArgumentParser(description="PRV1-01 Personal Runtime V1 cache-first dry-run refresh")
    parser.add_argument("--package-root", default=None, help="Path to personal_runtime_v1 package root. Defaults to parent of scripts/.")
    parser.add_argument("--print-summary", action="store_true", help="Print a compact JSON summary to stdout")
    args = parser.parse_args()
    package_root = package_root_from_arg(args.package_root)
    report = run(package_root)
    if args.print_summary:
        summary = {
            "status": report["result"],
            "refresh_mode": report["refresh_mode"],
            "active_instruments": report["scope_status"]["active_instruments"],
            "cache_surface_count": report["cache_status_summary"]["surface_count"],
            "files_written": report["files_written"],
            "boundary": "display_only_no_signal_no_execution",
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
