#!/usr/bin/env python3
"""Generate a simple display-ready PRV1-01 panel payload from packaged local state."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

CAVEAT_BANNER = "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Not a signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation verdict, not adaptation decision, not production readiness. SPX/NQ out of V1 active scope. Calendar/event and second-provider checks out of V1 scope. Row 2 retained unopened; Rows 6–7 deferred re-entry; matrix-complete ≠ matrix-open."
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
}

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> Dict[str, Any]:
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
    return Path(__file__).resolve().parent.parent

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PRV1-01 display-only panel payload")
    parser.add_argument("--package-root", default=None)
    parser.add_argument("--output", default="panel/panel_payload_generated_stage3.json")
    args = parser.parse_args()
    root = package_root_from_arg(args.package_root)
    created_at = utc_now()
    runtime = read_json(root / "state" / "runtime_state_v1.json")
    candidate = read_json(root / "state" / "candidate_lifecycle_state_v1.json")
    outcome = read_json(root / "state" / "outcome_observation_state_v1.json")
    source = read_json(root / "config" / "single_provider_source_confidence_config.json")
    heartbeat_path = root / "logs" / "runtime_heartbeat.json"
    last_run_path = root / "logs" / "last_run_status.json"
    heartbeat = read_json(heartbeat_path) if heartbeat_path.exists() else {}
    last_run = read_json(last_run_path) if last_run_path.exists() else {}
    payload = {
        "program": "PRV1-01",
        "artifact": "panel_payload_generated_stage3",
        "created_at_utc": created_at,
        "panel_mode": "simple_display_ready_payload_dry_run",
        "active_instruments": runtime.get("active_instruments", ["XAUUSD", "EURUSD", "USDJPY"]),
        "latest_state": runtime.get("latest_state", {}),
        "candidate_lifecycle_state": {
            "candidate_count": candidate.get("candidate_count"),
            "lifecycle_count": candidate.get("lifecycle_count"),
            "active_tracking_count": candidate.get("active_tracking_count"),
            "final_outcome_count": candidate.get("final_outcome_count"),
            "display_rule": candidate.get("display_rule"),
        },
        "outcome_observation_state": {
            "final_outcome_recorded": outcome.get("final_outcome_recorded"),
            "active_tracking": outcome.get("active_tracking"),
            "outcome_counts": outcome.get("outcome_counts", {}),
        },
        "source_confidence": {
            "mode": source.get("mode"),
            "provider": source.get("provider"),
            "meaning": source.get("source_confidence_meaning"),
            "not_meaning": source.get("source_confidence_not_meaning", []),
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
    out_path = root / args.output
    write_json(out_path, payload)
    print(json.dumps({"status":"panel_payload_written", "output": str(out_path), "boundary":"display_only_no_signal_no_execution"}, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
