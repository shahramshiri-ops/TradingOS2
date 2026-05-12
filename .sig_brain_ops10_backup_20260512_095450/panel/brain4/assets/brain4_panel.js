/* SIG-BRAIN-OPS9 — Official Server-Side Brain Event History
   Extends OPS8 with official repo-backed event history.
   Browser localStorage is no longer the source of truth for History; it is only used
   for notification de-duplication.

   Previous lineage: SIG-BRAIN-OPS8 — Local Time Display & Event History Cleanup
   Purpose: keep the backend brain multi-timeframe and advanced, but show a simple
   personal-research active-event surface with human-readable local times. UTC and
   technical M5/M15/H1/H4/D1 timing stay in Diagnostics. The UI remains display-only
   and never emits buy/sell/entry/stop/target/probability/broker instructions. */
const PANEL_VERSION = 'SIG-BRAIN-OPS9_OFFICIAL_SERVER_SIDE_HISTORY_v1_0';
const ACTIVE_EVENT_WINDOW_MIN = 10;
const HISTORY_KEEP_DAYS = 7;
const HISTORY_MAX_ITEMS = 500;
const STORAGE_HISTORY_KEY = 'sigBrain4.activeEventHistory.deprecated.v2';
const STORAGE_NOTIFIED_KEY = 'sigBrain4.notifiedEventIds.v2';

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
async function loadRefreshStatus(){ return await loadJson('sig_live_refresh_status_latest.json', false); }
async function loadOfficialHistory(){ return await loadJson('sig_brain4_event_history_current.json', false); }

function esc(x){ return String(x ?? '—').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' }[m])); }
function asArray(x){ return Array.isArray(x) ? x : []; }
function parseUtc(value){ if(!value) return null; const d = new Date(String(value)); return Number.isNaN(d.getTime()) ? null : d; }
function isoMinute(d){ return d ? d.toISOString().replace(/\.\d{3}Z$/, 'Z') : '—'; }
function browserTimeZone(){
  try{ return Intl.DateTimeFormat().resolvedOptions().timeZone || 'local'; }catch(_){ return 'local'; }
}
function localTimeOnly(d){
  if(!d) return '—';
  try{
    return new Intl.DateTimeFormat('fa-IR-u-nu-latn', {hour:'2-digit', minute:'2-digit', hour12:false}).format(d);
  }catch(_){
    return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12:false});
  }
}
function localDateShort(d){
  if(!d) return '—';
  try{
    return new Intl.DateTimeFormat('fa-IR-u-nu-latn', {month:'2-digit', day:'2-digit'}).format(d);
  }catch(_){
    return d.toLocaleDateString();
  }
}
function localDateTime(d){
  if(!d) return '—';
  try{
    return new Intl.DateTimeFormat('fa-IR-u-nu-latn', {year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false}).format(d);
  }catch(_){
    return d.toLocaleString([], {year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false});
  }
}
function localDateTimeWithZone(d){
  if(!d) return '—';
  const tz = browserTimeZone();
  return `${localDateTime(d)} · ${tz}`;
}
function remainingFa(now, expires){
  const m = minutesBetween(expires, now);
  if(m === null || m === undefined || Number.isNaN(m)) return 'نامشخص';
  if(m <= 0) return 'منقضی شده';
  if(m < 60) return `${m} دقیقه باقی‌مانده`;
  const h = Math.floor(m/60), r = m % 60;
  return r ? `${h} ساعت و ${r} دقیقه باقی‌مانده` : `${h} ساعت باقی‌مانده`;
}
function historyScopeLabel(){ return `History رسمی سروری؛ ${HISTORY_KEEP_DAYS} روز اخیر، حداکثر ${HISTORY_MAX_ITEMS} رویداد، مشترک بین همهٔ دستگاه‌ها`; }
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
function humanAgeFa(minutes){
  if(minutes === null || minutes === undefined || Number.isNaN(minutes)) return 'نامشخص';
  if(minutes <= 0) return 'همین الان';
  if(minutes < 60) return `${minutes} دقیقه پیش`;
  const h = Math.floor(minutes/60), m = minutes % 60;
  return m ? `${h} ساعت و ${m} دقیقه پیش` : `${h} ساعت پیش`;
}
function freshnessFromRefreshAge(age){
  if(age === null || age === undefined) return {status:'UNKNOWN', label:'نامشخص', css:'unknown'};
  if(age <= 15) return {status:'LIVE_OK', label:'بروزرسانی تازه است', css:'ok'};
  if(age <= 35) return {status:'LAGGING', label:'بروزرسانی کمی عقب است', css:'lagging'};
  if(age <= 75) return {status:'STALE', label:'بروزرسانی عقب افتاده است', css:'stale'};
  return {status:'VERY_STALE', label:'بروزرسانی خیلی عقب است', css:'very-stale'};
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
function refreshInfo(status, context, payload, cards){
  const now = new Date();
  const refreshTs = parseUtc(status?.last_successful_refresh_utc || status?.created_utc || context?.created_utc || payload?.source_context_summary?.context_created_utc || payload?.created_utc);
  const refreshAge = refreshTs ? minutesBetween(now, refreshTs) : null;
  const fresh = freshnessFromRefreshAge(refreshAge);
  const latest = latestContextRow(context, cards);
  const tfMin = timeframeMinutes(latest?.timeframe || 'M15');
  const latestClose = latest?.date ? addMinutes(latest.date, tfMin) : null;
  const ageFromClose = latestClose ? minutesBetween(now, latestClose) : null;
  const providerM5 = parseUtc(status?.provider_m5?.max_latest_bar_open_ts_utc);
  const latestProviderM5Label = providerM5 ? isoMinute(providerM5) : '—';
  return {now, refreshTs, refreshAge, ...fresh, expectedSession:sessionFromUtcDate(now), latest, latestClose, ageFromClose, latestProviderM5Label, statusPayload:status || null};
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
function eventFromCard(c, payload, context, refreshStatus, now){
  if(!c || !c.is_active_match || isParked(c) || isInsufficient(c)) return null;
  const lc = c.latest_context || {};
  const barOpen = parseUtc(lc.latest_bar_open_ts_utc);
  const barClose = barOpen ? addMinutes(barOpen, timeframeMinutes(c.timeframe)) : null;
  const detected = parseUtc(refreshStatus?.last_successful_refresh_utc || refreshStatus?.created_utc || context?.created_utc || payload?.source_context_summary?.context_created_utc || payload?.created_utc) || now;
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

function normalizeOfficialEvent(e){
  if(!e || !e.event_id) return null;
  const activated = e.activated_at_utc || e.detected_at_utc || e.first_seen_utc || null;
  const expires = e.expires_at_utc || null;
  const posture = e.posture_fa || e.simple_posture_fa || e.event_type_fa || e.event_type || 'memory event پژوهشی فعال';
  const meaning = e.meaning_fa || e.display_message_fa || e.simple_message_fa || e.plain_language_summary_fa || 'یک memory event رسمی فعال شده است.';
  const expired = String(e.status || '').toUpperCase() === 'EXPIRED' || (parseUtc(expires) && new Date().getTime() > parseUtc(expires).getTime());
  return {
    event_id:e.event_id,
    memory_id:e.memory_id,
    instrument:e.instrument,
    timeframe:e.timeframe,
    score_not_probability:e.score_not_probability,
    band:e.band,
    posture_fa:posture,
    meaning_fa:meaning,
    source_bar_open_ts_utc:e.source_bar_open_ts_utc || null,
    source_bar_close_ts_utc:e.source_bar_close_ts_utc || null,
    detected_at_utc:activated,
    activated_at_utc:activated,
    expires_at_utc:expires,
    session_bucket:e.session_bucket || e.session || '—',
    status:expired ? 'EXPIRED' : (e.status || 'ACTIVE_NOW'),
    expired,
    no_trade:Boolean(e.no_trade || String(e.event_type || '').toUpperCase().includes('NO_TRADE') || String(e.posture_fa || '').includes('اجتناب') || String(e.posture_fa || '').includes('احتیاط')),
    forbidden:e.forbidden || e.forbidden_use || 'بدون buy/sell، بدون entry/stop/target، بدون probability، بدون broker/execution.',
    sort_ts:parseUtc(activated)?.getTime() || parseUtc(expires)?.getTime() || 0,
    official:true,
    last_seen_utc:e.last_seen_utc || null
  };
}
function officialEvents(historyPayload){
  const rows = asArray(historyPayload?.events).map(normalizeOfficialEvent).filter(Boolean);
  return rows.sort((a,b)=>(b.sort_ts||0)-(a.sort_ts||0));
}
function officialActiveEvents(historyPayload, now){
  return officialEvents(historyPayload).filter(e=>{
    const expires = parseUtc(e.expires_at_utc);
    return !e.expired && expires && now.getTime() <= expires.getTime();
  });
}
function officialHistoryMeta(historyPayload){
  if(!historyPayload) return 'History رسمی هنوز ساخته نشده؛ fallback موقت از payload فعلی استفاده می‌شود.';
  const count = asArray(historyPayload.events).length;
  const created = parseUtc(historyPayload.created_utc);
  const createdText = created ? `${localDateTime(created)} · ${humanAgeFa(minutesBetween(new Date(), created))}` : 'نامشخص';
  return `History رسمی سروری · ${count} رویداد · آخرین ساخت ${createdText}`;
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
function renderSummary(info, activeEvents){
  const activeCount = activeEvents.length;
  const msg = activeCount ? `${activeCount} رویداد فعال معتبر` : 'هیچ رویداد فعال معتبری در ۱۰ دقیقهٔ اخیر نیست';
  const refreshText = info.refreshTs ? `${localDateTimeWithZone(info.refreshTs)} · ${humanAgeFa(info.refreshAge)}` : 'نامشخص';
  const currentText = `${localDateTimeWithZone(info.now)} · ${info.expectedSession}`;
  return `<div class="status-row ${esc(info.css)}">
      <div class="status-main"><b>${esc(msg)}</b><span>${esc(info.status)} · ${esc(info.label)}</span></div>
      <div><b>آخرین بروزرسانی موفق</b><span>${esc(refreshText)}</span></div>
      <div><b>دادهٔ زنده</b><span>M5 خام؛ هر memory با timeframe خودش ارزیابی می‌شود</span></div>
      <div><b>زمان محلی / session فعلی</b><span>${esc(currentText)}</span></div>
    </div>
    <div class="minimal-boundary">صفحهٔ اصلی فقط eventهای فعال و منقضی‌نشده را نشان می‌دهد. زمان‌ها به وقت همین دستگاه نمایش داده می‌شوند؛ UTC و جزئیات M5/M15/H1/H4/D1 در Diagnostics هستند.</div>`;
}
function eventCard(e){
  const cls = e.no_trade ? 'no-trade-event' : 'watch-event';
  const detected = parseUtc(e.detected_at_utc);
  const expires = parseUtc(e.expires_at_utc);
  const sourceClose = parseUtc(e.source_bar_close_ts_utc);
  const validText = expires ? `اعتبار تا ${localTimeOnly(expires)} · ${remainingFa(new Date(), expires)}` : 'اعتبار نامشخص';
  return `<article class="event-card ${cls}">
    <div class="event-head">
      <span class="event-badge">${e.no_trade ? 'NO-TRADE CONTEXT' : 'ACTIVE WATCH'}</span>
      <span class="event-expiry">${esc(validText)}</span>
    </div>
    <h2>${esc(e.instrument)} <small>${esc(e.timeframe)}</small></h2>
    <div class="event-posture">${esc(e.posture_fa)}</div>
    <p>${esc(e.meaning_fa)}</p>
    <div class="event-grid">
      <div><b>فعال‌شده</b><span>${esc(localDateTime(detected))}</span></div>
      <div><b>کندل مبنای memory</b><span>${esc(localTimeOnly(sourceClose))}</span></div>
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
    <p>هیچ memory event منقضی‌نشده‌ای در پنجرهٔ ۱۰ دقیقهٔ اخیر فعال نشده است. با بروزرسانی بعدی دوباره چک کن.</p>
  </section>`;
}
function historyCard(e){
  const expires = parseUtc(e.expires_at_utc);
  const detected = parseUtc(e.detected_at_utc);
  const expired = expires && new Date().getTime() > expires.getTime();
  const statusText = expired ? `منقضی شده · تا ${localTimeOnly(expires)}` : `هنوز معتبر · تا ${localTimeOnly(expires)}`;
  return `<div class="history-item ${expired ? 'expired' : 'live'}">
    <b>${esc(e.instrument)} ${esc(e.timeframe)}</b>
    <span>${esc(e.posture_fa)}</span>
    <em>${esc(statusText)} · فعال‌شده ${esc(localTimeOnly(detected))}</em>
  </div>`;
}
function renderHistory(history, historyPayload){
  const meta = officialHistoryMeta(historyPayload);
  if(!history.length) return `<section class="history official-history"><h2>History رسمی</h2><p class="muted">هنوز event رسمی فعالی در history سروری ثبت نشده است. ${esc(historyScopeLabel())}</p></section>`;
  return `<section class="history official-history"><h2>History رسمی</h2><p class="muted">${esc(historyScopeLabel())}. فقط ACTIVE_MEMORY_EVENTهای واقعی ثبت می‌شوند؛ watchهای ناقص، inactiveها و archiveها وارد تاریخچه رسمی نمی‌شوند.</p><p class="muted">${esc(meta)}</p>${history.slice(0,25).map(historyCard).join('')}</section>`;
}
function renderDiagnostics(payload, cards, context, activeEvents, refreshStatus, info, historyPayload){
  const hiddenInactive = cards.filter(c=>!c.is_active_match).length;
  const providerLatest = refreshStatus?.provider_m5?.max_latest_bar_open_ts_utc || '—';
  const latestContext = refreshStatus?.brain_context?.latest || null;
  const lagCode = refreshStatus?.lag_diagnostic?.lag_reason_code || '—';
  const lagText = refreshStatus?.lag_diagnostic?.plain_language_fa || '—';
  return `<details class="diagnostics">
    <summary>Diagnostics / جزئیات فنی پنهان</summary>
    <div class="diag-grid">
      <div><b>panel_version</b><span>${esc(PANEL_VERSION)}</span></div>
      <div><b>local_timezone</b><span>${esc(browserTimeZone())}</span></div>
      <div><b>last_successful_refresh_utc</b><span>${esc(refreshStatus?.last_successful_refresh_utc || info.refreshTs?.toISOString())}</span></div>
      <div><b>raw_live_feed</b><span>${esc(refreshStatus?.raw_live_feed_timeframe || 'M5')}</span></div>
      <div><b>latest_provider_m5_open</b><span>${esc(providerLatest)}</span></div>
      <div><b>latest_memory_context</b><span>${esc(latestContext ? `${latestContext.instrument} ${latestContext.timeframe} ${latestContext.latest_bar_open_ts_utc}→${latestContext.latest_bar_close_ts_utc}` : '—')}</span></div>
      <div><b>lag_reason</b><span>${esc(lagCode)} · ${esc(lagText)}</span></div>
      <div><b>payload_cards</b><span>${esc(cards.length)}</span></div>
      <div><b>active_events_visible</b><span>${esc(activeEvents.length)}</span></div>
      <div><b>inactive_or_watch_hidden</b><span>${esc(hiddenInactive)}</span></div>
      <div><b>payload_created_utc</b><span>${esc(payload?.created_utc)}</span></div>
      <div><b>context_created_utc</b><span>${esc(context?.created_utc)}</span></div>
      <div><b>memory_timeframe_policy</b><span>${esc(refreshStatus?.memory_timeframe_policy_fa || 'دادهٔ خام زنده M5 است؛ هر memory با timeframe خودش ارزیابی می‌شود.')}</span></div>
      <div><b>official_history</b><span>${esc(historyPayload ? `${asArray(historyPayload.events).length} events · ${historyPayload.created_utc || 'no created_utc'}` : 'missing')}</span></div>
    </div>
    <p class="muted">M5 دادهٔ خام live است. هر memory بر اساس timeframe خودش مثل M5/M15/H1/H4/D1 ارزیابی می‌شود. این بخش فقط برای عیب‌یابی است.</p>
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

Promise.all([loadPayload(), loadContext(), loadRefreshStatus(), loadOfficialHistory()]).then(([payload, context, refreshStatus, officialHistory])=>{
  const cards = asArray(payload.cards);
  const now = new Date();
  const info = refreshInfo(refreshStatus, context, payload, cards);
  const fallbackEvents = cards.map(c=>eventFromCard(c, payload, context, refreshStatus, now)).filter(Boolean);
  const serverActiveEvents = officialActiveEvents(officialHistory, now);
  const activeEvents = serverActiveEvents.length ? serverActiveEvents : fallbackEvents.filter(e=>!e.expired);
  const history = officialHistory ? officialEvents(officialHistory) : fallbackEvents;

  const summaryEl = document.getElementById('summary');
  summaryEl.classList.remove('skeleton');
  summaryEl.innerHTML = renderSummary(info, activeEvents);
  document.getElementById('context-strip').innerHTML = renderControls();
  document.getElementById('cards').innerHTML = `${activeEvents.length ? activeEvents.map(eventCard).join('') : emptyActive()}${renderHistory(history, officialHistory)}${renderDiagnostics(payload, cards, context, activeEvents, refreshStatus, info, officialHistory)}`;
  attachControls();
  maybeNotify(activeEvents);
}).catch(err=>{
  document.getElementById('summary').innerHTML = `<span class="warn">خطا در خواندن payload: ${esc(err.message)}</span>`;
});
