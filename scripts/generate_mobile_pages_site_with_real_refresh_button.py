
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from html import escape
BOUNDARY = {"runtime_observation_not_signal": True, "candidate_not_trade_recommendation": True, "outcome_observation_not_win_loss": True, "panel_payload_not_action_surface": True, "no_broker": True, "no_execution": True, "no_buy_sell_hold": True, "no_entry_stop_target": True, "no_pnl": True, "no_validation_verdict": True, "no_production_readiness_claim": True}

def read_json(path: Path) -> dict:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def first_present(*vals, default=None):
    for v in vals:
        if v is not None: return v
    return default

def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
    root = root.resolve(); public = root/'public'; public.mkdir(parents=True, exist_ok=True)
    panel = read_json(root/'panel'/'panel_payload_after_daily_runtime.json')
    validation = read_json(root/'proofs'/'daily_runtime_local_validation_result.json')
    last_run = read_json(root/'logs'/'last_run_status_after_daily_runtime.json')
    staged = read_json(root/'reports'/'staged_provider_fetch_report.json')
    detection = read_json(root/'reports'/'candidate_detection_report.json')
    summary = panel.get('summary') or panel.get('latest_exact_row_ledger_summary') or {}
    staged_summary = panel.get('staged_refresh_summary') or {}
    detection_summary = panel.get('candidate_detection_summary') or {}
    candidate_count = first_present(summary.get('candidate_count'), last_run.get('candidate_count'), default=0)
    lifecycle_count = first_present(summary.get('lifecycle_count'), last_run.get('lifecycle_count'), default=0)
    final_outcome_count = first_present(summary.get('final_outcome_count'), last_run.get('final_outcome_count'), default=0)
    active_tracking_count = first_present(summary.get('active_tracking_count'), last_run.get('active_tracking_count'), default=0)
    new_candidate_count = first_present(detection_summary.get('new_observation_candidate_count'), detection.get('new_observation_candidate_count'), last_run.get('new_observation_candidate_count'), default=0)
    successful_surfaces = first_present(staged_summary.get('successful_surface_count'), staged.get('successful_surface_count'), default=None)
    failed_surfaces = first_present(staged_summary.get('failed_surface_count'), staged.get('failed_surface_count'), default=None)
    selected_surfaces = first_present(staged_summary.get('selected_surface_count'), staged.get('selected_surface_count'), default=None)
    valid_cache_surfaces = first_present(detection_summary.get('valid_cache_surface_count'), detection.get('valid_cache_surface_count'), default=None)
    refresh_url = os.environ.get('MOBILE_REFRESH_WORKER_URL','').strip().rstrip('/')
    pages_url = os.environ.get('GITHUB_PAGES_URL','').strip()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    status_public = {"program":"PRV1I-01","artifact":"mobile_status_public_with_refresh_button","created_at_utc":generated_at,"panel_status":panel.get('panel_status') or 'display_ready_after_daily_runtime',"active_instruments":panel.get('active_instruments') or ['XAUUSD','EURUSD','USDJPY'],"candidate_count":candidate_count,"lifecycle_count":lifecycle_count,"final_outcome_count":final_outcome_count,"active_tracking_count":active_tracking_count,"new_observation_candidate_count":new_candidate_count,"selected_surface_count":selected_surfaces,"successful_surface_count":successful_surfaces,"failed_surface_count":failed_surfaces,"valid_cache_surface_count":valid_cache_surfaces,"validation_passed":validation.get('validation_passed'),"boundary_status":validation.get('boundary_status'),"refresh_button":{"enabled":bool(refresh_url),"worker_url_configured":bool(refresh_url),"worker_health_url":f'{refresh_url}/health' if refresh_url else None},"boundary":BOUNDARY}
    write_json(public/'status_public.json', status_public)
    (public/'refresh_config.js').write_text('window.PRV1_REFRESH_WORKER_URL = '+json.dumps(refresh_url)+';\nwindow.PRV1_GITHUB_PAGES_URL = '+json.dumps(pages_url)+';\n', encoding='utf-8')
    (public/'mobile_refresh_button.js').write_text("""
async function prv1RefreshNow(){
  const endpoint=(window.PRV1_REFRESH_WORKER_URL||'').replace(/\/$/,'');
  const box=document.getElementById('refresh-status');
  if(!endpoint){box.textContent='Refresh endpoint is not configured. Use GitHub Actions manual run.';box.className='status warn';return;}
  const pin=prompt('Enter refresh PIN');
  if(!pin){box.textContent='Refresh cancelled.';box.className='status warn';return;}
  box.textContent='Sending refresh request...';box.className='status pending';
  try{const res=await fetch(endpoint+'/refresh',{method:'POST',headers:{'content-type':'application/json','x-refresh-pin':pin},body:JSON.stringify({source:'mobile_panel',requested_at:new Date().toISOString()})});const data=await res.json();if(!res.ok)throw new Error(data.reason||data.status||('HTTP '+res.status));box.textContent='Refresh requested. GitHub Actions is running. Wait a few minutes, then reload this page.';box.className='status ok';prv1PollLatestRun(endpoint);}catch(e){box.textContent='Refresh failed: '+e.message;box.className='status error';}}
async function prv1PollLatestRun(endpoint){const box=document.getElementById('latest-run-status');if(!box)return;for(let i=0;i<12;i++){await new Promise(r=>setTimeout(r,10000));try{const res=await fetch(endpoint+'/latest-run');const data=await res.json();const run=data.latest_run;if(run){box.innerHTML='Latest run: <b>'+run.status+'</b>'+(run.conclusion?' / '+run.conclusion:'')+' — <a href="'+run.html_url+'" target="_blank">open</a>';if(run.status==='completed')break;}}catch(_){}}}
window.addEventListener('DOMContentLoaded',()=>{const btn=document.getElementById('refresh-now-button');if(btn)btn.addEventListener('click',prv1RefreshNow);});
""", encoding='utf-8')
    def safe(v): return escape(str(v if v is not None else '—'))
    html = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>PRV1 Mobile Runtime Panel</title><style>body{{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;margin:0;background:#f4f6fb;color:#111827}}.wrap{{max-width:920px;margin:0 auto;padding:18px}}.banner{{background:#0f172a;color:white;border-radius:18px;padding:18px;box-shadow:0 8px 28px rgba(15,23,42,.18)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin-top:14px}}.card{{background:white;border-radius:16px;padding:16px;box-shadow:0 6px 22px rgba(15,23,42,.08)}}.label{{color:#64748b;font-size:13px}}.num{{font-size:34px;font-weight:800}}button{{width:100%;border:0;border-radius:14px;padding:15px;background:#2563eb;color:white;font-size:17px;font-weight:800}}.status{{margin-top:10px;padding:12px;border-radius:12px;font-size:14px}}.ok{{background:#dcfce7;color:#14532d}}.warn{{background:#fef9c3;color:#713f12}}.error{{background:#fee2e2;color:#7f1d1d}}.pending{{background:#dbeafe;color:#1e3a8a}}.small{{font-size:13px;color:#475569;line-height:1.55}}.pill{{display:inline-block;background:#e2e8f0;border-radius:999px;padding:6px 10px;margin:3px;font-size:13px}}a{{color:#2563eb}}</style></head><body><div class='wrap'><div class='banner'><h1>PRV1 Mobile Runtime Panel</h1><p>Display-only personal runtime observation. Not signal, not execution, not broker/order, not PnL, not validation verdict, not production readiness.</p></div><div class='grid'><div class='card'><div class='label'>Candidates</div><div class='num'>{safe(candidate_count)}</div></div><div class='card'><div class='label'>Lifecycle</div><div class='num'>{safe(lifecycle_count)}</div></div><div class='card'><div class='label'>Final outcomes</div><div class='num'>{safe(final_outcome_count)}</div></div><div class='card'><div class='label'>Active tracking</div><div class='num'>{safe(active_tracking_count)}</div></div><div class='card'><div class='label'>New candidates</div><div class='num'>{safe(new_candidate_count)}</div></div><div class='card'><div class='label'>Boundary</div><div class='num' style='font-size:24px'>{safe(validation.get('boundary_status','—'))}</div></div></div><div class='card'><h2>Refresh</h2><button id='refresh-now-button'>Refresh Now</button><div id='refresh-status' class='status {'ok' if refresh_url else 'warn'}'>{'Refresh endpoint configured.' if refresh_url else 'Refresh endpoint not configured yet. Set MOBILE_REFRESH_WORKER_URL after deploying the Cloudflare Worker.'}</div><div id='latest-run-status' class='small'></div><p class='small'>This button triggers GitHub Actions through a Cloudflare Worker. It does not run broker, execution, signal, PnL, or validation logic in the browser or Worker.</p></div><div class='card'><h2>Provider / cache</h2><p>Surfaces: {safe(successful_surfaces)} successful / {safe(failed_surfaces)} failed / {safe(selected_surfaces)} selected.</p><p>Valid cache surfaces: {safe(valid_cache_surfaces)}.</p><p class='small'>Source confidence is single-provider caveated context only; not source truth.</p></div><div class='card'><h2>Active instruments</h2><span class='pill'>XAUUSD</span><span class='pill'>EURUSD</span><span class='pill'>USDJPY</span></div><div class='card small'><h2>Last generated</h2><p>{escape(generated_at)}</p><p><a href='status_public.json'>status_public.json</a></p></div></div><script src='refresh_config.js'></script><script src='mobile_refresh_button.js'></script></body></html>"""
    (public/'index.html').write_text(html, encoding='utf-8')
    proof={"program":"PRV1I-01","artifact":"mobile_pages_real_refresh_button_generation_proof","created_at_utc":generated_at,"refresh_worker_url_configured":bool(refresh_url),"secrets_written_to_public_site":False,"api_key_or_pat_written":False,"outputs":["public/index.html","public/status_public.json","public/refresh_config.js","public/mobile_refresh_button.js"],"boundary":BOUNDARY}
    write_json(root/'proofs'/'mobile_refresh_button_generation_proof.json', proof)
    print(json.dumps(proof, indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
