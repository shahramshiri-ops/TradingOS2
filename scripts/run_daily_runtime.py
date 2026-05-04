#!/usr/bin/env python3
"""
PRV1F-01 — One-Command End-to-End Daily Runtime Loop

Runs the personal runtime V1 daily loop:
1. Preflight
2. PRV1C staged credentialed read-only refresh
3. PRV1D post-refresh lifecycle update
4. PRV1E candidate detection with strict cache-read proof
5. Daily panel/status/heartbeat/final proofs

Observation-only. No broker, no orders, no execution, no signal, no buy/sell/hold,
no entry/stop/target, no PnL/win-loss, no optimizer, no validation verdict,
no adaptation decision, no production-readiness claim.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ENV_VAR = "LFB_TWELVE_DATA_API_KEY"
ACTIVE_REQUIRED = ["XAUUSD", "EURUSD", "USDJPY"]
FORBIDDEN_ACTIVE = {"SPX", "NQ"}
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
FORBIDDEN_ABSENT_KEYS = ["broker_status", "execution_queue", "action_buttons", "buy_sell_hold", "entry_stop_target", "pnl_win_loss"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Optional[Any] = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def run_cmd(root: Path, name: str, cmd: List[str]) -> Dict[str, Any]:
    started = utc_now()
    proc = subprocess.run(cmd, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "step": name,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "cmd": [str(x) for x in cmd],
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "passed": proc.returncode == 0,
    }


def active_scope_status(root: Path) -> Dict[str, Any]:
    cfg = read_json(root / "config" / "active_instrument_config.json", {})
    instruments: List[str] = []
    raw = cfg.get("active_instruments", []) if isinstance(cfg, dict) else []
    for item in raw:
        if isinstance(item, dict):
            instruments.append(item.get("instrument"))
        else:
            instruments.append(str(item))
    instruments = sorted([x for x in instruments if x])
    return {
        "active_instruments": instruments,
        "required_active_match": sorted(ACTIVE_REQUIRED) == instruments,
        "forbidden_active_present": sorted([x for x in instruments if x in FORBIDDEN_ACTIVE]),
        "scope_ok": sorted(ACTIVE_REQUIRED) == instruments and not any(x in FORBIDDEN_ACTIVE for x in instruments),
    }


def file_presence(root: Path) -> Dict[str, bool]:
    paths = [
        "scripts/run_staged_credentialed_refresh.py",
        "scripts/validate_staged_refresh_outputs.py",
        "scripts/run_post_refresh_candidate_lifecycle_update.py",
        "scripts/validate_post_refresh_update_outputs.py",
        "scripts/run_candidate_detection_rule_engine_cache_read_fix.py",
        "scripts/validate_candidate_detection_outputs_strict.py",
        "config/provider_rate_limit_policy.json",
        "config/post_refresh_update_policy.json",
        "config/candidate_detection_rule_policy.json",
        "state/sot02_current/shadow_candidate_registry.json",
        "state/sot02_current/shadow_lifecycle_state_store.json",
    ]
    return {p: (root / p).exists() for p in paths}


def build_preflight(root: Path) -> Dict[str, Any]:
    presence = file_presence(root)
    scope = active_scope_status(root)
    missing_required = [p for p, ok in presence.items() if not ok and p not in ["scripts/run_candidate_detection_rule_engine_cache_read_fix.py", "scripts/validate_candidate_detection_outputs_strict.py"]]
    # PRV1F requires cache-read correction for strict daily candidate detection.
    if not presence.get("scripts/run_candidate_detection_rule_engine_cache_read_fix.py"):
        missing_required.append("scripts/run_candidate_detection_rule_engine_cache_read_fix.py")
    if not presence.get("scripts/validate_candidate_detection_outputs_strict.py"):
        missing_required.append("scripts/validate_candidate_detection_outputs_strict.py")
    return {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_preflight_report",
        "created_at_utc": utc_now(),
        "credential_env_var_present": bool(os.environ.get(ENV_VAR)),
        "credential_env_var_name": ENV_VAR,
        "scope_status": scope,
        "file_presence": presence,
        "missing_required_files": sorted(set(missing_required)),
        "preflight_passed": bool(os.environ.get(ENV_VAR)) and scope.get("scope_ok") is True and not sorted(set(missing_required)),
        "boundary": BOUNDARY,
    }


def staged_ok(root: Path) -> bool:
    val = read_json(root / "proofs" / "staged_refresh_local_validation_result.json", {})
    return val.get("validation_passed") is True and val.get("coverage_status") == "all_surfaces_refreshed" and val.get("failed_surface_count") == 0


def post_ok(root: Path) -> bool:
    val = read_json(root / "proofs" / "post_refresh_update_local_validation_result.json", {})
    return val.get("validation_passed") is True and val.get("boundary_status") == "passed"


def candidate_ok(root: Path) -> bool:
    report = read_json(root / "reports" / "candidate_detection_report.json", {})
    val = read_json(root / "proofs" / "candidate_detection_local_validation_result.json", {})
    secret = read_json(root / "proofs" / "candidate_detection_secret_redaction_proof.json", {})
    action = read_json(root / "proofs" / "candidate_detection_no_action_surface_proof.json", {})
    boundary = read_json(root / "proofs" / "candidate_detection_boundary_proof.json", {})
    return (
        val.get("validation_passed") is True
        and report.get("valid_cache_surface_count", 0) > 0
        and report.get("skipped_surface_count", 9999) == 0
        and secret.get("api_key_requested_or_read") is False
        and secret.get("api_key_value_written") is False
        and action.get("action_surface_absent") is True
        and boundary.get("status") == "passed"
    )


def aggregate_secret(root: Path) -> Dict[str, Any]:
    staged = read_json(root / "proofs" / "staged_secret_redaction_proof.json", {})
    post = read_json(root / "proofs" / "post_refresh_secret_redaction_proof.json", {})
    cand = read_json(root / "proofs" / "candidate_detection_secret_redaction_proof.json", {})
    secret_hit_files = []
    for obj in [staged, post, cand]:
        secret_hit_files.extend(obj.get("secret_hit_files", []) or [])
    passed = (
        not secret_hit_files
        and staged.get("api_key_value_written") is False
        and post.get("api_key_value_written") is False
        and cand.get("api_key_value_written") is False
        and post.get("api_key_requested_or_read") is False
        and cand.get("api_key_requested_or_read") is False
    )
    return {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_secret_redaction_proof",
        "created_at_utc": utc_now(),
        "staged_secret_redaction_verdict": staged.get("verdict"),
        "post_refresh_secret_redaction_verdict": post.get("verdict"),
        "candidate_detection_secret_redaction_verdict": cand.get("verdict"),
        "secret_hit_files": secret_hit_files,
        "api_key_value_written": False if passed else None,
        "env_file_read": bool(staged.get("env_file_read") or post.get("env_file_read") or cand.get("env_file_read")),
        "verdict": "passed_no_secret_found_in_daily_runtime_outputs" if passed else "failed_or_requires_review",
        "boundary": BOUNDARY,
    }


def aggregate_no_action(root: Path) -> Dict[str, Any]:
    staged = read_json(root / "proofs" / "staged_no_action_surface_proof.json", {})
    post = read_json(root / "proofs" / "post_refresh_no_action_surface_proof.json", {})
    cand = read_json(root / "proofs" / "candidate_detection_no_action_surface_proof.json", {})
    panel = read_json(root / "panel" / "panel_payload_after_candidate_detection.json", {})
    forbidden = panel.get("forbidden_surfaces_absent", {}) if isinstance(panel, dict) else {}
    passed = all(obj.get("action_surface_absent") is True for obj in [staged, post, cand]) and all(forbidden.get(k) is True for k in FORBIDDEN_ABSENT_KEYS)
    return {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_no_action_surface_proof",
        "created_at_utc": utc_now(),
        "action_surface_absent": passed,
        "panel_forbidden_surfaces_absent": forbidden,
        "required_absent_flags_checked": FORBIDDEN_ABSENT_KEYS,
        "stage_proofs": {
            "staged_refresh": staged.get("action_surface_absent"),
            "post_refresh_update": post.get("action_surface_absent"),
            "candidate_detection": cand.get("action_surface_absent"),
        },
        "verdict": "passed" if passed else "failed_or_requires_review",
        "boundary": BOUNDARY,
    }


def build_daily_panel(root: Path, validation_passed: bool) -> Dict[str, Any]:
    staged = read_json(root / "proofs" / "staged_refresh_local_validation_result.json", {})
    post = read_json(root / "proofs" / "post_refresh_update_local_validation_result.json", {})
    cand_report = read_json(root / "reports" / "candidate_detection_report.json", {})
    cand_val = read_json(root / "proofs" / "candidate_detection_local_validation_result.json", {})
    candidate_panel = read_json(root / "panel" / "panel_payload_after_candidate_detection.json", {})
    summary = candidate_panel.get("summary", {}) if isinstance(candidate_panel, dict) else {}
    new_rows = read_json(root / "state" / "prv1e_candidate_detection" / "candidate_detection_new_rows_v1.json", {})
    if isinstance(new_rows, dict):
        new_candidate_rows = new_rows.get("rows", []) or new_rows.get("new_rows", []) or []
    elif isinstance(new_rows, list):
        new_candidate_rows = new_rows
    else:
        new_candidate_rows = []
    payload = {
        "program": "PRV1F-01",
        "artifact": "panel_payload_after_daily_runtime",
        "created_at_utc": utc_now(),
        "panel_status": "display_ready_after_one_command_daily_runtime" if validation_passed else "daily_runtime_requires_review",
        "active_instruments": ACTIVE_REQUIRED,
        "daily_loop_summary": {
            "staged_refresh_validation_passed": staged.get("validation_passed"),
            "staged_refresh_coverage_status": staged.get("coverage_status"),
            "staged_refresh_successful_surface_count": staged.get("successful_surface_count"),
            "staged_refresh_failed_surface_count": staged.get("failed_surface_count"),
            "post_refresh_update_validation_passed": post.get("validation_passed"),
            "existing_active_lifecycle_updates_performed": post.get("existing_active_lifecycle_updates_performed"),
            "finalized_now": post.get("finalized_now"),
            "candidate_detection_validation_passed": cand_val.get("validation_passed"),
            "valid_cache_surface_count": cand_report.get("valid_cache_surface_count"),
            "skipped_surface_count": cand_report.get("skipped_surface_count"),
            "new_observation_candidate_count": cand_report.get("new_observation_candidate_count"),
            "existing_duplicate_count": cand_report.get("existing_duplicate_count"),
        },
        "latest_runtime_summary": summary,
        "new_candidate_rows": new_candidate_rows,
        "source_confidence": {"mode": "single_provider_caveated_only", "provider": "twelve_data", "is_source_truth": False, "second_provider_conflict_check": "out_of_v1_scope"},
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "display_banner": "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. One-command daily runtime is observation-only; not signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, not production readiness.",
        "forbidden_surfaces_absent": {k: True for k in FORBIDDEN_ABSENT_KEYS},
        "boundary": BOUNDARY,
    }
    return payload


def write_daily_html(root: Path, payload: Dict[str, Any]) -> None:
    s = payload.get("daily_loop_summary", {})
    runtime = payload.get("latest_runtime_summary", {})
    rows = payload.get("new_candidate_rows", [])
    row_html = "".join(
        f"<tr><td>{html.escape(str(r.get('surface','')))}</td><td>{html.escape(str(r.get('candidate_type','')))}</td><td>{html.escape(str(r.get('trigger_reference_bar_ts_utc','')))}</td><td>{html.escape(str(r.get('row_quality','new_observation_candidate')))}</td></tr>"
        for r in rows if isinstance(r, dict)
    ) or "<tr><td colspan='4'>No new observation candidates in this run.</td></tr>"
    doc = f"""<!doctype html><html><head><meta charset='utf-8'><title>PRV1F Daily Runtime Panel</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f7f7f7;color:#111}}.card{{background:white;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 2px 10px #ddd}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.banner{{background:#111;color:white}}</style></head><body>
<div class='card banner'><h1>PRV1F — One-Command Daily Runtime</h1><p>Display-only. No signal, no execution, no broker, no entry/stop/target, no PnL.</p></div>
<div class='card'><h2>Daily Loop Status</h2><p>Status: {html.escape(payload.get('panel_status',''))}</p><p>Staged surfaces: {s.get('staged_refresh_successful_surface_count')}/{(s.get('staged_refresh_successful_surface_count') or 0)+(s.get('staged_refresh_failed_surface_count') or 0)} | Candidate detection valid cache surfaces: {s.get('valid_cache_surface_count')} | New observation candidates: {s.get('new_observation_candidate_count')}</p></div>
<div class='card'><h2>Runtime Summary</h2><p>Candidates: {runtime.get('candidate_count')} | Lifecycle: {runtime.get('lifecycle_count')} | Final: {runtime.get('final_outcome_count')} | Active: {runtime.get('active_tracking_count')}</p></div>
<div class='card'><h2>New Observation Candidate Rows</h2><table><thead><tr><th>Surface</th><th>Type</th><th>Trigger UTC</th><th>Quality</th></tr></thead><tbody>{row_html}</tbody></table></div>
</body></html>"""
    (root / "panel" / "index_daily_runtime.html").write_text(doc, encoding="utf-8")


def finalize(root: Path, step_results: List[Dict[str, Any]], stopped_reason: Optional[str] = None) -> int:
    staged_pass = staged_ok(root)
    post_pass = post_ok(root)
    cand_pass = candidate_ok(root)
    secret = aggregate_secret(root)
    action = aggregate_no_action(root)
    validation_passed = staged_pass and post_pass and cand_pass and secret.get("verdict", "").startswith("passed") and action.get("action_surface_absent") is True and stopped_reason is None
    payload = build_daily_panel(root, validation_passed)
    write_json(root / "panel" / "panel_payload_after_daily_runtime.json", payload)
    write_daily_html(root, payload)
    write_json(root / "proofs" / "daily_runtime_secret_redaction_proof.json", secret)
    write_json(root / "proofs" / "daily_runtime_no_action_surface_proof.json", action)
    boundary = {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_boundary_proof",
        "created_at_utc": utc_now(),
        "status": "passed" if validation_passed else "failed_or_requires_review",
        "staged_refresh_passed": staged_pass,
        "post_refresh_update_passed": post_pass,
        "candidate_detection_passed": cand_pass,
        "secret_redaction_passed": secret.get("verdict", "").startswith("passed"),
        "no_action_surface_passed": action.get("action_surface_absent") is True,
        "stopped_reason": stopped_reason,
        "boundary": BOUNDARY,
    }
    validation = {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_local_validation_result",
        "created_at_utc": utc_now(),
        "validation_passed": validation_passed,
        "coverage_status": "one_command_daily_runtime_completed" if validation_passed else "failed_or_requires_review",
        "staged_refresh_passed": staged_pass,
        "post_refresh_update_passed": post_pass,
        "candidate_detection_passed": cand_pass,
        "secret_redaction_passed": secret.get("verdict", "").startswith("passed"),
        "no_action_surface_passed": action.get("action_surface_absent") is True,
        "scope_ok": active_scope_status(root).get("scope_ok"),
        "stopped_reason": stopped_reason,
        "boundary_status": "passed" if validation_passed else "failed_or_requires_review",
        "boundary": BOUNDARY,
    }
    status = {
        "program": "PRV1F-01",
        "artifact": "last_run_status_after_daily_runtime",
        "created_at_utc": utc_now(),
        "status": "daily_runtime_completed" if validation_passed else "daily_runtime_failed_or_requires_review",
        "validation_passed": validation_passed,
        "candidate_count": (payload.get("latest_runtime_summary", {}).get("candidate_count")
                            or payload.get("latest_runtime_summary", {}).get("merged_candidate_lifecycle_row_count")),
        "lifecycle_count": (payload.get("latest_runtime_summary", {}).get("lifecycle_count")
                            or payload.get("latest_runtime_summary", {}).get("merged_candidate_lifecycle_row_count")),
        "final_outcome_count": payload.get("latest_runtime_summary", {}).get("final_outcome_count"),
        "active_tracking_count": payload.get("latest_runtime_summary", {}).get("active_tracking_count"),
        "new_observation_candidate_count": payload.get("daily_loop_summary", {}).get("new_observation_candidate_count"),
        "boundary": BOUNDARY,
    }
    heartbeat = {
        "program": "PRV1F-01",
        "artifact": "runtime_heartbeat_after_daily_runtime",
        "created_at_utc": utc_now(),
        "heartbeat_status": "daily_runtime_heartbeat_written",
        "not_production_readiness": True,
        "validation_passed": validation_passed,
        "boundary": BOUNDARY,
    }
    step_report = {
        "program": "PRV1F-01",
        "artifact": "daily_runtime_step_report",
        "created_at_utc": utc_now(),
        "step_results": step_results,
        "stopped_reason": stopped_reason,
        "validation_passed": validation_passed,
        "boundary": BOUNDARY,
    }
    write_json(root / "proofs" / "daily_runtime_boundary_proof.json", boundary)
    write_json(root / "proofs" / "daily_runtime_local_validation_result.json", validation)
    write_json(root / "logs" / "last_run_status_after_daily_runtime.json", status)
    write_json(root / "logs" / "runtime_heartbeat_after_daily_runtime.json", heartbeat)
    write_json(root / "reports" / "daily_runtime_step_report.json", step_report)
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    return 0 if validation_passed else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_root", nargs="?", default=".")
    ap.add_argument("--skip-staged-refresh", action="store_true", help="Use existing PRV1C outputs; for debugging only.")
    ap.add_argument("--skip-post-refresh-update", action="store_true", help="Use existing PRV1D outputs; for debugging only.")
    ap.add_argument("--skip-candidate-detection", action="store_true", help="Use existing PRV1E outputs; for debugging only.")
    ap.add_argument("--no-wait", action="store_true", help="Pass --no-wait to staged refresh; not recommended for real daily run.")
    args = ap.parse_args()
    root = Path(args.package_root).resolve()
    step_results: List[Dict[str, Any]] = []

    preflight = build_preflight(root)
    write_json(root / "reports" / "daily_runtime_preflight_report.json", preflight)
    if not preflight.get("preflight_passed"):
        return finalize(root, step_results, "preflight_failed")

    if not args.skip_staged_refresh:
        cmd = [sys.executable, str(root / "scripts" / "run_staged_credentialed_refresh.py"), "--package-root", str(root)]
        if args.no_wait:
            cmd.append("--no-wait")
        res = run_cmd(root, "staged_credentialed_refresh", cmd)
        step_results.append(res)
        if not res["passed"]:
            return finalize(root, step_results, "staged_credentialed_refresh_failed")
        val = run_cmd(root, "validate_staged_refresh_outputs", [sys.executable, str(root / "scripts" / "validate_staged_refresh_outputs.py"), str(root)])
        step_results.append(val)
        if not val["passed"] or not staged_ok(root):
            return finalize(root, step_results, "staged_refresh_validation_failed")

    if not args.skip_post_refresh_update:
        res = run_cmd(root, "post_refresh_lifecycle_update", [sys.executable, str(root / "scripts" / "run_post_refresh_candidate_lifecycle_update.py"), str(root)])
        step_results.append(res)
        if not res["passed"]:
            return finalize(root, step_results, "post_refresh_lifecycle_update_failed")
        val = run_cmd(root, "validate_post_refresh_update_outputs", [sys.executable, str(root / "scripts" / "validate_post_refresh_update_outputs.py"), str(root)])
        step_results.append(val)
        if not val["passed"] or not post_ok(root):
            return finalize(root, step_results, "post_refresh_update_validation_failed")

    if not args.skip_candidate_detection:
        detector = root / "scripts" / "run_candidate_detection_rule_engine_cache_read_fix.py"
        validator = root / "scripts" / "validate_candidate_detection_outputs_strict.py"
        res = run_cmd(root, "candidate_detection_rule_engine", [sys.executable, str(detector), str(root)])
        step_results.append(res)
        if not res["passed"]:
            return finalize(root, step_results, "candidate_detection_rule_engine_failed")
        val = run_cmd(root, "validate_candidate_detection_outputs_strict", [sys.executable, str(validator), str(root)])
        step_results.append(val)
        if not val["passed"] or not candidate_ok(root):
            return finalize(root, step_results, "candidate_detection_validation_failed")

    return finalize(root, step_results, None)


if __name__ == "__main__":
    raise SystemExit(main())
