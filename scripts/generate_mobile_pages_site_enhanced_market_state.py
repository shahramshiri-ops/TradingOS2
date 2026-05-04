from __future__ import annotations
import json, os, sys, math
from datetime import datetime, timezone
from pathlib import Path
from html import escape

PROGRAM = "PRV1K-01"
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
    "still_active_observation": "هنوز فعال / در حال پیگیری",
    "favorable_observation": "مشاهدهٔ هم‌جهت با فرض اولیه",
    "unfavorable_observation": "مشاهدهٔ خلاف یا ضعیف نسبت به فرض اولیه",
    "invalidated_observation": "مشاهده نامعتبر شده",
}
STATUS_FA = {
    "active_tracking": "فعال و در حال پیگیری",
    "final_outcome_recorded": "بسته شده / outcome توصیفی ثبت شده",
}
TYPE_FA = {
    "downside_range_breakout_observation_candidate": "مشاهدهٔ شکست محدوده به سمت پایین",
    "upside_range_breakout_observation_candidate": "مشاهدهٔ شکست محدوده به سمت بالا",
}
REASON_FA = {
    "no_completed_post_trigger_bars_available_yet": "هنوز کندل کامل کافی بعد از trigger برای بستن این مشاهده در دسترس نیست.",
    "post_trigger_low_extended_below_trigger_low_and_last_close_remains_below_trigger_close": "بعد از trigger، حرکت در جهت مشاهده ادامه پیدا کرده و close هنوز در همان سمت مانده است.",
    "last_post_trigger_close_back_above_trigger_close_without_full_high_close_invalidation": "بعد از trigger، close به محدودهٔ برگشت نزدیک شده، اما نامعتبرشدن کامل طبق rule ثبت نشده است.",
    "post_trigger_completed_bar_closed_below_trigger_bar_low": "یک کندل کامل بعد از trigger از مرجع نامعتبرسازی عبور کرده و observation طبق rule بسته شده است.",
    "no_range_breakout_observation_triggered": "اسکن rule انجام شده، اما شکست محدودهٔ قابل ثبت به‌عنوان observation candidate پیدا نشده است.",
    "cache_values_missing_or_unreadable": "cache این سطح در این اجرا قابل خواندن نبوده است.",
}

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def read_json(path: Path, default=None):
    if default is None: default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default
    return default

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def first_present(*vals, default=None):
    for v in vals:
        if v is not None:
            return v
    return default

def h(s):
    return escape(str(s if s is not None else '—'))

def token(s):
    return f"<span class='token' dir='ltr'>{h(s)}</span>"

def norm_surface(surface: str) -> tuple[str, str]:
    parts = (surface or '').split()
    if len(parts) >= 2: return parts[0], parts[1]
    return surface or 'UNKNOWN', 'UNKNOWN'

def tf_sort_key(surface: str):
    inst, tf = norm_surface(surface)
    return (INSTRUMENTS.index(inst) if inst in INSTRUMENTS else 99, TF_ORDER.index(tf) if tf in TF_ORDER else 99, surface)

def fnum(x, digits=2):
    try:
        val = float(x)
        if abs(val) >= 1000: return f"{val:,.2f}"
        if abs(val) >= 10: return f"{val:.3f}"
        return f"{val:.5f}".rstrip('0').rstrip('.')
    except Exception:
        return '—'

def fa_status(status: str) -> str: return STATUS_FA.get(status or '', status or 'نامشخص')
def fa_outcome(outcome: str) -> str: return OUTCOME_FA.get(outcome or '', outcome or 'نامشخص')
def fa_type(t: str) -> str: return TYPE_FA.get(t or '', t or 'Observation')
def fa_reason(r: str) -> str: return REASON_FA.get(r or '', r or 'دلیل مشخصی ثبت نشده است.')

def load_rows(root: Path) -> list[dict]:
    paths = [
        root/'ledger'/'candidate_lifecycle_rows_v1_after_candidate_detection.json',
        root/'ledger'/'candidate_lifecycle_rows_v1_post_refresh.json',
        root/'ledger'/'candidate_lifecycle_rows_v1_exact.json',
        root/'ledger'/'candidate_lifecycle_rows_v1.json',
        root/'panel'/'panel_payload_after_post_refresh_update.json',
        root/'panel'/'panel_payload_after_candidate_detection.json',
        root/'panel'/'panel_payload_after_daily_runtime.json',
    ]
    for p in paths:
        obj = read_json(p, {})
        for key in ['rows','post_refresh_lifecycle_rows','candidate_lifecycle_rows','post_refresh_lifecycle_rows']:
            rows = obj.get(key) if isinstance(obj, dict) else None
            if isinstance(rows, list) and rows:
                return rows
    return []

def load_surface_rows(root: Path):
    staged = read_json(root/'reports'/'staged_provider_fetch_report.json')
    cache = read_json(root/'reports'/'staged_cache_update_report.json')
    detection = read_json(root/'reports'/'candidate_detection_report.json')
    provider_rows = staged.get('surface_rows') or []
    cache_rows = cache.get('surface_rows') or []
    scan_rows = detection.get('scan_rows') or detection.get('surface_rows') or []
    return staged, cache, detection, provider_rows, cache_rows, scan_rows

def reference_levels_for_row(row: dict) -> dict:
    bar = row.get('trigger_bar_from_capture') or {}
    high, low, close = bar.get('high'), bar.get('low'), bar.get('close')
    typ = row.get('candidate_type') or ''
    direction = 'downside' if 'downside' in typ else 'upside' if 'upside' in typ else 'unknown'
    try:
        hi = float(high); lo = float(low); cl = float(close)
        rng = max(0.0, hi - lo)
    except Exception:
        hi = lo = cl = rng = None
    if direction == 'downside':
        extension_zone = {"label_fa":"محدودهٔ امتداد مشاهده", "from": lo-rng if rng is not None else None, "to": lo, "meaning_fa":"اگر قیمت/کندل‌ها زیر low مرجع ادامه بدهند، observation در جهت خودش پیشروی کرده است."}
        weakening = {"label_fa":"مرجع ضعیف‌شدن", "level": cl, "condition_fa":"close کامل بالای close مرجع"}
        invalidation = {"label_fa":"محدودهٔ نامعتبر شدن مشاهده", "level": hi, "condition_fa":"close کامل بالای high مرجع"}
        progress = {"level": lo, "condition_fa":"ادامه زیر low مرجع"}
    elif direction == 'upside':
        extension_zone = {"label_fa":"محدودهٔ امتداد مشاهده", "from": hi, "to": hi+rng if rng is not None else None, "meaning_fa":"اگر قیمت/کندل‌ها بالای high مرجع ادامه بدهند، observation در جهت خودش پیشروی کرده است."}
        weakening = {"label_fa":"مرجع ضعیف‌شدن", "level": cl, "condition_fa":"close کامل پایین close مرجع"}
        invalidation = {"label_fa":"محدودهٔ نامعتبر شدن مشاهده", "level": lo, "condition_fa":"close کامل پایین low مرجع"}
        progress = {"level": hi, "condition_fa":"ادامه بالای high مرجع"}
    else:
        extension_zone = weakening = invalidation = progress = {}
    return {
        "direction": direction,
        "trigger_bar": {"open": bar.get('open'), "high": high, "low": low, "close": close},
        "range_height": rng,
        "progress_reference": progress,
        "weakening_reference": weakening,
        "invalidation_reference": invalidation,
        "extension_zone": extension_zone,
        "boundary_note_fa": "این‌ها سطح‌های مرجع observation هستند؛ نه ورود، نه خروج، نه اندازه پوزیشن و نه توصیهٔ معاملاتی.",
    }

def attention_priority(row_or_surface: dict, kind: str) -> dict:
    if kind == 'active':
        return {"level":"بالا", "rank": 1, "reason_fa":"observation هنوز active است و در اجرای بعدی باید دوباره بررسی شود."}
    if kind == 'new':
        return {"level":"بالا", "rank": 1, "reason_fa":"candidate جدید پیدا شده و باید به‌عنوان observation جدید دیده شود."}
    if kind == 'final_recent':
        return {"level":"متوسط", "rank": 2, "reason_fa":"observation بسته شده و outcome توصیفی دارد؛ برای مرور مفید است اما active نیست."}
    if kind == 'caveat':
        return {"level":"متوسط", "rank": 2, "reason_fa":"cache یا provider caveat دارد؛ قبل از برداشت از وضعیت، freshness/coverage را چک کن."}
    return {"level":"پایین", "rank": 3, "reason_fa":"داده خوانده و اسکن شده، اما candidate جدید یا active watch ندارد."}

def build_state(root: Path) -> dict:
    panel = read_json(root/'panel'/'panel_payload_after_daily_runtime.json')
    validation = read_json(root/'proofs'/'daily_runtime_local_validation_result.json')
    last_run = read_json(root/'logs'/'last_run_status_after_daily_runtime.json')
    post_update = read_json(root/'reports'/'post_refresh_lifecycle_update_report.json')
    staged, cache, detection, provider_rows, cache_rows, scan_rows = load_surface_rows(root)
    rows = load_rows(root)
    summary = panel.get('summary') or panel.get('latest_runtime_summary') or panel.get('latest_exact_row_ledger_summary') or {}
    daily = panel.get('daily_loop_summary') or panel.get('latest_runtime_summary') or {}
    candidate_count = first_present(summary.get('candidate_count'), last_run.get('candidate_count'), daily.get('merged_candidate_lifecycle_row_count'), default=len(rows))
    lifecycle_count = first_present(summary.get('lifecycle_count'), last_run.get('lifecycle_count'), daily.get('merged_candidate_lifecycle_row_count'), default=len(rows))
    final_outcome_count = first_present(summary.get('final_outcome_count'), last_run.get('final_outcome_count'), default=sum(1 for r in rows if r.get('is_final') is True))
    active_tracking_count = first_present(summary.get('active_tracking_count'), last_run.get('active_tracking_count'), default=sum(1 for r in rows if r.get('is_final') is False or r.get('lifecycle_status')=='active_tracking'))
    new_count = first_present(daily.get('new_observation_candidate_count'), detection.get('new_observation_candidate_count'), last_run.get('new_observation_candidate_count'), default=0)

    cache_by_surface = {r.get('surface'): r for r in cache_rows if r.get('surface')}
    provider_by_surface = {r.get('surface'): r for r in provider_rows if r.get('surface')}
    scan_by_surface = {r.get('surface'): r for r in scan_rows if r.get('surface')}
    rows_by_surface: dict[str, list[dict]] = {}
    for row in rows:
        surf = row.get('surface') or f"{row.get('instrument','UNKNOWN')} {row.get('timeframe','UNKNOWN')}"
        rows_by_surface.setdefault(surf, []).append(row)
    surfaces = set(cache_by_surface) | set(provider_by_surface) | set(scan_by_surface) | set(rows_by_surface)
    if not surfaces:
        surfaces = {"EURUSD D1","EURUSD H1","EURUSD M15","EURUSD M5","USDJPY D1","USDJPY H1","USDJPY M15","USDJPY M5","XAUUSD D1","XAUUSD H1","XAUUSD M15"}

    active_rows, final_rows = [], []
    for r in rows:
        if r.get('lifecycle_status') == 'active_tracking' or r.get('is_final') is False:
            rr = dict(r); rr['reference_levels'] = reference_levels_for_row(rr); rr['attention_priority'] = attention_priority(rr,'active')
            active_rows.append(rr)
        elif r.get('is_final') is True or r.get('lifecycle_status') == 'final_outcome_recorded':
            rr = dict(r); rr['attention_priority'] = attention_priority(rr,'final_recent')
            final_rows.append(rr)

    market = {i: {"instrument": i, "overall_state_fa":"داده بررسی شده؛ candidate جدید ثبت نشده", "timeframes": []} for i in INSTRUMENTS}
    freshness_rows = []
    no_candidate_explanations = []
    priority_items = []
    for surface in sorted(surfaces, key=tf_sort_key):
        inst, tf = norm_surface(surface)
        if inst not in market: continue
        cache_r = cache_by_surface.get(surface, {})
        prov_r = provider_by_surface.get(surface, {})
        scan_r = scan_by_surface.get(surface, {})
        surf_rows = rows_by_surface.get(surface, [])
        updated = bool(cache_r.get('updated') if cache_r else prov_r.get('ok'))
        provider_status = cache_r.get('provider_status') or prov_r.get('provider_status') or ('ok' if updated else 'unknown')
        last_dt = cache_r.get('last_provider_datetime') or prov_r.get('last_provider_datetime')
        valid_bars = first_present(scan_r.get('valid_bar_count'), cache_r.get('value_count'), prov_r.get('value_count'))
        failed = provider_status not in ['ok','unknown'] and not updated
        if any(r.get('lifecycle_status')=='active_tracking' or r.get('is_final') is False for r in surf_rows):
            state_fa = 'observation فعال دارد'
            priority = attention_priority({}, 'active')
            detail_fa = 'این سطح در Active Watch هم دیده می‌شود و باید در اجرای بعدی دوباره بررسی شود.'
        elif surf_rows:
            state_fa = 'observation قبلی بسته‌شده دارد'
            priority = attention_priority({}, 'final_recent')
            detail_fa = 'این سطح observation تاریخی/بسته‌شده دارد، اما active watch فعلی نیست.'
        elif scan_r.get('status') == 'scanned_no_candidate' or detection.get('valid_cache_surface_count'):
            state_fa = 'candidate جدید پیدا نشد'
            priority = attention_priority({}, 'quiet')
            detail_fa = 'cache خوانده شد و rule scan انجام شد، اما observation candidate جدید طبق rule فعلی ثبت نشد.'
            no_candidate_explanations.append({"surface": surface, "instrument": inst, "timeframe": tf, "reason_fa": detail_fa, "valid_bar_count": valid_bars})
        elif failed:
            state_fa = 'caveat داده / نیازمند بررسی'
            priority = attention_priority({}, 'caveat')
            detail_fa = 'این سطح در provider/cache مشکل داشته و برداشت از آن باید با caveat باشد.'
        else:
            state_fa = 'بدون وضعیت خاص ثبت‌شده'
            priority = attention_priority({}, 'quiet')
            detail_fa = 'برای این سطح observation فعال یا candidate جدید در خروجی فعلی ثبت نشده است.'
        tf_obj = {"surface":surface,"instrument":inst,"timeframe":tf,"state_fa":state_fa,"detail_fa":detail_fa,"cache":{"updated":updated,"provider_status":provider_status,"value_count":valid_bars,"last_provider_datetime":last_dt},"scan":{"status":scan_r.get('status'),"valid_bar_count":scan_r.get('valid_bar_count'),"skipped_reason":scan_r.get('reason') or scan_r.get('detection_reason')},"rows":surf_rows,"attention_priority":priority}
        market[inst]['timeframes'].append(tf_obj)
        freshness_rows.append({"surface":surface,"updated":updated,"provider_status":provider_status,"value_count":valid_bars,"last_provider_datetime":last_dt})
        priority_items.append({"surface":surface,"state_fa":state_fa,"priority":priority,"detail_fa":detail_fa})
    for inst, data in market.items():
        if any(tf['attention_priority']['rank']==1 for tf in data['timeframes']): data['overall_state_fa']='observation فعال دارد'
        elif any(tf['attention_priority']['rank']==2 for tf in data['timeframes']): data['overall_state_fa']='observationهای قبلی دارد؛ active جدید ندارد'
        elif data['timeframes']: data['overall_state_fa']='داده بررسی شده؛ candidate جدید ندارد'

    latest_changes = {
        "new_observation_candidate_count": new_count,
        "existing_active_lifecycle_updates_performed": post_update.get('existing_active_lifecycle_updates_performed'),
        "finalized_now": post_update.get('finalized_now'),
        "staged_refresh_successful_surface_count": first_present(staged.get('successful_surface_count'), daily.get('staged_refresh_successful_surface_count')),
        "staged_refresh_failed_surface_count": first_present(staged.get('failed_surface_count'), daily.get('staged_refresh_failed_surface_count')),
        "valid_cache_surface_count": first_present(detection.get('valid_cache_surface_count'), daily.get('valid_cache_surface_count')),
        "skipped_surface_count": first_present(detection.get('skipped_surface_count'), daily.get('skipped_surface_count')),
        "candidate_detection_performed": detection.get('candidate_detection_performed') or True,
    }
    active_sentence = "یک observation فعال برای پیگیری وجود دارد." if active_rows else "در حال حاضر observation فعال ثبت نشده است."
    cand_sentence = "در آخرین اسکن candidate جدید پیدا نشده است." if not new_count else f"در آخرین اسکن {new_count} candidate جدید پیدا شده است."
    cov_ok = latest_changes.get('staged_refresh_successful_surface_count')
    plain = {
        "headline": f"داده‌ها refresh شده‌اند؛ {cov_ok if cov_ok is not None else '—'} سطح موفق بوده است. {cand_sentence} {active_sentence}",
        "what_to_check_first": ["اول Active Watch را ببین.", "بعد Freshness & Coverage را چک کن تا مطمئن شوی داده تازه بوده.", "بعد No Candidate Explanation را بخوان تا بفهمی نبودن candidate یعنی سیستم کار نکرده یا واقعاً چیزی پیدا نشده."],
        "boundary_simple": "این پنل برای فهم وضعیت observation است، نه برای تصمیم معاملاتی.",
    }
    return {
        "program": PROGRAM,
        "artifact": "enhanced_human_market_state_payload",
        "created_at_utc": utc_now(),
        "summary": {"candidate_count":candidate_count,"lifecycle_count":lifecycle_count,"final_outcome_count":final_outcome_count,"active_tracking_count":active_tracking_count,"new_observation_candidate_count":new_count,"validation_passed":validation.get('validation_passed'),"boundary_status":validation.get('boundary_status')},
        "active_watch_reference_levels": active_rows,
        "market_state_by_instrument": market,
        "latest_changes_summary": latest_changes,
        "freshness_coverage_summary": {"rows": freshness_rows, "updated_surface_count": sum(1 for r in freshness_rows if r['updated']), "surface_count": len(freshness_rows)},
        "no_candidate_explanation": {"rows": no_candidate_explanations, "meaning_fa":"اگر سطحی اینجا آمده، یعنی cache خوانده و rule scan انجام شده اما candidate جدید ثبت نشده است."},
        "attention_priority_summary": sorted(priority_items, key=lambda x: (x['priority']['rank'], x['surface'])),
        "plain_language_explanation_fa": plain,
        "source_confidence": panel.get('source_confidence') or {"mode":"single_provider_caveated_only","provider":"twelve_data","is_source_truth":False},
        "calendar_event": panel.get('calendar_event') or "calendar_event_source_not_in_v1_scope",
        "forbidden_surfaces_absent": panel.get('forbidden_surfaces_absent') or {"broker_status":True,"execution_queue":True,"action_buttons":True,"buy_sell_hold":True,"entry_stop_target":True,"pnl_win_loss":True},
        "boundary": BOUNDARY,
    }

def render_html(state: dict, refresh_url: str, pages_url: str) -> str:
    s = state['summary']; latest = state['latest_changes_summary']; plain = state['plain_language_explanation_fa']; market = state['market_state_by_instrument']; active = state['active_watch_reference_levels']; fresh = state['freshness_coverage_summary']; no_cand = state['no_candidate_explanation']['rows']; priorities = state['attention_priority_summary']
    def badge(txt, cls='neutral'): return f"<span class='badge {cls}'>{h(txt)}</span>"
    def ref_card(row):
        refs = row.get('reference_levels') or {}; trig = refs.get('trigger_bar') or {}; inv=refs.get('invalidation_reference') or {}; weak=refs.get('weakening_reference') or {}; ext=refs.get('extension_zone') or {}; prog=refs.get('progress_reference') or {}
        surf = row.get('surface') or f"{row.get('instrument','')} {row.get('timeframe','')}"
        return f"""
        <article class='watch-card'>
          <div class='watch-top'><h3>{token(surf)}</h3>{badge('توجه بالا','active')}</div>
          <p><b>{h(fa_type(row.get('candidate_type')))}</b> — {h(fa_status(row.get('lifecycle_status')))} / {h(fa_outcome(row.get('latest_outcome_category')))}</p>
          <p class='muted'>{h(fa_reason(row.get('latest_outcome_reason')))}</p>
          <div class='levels-grid'>
            <div><span>کندل مرجع</span><b class='ltr'>H {fnum(trig.get('high'))} / L {fnum(trig.get('low'))} / C {fnum(trig.get('close'))}</b></div>
            <div><span>محدودهٔ نامعتبر شدن مشاهده</span><b class='ltr'>{fnum(inv.get('level'))}</b><small>{h(inv.get('condition_fa'))}</small></div>
            <div><span>مرجع ضعیف‌شدن</span><b class='ltr'>{fnum(weak.get('level'))}</b><small>{h(weak.get('condition_fa'))}</small></div>
            <div><span>مرجع پیشروی</span><b class='ltr'>{fnum(prog.get('level'))}</b><small>{h(prog.get('condition_fa'))}</small></div>
            <div class='wide'><span>محدودهٔ امتداد تقریبی observation</span><b class='ltr'>{fnum(ext.get('from'))} → {fnum(ext.get('to'))}</b><small>{h(ext.get('meaning_fa'))}</small></div>
          </div>
          <p class='boundary-note'>این سطح‌ها فقط برای فهمیدن وضعیت observation هستند؛ نه ورود، نه خروج، نه اندازه‌گیری سود/ضرر و نه توصیهٔ معاملاتی.</p>
        </article>"""
    active_html = ''.join(ref_card(r) for r in active) if active else "<div class='empty'>الان Active Watch خالی است؛ observation باز برای پیگیری فوری ثبت نشده.</div>"
    freshness_html = ''.join(f"<tr><td>{token(r['surface'])}</td><td>{badge('ok' if r.get('updated') else 'caveat','quiet' if r.get('updated') else 'warn')}</td><td class='ltr'>{h(r.get('value_count'))}</td><td class='ltr'>{h(r.get('last_provider_datetime'))}</td></tr>" for r in fresh['rows'])
    priority_html = ''.join(f"<li><span class='priority p{item['priority']['rank']}'>{h(item['priority']['level'])}</span> {token(item['surface'])} — {h(item['state_fa'])}<br><small>{h(item['priority']['reason_fa'])}</small></li>" for item in priorities[:12])
    no_candidate_html = ''.join(f"<li>{token(r['surface'])}: {h(r['reason_fa'])} <span class='ltr'>({h(r.get('valid_bar_count'))} bars)</span></li>" for r in no_cand) or '<li>در خروجی فعلی توضیح No Candidate جداگانه ثبت نشده است.</li>'
    inst_html=[]
    for inst in INSTRUMENTS:
        data = market.get(inst,{"timeframes":[]})
        tf_html=[]
        for tf in data['timeframes']:
            cls = 'active' if tf['attention_priority']['rank']==1 else 'medium' if tf['attention_priority']['rank']==2 else 'quiet'
            cache = tf['cache']
            tf_html.append(f"""<article class='tf {cls}'><div class='tf-title'><span>{token(tf['timeframe'])}</span><b>{h(tf['state_fa'])}</b></div><p>{h(tf['detail_fa'])}</p><div class='mini'><span>Provider</span><b class='ltr'>{h(cache.get('provider_status'))}</b><span>Bars</span><b class='ltr'>{h(cache.get('value_count'))}</b><span>Last</span><b class='ltr'>{h(cache.get('last_provider_datetime'))}</b></div></article>""")
        inst_html.append(f"<section class='instrument'><div class='inst-head'><h2>{token(inst)}</h2><span>{h(data['overall_state_fa'])}</span></div><div class='tf-grid'>{''.join(tf_html)}</div></section>")
    refresh_cls = 'ok' if refresh_url else 'warn'; refresh_text = 'دکمه به Worker وصل است.' if refresh_url else 'Worker URL تنظیم نشده است.'
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>PRV1 — پنل روزانه</title><style>
    :root{{--bg:#f5f7fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--blue:#2563eb;--green:#16a34a;--amber:#d97706;--red:#dc2626;}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Vazirmatn,IRANSans,Segoe UI,Arial,sans-serif;line-height:1.75;direction:rtl;text-align:right}} .wrap{{max-width:1120px;margin:auto;padding:14px}} .hero{{background:linear-gradient(135deg,#0f172a,#1d4ed8);color:white;border-radius:26px;padding:22px;box-shadow:0 18px 42px #0002}} h1,h2,h3{{margin:0 0 10px}} .hero p{{color:#dbeafe;margin:0}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0}} .metric,.card,.instrument,.watch-card{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:15px;box-shadow:0 8px 24px #0f172a12;margin:14px 0}} .metric small,.muted,small{{color:var(--muted)}} .metric b{{font-size:30px;direction:ltr;unicode-bidi:isolate;display:block}} .token,.ltr{{direction:ltr;unicode-bidi:isolate;display:inline-block;font-family:ui-monospace,Consolas,monospace;text-align:left}} .badge{{display:inline-flex;border-radius:999px;padding:5px 10px;margin:2px;font-size:12px;font-weight:900}} .badge.quiet{{background:#dcfce7;color:#14532d}} .badge.warn{{background:#fef3c7;color:#92400e}} .badge.active{{background:#dbeafe;color:#1e3a8a}} .badge.neutral{{background:#f1f5f9;color:#334155}} .watch-top,.inst-head,.tf-title{{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}} .levels-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px}} .levels-grid div,.mini{{border:1px solid var(--line);border-radius:14px;background:#f8fafc;padding:10px}} .levels-grid span,.mini span{{display:block;color:var(--muted);font-size:12px}} .levels-grid b{{display:block;font-size:18px;margin:3px 0}} .wide{{grid-column:1/-1}} .boundary-note{{background:#f1f5f9;border-radius:12px;padding:10px;color:#334155}} table{{width:100%;border-collapse:collapse}} td,th{{border-bottom:1px solid var(--line);padding:8px;text-align:right}} .tf-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:12px}} .tf{{border-radius:16px;border:1px solid var(--line);padding:12px}} .tf.active{{background:#eff6ff;border-color:#93c5fd}} .tf.medium{{background:#f8fafc}} .tf.quiet{{background:#f0fdf4;border-color:#bbf7d0}} .mini{{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;margin-top:8px}} .priority{{display:inline-flex;min-width:64px;justify-content:center;border-radius:999px;padding:3px 8px;margin-left:6px;font-weight:900}} .p1{{background:#dbeafe;color:#1e3a8a}} .p2{{background:#fef3c7;color:#92400e}} .p3{{background:#dcfce7;color:#14532d}} button{{width:100%;border:0;border-radius:16px;background:var(--blue);color:white;padding:15px;font-weight:900;font-size:17px}} .status{{margin-top:10px;border-radius:14px;padding:10px}} .ok{{background:#dcfce7;color:#14532d}} .warn{{background:#fef3c7;color:#92400e}} .error{{background:#fee2e2;color:#7f1d1d}} .pending{{background:#dbeafe;color:#1e3a8a}} .empty{{background:#f0fdf4;border:1px solid #bbf7d0;color:#14532d;border-radius:16px;padding:14px}} @media(max-width:560px){{.hero h1{{font-size:23px}} .metric b{{font-size:26px}}}}
    </style></head><body><div class='wrap'><header class='hero'><h1>پنل روزانه PRV1</h1><p>نمای واضح وضعیت ابزارها و تایم‌فریم‌ها؛ observation-based و بدون سیگنال معاملاتی.</p></header>
    <section class='grid'><div class='metric'><small>Observationها</small><b>{h(s.get('candidate_count'))}</b></div><div class='metric'><small>Lifecycle</small><b>{h(s.get('lifecycle_count'))}</b></div><div class='metric'><small>Final</small><b>{h(s.get('final_outcome_count'))}</b></div><div class='metric'><small>Active</small><b>{h(s.get('active_tracking_count'))}</b></div><div class='metric'><small>New</small><b>{h(s.get('new_observation_candidate_count'))}</b></div></section>
    <section class='card'><h2>برداشت ساده</h2><p><b>{h(plain['headline'])}</b></p><ul>{''.join('<li>'+h(x)+'</li>' for x in plain['what_to_check_first'])}</ul></section>
    <section class='card'><h2>Active Watch با سطح‌های مرجع</h2>{active_html}</section>
    <section class='card'><h2>تغییرات آخرین اجرا</h2><p>{badge('Refresh موفق: '+h(latest.get('staged_refresh_successful_surface_count')),'quiet')} {badge('Refresh ناموفق: '+h(latest.get('staged_refresh_failed_surface_count')),'warn')} {badge('Cache معتبر: '+h(latest.get('valid_cache_surface_count')),'quiet')} {badge('Candidate جدید: '+h(latest.get('new_observation_candidate_count')),'neutral')} {badge('Finalized now: '+h(latest.get('finalized_now')),'neutral')}</p></section>
    <section class='card'><h2>Freshness & Coverage</h2><p>سطوح به‌روزشده: <span class='ltr'>{h(fresh['updated_surface_count'])}/{h(fresh['surface_count'])}</span></p><table><thead><tr><th>سطح</th><th>وضعیت</th><th>Bars</th><th>آخرین زمان</th></tr></thead><tbody>{freshness_html}</tbody></table></section>
    <section class='card'><h2>No Candidate یعنی چه؟</h2><p>این بخش توضیح می‌دهد کجا داده خوانده و rule scan انجام شده ولی candidate جدید پیدا نشده است.</p><ul>{no_candidate_html}</ul></section>
    <section class='card'><h2>Attention Priority</h2><p>این امتیاز فقط برای مرتب‌سازی توجه است، نه سیگنال.</p><ul>{priority_html}</ul></section>
    <section class='card'><h2>به‌روزرسانی</h2><button id='refresh-now-button'>به‌روزرسانی الآن</button><div id='refresh-status' class='status {refresh_cls}'>{h(refresh_text)}</div><div id='latest-run-status'></div><p class='muted'>این دکمه فقط workflow گیت‌هاب را از طریق Cloudflare Worker اجرا می‌کند.</p></section>
    {''.join(inst_html)}
    <section class='card'><h2>مرز استفاده</h2><p>این پنل وضعیت observation را روشن‌تر می‌کند، اما همچنان هیچ پیشنهاد خرید/فروش، ورود/خروج، تارگت، حد ضرر، PnL یا validation verdict تولید نمی‌کند.</p></section>
    <p class='muted'>Generated at {token(state['created_at_utc'])} · <a href='status_public.json'>status_public.json</a> · <a href='market_state_public.json'>market_state_public.json</a></p>
    </div><script src='refresh_config.js'></script><script src='mobile_refresh_button.js'></script></body></html>"""

def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    root = root.resolve()
    public = root/'public'; public.mkdir(parents=True, exist_ok=True)
    state = build_state(root)
    refresh_url = os.environ.get('MOBILE_REFRESH_WORKER_URL','').strip().rstrip('/')
    pages_url = os.environ.get('GITHUB_PAGES_URL','').strip()
    panel = root/'panel'; panel.mkdir(exist_ok=True)
    write_json(panel/'panel_human_state_payload.json', state)
    write_json(panel/'active_watch_reference_levels.json', {"created_at_utc": state['created_at_utc'], "rows": state['active_watch_reference_levels'], "boundary": BOUNDARY})
    write_json(panel/'market_state_by_instrument.json', state['market_state_by_instrument'])
    write_json(panel/'latest_changes_summary.json', state['latest_changes_summary'])
    write_json(panel/'freshness_coverage_summary.json', state['freshness_coverage_summary'])
    write_json(panel/'no_candidate_explanation.json', state['no_candidate_explanation'])
    write_json(panel/'attention_priority_summary.json', state['attention_priority_summary'])
    write_json(panel/'plain_language_explanation_fa.json', state['plain_language_explanation_fa'])
    public_status = {"program": PROGRAM, "created_at_utc": state['created_at_utc'], "active_instruments": INSTRUMENTS, **state['summary'], "latest_changes_summary": state['latest_changes_summary'], "freshness_coverage_summary": {"updated_surface_count":state['freshness_coverage_summary']['updated_surface_count'],"surface_count":state['freshness_coverage_summary']['surface_count']}, "plain_headline_fa": state['plain_language_explanation_fa']['headline'], "refresh_button": {"enabled": bool(refresh_url), "worker_url_configured": bool(refresh_url), "worker_health_url": f"{refresh_url}/health" if refresh_url else None}, "boundary": BOUNDARY}
    write_json(public/'status_public.json', public_status)
    write_json(public/'market_state_public.json', state)
    write_json(public/'active_watch_reference_levels.json', {"rows": state['active_watch_reference_levels'], "boundary": BOUNDARY})
    write_json(public/'freshness_coverage_summary.json', state['freshness_coverage_summary'])
    write_json(public/'no_candidate_explanation.json', state['no_candidate_explanation'])
    write_json(public/'attention_priority_summary.json', {"rows": state['attention_priority_summary'], "boundary": BOUNDARY})
    (public/'refresh_config.js').write_text('window.PRV1_REFRESH_WORKER_URL = '+json.dumps(refresh_url)+';\nwindow.PRV1_GITHUB_PAGES_URL = '+json.dumps(pages_url)+';\n', encoding='utf-8')
    (public/'mobile_refresh_button.js').write_text("""
async function prv1RefreshNow(){const endpoint=(window.PRV1_REFRESH_WORKER_URL||'').replace(/\/$/,'');const box=document.getElementById('refresh-status');if(!endpoint){box.textContent='Refresh endpoint تنظیم نشده است.';box.className='status warn';return;}const pin=prompt('PIN به‌روزرسانی را وارد کن');if(!pin){box.textContent='لغو شد.';box.className='status warn';return;}box.textContent='درخواست ارسال شد...';box.className='status pending';try{const res=await fetch(endpoint+'/refresh',{method:'POST',headers:{'content-type':'application/json','x-refresh-pin':pin},body:JSON.stringify({source:'mobile_prv1k_panel',requested_at:new Date().toISOString()})});const data=await res.json();if(!res.ok)throw new Error(data.reason||data.status||('HTTP '+res.status));box.textContent='درخواست ثبت شد. چند دقیقه بعد صفحه را reload کن.';box.className='status ok';poll(endpoint);}catch(e){box.textContent='Refresh failed: '+e.message;box.className='status error';}}
async function poll(endpoint){const box=document.getElementById('latest-run-status');if(!box)return;for(let i=0;i<12;i++){await new Promise(r=>setTimeout(r,10000));try{const res=await fetch(endpoint+'/latest-run');const data=await res.json();const run=data.latest_run;if(run){box.innerHTML='آخرین run: <span class="token" dir="ltr">'+run.status+'</span>'+(run.conclusion?' / <span class="token" dir="ltr">'+run.conclusion+'</span>':'')+' — <a target="_blank" href="'+run.html_url+'">باز کردن</a>';if(run.status==='completed')break;}}catch(_){}}}
window.addEventListener('DOMContentLoaded',()=>{const b=document.getElementById('refresh-now-button');if(b)b.addEventListener('click',prv1RefreshNow);});
""", encoding='utf-8')
    (public/'index.html').write_text(render_html(state, refresh_url, pages_url), encoding='utf-8')
    proof = {"program": PROGRAM, "artifact":"enhanced_market_state_panel_generation_proof", "created_at_utc": state['created_at_utc'], "features_added":["active_watch_reference_levels","run_to_run_change_log","freshness_coverage_card","no_candidate_explanation","attention_priority","rtl_mobile_ux_polish"], "html_lang":"fa", "html_dir":"rtl", "mixed_ltr_tokens_isolated": True, "refresh_button_preserved": bool(refresh_url), "no_action_surface_added": True, "outputs":["public/index.html","public/status_public.json","public/market_state_public.json","panel/active_watch_reference_levels.json","panel/freshness_coverage_summary.json","panel/no_candidate_explanation.json","panel/attention_priority_summary.json"], "boundary": BOUNDARY}
    write_json(root/'proofs'/'enhanced_market_state_panel_generation_proof.json', proof)
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
