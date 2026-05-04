#!/usr/bin/env python3
"""PRV1B credentialed refresh preflight.
Checks local env and package structure without making provider calls.
Does not print or write the API key.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys
from pathlib import Path

ENV_VAR = "LFB_TWELVE_DATA_API_KEY"
REDACTED = f"***REDACTED_ENV_VAR:{ENV_VAR}***"
REQUIRED = {"XAUUSD", "EURUSD", "USDJPY"}
FORBIDDEN = {"SPX", "NQ"}

def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def active_symbols(config):
    rows = config.get("active_instruments", [])
    return {r.get("instrument") for r in rows if isinstance(r, dict)}

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", default=".")
    ap.add_argument("--print-summary", action="store_true")
    args = ap.parse_args()
    root = Path(args.package_root).resolve()
    key_present = bool(os.environ.get(ENV_VAR, ""))
    required_files = [
        "config/active_instrument_config.json",
        "config/single_provider_source_confidence_config.json",
        "data/cache/cache_first_feed_plan_v1.json",
        "ledger/candidate_observation_ledger_v1_exact.json",
        "panel/row_level_panel_payload_v1_exact.json",
    ]
    missing = [f for f in required_files if not (root/f).exists()]
    scope_ok = False
    active = []
    forbidden_present = []
    if not missing:
        cfg = load_json(root/"config/active_instrument_config.json")
        active = sorted(active_symbols(cfg))
        forbidden_present = sorted(set(active) & FORBIDDEN)
        scope_ok = set(active) == REQUIRED and not forbidden_present
    verdict = "preflight_passed_ready_for_local_credentialed_refresh" if (key_present and not missing and scope_ok) else "preflight_blocked_or_caveated"
    report = {
        "program": "PRV1B-01",
        "artifact": "credentialed_refresh_preflight_report",
        "created_at_utc": utc_now(),
        "verdict": verdict,
        "package_root": str(root),
        "credential_policy": {
            "env_var_expected": ENV_VAR,
            "env_var_present": key_present,
            "api_key_value_written": False,
            "api_key_display_value": REDACTED if key_present else None,
            "env_file_read": False,
        },
        "scope_status": {
            "active_instruments": active,
            "required_active_match": set(active) == REQUIRED,
            "forbidden_active_present": forbidden_present,
            "scope_ok": scope_ok,
        },
        "required_files_missing": missing,
        "network_call_performed": False,
        "boundary": BOUNDARY,
    }
    write_json(root/"reports/credentialed_refresh_preflight_report.json", report)
    write_json(root/"proofs/credential_presence_redaction_precheck.json", {
        "program": "PRV1B-01",
        "artifact": "credential_presence_redaction_precheck",
        "created_at_utc": report["created_at_utc"],
        "env_var_present": key_present,
        "api_key_not_printed": True,
        "api_key_not_written": True,
        "redaction_token_used": REDACTED if key_present else None,
        "boundary": BOUNDARY,
    })
    if args.print_summary:
        print(f"PRV1B preflight: {verdict}")
        print(f"Package root: {root}")
        print(f"{ENV_VAR} present: {key_present}")
        print(f"Scope OK: {scope_ok}; active={active}; forbidden={forbidden_present}")
        if missing:
            print("Missing files:", ", ".join(missing))
    return 0 if key_present and not missing and scope_ok else 2

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
  "matrix_complete_not_matrix_open": True
}

if __name__ == "__main__":
    raise SystemExit(main())
