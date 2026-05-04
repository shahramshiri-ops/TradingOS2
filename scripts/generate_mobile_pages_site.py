import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

BOUNDARY_KEYS = [
    "runtime_observation_not_signal",
    "candidate_not_trade_recommendation",
    "outcome_observation_not_win_loss",
    "lifecycle_tracking_not_execution_tracking",
    "cache_not_source_authority",
    "single_provider_confidence_not_source_truth",
    "scheduler_heartbeat_not_production_readiness",
    "panel_payload_not_action_surface",
    "no_broker",
    "no_order",
    "no_execution",
    "no_buy_sell_hold",
    "no_entry_stop_target",
    "no_pnl",
    "no_optimizer",
    "no_validation_verdict",
    "no_adaptation_decision",
    "no_production_readiness_claim",
]


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def h(value):
    return html.escape("" if value is None else str(value))


def main():
    parser = argparse.ArgumentParser(description="Build static mobile PRV1 GitHub Pages site from latest daily runtime outputs.")
    parser.add_argument("--package-root", default=".")
    parser.add_argument("--site-dir", default="site")
    parser.add_argument("--repo", default="")
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    root = Path(args.package_root).resolve()
    site = Path(args.site_dir).resolve()
    site.mkdir(parents=True, exist_ok=True)

    panel = read_json(root / "panel" / "panel_payload_after_daily_runtime.json", {}) or read_json(root / "panel" / "panel_payload_current.json", {}) or {}
    status = read_json(root / "logs" / "last_run_status_after_daily_runtime.json", {}) or read_json(root / "logs" / "last_run_status_current.json", {}) or {}
    heartbeat = read_json(root / "logs" / "runtime_heartbeat_after_daily_runtime.json", {}) or read_json(root / "logs" / "runtime_heartbeat_current.json", {}) or {}
    validation = read_json(root / "proofs" / "daily_runtime_local_validation_result.json", {}) or {}
    boundary = read_json(root / "proofs" / "daily_runtime_boundary_proof.json", {}) or {}
    no_action = read_json(root / "proofs" / "daily_runtime_no_action_surface_proof.json", {}) or {}
    secret = read_json(root / "proofs" / "daily_runtime_secret_redaction_proof.json", {}) or {}

    summary = panel.get("summary") or panel.get("latest_exact_row_ledger_summary") or {}
    daily_summary = panel.get("daily_runtime_summary") or panel.get("post_refresh_update_summary") or {}
    staged = panel.get("staged_refresh_summary") or {}
    detection = panel.get("candidate_detection_summary") or {}

    active = panel.get("active_instruments") or status.get("active_instruments") or ["XAUUSD", "EURUSD", "USDJPY"]
    candidate_count = status.get("candidate_count", summary.get("candidate_count", summary.get("merged_candidate_lifecycle_row_count")))
    lifecycle_count = status.get("lifecycle_count", summary.get("lifecycle_count", summary.get("merged_candidate_lifecycle_row_count")))
    final_outcome_count = status.get("final_outcome_count", summary.get("final_outcome_count"))
    active_tracking_count = status.get("active_tracking_count", summary.get("active_tracking_count"))
    new_candidate_count = status.get("new_observation_candidate_count", detection.get("new_observation_candidate_count", daily_summary.get("new_observation_candidate_count")))

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    repo = args.repo
    actions_url = f"https://github.com/{repo}/actions/workflows/prv1_daily_runtime_mobile_panel.yml" if repo else ""
    run_url = f"https://github.com/{repo}/actions/runs/{args.run_id}" if repo and args.run_id else ""

    public_payload = {
        "program": "PRV1H-01",
        "artifact": "mobile_static_panel_payload",
        "built_at_utc": built_at,
        "repo": repo,
        "github_run_id": args.run_id,
        "active_instruments": active,
        "counts": {
            "candidate_count": candidate_count,
            "lifecycle_count": lifecycle_count,
            "final_outcome_count": final_outcome_count,
            "active_tracking_count": active_tracking_count,
            "new_observation_candidate_count": new_candidate_count,
        },
        "validation": {
            "daily_runtime_validation_passed": validation.get("validation_passed"),
            "boundary_status": validation.get("boundary_status") or boundary.get("status"),
            "secret_redaction_passed": validation.get("secret_redaction_passed") or secret.get("verdict"),
            "no_action_surface_passed": validation.get("no_action_surface_passed") or no_action.get("verdict"),
        },
        "staged_refresh": staged,
        "candidate_detection": detection,
        "status": status,
        "heartbeat": heartbeat,
        "boundary": {k: True for k in BOUNDARY_KEYS},
        "mobile_panel_note": "Static display-only panel. Refresh is triggered by GitHub Actions schedule or manual workflow dispatch, not by an in-panel backend button."
    }
    write_json(site / "panel_payload_public.json", public_payload)
    write_json(site / "status_public.json", {"status": status, "heartbeat": heartbeat, "validation": validation})

    def pill(label, value):
        return f"<div class='pill'><div class='pill-label'>{h(label)}</div><div class='pill-value'>{h(value)}</div></div>"

    action_button = ""
    if actions_url:
        action_button = f"<a class='button' href='{h(actions_url)}' target='_blank' rel='noopener'>Refresh via GitHub Actions</a>"
    run_button = f"<a class='button secondary' href='{h(run_url)}' target='_blank' rel='noopener'>Open latest run</a>" if run_url else ""

    surface_ok = staged.get("successful_surface_count")
    surface_fail = staged.get("failed_surface_count")
    valid_cache = detection.get("valid_cache_surface_count")

    index = f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>PRV1 Mobile Runtime Panel</title>
  <style>
    :root {{ --bg:#0f172a; --card:#111827; --card2:#1f2937; --text:#f9fafb; --muted:#9ca3af; --ok:#22c55e; --warn:#f59e0b; --line:#374151; }}
    body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:var(--bg); color:var(--text); }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 18px; }}
    .card {{ background: var(--card); border:1px solid var(--line); border-radius:18px; padding:16px; margin:12px 0; box-shadow:0 8px 30px rgba(0,0,0,.2); }}
    .hero {{ background: linear-gradient(135deg,#111827,#1e293b); }}
    h1 {{ font-size: 24px; margin:0 0 8px; }}
    h2 {{ font-size: 18px; margin:0 0 12px; }}
    p {{ color:var(--muted); line-height:1.5; }}
    .grid {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; }}
    .pill {{ background:var(--card2); border:1px solid var(--line); border-radius:14px; padding:12px; }}
    .pill-label {{ color:var(--muted); font-size:12px; }}
    .pill-value {{ font-size:22px; font-weight:700; margin-top:2px; }}
    .button {{ display:block; text-align:center; background:#2563eb; color:white; text-decoration:none; border-radius:14px; padding:14px 16px; margin:10px 0; font-weight:700; }}
    .secondary {{ background:#334155; }}
    .ok {{ color:var(--ok); font-weight:700; }}
    .warn {{ color:var(--warn); font-weight:700; }}
    code {{ color:#e5e7eb; background:#020617; padding:2px 6px; border-radius:6px; }}
    .small {{ font-size:12px; color:var(--muted); }}
    @media (min-width: 700px) {{ .grid {{ grid-template-columns: repeat(5, minmax(0,1fr)); }} h1 {{ font-size:30px; }} }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='card hero'>
      <h1>PRV1 Mobile Runtime Panel</h1>
      <p>Display-only personal runtime observation. No signal, no broker, no order, no execution, no buy/sell/hold, no entry/stop/target, no PnL, no validation verdict.</p>
      <p class='small'>Built at UTC: <code>{h(built_at)}</code></p>
    </div>

    <div class='card'>
      <h2>Daily state</h2>
      <div class='grid'>
        {pill('Candidates', candidate_count)}
        {pill('Lifecycle', lifecycle_count)}
        {pill('Final outcomes', final_outcome_count)}
        {pill('Active tracking', active_tracking_count)}
        {pill('New candidates', new_candidate_count)}
      </div>
    </div>

    <div class='card'>
      <h2>Refresh / validation</h2>
      <p>Active instruments: <strong>{h(', '.join(active))}</strong></p>
      <p>Provider surfaces: <span class='ok'>{h(surface_ok)}</span> successful / <span class='warn'>{h(surface_fail)}</span> failed. Valid cache surfaces: <span class='ok'>{h(valid_cache)}</span>.</p>
      <p>Boundary status: <strong>{h(validation.get('boundary_status') or boundary.get('status'))}</strong></p>
      {action_button}
      {run_button}
      <p class='small'>On GitHub Pages, the refresh control links to GitHub Actions. A true in-panel refresh button requires a backend service such as Cloud Run and is outside this static-free setup.</p>
    </div>

    <div class='card'>
      <h2>Scope locks</h2>
      <p>Source confidence: single-provider caveated only. Calendar/event: not in V1 scope. SPX/NQ: out of active V1 scope.</p>
      <p class='small'>Files: <a style='color:#93c5fd' href='panel_payload_public.json'>panel_payload_public.json</a> · <a style='color:#93c5fd' href='status_public.json'>status_public.json</a></p>
    </div>
  </div>
</body>
</html>"""
    (site / "index.html").write_text(index, encoding="utf-8")

    print(json.dumps({
        "program": "PRV1H-01",
        "site_built": True,
        "site_dir": str(site),
        "built_at_utc": built_at,
        "candidate_count": candidate_count,
        "lifecycle_count": lifecycle_count,
        "final_outcome_count": final_outcome_count,
        "active_tracking_count": active_tracking_count,
        "new_observation_candidate_count": new_candidate_count,
        "actions_url": actions_url,
        "boundary": {k: True for k in BOUNDARY_KEYS}
    }, indent=2))


if __name__ == "__main__":
    main()
