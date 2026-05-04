#!/usr/bin/env python3
"""PRV1B credentialed read-only refresh runner.

Local-only expectations:
- Reads API key only from LFB_TWELVE_DATA_API_KEY environment variable.
- Does not read .env.
- Performs read-only Twelve Data time_series calls for V1 cache-plan surfaces only.
- Writes sanitized provider/cache/panel/proof reports.
- Does not create signals, action surfaces, execution artifacts, PnL, validation verdicts, or production-readiness claims.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ENV_VAR = "LFB_TWELVE_DATA_API_KEY"
REDACTED = f"***REDACTED_ENV_VAR:{ENV_VAR}***"
REQUIRED = {"XAUUSD", "EURUSD", "USDJPY"}
FORBIDDEN = {"SPX", "NQ"}
BASE_URL = "https://api.twelvedata.com/time_series"
INTERVAL_MAP = {"M5": "5min", "M15": "15min", "H1": "1h", "D1": "1day"}

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

def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def active_config(root: Path):
    cfg = load_json(root/"config/active_instrument_config.json", {})
    rows = cfg.get("active_instruments", [])
    active = []
    symbol_map = {}
    for r in rows:
        if isinstance(r, dict) and r.get("instrument"):
            active.append(r["instrument"])
            symbol_map[r["instrument"]] = r.get("provider_symbol") or r["instrument"]
    return cfg, active, symbol_map

def parse_surface(surface: str):
    parts = surface.split()
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]

def select_surfaces(root: Path, active: list[str], due_only=True, max_surfaces=0):
    plan = load_json(root/"data/cache/cache_first_feed_plan_v1.json", {})
    rows = plan.get("surface_rows", [])
    selected = []
    for row in rows:
        surface = row.get("surface")
        inst, tf = parse_surface(surface or "")
        if inst not in active:
            continue
        if inst in FORBIDDEN:
            continue
        if tf not in INTERVAL_MAP:
            continue
        if due_only and row.get("refresh_status") not in {"refresh_due_or_soon", "stale_refresh_due", "refresh_due"}:
            continue
        selected.append(row)
    if max_surfaces and max_surfaces > 0:
        selected = selected[:max_surfaces]
    return selected

def build_url(symbol, interval, outputsize, key):
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": str(outputsize),
        "timezone": "UTC",
        "format": "JSON",
        "apikey": key,
    }
    return BASE_URL + "?" + urllib.parse.urlencode(params)

def redacted_request(symbol, interval, outputsize):
    return {
        "path": "/time_series",
        "params": {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "timezone": "UTC",
            "format": "JSON",
            "apikey": REDACTED,
        }
    }

def provider_fetch(symbol, interval, outputsize, key, timeout):
    url = build_url(symbol, interval, outputsize, key)
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PRV1B-read-only-refresh/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = getattr(resp, "status", 200)
        elapsed_ms = int((time.time()-start)*1000)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "status_code": status, "elapsed_ms": elapsed_ms, "error": "provider_response_not_json", "data": None}
        if isinstance(data, dict) and data.get("status") == "error":
            return {"ok": False, "status_code": status, "elapsed_ms": elapsed_ms, "error": data.get("message") or "provider_status_error", "data": data}
        return {"ok": True, "status_code": status, "elapsed_ms": elapsed_ms, "error": None, "data": data}
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time()-start)*1000)
        try:
            body = e.read().decode("utf-8", "replace")
            data = json.loads(body)
        except Exception:
            data = None
        return {"ok": False, "status_code": e.code, "elapsed_ms": elapsed_ms, "error": str(e), "data": data}
    except Exception as e:
        elapsed_ms = int((time.time()-start)*1000)
        return {"ok": False, "status_code": None, "elapsed_ms": elapsed_ms, "error": type(e).__name__ + ": " + str(e), "data": None}

def summarize_values(data):
    values = []
    if isinstance(data, dict):
        values = data.get("values") or []
    times = [v.get("datetime") for v in values if isinstance(v, dict) and v.get("datetime")]
    return {
        "value_count": len(values),
        "first_provider_datetime": times[-1] if times else None,
        "last_provider_datetime": times[0] if times else None,
        "provider_status": data.get("status") if isinstance(data, dict) else None,
    }

def safe_provider_snapshot(surface, symbol, interval, fetched_at, data):
    # The provider response should not include the key. Store values + meta only.
    return {
        "program": "PRV1B-01",
        "artifact": "twelve_data_read_only_cache_snapshot",
        "surface": surface,
        "provider": "twelve_data",
        "provider_symbol": symbol,
        "interval": interval,
        "fetched_at_utc": fetched_at,
        "request": redacted_request(symbol, interval, None),
        "response": data,
        "boundary": {
            "read_only_provider_snapshot": True,
            "cache_not_source_authority": True,
            "not_signal": True,
            "not_execution": True,
        }
    }

def scan_for_secret(root: Path, secret: str, include_cache=False):
    if not secret:
        return []
    hits = []
    dirs = ["reports", "proofs", "logs", "panel"]
    if include_cache:
        dirs.append("data/provider_cache")
    for d in dirs:
        base = root/d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".json", ".md", ".html", ".txt", ".jsonl"}:
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if secret in txt:
                    hits.append(str(p.relative_to(root)))
    return hits

def forbidden_surface_scan(panel_obj):
    # This scans for action-surface structures, not boundary caveat words.
    banned_keys = {"broker_status", "execution_queue", "action_buttons", "position_instruction", "entry", "stop", "target", "pnl", "win_loss", "allocation", "order_ticket"}
    hits = []
    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                kl = str(k).lower()
                if kl in banned_keys:
                    hits.append(path + "/" + str(k))
                walk(v, path + "/" + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, path + f"[{i}]")
    walk(panel_obj)
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", default=".")
    ap.add_argument("--outputsize", type=int, default=160)
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--max-surfaces", type=int, default=0, help="Limit surfaces for a cautious first proof. 0 means all selected surfaces.")
    ap.add_argument("--all-cache-plan-surfaces", action="store_true", help="Fetch all V1 cache-plan surfaces rather than due/stale surfaces only.")
    ap.add_argument("--print-summary", action="store_true")
    args = ap.parse_args()
    root = Path(args.package_root).resolve()
    created = utc_now()
    key = os.environ.get(ENV_VAR, "")

    cfg, active, symbol_map = active_config(root)
    forbidden_active = sorted(set(active) & FORBIDDEN)
    scope_ok = set(active) == REQUIRED and not forbidden_active
    if not key or not scope_ok:
        report = {
            "program": "PRV1B-01",
            "artifact": "credentialed_refresh_blocked_report",
            "created_at_utc": created,
            "result": "blocked_before_provider_call",
            "credential_present": bool(key),
            "scope_ok": scope_ok,
            "active_instruments": active,
            "forbidden_active_present": forbidden_active,
            "network_call_performed": False,
            "boundary": BOUNDARY,
        }
        write_json(root/"reports/credentialed_refresh_blocked_report.json", report)
        if args.print_summary:
            print("PRV1B credentialed refresh blocked before provider call.")
            print(f"Credential present: {bool(key)}; scope_ok: {scope_ok}; active={active}")
        return 2

    surfaces = select_surfaces(root, active, due_only=not args.all_cache_plan_surfaces, max_surfaces=args.max_surfaces)
    fetch_rows = []
    cache_rows = []
    ok_count = 0
    fail_count = 0
    for row in surfaces:
        surface = row.get("surface")
        inst, tf = parse_surface(surface)
        symbol = symbol_map.get(inst, inst)
        interval = INTERVAL_MAP[tf]
        fetched_at = utc_now()
        result = provider_fetch(symbol, interval, args.outputsize, key, args.timeout)
        summ = summarize_values(result.get("data"))
        if result["ok"]:
            ok_count += 1
            safe_name = surface.replace(" ", "_") + ".json"
            rel_cache = Path("data/provider_cache/twelve_data")/safe_name
            snapshot = safe_provider_snapshot(surface, symbol, interval, fetched_at, result["data"])
            write_json(root/rel_cache, snapshot)
            cache_rows.append({
                "surface": surface,
                "cache_snapshot_file": str(rel_cache).replace("\\", "/"),
                "updated": True,
                **summ,
            })
        else:
            fail_count += 1
            cache_rows.append({
                "surface": surface,
                "cache_snapshot_file": None,
                "updated": False,
                "error": result["error"],
                **summ,
            })
        fetch_rows.append({
            "surface": surface,
            "instrument": inst,
            "timeframe": tf,
            "provider": "twelve_data",
            "provider_symbol": symbol,
            "interval": interval,
            "ok": result["ok"],
            "status_code": result["status_code"],
            "elapsed_ms": result["elapsed_ms"],
            "error": result["error"],
            "request": redacted_request(symbol, interval, args.outputsize),
            **summ,
            "boundary": {
                "read_only_provider_call": True,
                "not_signal": True,
                "not_execution": True,
                "not_source_truth": True,
            }
        })

    fetch_report = {
        "program": "PRV1B-01",
        "artifact": "provider_read_only_fetch_report",
        "created_at_utc": created,
        "provider": "twelve_data",
        "result": "completed_with_successes" if ok_count else "completed_with_no_successful_provider_rows",
        "credential_policy": {
            "env_var_used": ENV_VAR,
            "api_key_value_written": False,
            "api_key_redacted_as": REDACTED,
            "env_file_read": False,
        },
        "scope_status": {
            "active_instruments": active,
            "forbidden_active_present": forbidden_active,
            "scope_ok": scope_ok,
        },
        "selected_surface_count": len(surfaces),
        "successful_surface_count": ok_count,
        "failed_surface_count": fail_count,
        "surface_rows": fetch_rows,
        "not_performed": [
            "broker_connection", "order_creation", "execution", "signal_generation", "buy_sell_hold_generation",
            "entry_stop_target_generation", "PnL_or_win_loss_calculation", "optimizer_run", "validation_verdict",
            "adaptation_decision", "production_readiness_claim", "calendar_event_logic", "second_provider_conflict_check"
        ],
        "boundary": BOUNDARY,
    }
    write_json(root/"reports/provider_read_only_fetch_report.json", fetch_report)

    cache_report = {
        "program": "PRV1B-01",
        "artifact": "cache_update_report",
        "created_at_utc": utc_now(),
        "mode": "provider_snapshot_cache_update_from_read_only_fetch",
        "cache_not_source_authority": True,
        "surface_rows": cache_rows,
        "updated_surface_count": sum(1 for r in cache_rows if r.get("updated")),
        "failed_surface_count": sum(1 for r in cache_rows if not r.get("updated")),
        "xauusd_m5_caveat": "XAUUSD M5 is not fabricated into RSP cache feed plan if absent.",
        "boundary": BOUNDARY,
    }
    write_json(root/"reports/cache_update_report.json", cache_report)

    ledger = load_json(root/"ledger/candidate_observation_ledger_v1_exact.json", {})
    row_payload = load_json(root/"panel/row_level_panel_payload_v1_exact.json", {})
    ledger_refresh_report = {
        "program": "PRV1B-01",
        "artifact": "row_level_ledger_refresh_report",
        "created_at_utc": utc_now(),
        "mode": "credentialed_cache_refresh_with_existing_exact_row_ledger_preserved",
        "candidate_count_before": ledger.get("candidate_count"),
        "lifecycle_count_before": ledger.get("lifecycle_count"),
        "final_outcome_count_before": ledger.get("final_outcome_count"),
        "active_tracking_count_before": ledger.get("active_tracking_count"),
        "candidate_count_after": ledger.get("candidate_count"),
        "lifecycle_count_after": ledger.get("lifecycle_count"),
        "final_outcome_count_after": ledger.get("final_outcome_count"),
        "active_tracking_count_after": ledger.get("active_tracking_count"),
        "new_candidate_detection_performed": False,
        "lifecycle_classifier_run_performed": False,
        "reason": "PRV1B package proves credentialed read-only fetch/cache/panel refresh. It preserves exact SOT02 ledger unless a dedicated local SOT02 updater is explicitly run and supplied.",
        "exact_row_count_preserved": len(ledger.get("rows", [])) if isinstance(ledger.get("rows"), list) else None,
        "boundary": BOUNDARY,
    }
    write_json(root/"reports/row_level_ledger_refresh_report.json", ledger_refresh_report)

    panel_after = {
        "program": "PRV1B-01",
        "artifact": "panel_payload_after_credentialed_refresh",
        "created_at_utc": utc_now(),
        "panel_status": "display_ready_after_local_credentialed_read_only_refresh" if ok_count else "display_ready_but_provider_fetch_had_no_successful_rows",
        "active_instruments": active,
        "latest_exact_row_ledger_summary": {
            "candidate_count": ledger.get("candidate_count"),
            "lifecycle_count": ledger.get("lifecycle_count"),
            "status_counts": ledger.get("status_counts"),
            "outcome_counts": ledger.get("outcome_counts"),
            "active_tracking_count": ledger.get("active_tracking_count"),
            "final_outcome_count": ledger.get("final_outcome_count"),
            "row_quality_counts": ledger.get("row_quality_counts"),
        },
        "credentialed_refresh_summary": {
            "provider": "twelve_data",
            "selected_surface_count": len(surfaces),
            "successful_surface_count": ok_count,
            "failed_surface_count": fail_count,
            "cache_snapshots_written": [r.get("cache_snapshot_file") for r in cache_rows if r.get("cache_snapshot_file")],
            "api_key_redacted": True,
            "env_file_read": False,
            "cache_not_source_authority": True,
        },
        "row_level_payload_reference": "panel/row_level_panel_payload_v1_exact.json",
        "source_confidence": {
            "mode": "single_provider_caveated_only",
            "provider": "twelve_data",
            "is_source_truth": False,
            "second_provider_conflict_check": "out_of_v1_scope",
        },
        "calendar_event": "calendar_event_source_not_in_v1_scope",
        "display_banner": "DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Credentialed provider refresh is read-only cache context only; not signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, not production readiness.",
        "provider_surface_rows": [{k: v for k, v in r.items() if k not in {"request"}} for r in fetch_rows],
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
    write_json(root/"panel/panel_payload_after_credentialed_refresh.json", panel_after)
    html_rows = "".join(f"<tr><td>{r.get('surface')}</td><td>{r.get('ok')}</td><td>{r.get('value_count')}</td><td>{r.get('last_provider_datetime')}</td><td>{r.get('error') or ''}</td></tr>" for r in fetch_rows)
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PRV1B Credentialed Refresh Panel</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f7f7f7;color:#111}}.card{{background:white;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 2px 10px #ddd}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.banner{{background:#111;color:white}}</style></head><body>
<div class='card banner'><h1>PRV1B — Credentialed Read-Only Refresh</h1><p>Display-only. No signal, no execution, no broker, no entry/stop/target, no PnL.</p></div>
<div class='card'><h2>Refresh Summary</h2><p>Provider: twelve_data | Successful surfaces: {ok_count}/{len(surfaces)} | Active: {', '.join(active)}</p><p>Exact rows preserved: {ledger.get('candidate_count')} candidates, {ledger.get('final_outcome_count')} final, {ledger.get('active_tracking_count')} active.</p></div>
<div class='card'><h2>Provider Surface Rows</h2><table><thead><tr><th>Surface</th><th>OK</th><th>Values</th><th>Last provider datetime</th><th>Error</th></tr></thead><tbody>{html_rows}</tbody></table></div>
</body></html>"""
    (root/"panel/index_credentialed_refresh.html").write_text(html, encoding="utf-8")

    last_run = {
        "program": "PRV1B-01",
        "artifact": "last_run_status_after_credentialed_refresh",
        "created_at_utc": utc_now(),
        "status": "credentialed_read_only_refresh_completed" if ok_count else "credentialed_read_only_refresh_completed_with_no_successful_provider_rows",
        "mode": "local_credentialed_read_only_cache_update_display_only",
        "active_instruments": active,
        "provider": "twelve_data",
        "selected_surface_count": len(surfaces),
        "successful_surface_count": ok_count,
        "failed_surface_count": fail_count,
        "api_key_requested_or_written": False,
        "env_file_read": False,
        "broker_connection_attempted": False,
        "orders_created": False,
        "signals_generated": False,
        "panel_payload_generated": True,
        "boundary": BOUNDARY,
    }
    heartbeat = {
        "program": "PRV1B-01",
        "artifact": "runtime_heartbeat_after_credentialed_refresh",
        "created_at_utc": utc_now(),
        "heartbeat_status": "credentialed_read_only_refresh_file_written",
        "runtime_mode": "local_credentialed_read_only_display_only",
        "scope_ok": scope_ok,
        "active_instruments": active,
        "successful_surface_count": ok_count,
        "scheduler_claim": "heartbeat_file_written_only_no_background_scheduler_claimed",
        "not_production_readiness": True,
        "boundary": BOUNDARY,
    }
    write_json(root/"logs/last_run_status_after_credentialed_refresh.json", last_run)
    write_json(root/"logs/runtime_heartbeat_after_credentialed_refresh.json", heartbeat)

    # Proofs after all files are written.
    secret_hits = scan_for_secret(root, key, include_cache=True)
    secret_proof = {
        "program": "PRV1B-01",
        "artifact": "secret_redaction_proof",
        "created_at_utc": utc_now(),
        "env_var_used": ENV_VAR,
        "api_key_value_written": bool(secret_hits),
        "secret_hit_files": secret_hits,
        "redacted_request_marker_expected": REDACTED,
        "env_file_read": False,
        "verdict": "passed_no_secret_found_in_generated_outputs" if not secret_hits else "failed_secret_found_in_generated_outputs",
        "boundary": BOUNDARY,
    }
    write_json(root/"proofs/secret_redaction_proof.json", secret_proof)
    action_hits = forbidden_surface_scan(panel_after)
    no_action = {
        "program": "PRV1B-01",
        "artifact": "no_action_surface_proof",
        "created_at_utc": utc_now(),
        "forbidden_action_surface_keys_present": action_hits,
        "action_surface_absent": not action_hits,
        "note": "Boundary/caveat wording can negate forbidden concepts; this proof checks generated action structures.",
        "boundary": BOUNDARY,
    }
    write_json(root/"proofs/no_action_surface_proof.json", no_action)
    bound = {
        "program": "PRV1B-01",
        "artifact": "credentialed_refresh_boundary_proof",
        "created_at_utc": utc_now(),
        "status": "passed_with_caveats" if not secret_hits and not action_hits else "failed_or_requires_review",
        "read_only_provider_calls_only": True,
        "api_key_redacted": not secret_hits,
        "api_key_not_written": not secret_hits,
        "single_provider_caveated_only": True,
        "calendar_event_not_in_v1_scope": True,
        "second_provider_not_in_v1_scope": True,
        "local_execution_proof_required": False,
        "successful_surface_count": ok_count,
        "failed_surface_count": fail_count,
        "boundary": BOUNDARY,
    }
    write_json(root/"proofs/credentialed_refresh_boundary_proof.json", bound)

    delivery = {
        "program": "PRV1B-01",
        "artifact": "credentialed_refresh_delivery_pack_index",
        "created_at_utc": utc_now(),
        "verdict": "package_built_for_local_credentialed_read_only_refresh_proof",
        "local_run_outputs_expected_after_user_execution": [
            "reports/credentialed_refresh_preflight_report.json",
            "reports/provider_read_only_fetch_report.json",
            "reports/cache_update_report.json",
            "reports/row_level_ledger_refresh_report.json",
            "panel/panel_payload_after_credentialed_refresh.json",
            "panel/index_credentialed_refresh.html",
            "logs/last_run_status_after_credentialed_refresh.json",
            "logs/runtime_heartbeat_after_credentialed_refresh.json",
            "proofs/secret_redaction_proof.json",
            "proofs/no_action_surface_proof.json",
            "proofs/credentialed_refresh_boundary_proof.json"
        ],
        "boundary": BOUNDARY,
    }
    write_json(root/"reports/PRV1B_credentialed_refresh_delivery_pack_index.json", delivery)

    if args.print_summary:
        print("PRV1B credentialed read-only refresh completed.")
        print(f"Provider: twelve_data; surfaces OK: {ok_count}/{len(surfaces)}; failed: {fail_count}")
        print("Panel: panel/index_credentialed_refresh.html")
        print("Secret proof:", secret_proof["verdict"])
        print("No-action-surface proof:", no_action["action_surface_absent"])
    return 0 if not secret_hits and not action_hits else 3

if __name__ == "__main__":
    raise SystemExit(main())
