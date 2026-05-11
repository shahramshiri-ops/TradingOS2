/* SIG-BRAIN-OPS5 — Active Event Minimal Panel Redesign
   Purpose: keep the backend brain powerful, but show only confirmed active memory events
   from a short recent validity window. This UI remains display-only and never emits
   buy/sell/entry/stop/target/probability/broker instructions. */
const PANEL_VERSION = 'SIG-BRAIN-OPS5_ACTIVE_EVENT_MINIMAL_PANEL_v1_0';
const ACTIVE_EVENT_WINDOW_MIN = 10;
const HISTORY_KEEP_HOURS = 24;
const HISTORY_MAX_ITEMS = 20;
const STORAGE_HISTORY_KEY = 'sigBrain4.activeEventHistory.v1';
const STORAGE_NOTIFIED_KEY = 'sigBrain4.notifiedEventIds.v1';

async function loadJson(path, required=false){
  try{
    const res = await fetch(path + (path.includes('?') ? '&' : '?') + 'ts=' + Date.now());
    if(!res.ok) throw new Error(`${path} not found`);
    return await res.json();
  }catch(err){
    if(required) throw err;
    return null;
  }
}
async function loadPayload(){ return await loadJson('sig_brain4_runtime_payload_current.json', true); }
async function loadContext(){ return await loadJson('../../inputs/sig_brain4_live_context_latest.json', false); }

function esc(x){ return String(x ?? '—').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' }[m])); }
function asArray(x){ return Array.isArray(x) ? x : []; }
function parseUtc(value){ if(!value) return null; const d = new Date(String(value)); return Number.isNaN(d.getTime()) ? null : d; }
function isoMinute(d){ return d ? d.toISOString().replace(/\.\d{3}Z$/, 'Z') : '—'; }
function addMinutes(d, min){ return d ? new Date(d.getTime() + min*60000) : null; }
function minutesBetween(later, earlier){ if(!later || !earlier) return null; return Math.round((later.getTime()-earlier.getTime())/60000); }
function numberFmt(x){
  if(x === null || x === undefined || x === '') return '—';
  if(typeof x === 'number') return Number.isInteger(x) ? String(x) : x.toFixed(5).replace(/0+$/,'').replace(/\.$/,'');
  return String(x);
}
function timeframeMinutes(tf){
  const s = String(tf || '').toUpperCase();
  const m = s.match(/^(M|H|D)(\d+)$/);
  if(!m) return 15;
  const n = Number(m[2]);
  if(m[1] === 'M') return n;
  if(m[1] === 'H') return n*60;
  if(m[1] === 'D') return n*1440;
  return 15;
}
function sessionFromUtcDate(d){
  if(!d) return '—';
  const h = d.getUTCHours() + d.getUTCMinutes()/60;
  if(h >= 0 && h < 7) return 'ASIA';
  if(h >= 7 && h < 12) return 'LONDON';
  if(h >= 12 && h < 16) return 'LONDON_NY_OVERLAP';
  if(h >= 16 && h < 21) return 'NEW_YORK';
  return 'ROLLOVER_THIN_LIQUIDITY';
}
function latestContextRow(context, cards){
  const rows = [];
  for(const s of asArray(context?.surfaces)){
    const d = parseUtc(s.latest_bar_open_ts_utc);
    if(d) rows.push({date:d, ts:s.latest_bar_open_ts_utc, instrument:s.instrument, timeframe:s.timeframe, session:s.session_bucket});
  }
  for(const c of asArray(cards)){
    const lc = c.latest_context || {};
    const d = parseUtc(lc.latest_bar_open_ts_utc);
    if(d) rows.push({date:d, ts:lc.latest_bar_open_ts_utc, instrument:c.instrument, timeframe:c.timeframe, session:lc.session_bucket});
  }
  rows.sort((a,b)=>b.date.getTime()-a.date.getTime());
  return rows[0] || null;
}
function freshnessInfo(context, payload, cards){
  const now = new Date();
  const latest = latestContextRow(context, cards);
  const tfMin = timeframeMinutes(latest?.timeframe || 'M15');
  const latestClose = latest?.date ? addMinutes(latest.date, tfMin) : null;
  const ageFromClose = latestClose ? minutesBetween(now, latestClose) : null;
  const refreshTs = parseUtc(context?.created_utc || payload?.source_context_summary?.context_created_utc || payload?.created_utc);
  let status = 'UNKNOWN', label = 'نامشخص', css = 'unknown';
  if(ageFromClose === null){ status='UNKNOWN'; label='زمان آخرین کندل پیدا نشد'; css='unknown'; }
  else if(ageFromClose <= 20){ status='LIVE_OK'; label='تازه'; css='ok'; }
  else if(ageFromClose <= 45){ status='LAGGING'; label='کمی عقب'; css='lagging'; }
  else if(ageFromClose <= 90){ status='STALE'; label='عقب‌مانده'; css='stale'; }
  else { status='VERY_STALE'; label='خیلی عقب'; css='very-stale'; }
  return {now, latest, latestClose, ageFromClose, refreshTs, status, label, css, expectedSession:sessionFromUtcDate(now)};
}
function isParked(c){
  const text = `${c.memory_class||''} ${c.brain_state||''} ${c.band||''}`.toUpperCase();
  return text.includes('WEAKENED') || text.includes('PARKED') || c.active_in_runtime === false;
}
function isInsufficient(c){
  const text = `${c.brain_state||''} ${c.primary_reason||''}`.toUpperCase();
  return asArray(c.missing_inputs).length > 0 || text.includes('INSUFFICIENT') || text.includes('MISSING');
}
function isNoTrade(c){
  const text = `${c.memory_class||''} ${c.band||''} ${c.memory_id||''} ${c.plain_language_summary_fa||''}`.toUpperCase();
  return text.includes('NO_TRADE') || text.includes('AVOID') || text.includes('AVOID_SHORT');
}
function postureFa(c){
  const id = c.memory_id || '';
  if(isNoTrade(c)) return 'هشدار احتیاط / اجتناب از short-like context';
  if(id.includes('PRIOR48')) return 'watch پژوهشی: prior48 sweep rejection / fade-down context';
  if(id.includes('SWEEP_REJECTION')) return 'watch پژوهشی: sweep rejection / fade-down context';
  return 'memory event پژوهشی فعال';
}
function compactMeaningFa(c){
  const id = c.memory_id || '';
  if(isNoTrade(c)) return 'این context از نظر حافظهٔ تاریخی برای ادامهٔ short-like نامساعدتر از baseline بوده؛ فقط برای احتیاط شخصی.';
  if(id.includes('PRIOR48')) return 'شرط prior48 upside sweep و برگشت داخل سطح روی کندل بسته‌شده فعال شده؛ فقط watch پژوهشی fade-down.';
  if(id.includes('SWEEP_REJECTION')) return 'شرط sweep سطح بالایی و برگشت داخل سطح روی کندل بسته‌شده فعال شده؛ فقط watch پژوهشی fade-down.';
  return c.plain_language_summary_fa || 'یک memory event روی آخرین context بسته‌شده فعال شده است.';
}
function eventFromCard(c, payload, context, now){
  if(!c || !c.is_active_match || isParked(c) || isInsufficient(c)) return null;
  const lc = c.latest_context || {};
  const barOpen = parseUtc(lc.latest_bar_open_ts_utc);
  const barClose = barOpen ? addMinutes(barOpen, timeframeMinutes(c.timeframe)) : null;
  const detected = parseUtc(context?.created_utc || payload?.source_context_summary?.context_created_utc || payload?.created_utc) || now;
  const expires = addMinutes(detected, ACTIVE_EVENT_WINDOW_MIN);
  const eventId = `${c.memory_id || 'memory'}::${lc.latest_bar_open_ts_utc || isoMinute(detected)}`;
  const expired = expires ? now.getTime() > expires.getTime() : false;
  return {
    event_id:eventId,
    memory_id:c.memory_id,
    instrument:c.instrument,
    timeframe:c.timeframe,
    score_not_probability:c.score_not_probability,
    band:c.band,
    posture_fa:postureFa(c),
    meaning_fa:compactMeaningFa(c),
    source_bar_open_ts_utc:lc.latest_bar_open_ts_utc || null,
    source_bar_close_ts_utc:isoMinute(barClose),
    detected_at_utc:isoMinute(detected),
    expires_at_utc:isoMinute(expires),
    session_bucket:lc.session_bucket || '—',
    status:expired ? 'EXPIRED' : 'ACTIVE_NOW',
    expired,
    no_trade:isNoTrade(c),
    forbidden:'بدون buy/sell، بدون entry/stop/target، بدون probability، بدون broker/execution.',
    sort_ts:detected ? detected.getTime() : now.getTime()
  };
}
function safeLoad(key, fallback){
  try{ const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }catch(_){ return fallback; }
}
function safeSave(key, value){ try{ localStorage.setItem(key, JSON.stringify(value)); }catch(_){} }
function mergeHistory(activeEvents, now){
  const cutoff = now.getTime() - HISTORY_KEEP_HOURS*3600000;
  const existing = asArray(safeLoad(STORAGE_HISTORY_KEY, []));
  const map = new Map();
  for(const e of existing){
    const t = parseUtc(e.detected_at_utc)?.getTime() || parseUtc(e.expires_at_utc)?.getTime() || 0;
    if(t >= cutoff && e.event_id) map.set(e.event_id, e);
  }
  for(const e of activeEvents){ map.set(e.event_id, {...map.get(e.event_id), ...e, last_seen_utc:isoMinute(now)}); }
  const out = [...map.values()].sort((a,b)=>(b.sort_ts||0)-(a.sort_ts||0)).slice(0, HISTORY_MAX_ITEMS);
  safeSave(STORAGE_HISTORY_KEY, out);
  return out;
}
function notificationPermissionLabel(){
  if(!('Notification' in window)) return 'اعلان مرورگر پشتیبانی نمی‌شود';
  if(Notification.permission === 'granted') return 'اعلان فعال است';
  if(Notification.permission === 'denied') return 'اعلان در مرورگر بسته است';
  return 'فعال‌سازی اعلان مرورگر';
}
function renderSummary(info, activeEvents, payload){
  const activeCount = activeEvents.length;
  const latestLabel = info.latest ? `${info.latest.ts} · ${info.latest.instrument || ''} ${info.latest.timeframe || ''}` : '—';
  const closeAge = info.ageFromClose === null ? '—' : `${info.ageFromClose} دقیقه از بسته‌شدن`;
  const msg = activeCount ? `${activeCount} رویداد فعال معتبر` : 'هیچ رویداد فعال معتبر در ۱۰ دقیقهٔ اخیر نیست';
  return `<div class="status-row ${esc(info.css)}">
      <div class="status-main"><b>${esc(msg)}</b><span>${esc(info.status)} · ${esc(info.label)}</span></div>
      <div><b>آخرین کندل</b><span>${esc(latestLabel)}</span></div>
      <div><b>سن داده</b><span>${esc(closeAge)}</span></div>
      <div><b>UTC / session</b><span>${esc(isoMinute(info.now))} · ${esc(info.expectedSession)}</span></div>
    </div>
    <div class="minimal-boundary">این پنل فقط eventهای فعال و منقضی‌نشده را نشان می‌دهد. watchهای ناقص، شرط‌های خام و memoryهای آرشیوی از صفحهٔ اصلی حذف شده‌اند.</div>`;
}
function eventCard(e){
  const cls = e.no_trade ? 'no-trade-event' : 'watch-event';
  return `<article class="event-card ${cls}">
    <div class="event-head">
      <span class="event-badge">${e.no_trade ? 'NO-TRADE CONTEXT' : 'ACTIVE WATCH'}</span>
      <span class="event-expiry">اعتبار تا ${esc(e.expires_at_utc)}</span>
    </div>
    <h2>${esc(e.instrument)} ${esc(e.timeframe)}</h2>
    <div class="event-posture">${esc(e.posture_fa)}</div>
    <p>${esc(e.meaning_fa)}</p>
    <div class="event-grid">
      <div><b>فعال‌شده</b><span>${esc(e.detected_at_utc)}</span></div>
      <div><b>کندل مبنا</b><span>${esc(e.source_bar_close_ts_utc)}</span></div>
      <div><b>session</b><span>${esc(e.session_bucket)}</span></div>
      <div><b>قدرت پژوهشی</b><span>${esc(e.score_not_probability)}/100 · نه احتمال</span></div>
    </div>
    <div class="event-footer">${esc(e.forbidden)}</div>
  </article>`;
}
function emptyActive(){
  return `<section class="empty-active">
    <div class="empty-icon">●</div>
    <h2>فعلاً رویداد فعال نداریم</h2>
    <p>هیچ memory event منقضی‌نشده‌ای در پنجرهٔ ۱۰ دقیقهٔ اخیر فعال نشده است. پنل را بعد از refresh بعدی دوباره چک کن.</p>
  </section>`;
}
function historyCard(e){
  const expired = parseUtc(e.expires_at_utc) && new Date().getTime() > parseUtc(e.expires_at_utc).getTime();
  return `<div class="history-item ${expired ? 'expired' : 'live'}">
    <b>${esc(e.instrument)} ${esc(e.timeframe)}</b>
    <span>${esc(e.posture_fa)}</span>
    <em>${expired ? 'منقضی شده' : 'هنوز در پنجره اعتبار'} · ${esc(e.detected_at_utc)}</em>
  </div>`;
}
function renderHistory(history){
  if(!history.length) return `<section class="history"><h2>History</h2><p class="muted">هنوز event فعالی در این مرورگر ثبت نشده است.</p></section>`;
  return `<section class="history"><h2>History</h2><p class="muted">رویدادهای ثبت‌شدهٔ اخیر در همین مرورگر؛ برای audit سبک، نه صفحه اصلی تصمیم.</p>${history.slice(0,10).map(historyCard).join('')}</section>`;
}
function renderDiagnostics(payload, cards, context, activeEvents){
  const hiddenInactive = cards.filter(c=>!c.is_active_match).length;
  return `<details class="diagnostics">
    <summary>Diagnostics / جزئیات فنی پنهان</summary>
    <div class="diag-grid">
      <div><b>panel_version</b><span>${esc(PANEL_VERSION)}</span></div>
      <div><b>payload_cards</b><span>${esc(cards.length)}</span></div>
      <div><b>active_events_visible</b><span>${esc(activeEvents.length)}</span></div>
      <div><b>inactive_or_watch_hidden</b><span>${esc(hiddenInactive)}</span></div>
      <div><b>payload_created_utc</b><span>${esc(payload?.created_utc)}</span></div>
      <div><b>context_created_utc</b><span>${esc(context?.created_utc)}</span></div>
    </div>
    <p class="muted">شرط‌های خام و watchهای ناقص عمداً در صفحهٔ اصلی نمایش داده نمی‌شوند. برای ممیزی کامل، payload JSON و registryهای repo را بررسی کن.</p>
  </details>`;
}
function showToast(text){
  const box = document.createElement('div');
  box.className = 'toast';
  box.textContent = text;
  document.body.appendChild(box);
  window.setTimeout(()=>box.classList.add('show'), 20);
  window.setTimeout(()=>{ box.classList.remove('show'); window.setTimeout(()=>box.remove(), 400); }, 6200);
}
function maybeNotify(activeEvents){
  if(!activeEvents.length) return;
  const notified = new Set(asArray(safeLoad(STORAGE_NOTIFIED_KEY, [])));
  const fresh = activeEvents.filter(e=>!notified.has(e.event_id));
  if(!fresh.length) return;
  for(const e of fresh){
    showToast(`رویداد فعال مغز: ${e.instrument} ${e.timeframe}`);
    if('Notification' in window && Notification.permission === 'granted'){
      try{ new Notification('SIG Brain active event', {body:`${e.instrument} ${e.timeframe} · ${e.posture_fa}`}); }catch(_){}
    }
    notified.add(e.event_id);
  }
  safeSave(STORAGE_NOTIFIED_KEY, [...notified].slice(-100));
}
function renderControls(){
  return `<button id="notifyBtn" class="notify-btn" type="button">${esc(notificationPermissionLabel())}</button>
  <button id="refreshBtn" class="ghost-btn" type="button">Refresh panel</button>`;
}
function attachControls(){
  const notifyBtn = document.getElementById('notifyBtn');
  if(notifyBtn){
    notifyBtn.onclick = async ()=>{
      if(!('Notification' in window)){ showToast('اعلان مرورگر در این محیط پشتیبانی نمی‌شود.'); return; }
      try{ await Notification.requestPermission(); }catch(_){}
      notifyBtn.textContent = notificationPermissionLabel();
    };
  }
  const refreshBtn = document.getElementById('refreshBtn');
  if(refreshBtn) refreshBtn.onclick = ()=>window.location.reload();
}

Promise.all([loadPayload(), loadContext()]).then(([payload, context])=>{
  const cards = asArray(payload.cards);
  const now = new Date();
  const info = freshnessInfo(context, payload, cards);
  const candidateEvents = cards.map(c=>eventFromCard(c, payload, context, now)).filter(Boolean);
  const activeEvents = candidateEvents.filter(e=>!e.expired);
  const history = mergeHistory(candidateEvents, now);

  const summaryEl = document.getElementById('summary');
  summaryEl.classList.remove('skeleton');
  summaryEl.innerHTML = renderSummary(info, activeEvents, payload);
  document.getElementById('context-strip').innerHTML = renderControls();
  document.getElementById('cards').innerHTML = `${activeEvents.length ? activeEvents.map(eventCard).join('') : emptyActive()}${renderHistory(history)}${renderDiagnostics(payload, cards, context, activeEvents)}`;
  attachControls();
  maybeNotify(activeEvents);
}).catch(err=>{
  document.getElementById('summary').innerHTML = `<span class="warn">خطا در خواندن payload: ${esc(err.message)}</span>`;
});
