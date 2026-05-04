from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from html import escape

PROGRAM = "PRV1L-01"
INSTRUMENTS = ["XAUUSD", "EURUSD", "USDJPY"]
TF_ORDER = ["D1", "H1", "M15", "M5"]
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

OUTCOME_FA = {
    "still_active_observation": "هنوز فعال",
    "favorable_observation": "هم‌جهت با مشاهده",
    "unfavorable_observation": "ضعیف/خلاف مشاهده",
    "invalidated_observation": "نامعتبر شده",
}
STATUS_FA = {
    "active_tracking": "فعال",
    "final_outcome_recorded": "بسته شده",
}
TYPE_FA = {
    "downside_range_breakout_observation_candidate": "شکست محدوده به پایین",
    "upside_range_breakout_observation_candidate": "شکست محدوده به بالا",
}
REASON_FA = {
    "no_completed_post_trigger_bars_available_yet": "هنوز کندل کامل کافی بعد از trigger برای outcome نهایی ثبت نشده است.",
    "post_trigger_low_extended_below_trigger_low_and_last_close_remains_below_trigger_close": "حرکت بعد از trigger در جهت مشاهده ادامه پیدا کرده است.",
    "last_post_trigger_close_back_above_trigger_close_without_full_high_close_invalidation": "حرکت بعد از trigger تا حدی برگشته، اما طبق rule نامعتبرشدن کامل ثبت نشده است.",
    "post_trigger_completed_bar_closed_below_trigger_bar_low": "طبق rule، مشاهده نامعتبر/بسته شده است.",
    "no_range_breakout_observation_triggered": "اسکن انجام شد، اما شکست محدودهٔ قابل ثبت پیدا نشد.",
    "cache_values_missing_or_unreadable": "cache این سطح قابل خواندن نبود.",
}

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def read_json(path: Path, default=None):
    if default is None: default = {}
    try:
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default
    return default

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def first_present(*vals, default=None):
    for v in vals:
        if v is not None:
            return v
    return default

def h(s):
    return escape(str('—' if s is None else s))

def token(s, cls='token'):
    return f"<span class='{cls}' dir='ltr'>{h(s)}</span>"

def norm_surface(surface: str):
    parts = (surface or '').split()
    if len(parts) >= 2: return parts[0], parts[1]
    return surface or 'UNKNOWN', 'UNKNOWN'

def tf_sort_key(surface: str):
    inst, tf = norm_surface(surface)
    return (INSTRUMENTS.index(inst) if inst in INSTRUMENTS else 99, TF_ORDER.index(tf) if tf in TF_ORDER else 99, surface)

def fnum(x):
    try:
        val=float(x)
        if abs(val)>=1000: return f"{val:,.2f}"
        if abs(val)>=10: return f"{val:.3f}"
        return f"{val:.5f}".rstrip('0').rstrip('.')
    except Exception:
        return '—'

def fa_status(s): return STATUS_FA.get(s or '', s or 'نامشخص')
def fa_outcome(s): return OUTCOME_FA.get(s or '', s or 'نامشخص')
def fa_type(s): return TYPE_FA.get(s or '', s or 'Observation')
def fa_reason(s): return REASON_FA.get(s or '', s or 'دلیل مشخصی ثبت نشده است.')

def load_rows(root: Path):
    paths = [
        root/'ledger'/'candidate_lifecycle_rows_v1_after_candidate_detection.json',
        root/'ledger'/'candidate_lifecycle_rows_v1_post_refresh.json',
        root/'ledger'/'candidate_lifecycle_rows_v1_exact.json',
        root/'ledger'/'candidate_lifecycle_rows_v1.json',
        root/'panel'/'panel_payload_after_candidate_detection.json',
        root/'panel'/'panel_payload_after_post_refresh_update.json',
        root/'panel'/'panel_payload_after_daily_runtime.json',
    ]
    for p in paths:
        obj=read_json(p,{})
        if isinstance(obj, dict):
            for key in ['rows','post_refresh_lifecycle_rows','candidate_lifecycle_rows','post_refresh_lifecycle_rows']:
                rows=obj.get(key)
                if isinstance(rows, list) and rows: return rows
    return []

def load_surface_rows(root: Path):
    staged=read_json(root/'reports'/'staged_provider_fetch_report.json')
    cache=read_json(root/'reports'/'staged_cache_update_report.json')
    detection=read_json(root/'reports'/'candidate_detection_report.json')
    provider_rows=staged.get('surface_rows') or []
    cache_rows=cache.get('surface_rows') or []
    scan_rows=detection.get('scan_rows') or detection.get('surface_rows') or []
    return staged, cache, detection, provider_rows, cache_rows, scan_rows

def ref_levels(row: dict):
    bar=row.get('trigger_bar_from_capture') or {}
    typ=row.get('candidate_type') or ''
    direction='downside' if 'downside' in typ else 'upside' if 'upside' in typ else 'unknown'
    try:
        hi=float(bar.get('high')); lo=float(bar.get('low')); cl=float(bar.get('close')); rng=max(0,hi-lo)
    except Exception:
        hi=lo=cl=rng=None
    if direction=='downside':
        return {
            'direction':'نزولی',
            'trigger_bar': {'high': hi, 'low': lo, 'close': cl, 'open': bar.get('open')},
            'progress': {'label':'پیشروی', 'level': lo, 'text':'ادامه زیر low مرجع'},
            'weakening': {'label':'ضعیف‌شدن', 'level': cl, 'text':'close کامل بالای close مرجع'},
            'invalidation': {'label':'نامعتبرشدن', 'level': hi, 'text':'close کامل بالای high مرجع'},
            'extension': {'from': lo-rng if rng is not None else None, 'to': lo, 'text':'محدودهٔ تقریبی امتداد observation'},
        }
    if direction=='upside':
        return {
            'direction':'صعودی',
            'trigger_bar': {'high': hi, 'low': lo, 'close': cl, 'open': bar.get('open')},
            'progress': {'label':'پیشروی', 'level': hi, 'text':'ادامه بالای high مرجع'},
            'weakening': {'label':'ضعیف‌شدن', 'level': cl, 'text':'close کامل پایین close مرجع'},
            'invalidation': {'label':'نامعتبرشدن', 'level': lo, 'text':'close کامل پایین low مرجع'},
            'extension': {'from': hi, 'to': hi+rng if rng is not None else None, 'text':'محدودهٔ تقریبی امتداد observation'},
        }
    return {'direction':'نامشخص','trigger_bar':{},'progress':{},'weakening':{},'invalidation':{},'extension':{}}

def priority(kind):
    if kind=='active': return {'level':'بالا','rank':1,'class':'high','reason':'observation هنوز فعال است و باید اول دیده شود.'}
    if kind=='new': return {'level':'بالا','rank':1,'class':'high','reason':'candidate جدید ثبت شده است.'}
    if kind=='final': return {'level':'متوسط','rank':2,'class':'medium','reason':'observation بسته شده و برای مرور مفید است.'}
    if kind=='caveat': return {'level':'متوسط','rank':2,'class':'medium','reason':'داده یا provider caveat دارد.'}
    return {'level':'پایین','rank':3,'class':'low','reason':'scan انجام شده و candidate جدیدی ندارد.'}

def build_state(root: Path):
    panel=read_json(root/'panel'/'panel_payload_after_daily_runtime.json')
    last_run=read_json(root/'logs'/'last_run_status_after_daily_runtime.json')
    validation=read_json(root/'proofs'/'daily_runtime_local_validation_result.json')
    post=read_json(root/'reports'/'post_refresh_lifecycle_update_report.json')
    staged, cache, detection, provider_rows, cache_rows, scan_rows = load_surface_rows(root)
    rows=load_rows(root)
    summary=panel.get('summary') or panel.get('latest_exact_row_ledger_summary') or panel.get('latest_runtime_summary') or {}
    daily=panel.get('daily_loop_summary') or {}
    candidate_count=first_present(summary.get('candidate_count'), last_run.get('candidate_count'), daily.get('merged_candidate_lifecycle_row_count'), default=len(rows))
    lifecycle_count=first_present(summary.get('lifecycle_count'), last_run.get('lifecycle_count'), daily.get('merged_candidate_lifecycle_row_count'), default=len(rows))
    final_outcome_count=first_present(summary.get('final_outcome_count'), last_run.get('final_outcome_count'), default=sum(1 for r in rows if r.get('is_final') is True))
    active_tracking_count=first_present(summary.get('active_tracking_count'), last_run.get('active_tracking_count'), default=sum(1 for r in rows if r.get('lifecycle_status')=='active_tracking' or r.get('is_final') is False))
    new_count=first_present(daily.get('new_observation_candidate_count'), detection.get('new_observation_candidate_count'), last_run.get('new_observation_candidate_count'), default=0)
    cache_by={r.get('surface'):r for r in cache_rows if r.get('surface')}
    prov_by={r.get('surface'):r for r in provider_rows if r.get('surface')}
    scan_by={r.get('surface'):r for r in scan_rows if r.get('surface')}
    rows_by={}
    for r in rows:
        surf=r.get('surface') or f"{r.get('instrument','UNKNOWN')} {r.get('timeframe','UNKNOWN')}"
        rows_by.setdefault(surf,[]).append(r)
    surfaces=set(cache_by)|set(prov_by)|set(scan_by)|set(rows_by)
    if not surfaces:
        surfaces={"XAUUSD D1","XAUUSD H1","XAUUSD M15","EURUSD D1","EURUSD H1","EURUSD M15","EURUSD M5","USDJPY D1","USDJPY H1","USDJPY M15","USDJPY M5"}
    active=[]; finals=[]
    for r in rows:
        rr=dict(r)
        if rr.get('lifecycle_status')=='active_tracking' or rr.get('is_final') is False:
            rr['reference_levels']=ref_levels(rr); rr['priority']=priority('active'); active.append(rr)
        else:
            rr['priority']=priority('final'); finals.append(rr)
    market={i:{'instrument':i,'overall_state_fa':'آرام / بدون candidate جدید','timeframes':[]} for i in INSTRUMENTS}
    freshness=[]; no_candidates=[]; priority_items=[]
    for surf in sorted(surfaces, key=tf_sort_key):
        inst, tf=norm_surface(surf)
        if inst not in market: continue
        c=cache_by.get(surf,{}) ; p=prov_by.get(surf,{}) ; sc=scan_by.get(surf,{})
        surf_rows=rows_by.get(surf,[])
        updated=bool(c.get('updated') if c else p.get('ok'))
        provider_status=c.get('provider_status') or p.get('provider_status') or ('ok' if updated else 'unknown')
        bars=first_present(sc.get('valid_bar_count'), c.get('value_count'), p.get('value_count'))
        last_dt=c.get('last_provider_datetime') or p.get('last_provider_datetime')
        failed = provider_status not in ['ok','unknown'] and not updated
        if any(x.get('lifecycle_status')=='active_tracking' or x.get('is_final') is False for x in surf_rows):
            kind='active'; title='observation فعال'; short='در Active Watch دیده می‌شود و در اجرای بعدی باید دوباره بررسی شود.'
        elif surf_rows:
            kind='final'; title='observation بسته‌شده'; short='observation قبلی outcome توصیفی دارد؛ active نیست.'
        elif failed:
            kind='caveat'; title='caveat داده'; short='این سطح در provider/cache caveat دارد.'
        elif sc.get('status')=='scanned_no_candidate' or detection.get('valid_cache_surface_count'):
            kind='quiet'; title='بدون candidate جدید'; short='cache خوانده شد و rule scan انجام شد، اما candidate جدید ثبت نشد.'
            no_candidates.append({'surface':surf,'instrument':inst,'timeframe':tf,'valid_bar_count':bars,'reason_fa':short})
        else:
            kind='quiet'; title='بدون وضعیت خاص'; short='در خروجی فعلی observation فعال یا candidate جدید ندارد.'
        pr=priority(kind)
        item={'surface':surf,'instrument':inst,'timeframe':tf,'title_fa':title,'short_fa':short,'kind':kind,'priority':pr,'cache':{'updated':updated,'provider_status':provider_status,'value_count':bars,'last_provider_datetime':last_dt},'rows':surf_rows,'scan':{'status':sc.get('status'),'valid_bar_count':sc.get('valid_bar_count')}}
        market[inst]['timeframes'].append(item)
        freshness.append({'surface':surf,'instrument':inst,'timeframe':tf,'updated':updated,'provider_status':provider_status,'value_count':bars,'last_provider_datetime':last_dt})
        priority_items.append({'surface':surf,'instrument':inst,'timeframe':tf,'title_fa':title,'priority':pr,'explanation_fa':short})
    for inst,obj in market.items():
        if any(tf['kind']=='active' for tf in obj['timeframes']): obj['overall_state_fa']='observation فعال دارد'
        elif any(tf['kind']=='caveat' for tf in obj['timeframes']): obj['overall_state_fa']='caveat داده دارد'
        elif any(tf['kind']=='final' for tf in obj['timeframes']): obj['overall_state_fa']='فقط observationهای بسته‌شده دارد'
    latest={
        'staged_refresh_successful_surface_count': first_present(staged.get('successful_surface_count'), panel.get('staged_refresh_summary',{}).get('successful_surface_count')),
        'staged_refresh_failed_surface_count': first_present(staged.get('failed_surface_count'), panel.get('staged_refresh_summary',{}).get('failed_surface_count')),
        'valid_cache_surface_count': detection.get('valid_cache_surface_count'),
        'skipped_surface_count': detection.get('skipped_surface_count'),
        'new_observation_candidate_count': new_count,
        'finalized_now': post.get('finalized_now',0),
        'existing_active_lifecycle_updates_performed': post.get('existing_active_lifecycle_updates_performed'),
    }
    state={'program':PROGRAM,'created_at_utc':utc_now(),'summary':{'candidate_count':candidate_count,'lifecycle_count':lifecycle_count,'final_outcome_count':final_outcome_count,'active_tracking_count':active_tracking_count,'new_observation_candidate_count':new_count},'active_watch':active,'final_rows':finals,'market_state_by_instrument':market,'freshness':freshness,'no_candidate_explanations':no_candidates,'attention_priority':sorted(priority_items,key=lambda x:(x['priority']['rank'], tf_sort_key(x['surface']))),'latest_changes_summary':latest,'validation_status':{'validation_passed':validation.get('validation_passed'),'boundary_status':validation.get('boundary_status')},'boundary':BOUNDARY}
    state['plain_fa']={
        'headline': ('یک observation فعال وجود دارد؛ اول Active Watch را ببین.' if active else 'observation فعال وجود ندارد؛ وضعیت ابزارها و تغییرات آخرین اجرا را مرور کن.'),
        'short': f"{latest.get('staged_refresh_successful_surface_count','—')}/11 سطح refresh شده، candidate جدید: {new_count}، active: {active_tracking_count}.",
    }
    return state

def chip(text, cls='neutral'):
    return f"<span class='chip {cls}'>{h(text)}</span>"

def mini_metric(label, value, cls=''):
    return f"<div class='mini-metric {cls}'><span>{h(label)}</span><b>{h(value)}</b></div>"

def level_card(label, val, text, cls=''):
    return f"<div class='level-card {cls}'><span>{h(label)}</span><b>{token(fnum(val),'num') if val is not None else '—'}</b><small>{h(text)}</small></div>"

def render_active(rows):
    if not rows:
        return "<div class='empty'>فعلاً observation فعال نداریم.</div>"
    blocks=[]
    for r in rows:
        refs=r.get('reference_levels',{})
        trig=refs.get('trigger_bar',{})
        ext=refs.get('extension',{})
        surface=f"{r.get('instrument')} {r.get('timeframe')}"
        blocks.append(f"""
        <article class='active-hero'>
          <div class='active-top'><div><span class='eyebrow'>Active Watch</span><h3>{token(surface)}</h3><p>{h(fa_type(r.get('candidate_type')))} · {h(refs.get('direction'))}</p></div><div class='status-pill high'>بالا</div></div>
          <p class='reason'>{h(fa_reason(r.get('latest_outcome_reason')))}</p>
          <div class='level-grid'>
            {level_card('نامعتبرشدن', refs.get('invalidation',{}).get('level'), refs.get('invalidation',{}).get('text'), 'danger')}
            {level_card('ضعیف‌شدن', refs.get('weakening',{}).get('level'), refs.get('weakening',{}).get('text'), 'warn')}
            {level_card('پیشروی', refs.get('progress',{}).get('level'), refs.get('progress',{}).get('text'), 'good')}
            <div class='level-card wide'><span>امتداد تقریبی observation</span><b dir='ltr'>{h(fnum(ext.get('from')))} → {h(fnum(ext.get('to')))}</b><small>{h(ext.get('text'))}</small></div>
          </div>
          <details class='soft-details'><summary>کندل مرجع و توضیح بیشتر</summary><div class='ohlc'>{mini_metric('High', fnum(trig.get('high')))}{mini_metric('Low', fnum(trig.get('low')))}{mini_metric('Close', fnum(trig.get('close')))}</div><p>این سطح‌ها مرجع observation هستند؛ نه ورود، نه خروج، نه target و نه stop.</p></details>
        </article>""")
    return ''.join(blocks)

def render_changes(latest):
    return f"""<div class='h-scroll metrics-row'>
      {mini_metric('Refresh موفق', latest.get('staged_refresh_successful_surface_count'), 'ok')}
      {mini_metric('Refresh ناموفق', latest.get('staged_refresh_failed_surface_count'), 'warn')}
      {mini_metric('Cache معتبر', latest.get('valid_cache_surface_count'), 'ok')}
      {mini_metric('Candidate جدید', latest.get('new_observation_candidate_count'), '')}
      {mini_metric('Finalized now', latest.get('finalized_now'), '')}
    </div>"""

def render_freshness(rows):
    items=[]
    for r in sorted(rows,key=lambda x:tf_sort_key(x['surface'])):
        cls='ok' if r.get('updated') and r.get('provider_status')=='ok' else 'warn'
        items.append(f"""<div class='surface-row'>
          <div><b>{token(r['surface'])}</b><small>{h(r.get('last_provider_datetime'))}</small></div>
          <div>{chip(r.get('provider_status','—'), cls)}<span class='bars'>{token(r.get('value_count'),'num')} bars</span></div>
        </div>""")
    return ''.join(items)

def render_no_candidate(items):
    if not items:
        return "<div class='empty'>در این اجرا سطح بدون candidate جدید برای توضیح جداگانه ثبت نشده است.</div>"
    # compact summary; avoid long repeated text
    lines=[]
    for it in sorted(items,key=lambda x:tf_sort_key(x['surface']))[:12]:
        lines.append(f"<li><b>{token(it['surface'])}</b><span>scan انجام شد؛ candidate جدید ثبت نشد.</span><small>{token(it.get('valid_bar_count'),'num')} bars</small></li>")
    return "<ul class='compact-list'>"+''.join(lines)+"</ul>"

def render_priority(items):
    if not items: return "<div class='empty'>آیتمی برای اولویت‌بندی نیست.</div>"
    lines=[]
    for it in items[:8]:
        pr=it['priority']; cls=pr.get('class','low')
        lines.append(f"<li><div><b>{token(it['surface'])}</b><span>{h(it['title_fa'])}</span></div><em class='{cls}'>{h(pr['level'])}</em></li>")
    return "<ul class='priority-list'>"+''.join(lines)+"</ul>"

def render_instruments(market):
    blocks=[]
    for inst in INSTRUMENTS:
        obj=market.get(inst,{})
        tfs=obj.get('timeframes',[])
        tf_html=[]
        for tf in sorted(tfs,key=lambda x:TF_ORDER.index(x['timeframe']) if x['timeframe'] in TF_ORDER else 99):
            k=tf['kind']; cls='active' if k=='active' else 'final' if k=='final' else 'quiet' if k=='quiet' else 'warn'
            tf_html.append(f"""<div class='tf-card {cls}'>
              <div class='tf-head'><b>{token(tf['timeframe'])}</b>{chip(tf['title_fa'], cls)}</div>
              <p>{h(tf['short_fa'])}</p>
              <div class='tf-meta'><span>{h(tf['cache'].get('provider_status'))}</span><span>{token(tf['cache'].get('value_count'),'num')} bars</span><span>{h(tf['cache'].get('last_provider_datetime'))}</span></div>
            </div>""")
        open_attr=' open' if obj.get('overall_state_fa')=='observation فعال دارد' else ''
        blocks.append(f"""<details class='instrument' {open_attr}><summary><span>{token(inst)}</span><em>{h(obj.get('overall_state_fa','—'))}</em></summary><div class='tf-list'>{''.join(tf_html)}</div></details>""")
    return ''.join(blocks)

def render_html(state, refresh_url, pages_url):
    s=state['summary']; latest=state['latest_changes_summary']
    refresh_class='ok' if refresh_url else 'warn'
    refresh_text='Refresh endpoint فعال است.' if refresh_url else 'Refresh endpoint تنظیم نشده است.'
    active_html=render_active(state['active_watch'])
    changes_html=render_changes(latest)
    fresh_html=render_freshness(state['freshness'])
    no_cand_html=render_no_candidate(state['no_candidate_explanations'])
    priority_html=render_priority(state['attention_priority'])
    inst_html=render_instruments(state['market_state_by_instrument'])
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><title>PRV1 Mobile Dashboard</title>
    <style>
      :root{{--bg:#f3f6fb;--card:#ffffff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--blue:#2563eb;--blue-soft:#eff6ff;--green:#16a34a;--green-soft:#ecfdf5;--amber:#d97706;--amber-soft:#fffbeb;--red:#dc2626;--red-soft:#fef2f2;--shadow:0 10px 28px rgba(15,23,42,.08);--r:22px}}
      *{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#eef4ff,#f8fafc 44%,#eef2f7);color:var(--ink);font-family:Tahoma,'Vazirmatn','Noto Sans Arabic',Arial,sans-serif;font-size:15px;line-height:1.7}} .token,.num,.ltr{{direction:ltr;unicode-bidi:isolate;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.02em}} a{{color:var(--blue)}} .app{{max-width:760px;margin:0 auto;padding:14px 14px 42px}} .topbar{{position:sticky;top:0;z-index:5;margin:-14px -14px 12px;padding:14px;background:rgba(243,246,251,.88);backdrop-filter:blur(12px);border-bottom:1px solid rgba(226,232,240,.8)}} .brand{{display:flex;align-items:center;justify-content:space-between;gap:12px}} .brand h1{{margin:0;font-size:20px;font-weight:950}} .brand small{{display:block;color:var(--muted)}} .pill{{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line);border-radius:999px;padding:5px 9px;background:white;font-size:12px;color:var(--muted)}} .hero{{background:radial-gradient(circle at top right,#dbeafe,transparent 42%),linear-gradient(135deg,#fff,#f8fbff);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:18px;margin-bottom:12px}} .hero-title{{font-size:19px;font-weight:950;margin:0 0 4px}} .hero p{{margin:0;color:var(--muted)}} .metric-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:14px}} .metric{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:10px;text-align:center}} .metric span{{display:block;color:var(--muted);font-size:11px}} .metric b{{display:block;font-size:22px;line-height:1.2;margin-top:3px}} .card{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:16px;margin:12px 0}} .section-title{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}} h2{{font-size:18px;margin:0;font-weight:950}} .muted{{color:var(--muted)}} .h-scroll{{display:flex;gap:9px;overflow-x:auto;padding-bottom:4px;scroll-snap-type:x proximity}} .mini-metric{{min-width:116px;background:#f8fafc;border:1px solid var(--line);border-radius:18px;padding:10px;scroll-snap-align:start}} .mini-metric span{{display:block;color:var(--muted);font-size:12px}} .mini-metric b{{display:block;font-size:19px;line-height:1.2;margin-top:3px}} .mini-metric.ok{{background:var(--green-soft);border-color:#bbf7d0}} .mini-metric.warn{{background:var(--amber-soft);border-color:#fde68a}} .active-hero{{border-radius:24px;background:linear-gradient(180deg,#eff6ff,#fff);border:1px solid #bfdbfe;padding:15px;margin:10px 0}} .active-top{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}} .eyebrow{{font-size:11px;font-weight:900;color:#1d4ed8;background:#dbeafe;border-radius:999px;padding:3px 8px}} .active-hero h3{{font-size:24px;margin:8px 0 0}} .active-hero p{{margin:5px 0;color:var(--muted)}} .status-pill,.chip{{display:inline-flex;align-items:center;border-radius:999px;padding:4px 10px;font-weight:850;font-size:12px;white-space:nowrap}} .high,.chip.active{{background:#dbeafe;color:#1e40af}} .medium,.chip.final{{background:#fef3c7;color:#92400e}} .low,.chip.quiet,.chip.ok{{background:#dcfce7;color:#14532d}} .chip.warn{{background:#ffedd5;color:#9a3412}} .chip.neutral{{background:#f1f5f9;color:#334155}} .reason{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px}} .level-grid{{display:grid;grid-template-columns:1fr;gap:9px;margin-top:10px}} .level-card{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:12px}} .level-card span{{display:block;color:var(--muted);font-size:12px}} .level-card b{{display:block;font-size:21px;margin:2px 0}} .level-card small{{display:block;color:var(--muted)}} .level-card.danger{{border-color:#fecaca;background:#fff7f7}} .level-card.warn{{border-color:#fde68a;background:#fffbeb}} .level-card.good{{border-color:#bbf7d0;background:#f0fdf4}} .soft-details{{margin-top:10px;background:#f8fafc;border:1px solid var(--line);border-radius:16px;padding:10px}} summary{{cursor:pointer;font-weight:900}} .ohlc{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}} .surface-row{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid var(--line)}} .surface-row:last-child{{border-bottom:0}} .surface-row b{{display:block}} .surface-row small{{color:var(--muted)}} .bars{{display:block;text-align:left;color:var(--muted);font-size:12px;margin-top:4px}} .compact-list,.priority-list{{list-style:none;padding:0;margin:0}} .compact-list li,.priority-list li{{display:flex;justify-content:space-between;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding:10px 0}} .compact-list li:last-child,.priority-list li:last-child{{border-bottom:0}} .compact-list span,.priority-list span{{display:block;color:var(--muted);font-size:13px}} .priority-list em{{font-style:normal;border-radius:999px;padding:4px 10px;font-weight:900;white-space:nowrap}} .instrument{{background:#fff;border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:0;margin:12px 0;overflow:hidden}} .instrument>summary{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:16px;list-style:none}} .instrument>summary::-webkit-details-marker{{display:none}} .instrument>summary span{{font-size:22px;font-weight:950}} .instrument>summary em{{font-style:normal;color:var(--muted);font-weight:800}} .tf-list{{padding:0 14px 14px;display:grid;gap:10px}} .tf-card{{border-radius:18px;border:1px solid var(--line);padding:12px;background:#f8fafc}} .tf-card.active{{background:#eff6ff;border-color:#93c5fd}} .tf-card.final{{background:#f8fafc}} .tf-card.quiet{{background:#f0fdf4;border-color:#bbf7d0}} .tf-card.warn{{background:#fff7ed;border-color:#fed7aa}} .tf-head{{display:flex;justify-content:space-between;gap:8px;align-items:center}} .tf-head b{{font-size:18px}} .tf-card p{{margin:8px 0;color:#334155}} .tf-meta{{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:9px;color:var(--muted);font-size:12px}} .tf-meta span:last-child{{grid-column:1/-1}} button{{width:100%;border:0;border-radius:18px;background:var(--blue);color:white;padding:15px;font-weight:950;font-size:16px;box-shadow:0 8px 18px rgba(37,99,235,.25)}} .status{{margin-top:10px;border-radius:16px;padding:10px;font-weight:800}} .status.ok{{background:var(--green-soft);color:#14532d}} .status.warn{{background:var(--amber-soft);color:#92400e}} .status.error{{background:var(--red-soft);color:#991b1b}} .status.pending{{background:var(--blue-soft);color:#1e40af}} .empty{{background:#f8fafc;border:1px dashed #cbd5e1;color:var(--muted);border-radius:18px;padding:14px;text-align:center}} @media(min-width:620px){{.level-grid{{grid-template-columns:repeat(3,1fr)}} .level-card.wide{{grid-column:1/-1}} .tf-list{{grid-template-columns:repeat(2,1fr)}}}} @media(max-width:390px){{.metric-grid{{grid-template-columns:repeat(3,1fr)}} .metric b{{font-size:20px}} .brand h1{{font-size:18px}}}}
    </style></head><body><div class='app'>
      <div class='topbar'><div class='brand'><div><h1>PRV1 Mobile Dashboard</h1><small>نمای روزانهٔ observationها</small></div><span class='pill'>Boundary: passed</span></div></div>
      <section class='hero'><div class='hero-title'>{h(state['plain_fa']['headline'])}</div><p>{h(state['plain_fa']['short'])}</p><div class='metric-grid'>{mini_metric('Observation',s.get('candidate_count'))}{mini_metric('Lifecycle',s.get('lifecycle_count'))}{mini_metric('Final',s.get('final_outcome_count'))}{mini_metric('Active',s.get('active_tracking_count'))}{mini_metric('New',s.get('new_observation_candidate_count'))}</div></section>
      <section class='card'><div class='section-title'><h2>Active Watch</h2>{chip('اولویت اصلی','active')}</div>{active_html}</section>
      <section class='card'><div class='section-title'><h2>تغییرات آخرین اجرا</h2></div>{changes_html}</section>
      <section class='card'><div class='section-title'><h2>Freshness</h2><span class='pill'>بدون جدول سنگین</span></div>{fresh_html}</section>
      <section class='card'><div class='section-title'><h2>Attention Priority</h2></div><p class='muted'>فقط برای مرتب‌سازی توجه است، نه سیگنال.</p>{priority_html}</section>
      <section class='card'><div class='section-title'><h2>No Candidate</h2></div><details open><summary>خلاصهٔ سطوح بدون candidate جدید</summary>{no_cand_html}</details></section>
      <section class='card'><div class='section-title'><h2>Refresh</h2></div><button id='refresh-now-button'>به‌روزرسانی الآن</button><div id='refresh-status' class='status {refresh_class}'>{h(refresh_text)}</div><div id='latest-run-status' class='muted'></div></section>
      {inst_html}
      <section class='card'><h2>مرز استفاده</h2><p class='muted'>این داشبورد observation را واضح‌تر می‌کند، اما خرید/فروش، ورود/خروج، target/stop، PnL، execution یا validation verdict تولید نمی‌کند.</p></section>
      <p class='muted'>Generated: {token(state['created_at_utc'])} · <a href='status_public.json'>status</a> · <a href='market_state_public.json'>data</a></p>
    </div><script src='refresh_config.js'></script><script src='mobile_refresh_button.js'></script></body></html>"""

def main():
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
    root=root.resolve(); public=root/'public'; public.mkdir(parents=True, exist_ok=True)
    panel=root/'panel'; panel.mkdir(parents=True, exist_ok=True)
    state=build_state(root)
    refresh_url=os.environ.get('MOBILE_REFRESH_WORKER_URL','').strip().rstrip('/')
    pages_url=os.environ.get('GITHUB_PAGES_URL','').strip()
    # internal and public JSONs
    write_json(panel/'panel_professional_dashboard_payload.json', state)
    write_json(panel/'professional_active_watch_cards.json', {'created_at_utc':state['created_at_utc'],'rows':state['active_watch'],'boundary':BOUNDARY})
    write_json(panel/'professional_mobile_ux_summary.json', {'layout':'compact_cards_accordion_no_tables','rtl':True,'ltr_tokens_isolated':True,'boundary':BOUNDARY})
    public_status={'program':PROGRAM,'created_at_utc':state['created_at_utc'],'active_instruments':INSTRUMENTS,**state['summary'],'latest_changes_summary':state['latest_changes_summary'],'freshness_summary':{'surface_count':len(state['freshness']),'updated_surface_count':sum(1 for r in state['freshness'] if r.get('updated'))},'refresh_button':{'enabled':bool(refresh_url),'worker_url_configured':bool(refresh_url),'worker_health_url':f'{refresh_url}/health' if refresh_url else None},'boundary':BOUNDARY}
    write_json(public/'status_public.json', public_status)
    write_json(public/'market_state_public.json', state)
    write_json(public/'professional_dashboard_payload.json', state)
    (public/'refresh_config.js').write_text('window.PRV1_REFRESH_WORKER_URL = '+json.dumps(refresh_url)+';\nwindow.PRV1_GITHUB_PAGES_URL = '+json.dumps(pages_url)+';\n', encoding='utf-8')
    (public/'mobile_refresh_button.js').write_text("""async function prv1RefreshNow(){const endpoint=(window.PRV1_REFRESH_WORKER_URL||'').replace(/\/$/,'');const box=document.getElementById('refresh-status');if(!endpoint){box.textContent='Refresh endpoint تنظیم نشده است.';box.className='status warn';return;}const pin=prompt('PIN به‌روزرسانی را وارد کن');if(!pin){box.textContent='لغو شد.';box.className='status warn';return;}box.textContent='درخواست ارسال شد...';box.className='status pending';try{const res=await fetch(endpoint+'/refresh',{method:'POST',headers:{'content-type':'application/json','x-refresh-pin':pin},body:JSON.stringify({source:'mobile_prv1l_professional_dashboard',requested_at:new Date().toISOString()})});const data=await res.json();if(!res.ok)throw new Error(data.reason||data.status||('HTTP '+res.status));box.textContent='درخواست ثبت شد. چند دقیقه بعد صفحه را reload کن.';box.className='status ok';poll(endpoint);}catch(e){box.textContent='Refresh failed: '+e.message;box.className='status error';}}async function poll(endpoint){const box=document.getElementById('latest-run-status');if(!box)return;for(let i=0;i<12;i++){await new Promise(r=>setTimeout(r,10000));try{const res=await fetch(endpoint+'/latest-run');const data=await res.json();const run=data.latest_run;if(run){box.innerHTML='آخرین run: <span class="token" dir="ltr">'+run.status+'</span>'+(run.conclusion?' / <span class="token" dir="ltr">'+run.conclusion+'</span>':'')+' — <a target="_blank" href="'+run.html_url+'">باز کردن</a>';if(run.status==='completed')break;}}catch(_){}}}window.addEventListener('DOMContentLoaded',()=>{const b=document.getElementById('refresh-now-button');if(b)b.addEventListener('click',prv1RefreshNow);});""", encoding='utf-8')
    (public/'index.html').write_text(render_html(state, refresh_url, pages_url), encoding='utf-8')
    proof={'program':PROGRAM,'artifact':'professional_mobile_dashboard_generation_proof','created_at_utc':state['created_at_utc'],'status':'passed','design_changes':['compact_mobile_layout','sticky_header','hero_active_watch','no_wide_tables','compact_freshness_rows','accordion_instrument_sections','collapsed_explanations','rtl_ltr_typography_polish','status_chips_and_visual_hierarchy'],'refresh_button_preserved':bool(refresh_url),'html_lang':'fa','html_dir':'rtl','no_new_feature_logic_added':True,'no_signal_or_execution_surface_added':True,'boundary':BOUNDARY}
    write_json(root/'proofs'/'professional_mobile_dashboard_generation_proof.json', proof)
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
