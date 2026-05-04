from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from html import escape

BOUNDARY = {
    "runtime_observation_not_signal": True,
    "candidate_not_trade_recommendation": True,
    "outcome_observation_not_win_loss": True,
    "panel_payload_not_action_surface": True,
    "no_broker": True,
    "no_order": True,
    "no_execution": True,
    "no_buy_sell_hold": True,
    "no_entry_stop_target": True,
    "no_pnl": True,
    "no_optimizer": True,
    "no_validation_verdict": True,
    "no_production_readiness_claim": True,
}
INSTRUMENTS = ["XAUUSD", "EURUSD", "USDJPY"]
TF_ORDER = ["D1", "H1", "M15", "M5"]

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
    "post_trigger_low_extended_below_trigger_low_and_last_close_remains_below_trigger_close": "بعد از trigger، قیمت به سمت پایین ادامه داده و آخرین close هنوز پایین‌تر از close کندل trigger مانده است.",
    "last_post_trigger_close_back_above_trigger_close_without_full_high_close_invalidation": "بعد از trigger، آخرین close دوباره بالای close کندل trigger برگشته، اما invalidation کامل ثبت نشده است.",
    "post_trigger_completed_bar_closed_below_trigger_bar_low": "یک کندل کامل بعد از trigger زیر low کندل trigger بسته شده و طبق rule مشاهده نامعتبر شده است.",
    "no_range_breakout_observation_triggered": "اسکن rule انجام شده ولی شکست محدودهٔ قابل ثبت به‌عنوان observation candidate پیدا نشده است.",
    "ok": "داده خوانده شده و قابل بررسی بوده است.",
}


def read_json(path: Path, default=None):
    if default is None: default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def first_present(*vals, default=None):
    for v in vals:
        if v is not None:
            return v
    return default


def norm_surface(surface: str) -> tuple[str, str]:
    parts = (surface or "").split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return surface or "UNKNOWN", "UNKNOWN"


def token(s) -> str:
    return f"<span class='token' dir='ltr'>{escape(str(s if s is not None else '—'))}</span>"


def fa_status(status: str) -> str:
    return STATUS_FA.get(status or "", status or "نامشخص")


def fa_outcome(outcome: str) -> str:
    return OUTCOME_FA.get(outcome or "", outcome or "نامشخص")


def fa_type(t: str) -> str:
    return TYPE_FA.get(t or "", t or "Observation")


def fa_reason(r: str) -> str:
    return REASON_FA.get(r or "", r or "دلیل مشخصی ثبت نشده است.")


def row_meaning(row: dict) -> str:
    status = row.get("lifecycle_status") or row.get("status")
    outcome = row.get("latest_outcome_category")
    if status == "active_tracking" or row.get("is_final") is False:
        return "این ردیف هنوز بسته نشده و در اجرای بعدی دوباره بررسی می‌شود. این جمله یعنی «زیر نظر بماند»، نه اینکه معامله‌ای انجام شود."
    if outcome == "favorable_observation":
        return "این outcome فقط می‌گوید حرکت بعد از trigger با جهت observation هم‌خوان بوده است؛ win، سود یا تأیید استراتژی نیست."
    if outcome == "unfavorable_observation":
        return "این outcome فقط می‌گوید حرکت بعد از trigger طبق rule هم‌جهت/قوی نبوده است؛ loss یا دستور خروج نیست."
    if outcome == "invalidated_observation":
        return "این outcome فقط می‌گوید طبق rule، مشاهده دیگر معتبر نیست؛ loss یا تصمیم معاملاتی نیست."
    return "این ردیف یک مشاهدهٔ توصیفی است، نه توصیهٔ معامله."


def load_rows(root: Path) -> list[dict]:
    candidate_paths = [
        root/"ledger"/"candidate_lifecycle_rows_v1_after_candidate_detection.json",
        root/"ledger"/"candidate_lifecycle_rows_v1_post_refresh.json",
        root/"ledger"/"candidate_lifecycle_rows_v1_exact.json",
        root/"ledger"/"candidate_lifecycle_rows_v1.json",
    ]
    for p in candidate_paths:
        obj = read_json(p, {})
        rows = obj.get("rows") if isinstance(obj, dict) else None
        if isinstance(rows, list) and rows:
            return rows
    # fallback: panel post-refresh rows
    for p in [root/"panel"/"panel_payload_after_post_refresh_update.json", root/"panel"/"panel_payload_current.json"]:
        obj = read_json(p, {})
        rows = obj.get("post_refresh_lifecycle_rows") if isinstance(obj, dict) else None
        if isinstance(rows, list) and rows:
            return rows
    return []


def build_state(root: Path) -> dict:
    panel = read_json(root/"panel"/"panel_payload_after_daily_runtime.json")
    validation = read_json(root/"proofs"/"daily_runtime_local_validation_result.json")
    last_run = read_json(root/"logs"/"last_run_status_after_daily_runtime.json")
    staged = read_json(root/"reports"/"staged_provider_fetch_report.json")
    cache = read_json(root/"reports"/"staged_cache_update_report.json")
    detection = read_json(root/"reports"/"candidate_detection_report.json")
    post_update = read_json(root/"reports"/"post_refresh_lifecycle_update_report.json")

    summary = panel.get("summary") or panel.get("latest_runtime_summary") or panel.get("latest_exact_row_ledger_summary") or {}
    daily_summary = panel.get("daily_loop_summary") or {}
    latest_summary = panel.get("latest_runtime_summary") or {}
    candidate_count = first_present(summary.get("candidate_count"), latest_summary.get("merged_candidate_lifecycle_row_count"), last_run.get("candidate_count"), default=0)
    lifecycle_count = first_present(summary.get("lifecycle_count"), latest_summary.get("merged_candidate_lifecycle_row_count"), last_run.get("lifecycle_count"), default=candidate_count)
    final_outcome_count = first_present(summary.get("final_outcome_count"), latest_summary.get("final_outcome_count"), last_run.get("final_outcome_count"), default=0)
    active_tracking_count = first_present(summary.get("active_tracking_count"), latest_summary.get("active_tracking_count"), last_run.get("active_tracking_count"), default=0)
    new_candidate_count = first_present(daily_summary.get("new_observation_candidate_count"), latest_summary.get("new_observation_candidate_count"), detection.get("new_observation_candidate_count"), last_run.get("new_observation_candidate_count"), default=0)

    rows = load_rows(root)
    cache_rows = cache.get("surface_rows") or []
    fetch_rows = staged.get("surface_rows") or []
    scan_rows = detection.get("scan_rows") or []

    cache_by_surface = {r.get("surface"): r for r in cache_rows if r.get("surface")}
    fetch_by_surface = {r.get("surface"): r for r in fetch_rows if r.get("surface")}
    scan_by_surface = {r.get("surface"): r for r in scan_rows if r.get("surface")}
    rows_by_surface: dict[str, list[dict]] = {}
    for row in rows:
        surf = row.get("surface") or f"{row.get('instrument','UNKNOWN')} {row.get('timeframe','UNKNOWN')}"
        rows_by_surface.setdefault(surf, []).append(row)

    # Surface universe from staged plan/cache/scan plus known V1 surfaces
    surfaces = set(cache_by_surface) | set(fetch_by_surface) | set(scan_by_surface) | set(rows_by_surface)
    if not surfaces:
        surfaces = {"XAUUSD D1","XAUUSD H1","XAUUSD M15","EURUSD D1","EURUSD H1","EURUSD M15","EURUSD M5","USDJPY D1","USDJPY H1","USDJPY M15","USDJPY M5"}

    market: dict[str, dict] = {i: {"instrument": i, "overall_state": "بدون observation فعال", "timeframes": []} for i in INSTRUMENTS}
    active_rows = []
    final_rows = []

    for row in rows:
        if row.get("lifecycle_status") == "active_tracking" or row.get("is_final") is False:
            active_rows.append(row)
        elif row.get("is_final") is True or row.get("lifecycle_status") == "final_outcome_recorded":
            final_rows.append(row)

    for inst in INSTRUMENTS:
        inst_surfs = [s for s in surfaces if norm_surface(s)[0] == inst]
        inst_surfs = sorted(inst_surfs, key=lambda s: (TF_ORDER.index(norm_surface(s)[1]) if norm_surface(s)[1] in TF_ORDER else 99, s))
        for surf in inst_surfs:
            inst2, tf = norm_surface(surf)
            c = cache_by_surface.get(surf, {})
            f = fetch_by_surface.get(surf, {})
            sc = scan_by_surface.get(surf, {})
            rws = rows_by_surface.get(surf, [])
            updated = c.get("updated") if c else f.get("ok")
            provider_status = c.get("provider_status") or f.get("provider_status") or ("ok" if updated else "unknown")
            last_dt = c.get("last_provider_datetime") or f.get("last_provider_datetime")
            valid_bars = sc.get("valid_bar_count")
            scan_status = sc.get("status") or ("not_scanned_or_not_reported" if not sc else "unknown")
            detection_reason = sc.get("detection_reason") or sc.get("reason")
            if rws:
                if any((r.get("lifecycle_status") == "active_tracking" or r.get("is_final") is False) for r in rws):
                    plain_state = "مشاهدهٔ فعال وجود دارد"
                    priority = "active_watch"
                else:
                    plain_state = "فقط observationهای بسته‌شده دارد"
                    priority = "history"
            elif scan_status == "scanned_no_candidate":
                plain_state = "candidate جدید پیدا نشد"
                priority = "quiet"
            elif provider_status == "ok":
                plain_state = "داده تازه است؛ observation فعالی ثبت نشده"
                priority = "quiet"
            else:
                plain_state = "وضعیت نامشخص یا cache قابل اتکا نیست"
                priority = "caveat"
            market[inst]["timeframes"].append({
                "surface": surf,
                "instrument": inst2,
                "timeframe": tf,
                "plain_state_fa": plain_state,
                "priority": priority,
                "cache": {"updated": bool(updated), "provider_status": provider_status, "value_count": c.get("value_count") or f.get("value_count"), "last_provider_datetime": last_dt},
                "scan": {"status": scan_status, "valid_bar_count": valid_bars, "detection_reason": detection_reason, "detection_reason_fa": fa_reason(detection_reason)},
                "rows": rws,
            })
        if any(tf["priority"] == "active_watch" for tf in market[inst]["timeframes"]):
            market[inst]["overall_state"] = "یک یا چند observation فعال دارد"
        elif any(tf["priority"] == "history" for tf in market[inst]["timeframes"]):
            market[inst]["overall_state"] = "observationهای قبلی بسته شده‌اند؛ فعال جدید ندارد"
        elif market[inst]["timeframes"]:
            market[inst]["overall_state"] = "داده بررسی شده؛ candidate جدید ثبت نشده"

    latest_changes = {
        "new_observation_candidate_count": new_candidate_count,
        "existing_active_lifecycle_updates_performed": post_update.get("existing_active_lifecycle_updates_performed"),
        "finalized_now": post_update.get("finalized_now"),
        "staged_refresh_successful_surface_count": first_present(daily_summary.get("staged_refresh_successful_surface_count"), staged.get("successful_surface_count")),
        "staged_refresh_failed_surface_count": first_present(daily_summary.get("staged_refresh_failed_surface_count"), staged.get("failed_surface_count")),
        "valid_cache_surface_count": first_present(daily_summary.get("valid_cache_surface_count"), detection.get("valid_cache_surface_count")),
        "skipped_surface_count": first_present(daily_summary.get("skipped_surface_count"), detection.get("skipped_surface_count")),
        "candidate_detection_performed": detection.get("candidate_detection_performed"),
    }
    if active_rows:
        active_sentence = "یک observation هنوز فعال است و باید در اجرای بعدی دوباره بررسی شود."
    else:
        active_sentence = "در حال حاضر observation فعال ثبت نشده است."
    if new_candidate_count == 0:
        new_sentence = "در آخرین اسکن، candidate جدید پیدا نشده است."
    else:
        new_sentence = f"در آخرین اسکن، {new_candidate_count} candidate جدید پیدا شده است."
    provider_sentence = f"داده‌های provider برای {latest_changes.get('staged_refresh_successful_surface_count','—')} سطح با موفقیت refresh شده و {latest_changes.get('staged_refresh_failed_surface_count','—')} سطح fail شده است."
    plain_fa = {
        "headline": f"{provider_sentence} {new_sentence} {active_sentence}",
        "what_to_watch": [
            "بخش «Active Watch» مهم‌ترین بخش روزانه است؛ اگر چیزی آنجا بود یعنی هنوز باید در refresh بعدی پیگیری شود.",
            "بخش «وضعیت ابزارها» نشان می‌دهد هر instrument/timeframe چه وضعی دارد: فعال، بسته‌شده، یا بدون candidate جدید.",
            "هیچ‌کدام از این‌ها سیگنال خرید/فروش، ورود، خروج، حد ضرر، تارگت، PnL یا تأیید استراتژی نیست.",
        ],
        "boundary_simple": "این پنل برای مشاهده و پیگیری وضعیت است، نه تصمیم معاملاتی.",
    }

    state = {
        "program": "PRV1J-01",
        "artifact": "human_readable_market_state_payload",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
        "summary": {
            "candidate_count": candidate_count,
            "lifecycle_count": lifecycle_count,
            "final_outcome_count": final_outcome_count,
            "active_tracking_count": active_tracking_count,
            "new_observation_candidate_count": new_candidate_count,
            "validation_passed": validation.get("validation_passed"),
            "boundary_status": validation.get("boundary_status"),
        },
        "market_state_by_instrument": market,
        "active_watch_rows": active_rows,
        "final_observation_rows": final_rows,
        "latest_changes_summary": latest_changes,
        "plain_language_explanation_fa": plain_fa,
        "source_confidence": panel.get("source_confidence") or {"mode":"single_provider_caveated_only","provider":"twelve_data","is_source_truth":False},
        "calendar_event": panel.get("calendar_event") or "calendar_event_source_not_in_v1_scope",
        "forbidden_surfaces_absent": panel.get("forbidden_surfaces_absent") or {},
        "boundary": BOUNDARY,
    }
    return state


def render_html(state: dict, refresh_url: str, pages_url: str) -> str:
    generated_at = state["created_at_utc"]
    summary = state["summary"]
    latest = state["latest_changes_summary"]
    plain = state["plain_language_explanation_fa"]
    market = state["market_state_by_instrument"]
    active_rows = state["active_watch_rows"]

    def h(s): return escape(str(s if s is not None else '—'))
    def badge(text, cls="neutral"):
        return f"<span class='badge {cls}'>{h(text)}</span>"

    def row_chip(row):
        surf = row.get("surface") or f"{row.get('instrument','')} {row.get('timeframe','')}"
        status = row.get("lifecycle_status")
        outcome = row.get("latest_outcome_category")
        cls = "active" if status == "active_tracking" or row.get("is_final") is False else "final"
        return f"<div class='watch-row {cls}'><div class='watch-title'>{token(surf)} — {h(fa_type(row.get('candidate_type')))}</div><div class='watch-meta'>{badge(fa_status(status), cls)} {badge(fa_outcome(outcome), cls)}</div><p>{h(row_meaning(row))}</p><p class='reason'>دلیل ثبت‌شده: {h(fa_reason(row.get('latest_outcome_reason')))}</p></div>"

    active_html = "".join(row_chip(r) for r in active_rows) if active_rows else "<div class='empty-state'>الان هیچ observation فعالی وجود ندارد. یعنی چیزی برای پیگیری فوری در بخش active ثبت نشده است.</div>"

    inst_html = []
    for inst in INSTRUMENTS:
        data = market.get(inst, {"timeframes": []})
        tf_cards = []
        for tf in data.get("timeframes", []):
            priority = tf.get("priority")
            cls = {"active_watch":"active","history":"final","quiet":"quiet","caveat":"warn"}.get(priority,"neutral")
            row_bits = []
            for r in tf.get("rows") or []:
                row_bits.append(f"<div class='mini-row'><b>{h(fa_status(r.get('lifecycle_status')))}</b><br><span>{h(fa_outcome(r.get('latest_outcome_category')))}</span><br><small>{h(fa_reason(r.get('latest_outcome_reason')))}</small></div>")
            if not row_bits:
                row_bits.append(f"<div class='mini-row quiet-text'>{h(tf.get('scan',{}).get('detection_reason_fa') or 'Observation فعالی در این سطح ثبت نشده است.')}</div>")
            cache = tf.get("cache", {})
            scan = tf.get("scan", {})
            tf_cards.append(f"""
            <article class='tf-card {cls}'>
              <div class='tf-head'><span class='token' dir='ltr'>{h(tf.get('timeframe'))}</span><span>{h(tf.get('plain_state_fa'))}</span></div>
              <div class='tf-sub'>سطح: {token(tf.get('surface'))}</div>
              <div class='tf-grid'>
                <div><span class='label'>Cache</span><b>{h(cache.get('provider_status'))}</b></div>
                <div><span class='label'>Bars</span><b class='ltr'>{h(scan.get('valid_bar_count') or cache.get('value_count'))}</b></div>
                <div><span class='label'>آخرین زمان provider</span><b class='ltr'>{h(cache.get('last_provider_datetime'))}</b></div>
              </div>
              {''.join(row_bits)}
            </article>""")
        inst_html.append(f"""
        <section class='instrument-card'>
          <div class='instrument-head'><h2><span class='token' dir='ltr'>{h(inst)}</span></h2><span class='instrument-state'>{h(data.get('overall_state'))}</span></div>
          <div class='timeframe-grid'>{''.join(tf_cards)}</div>
        </section>""")

    refresh_status = "endpoint تنظیم شده است" if refresh_url else "endpoint هنوز تنظیم نشده است"
    refresh_cls = "ok" if refresh_url else "warn"

    return f"""<!doctype html>
<html lang='fa' dir='rtl'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>PRV1 — پنل وضعیت قابل فهم</title>
<style>
:root {{ --bg:#f5f7fb; --card:#ffffff; --ink:#111827; --muted:#64748b; --line:#e5e7eb; --active:#2563eb; --final:#475569; --quiet:#16a34a; --warn:#d97706; --bad:#dc2626; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Tahoma, Vazirmatn, IRANSans, Segoe UI, Arial, sans-serif; direction:rtl; text-align:right; line-height:1.7; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:16px; }}
.hero {{ background:linear-gradient(135deg,#0f172a,#1e3a8a); color:white; border-radius:24px; padding:20px; box-shadow:0 16px 38px rgba(15,23,42,.22); }}
.hero h1 {{ margin:0 0 8px; font-size:28px; }}
.hero p {{ margin:0; color:#dbeafe; }}
.summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(138px,1fr)); gap:12px; margin:14px 0; }}
.metric {{ background:var(--card); border-radius:18px; padding:16px; box-shadow:0 8px 24px rgba(15,23,42,.08); border:1px solid var(--line); }}
.metric .label {{ color:var(--muted); font-size:13px; }}
.metric .num {{ direction:ltr; unicode-bidi:isolate; text-align:right; font-size:32px; font-weight:900; margin-top:4px; }}
.card, .instrument-card {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:16px; margin:14px 0; box-shadow:0 8px 24px rgba(15,23,42,.07); }}
.card h2, .instrument-card h2 {{ margin:0 0 10px; font-size:21px; }}
.plain {{ font-size:18px; font-weight:700; }}
.small {{ color:var(--muted); font-size:13px; }}
.token, .ltr {{ direction:ltr; unicode-bidi:isolate; display:inline-block; font-family:ui-monospace, SFMono-Regular, Consolas, monospace; text-align:left; }}
.badge {{ display:inline-flex; align-items:center; border-radius:999px; padding:5px 10px; margin:3px; font-size:12px; font-weight:800; }}
.badge.active {{ background:#dbeafe; color:#1e3a8a; }} .badge.final {{ background:#e2e8f0; color:#334155; }} .badge.quiet {{ background:#dcfce7; color:#14532d; }} .badge.warn {{ background:#fef3c7; color:#92400e; }} .badge.neutral {{ background:#f1f5f9; color:#334155; }}
button {{ width:100%; border:0; border-radius:16px; padding:15px; background:#2563eb; color:white; font-size:17px; font-weight:900; cursor:pointer; }}
.status {{ margin-top:10px; padding:12px; border-radius:14px; font-size:14px; }} .ok {{ background:#dcfce7; color:#14532d; }} .warn {{ background:#fef3c7; color:#92400e; }} .error {{ background:#fee2e2; color:#7f1d1d; }} .pending {{ background:#dbeafe; color:#1e3a8a; }}
.watch-row {{ border:1px solid var(--line); border-right:6px solid var(--active); border-radius:16px; padding:13px; margin:10px 0; background:#f8fafc; }}
.watch-row.final {{ border-right-color:var(--final); }} .watch-title {{ font-weight:900; }} .watch-meta {{ margin:6px 0; }} .reason {{ color:#334155; margin:6px 0 0; }}
.empty-state {{ background:#f0fdf4; border:1px solid #bbf7d0; color:#14532d; border-radius:16px; padding:14px; }}
.instrument-head {{ display:flex; gap:10px; justify-content:space-between; align-items:center; flex-wrap:wrap; border-bottom:1px solid var(--line); padding-bottom:10px; margin-bottom:12px; }}
.instrument-state {{ color:#334155; background:#f1f5f9; padding:7px 11px; border-radius:999px; font-weight:800; }}
.timeframe-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }}
.tf-card {{ border:1px solid var(--line); border-radius:18px; padding:13px; background:#fff; }} .tf-card.active {{ border-color:#93c5fd; background:#eff6ff; }} .tf-card.final {{ border-color:#cbd5e1; background:#f8fafc; }} .tf-card.quiet {{ border-color:#bbf7d0; background:#f0fdf4; }} .tf-card.warn {{ border-color:#fed7aa; background:#fff7ed; }}
.tf-head {{ display:flex; justify-content:space-between; align-items:center; gap:8px; font-weight:900; }} .tf-sub {{ color:var(--muted); font-size:13px; margin-top:6px; }}
.tf-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:10px 0; }} .tf-grid div {{ background:rgba(255,255,255,.68); border:1px solid rgba(148,163,184,.25); border-radius:12px; padding:8px; }} .tf-grid .label {{ display:block; color:var(--muted); font-size:11px; }}
.mini-row {{ border-top:1px dashed #cbd5e1; padding-top:8px; margin-top:8px; }} .quiet-text {{ color:#166534; }}
.footer-note {{ margin:20px 0; color:#475569; font-size:13px; }}
@media (max-width:560px) {{ .hero h1 {{ font-size:23px; }} .metric .num {{ font-size:28px; }} .tf-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class='wrap'>
  <header class='hero'>
    <h1>پنل وضعیت PRV1</h1>
    <p>زبان ساده برای فهمیدن اینکه هر ابزار و تایم‌فریم چه وضعی دارد؛ نه سیگنال، نه معامله، نه توصیه.</p>
  </header>

  <section class='summary-grid'>
    <div class='metric'><div class='label'>کل observationها</div><div class='num'>{h(summary.get('candidate_count'))}</div></div>
    <div class='metric'><div class='label'>Lifecycleها</div><div class='num'>{h(summary.get('lifecycle_count'))}</div></div>
    <div class='metric'><div class='label'>بسته‌شده‌ها</div><div class='num'>{h(summary.get('final_outcome_count'))}</div></div>
    <div class='metric'><div class='label'>فعال‌ها</div><div class='num'>{h(summary.get('active_tracking_count'))}</div></div>
    <div class='metric'><div class='label'>candidate جدید</div><div class='num'>{h(summary.get('new_observation_candidate_count'))}</div></div>
  </section>

  <section class='card'>
    <h2>برداشت ساده</h2>
    <p class='plain'>{h(plain.get('headline'))}</p>
    <ul>{''.join('<li>'+h(x)+'</li>' for x in plain.get('what_to_watch', []))}</ul>
  </section>

  <section class='card'>
    <h2>Active Watch — چیزهایی که هنوز باز هستند</h2>
    {active_html}
  </section>

  <section class='card'>
    <h2>تغییرات آخرین اجرا</h2>
    <p>{badge('Refresh موفق: '+h(latest.get('staged_refresh_successful_surface_count')), 'quiet')} {badge('Refresh ناموفق: '+h(latest.get('staged_refresh_failed_surface_count')), 'warn')} {badge('Cache معتبر: '+h(latest.get('valid_cache_surface_count')), 'quiet')} {badge('جدید: '+h(latest.get('new_observation_candidate_count')), 'neutral')} {badge('Final شده در این اجرا: '+h(latest.get('finalized_now')), 'neutral')}</p>
  </section>

  <section class='card'>
    <h2>به‌روزرسانی</h2>
    <button id='refresh-now-button'>به‌روزرسانی الآن</button>
    <div id='refresh-status' class='status {refresh_cls}'>Refresh endpoint: {h(refresh_status)}</div>
    <div id='latest-run-status' class='small'></div>
    <p class='small'>این دکمه فقط GitHub Actions را از طریق Cloudflare Worker اجرا می‌کند. داخل مرورگر یا Worker هیچ broker، execution، signal، PnL یا validation logic اجرا نمی‌شود.</p>
  </section>

  {''.join(inst_html)}

  <section class='card'>
    <h2>مرز استفاده</h2>
    <p>این پنل عمداً واضح‌تر شده، اما هنوز تصمیم معاملاتی نمی‌دهد. عبارت‌هایی مثل active، favorable یا invalidated فقط وضعیت observation هستند، نه خرید/فروش/ورود/خروج/سود/ضرر.</p>
  </section>
  <p class='footer-note'>Generated at <span class='token' dir='ltr'>{h(generated_at)}</span> — <a href='status_public.json'>status_public.json</a> · <a href='market_state_public.json'>market_state_public.json</a></p>
</div>
<script src='refresh_config.js'></script>
<script src='mobile_refresh_button.js'></script>
</body>
</html>"""


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
    root = root.resolve()
    public = root/"public"
    public.mkdir(parents=True, exist_ok=True)
    state = build_state(root)
    refresh_url = os.environ.get('MOBILE_REFRESH_WORKER_URL','').strip().rstrip('/')
    pages_url = os.environ.get('GITHUB_PAGES_URL','').strip()

    write_json(root/"panel"/"panel_human_state_payload.json", state)
    write_json(root/"panel"/"market_state_by_instrument.json", state["market_state_by_instrument"])
    write_json(root/"panel"/"active_watch_summary.json", {"created_at_utc": state["created_at_utc"], "rows": state["active_watch_rows"], "boundary": BOUNDARY})
    write_json(root/"panel"/"latest_changes_summary.json", {"created_at_utc": state["created_at_utc"], **state["latest_changes_summary"], "boundary": BOUNDARY})
    write_json(root/"panel"/"plain_language_explanation_fa.json", state["plain_language_explanation_fa"])

    status_public = {
        "program": "PRV1J-01",
        "artifact": "status_public_human_readable",
        "created_at_utc": state["created_at_utc"],
        "active_instruments": INSTRUMENTS,
        **state["summary"],
        "latest_changes_summary": state["latest_changes_summary"],
        "plain_headline_fa": state["plain_language_explanation_fa"].get("headline"),
        "refresh_button": {"enabled": bool(refresh_url), "worker_url_configured": bool(refresh_url), "worker_health_url": f"{refresh_url}/health" if refresh_url else None},
        "boundary": BOUNDARY,
    }
    write_json(public/"status_public.json", status_public)
    write_json(public/"market_state_public.json", state)
    write_json(public/"active_watch_public.json", {"rows": state["active_watch_rows"], "boundary": BOUNDARY})
    write_json(public/"latest_changes_public.json", state["latest_changes_summary"])
    write_json(public/"plain_language_fa.json", state["plain_language_explanation_fa"])

    (public/'refresh_config.js').write_text('window.PRV1_REFRESH_WORKER_URL = '+json.dumps(refresh_url)+';\nwindow.PRV1_GITHUB_PAGES_URL = '+json.dumps(pages_url)+';\n', encoding='utf-8')
    (public/'mobile_refresh_button.js').write_text("""
async function prv1RefreshNow(){
  const endpoint=(window.PRV1_REFRESH_WORKER_URL||'').replace(/\\/$/,'');
  const box=document.getElementById('refresh-status');
  if(!endpoint){box.textContent='Refresh endpoint تنظیم نشده است. از GitHub Actions به‌صورت دستی اجرا کن.';box.className='status warn';return;}
  const pin=prompt('PIN به‌روزرسانی را وارد کن');
  if(!pin){box.textContent='به‌روزرسانی لغو شد.';box.className='status warn';return;}
  box.textContent='درخواست به‌روزرسانی ارسال شد...';box.className='status pending';
  try{const res=await fetch(endpoint+'/refresh',{method:'POST',headers:{'content-type':'application/json','x-refresh-pin':pin},body:JSON.stringify({source:'mobile_human_panel',requested_at:new Date().toISOString()})});const data=await res.json();if(!res.ok)throw new Error(data.reason||data.status||('HTTP '+res.status));box.textContent='درخواست ثبت شد. GitHub Actions در حال اجراست. چند دقیقه صبر کن و صفحه را reload کن.';box.className='status ok';prv1PollLatestRun(endpoint);}catch(e){box.textContent='Refresh failed: '+e.message;box.className='status error';}}
async function prv1PollLatestRun(endpoint){const box=document.getElementById('latest-run-status');if(!box)return;for(let i=0;i<12;i++){await new Promise(r=>setTimeout(r,10000));try{const res=await fetch(endpoint+'/latest-run');const data=await res.json();const run=data.latest_run;if(run){box.innerHTML='آخرین run: <b class="token" dir="ltr">'+run.status+'</b>'+(run.conclusion?' / <span class="token" dir="ltr">'+run.conclusion+'</span>':'')+' — <a href="'+run.html_url+'" target="_blank">باز کردن</a>';if(run.status==='completed')break;}}catch(_){}}}
window.addEventListener('DOMContentLoaded',()=>{const btn=document.getElementById('refresh-now-button');if(btn)btn.addEventListener('click',prv1RefreshNow);});
""", encoding='utf-8')
    (public/'index.html').write_text(render_html(state, refresh_url, pages_url), encoding='utf-8')

    proof = {
        "program":"PRV1J-01",
        "artifact":"human_readable_panel_generation_proof",
        "created_at_utc": state["created_at_utc"],
        "rtl_enabled": True,
        "html_lang":"fa",
        "html_dir":"rtl",
        "mixed_ltr_tokens_isolated": True,
        "outputs":["public/index.html","public/status_public.json","public/market_state_public.json","panel/panel_human_state_payload.json","panel/market_state_by_instrument.json","panel/active_watch_summary.json","panel/plain_language_explanation_fa.json"],
        "refresh_button_preserved": bool(refresh_url),
        "no_action_surface_added": True,
        "boundary": BOUNDARY,
    }
    write_json(root/"proofs"/"human_readable_panel_generation_proof.json", proof)
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
