#!/usr/bin/env python3
"""Read PRV1-01 local runtime status files and print a compact display-only status."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def package_root_from_arg(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PRV1-01 Personal Runtime V1 local status")
    parser.add_argument("--package-root", default=None)
    args = parser.parse_args()
    root = package_root_from_arg(args.package_root)
    runtime = read_json(root / "state" / "runtime_state_v1.json")
    last_run_path = root / "logs" / "last_run_status.json"
    heartbeat_path = root / "logs" / "runtime_heartbeat.json"
    cache_path = root / "reports" / "cache_status.json"
    last_run = read_json(last_run_path) if last_run_path.exists() else {"status": "not_yet_run_stage3"}
    heartbeat = read_json(heartbeat_path) if heartbeat_path.exists() else {"heartbeat_status": "not_yet_written_stage3"}
    cache = read_json(cache_path) if cache_path.exists() else {"surface_count": None}
    latest = runtime.get("latest_state", {})
    status = {
        "program": "PRV1-01",
        "status_view": "display_only_runtime_status",
        "active_instruments": runtime.get("active_instruments", []),
        "candidate_count": latest.get("candidate_count"),
        "lifecycle_count": latest.get("lifecycle_count"),
        "active_tracking_count": latest.get("active_tracking_count"),
        "final_outcome_count": latest.get("final_outcome_count"),
        "last_run_status": last_run.get("status"),
        "heartbeat_status": heartbeat.get("heartbeat_status"),
        "cache_surface_count": cache.get("surface_count"),
        "source_confidence": "single_provider_caveated_only_not_source_truth",
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "boundary": "Not a signal. Not buy/sell/hold. Not entry/stop/target. No broker, order, execution, PnL, optimizer, validation verdict, adaptation decision, or production-readiness claim.",
    }
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
