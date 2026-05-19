/* SIG-BRAIN-OPS9 — Official Server-Side Brain Event History
   Extends OPS8 with official repo-backed event history.
   Browser localStorage is no longer the source of truth for History; it is only used
   for notification de-duplication.

   Previous lineage: SIG-BRAIN-OPS8 — Local Time Display & Event History Cleanup
   Purpose: keep the backend brain multi-timeframe and advanced, but show a simple
   personal-research active-event surface with human-readable local times. UTC and
   technical M5/M15/H1/H4/D1 timing stay in Diagnostics. The UI remains display-only
   and never emits buy/sell/entry/stop/target/probability/broker instructions. */
const PANEL_VERSION = 'SIG-BRAIN-OPS19_UI_INTERIOR_MINIMALISM_REFINEMENT_v1_0';
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
function isDirectionalWatch(c){
  const text = `${c.memory_class||''} ${c.candidate_type||''} ${c.brain_state||''} ${c.memory_id||''}`.toUpperCase();
  return text.includes('DIRECTIONAL');
}
function postureFa(c){
  const id = c.memory_id || '';
  if(isNoTrade(c)) return 'هشدار احتیاط / اجتناب از short-like context';
  if(isDirectionalWatch(c)){
    const side = String(c.direction_side || '').toUpperCase();
    return side === 'LONG' ? 'directional watch پژوهشی: LONG-bias context' : 'directional watch پژوهشی';
  }
  if(id.includes('PRIOR48')) return 'watch پژوهشی: prior48 sweep rejection / fade-down context';
  if(id.includes('SWEEP_REJECTION')) return 'watch پژوهشی: sweep rejection / fade-down context';
  return 'memory event پژوهشی فعال';
}
function compactMeaningFa(c){
  const id = c.memory_id || '';
  if(isNoTrade(c)) return 'این context از نظر حافظهٔ تاریخی برای ادامهٔ short-like نامساعدتر از baseline بوده؛ فقط برای احتیاط شخصی.';
  if(isDirectionalWatch(c)) return c.plain_language_summary_fa || 'یک directional watch پژوهشی روی کندل بسته‌شده فعال شده است؛ این دستور خرید/فروش یا نقطه ورود نیست.';
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
    direction_side:c.direction_side || null,
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
    direction_side:e.direction_side || e.directional_side || null,
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

function memoryRuntimeStatusFa(c){
  if(c.active_in_runtime === true) return 'در حال پایش';
  const state = String(c.brain_state || '').toUpperCase();
  const cls = String(c.memory_class || '').toUpperCase();
  if(state.includes('WEAKENED') || cls.includes('WEAKENED')) return 'آرشیو شده';
  return 'غیرفعال/آرشیو';
}
function memoryLibraryClass(c){
  if(c.active_in_runtime === true) return 'runtime-enabled';
  if(isParked(c)) return 'archived';
  return 'inactive';
}
function ifActiveMeaningFa(c){
  if(c.if_active_historical_posture_fa) return c.if_active_historical_posture_fa;
  if(isNoTrade(c)) return 'اگر فعال شود، context تاریخی احتیاط/اجتناب از short-like تصمیم را برجسته‌تر می‌کند؛ این buy signal نیست.';
  if(isDirectionalWatch(c)){
    const side = String(c.direction_side || '').toUpperCase();
    if(side === 'LONG') return 'اگر فعال شود، سناریوی تاریخی LONG-like نسبت به baseline برجسته‌تر می‌شود؛ این دستور خرید نیست.';
    if(side === 'SHORT') return 'اگر فعال شود، سناریوی تاریخی SHORT-like نسبت به baseline برجسته‌تر می‌شود؛ این دستور فروش نیست.';
    return 'اگر فعال شود، یک directional watch پژوهشی نسبت به baseline برجسته‌تر می‌شود؛ این signal نیست.';
  }
  const id = String(c.memory_id || '');
  if(id.includes('FADE_DOWN') || id.includes('SWEEP_REJECTION')) return 'اگر فعال شود، رفتار تاریخی fade-down / rejection context برجسته‌تر می‌شود؛ این دستور فروش نیست.';
  if(isParked(c)) return 'این memory فعلاً فقط برای audit و سابقه نگه‌داری می‌شود و در runtime فعال نمی‌شود مگر review جدید بیاید.';
  return c.plain_language_summary_fa || 'اگر فعال شود، فقط یک context پژوهشی تاریخی را برجسته می‌کند، نه دستور معامله.';
}
function memoryShortTypeFa(c){
  if(isNoTrade(c)) return 'no-trade / احتیاط';
  if(isDirectionalWatch(c)) return 'directional watch';
  if(isParked(c)) return 'archived';
  return 'watch context';
}
function plainStatusFa(c){
  const raw = String(c.brain_state || c.activation_status || '').toUpperCase();
  if(c.active_in_runtime === true && isInsufficient(c)) return 'نیاز به دادهٔ بیشتر';
  if(c.active_in_runtime === true) return 'در حال پایش';
  if(raw.includes('WEAKENED') || raw.includes('PARKED')) return 'آرشیو شده';
  return 'غیرفعال/آرشیو';
}
function libraryOutcomeLabel(c){
  if(isNoTrade(c)) return 'اگر فعال شود: احتیاط / اجتناب از short-like context برجسته می‌شود.';
  if(isDirectionalWatch(c)){
    const side = String(c.direction_side || '').toUpperCase();
    if(side === 'LONG') return 'اگر فعال شود: سناریوی LONG-like تاریخی نسبت به baseline برجسته‌تر می‌شود.';
    if(side === 'SHORT') return 'اگر فعال شود: سناریوی SHORT-like تاریخی نسبت به baseline برجسته‌تر می‌شود.';
    return 'اگر فعال شود: یک directional watch تاریخی برجسته‌تر می‌شود.';
  }
  return ifActiveMeaningFa(c);
}
function memoryLibraryCard(c){
  const cls = memoryLibraryClass(c);
  const score = c.score_not_probability ?? '—';
  const searchText = `${c.instrument||''} ${c.timeframe||''} ${c.memory_id||''} ${c.headline_fa||''} ${c.plain_language_label_fa||''} ${ifActiveMeaningFa(c)||''}`.toLowerCase();
  const statusKey = c.active_in_runtime === true ? 'runtime' : 'archived';
  const title = c.headline_fa || c.plain_language_label_fa || memoryShortTypeFa(c);
  const outcome = libraryOutcomeLabel(c);
  const status = plainStatusFa(c);
  const muted = cls === 'archived' ? 'این الگو فعلاً فقط برای سابقه نگهداری می‌شود.' : 'اگر شرایط کامل شود، در صفحهٔ رویدادهای فعال نمایش داده می‌شود.';
  return `<article class="memory-lib-card ${cls}" data-search="${esc(searchText)}" data-status="${esc(statusKey)}">
    <div class="memory-card-topline">
      <span class="library-state ${cls}">${esc(status)}</span>
      <span class="library-type">${esc(memoryShortTypeFa(c))}</span>
    </div>
    <div class="memory-card-main">
      <div class="memory-symbol" dir="ltr">${esc(c.instrument || '—')} <small>${esc(c.timeframe || '—')}</small></div>
      <h3>${esc(title)}</h3>
      <p class="memory-outcome">${esc(outcome)}</p>
      <p class="memory-note">${esc(muted)} بدون buy/sell، entry/stop/target یا probability.</p>
    </div>
    <div class="memory-card-meta">
      <span><b>قدرت پژوهشی</b>${esc(score)}/100</span>
      <span><b>وضعیت</b>${esc(status)}</span>
    </div>
    <details class="memory-technical">
      <summary>شناسه و جزئیات فنی</summary>
      <code>${esc(c.memory_id)}</code>
      <div>${esc(c.activation_status || c.brain_state || '—')}</div>
    </details>
  </article>`;
}
function renderMemoryLibrary(cards){
  const sorted = [...asArray(cards)].sort((a,b)=>{
    const ar = a.active_in_runtime === true ? 0 : 1;
    const br = b.active_in_runtime === true ? 0 : 1;
    if(ar !== br) return ar - br;
    return String(a.instrument||'').localeCompare(String(b.instrument||'')) || String(a.timeframe||'').localeCompare(String(b.timeframe||''));
  });
  const activeCount = sorted.filter(c=>c.active_in_runtime === true).length;
  const archivedCount = sorted.length - activeCount;
  return `<section class="memory-library">
    <div class="library-header-card">
      <div>
        <h2>${esc(sorted.length)} الگو در مغز</h2>
        <p>این تب فقط کتابخانهٔ سادهٔ الگوهاست. صفحهٔ اصلی فقط رویدادهای فعال معتبر را نشان می‌دهد.</p>
      </div>
      <div class="library-stats">
        <span><b>${esc(activeCount)}</b> در حال پایش</span>
        <span><b>${esc(archivedCount)}</b> آرشیو/غیرفعال</span>
      </div>
    </div>
    <div class="library-tools" aria-label="فیلتر کتابخانه الگوها">
      <input id="memorySearch" class="library-search" type="search" placeholder="جستجو: EURUSD، H1، شکست ناموفق، London..." />
      <select id="memoryStatusFilter" class="library-filter" aria-label="فیلتر وضعیت">
        <option value="all">همهٔ الگوها</option>
        <option value="runtime">در حال پایش</option>
        <option value="archived">آرشیو/غیرفعال</option>
      </select>
    </div>
    <div id="memoryLibraryGrid" class="memory-lib-grid-wrap">${sorted.map(memoryLibraryCard).join('')}</div>
    <div id="memoryLibraryEmpty" class="library-empty" style="display:none">موردی با این فیلتر پیدا نشد.</div>
  </section>`;
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
  const msg = activeCount ? `${activeCount} رویداد فعال معتبر` : 'فعلاً رویداد فعال نداریم';
  const refreshText = info.refreshTs ? `${localTimeOnly(info.refreshTs)} · ${humanAgeFa(info.refreshAge)}` : 'نامشخص';
  const currentText = `${localTimeOnly(info.now)} · ${info.expectedSession}`;
  return `<div class="status-hero ${esc(info.css)}">
      <div class="status-pulse" aria-hidden="true"></div>
      <div class="status-copy">
        <span class="status-kicker">وضعیت فعلی</span>
        <b>${esc(msg)}</b>
        <em>${esc(info.label)}</em>
      </div>
      <div class="status-facts" aria-label="خلاصه وضعیت فعلی">
        <div class="fact-row"><span>آخرین بروزرسانی</span><b>${esc(refreshText)}</b></div>
        <div class="fact-row"><span>دادهٔ خام</span><b>M5 · پردازش چندتایم‌فریمی در پشت صحنه</b></div>
        <div class="fact-row"><span>زمان / session</span><b>${esc(currentText)}</b></div>
      </div>
    </div>
    <p class="minimal-boundary"><strong>یادآوری:</strong> صفحهٔ اصلی فقط event فعال معتبر را نشان می‌دهد. کتابخانهٔ الگوها و History رسمی در تب‌های جدا هستند.</p>`;
}
function eventCard(e){
  const cls = e.no_trade ? 'no-trade-event' : 'watch-event';
  const detected = parseUtc(e.detected_at_utc);
  const expires = parseUtc(e.expires_at_utc);
  const sourceClose = parseUtc(e.source_bar_close_ts_utc);
  const validText = expires ? `${localTimeOnly(expires)} · ${remainingFa(new Date(), expires)}` : 'اعتبار نامشخص';
  return `<article class="event-card ${cls}">
    <div class="event-head">
      <span class="event-badge">${e.no_trade ? 'احتیاط فعال' : 'watch فعال'}</span>
      <span class="event-expiry">اعتبار تا ${esc(validText)}</span>
    </div>
    <div class="event-title-row">
      <h2>${esc(e.instrument)} <small>${esc(e.timeframe)}</small></h2>
      <span class="research-score">${esc(e.score_not_probability)}/100 · نه احتمال</span>
    </div>
    <div class="event-posture">${esc(e.posture_fa)}</div>
    <p>${esc(e.meaning_fa)}</p>
    <div class="event-meta-list">
      <div class="event-meta-row"><b>فعال‌شده</b><span>${esc(localTimeOnly(detected))}</span></div>
      <div class="event-meta-row"><b>کندل مبنا</b><span>${esc(localTimeOnly(sourceClose))}</span></div>
      <div class="event-meta-row"><b>session</b><span>${esc(e.session_bucket)}</span></div>
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
  return `<section class="history official-history"><h2>History رسمی</h2><p class="muted">${esc(historyScopeLabel())}. فقط ACTIVE_MEMORY_EVENTهای واقعی ثبت می‌شوند؛ watchهای ناقص، inactiveها و archiveها وارد تاریخچه رسمی نمی‌شوند.</p><p class="muted">${esc(meta)}</p><div class="history-list">${history.slice(0,25).map(historyCard).join('')}</div></section>`;
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
function renderControls(activeCount=0, memoryCount=0, historyCount=0){
  return `<div class="tabs" role="tablist" aria-label="SIG Brain tabs">
    <button id="activeTabBtn" class="tab-btn active" type="button" data-tab="active"><span>رویدادها</span><em>${esc(activeCount)}</em></button>
    <button id="libraryTabBtn" class="tab-btn" type="button" data-tab="library"><span>کتابخانه الگوها</span><em>${esc(memoryCount)}</em></button>
    <button id="historyTabBtn" class="tab-btn" type="button" data-tab="history"><span>History رسمی</span><em>${esc(historyCount)}</em></button>
  </div>
  <div class="panel-actions">
    <button id="notifyBtn" class="notify-btn" type="button">${esc(notificationPermissionLabel())}</button>
    <button id="refreshBtn" class="ghost-btn" type="button">بروزرسانی</button>
  </div>`;
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
  for(const btn of document.querySelectorAll('.tab-btn')){
    btn.onclick = ()=>{
      const tab = btn.getAttribute('data-tab');
      for(const b of document.querySelectorAll('.tab-btn')) b.classList.toggle('active', b === btn);
      document.getElementById('active-tab')?.classList.toggle('hidden', tab !== 'active');
      document.getElementById('library-tab')?.classList.toggle('hidden', tab !== 'library');
      document.getElementById('history-tab')?.classList.toggle('hidden', tab !== 'history');
    };
  }
  attachMemoryLibraryFilters();
}

function attachMemoryLibraryFilters(){
  const search = document.getElementById('memorySearch');
  const status = document.getElementById('memoryStatusFilter');
  const cards = Array.from(document.querySelectorAll('.memory-lib-card'));
  const empty = document.getElementById('memoryLibraryEmpty');
  if(!cards.length) return;
  const apply = ()=>{
    const q = String(search?.value || '').trim().toLowerCase();
    const s = status?.value || 'all';
    let visible = 0;
    for(const card of cards){
      const matchText = !q || String(card.dataset.search || '').includes(q);
      const matchStatus = s === 'all' || card.dataset.status === s;
      const ok = matchText && matchStatus;
      card.style.display = ok ? '' : 'none';
      if(ok) visible += 1;
    }
    if(empty) empty.style.display = visible ? 'none' : '';
  };
  if(search) search.oninput = apply;
  if(status) status.onchange = apply;
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
  document.getElementById('context-strip').innerHTML = renderControls(activeEvents.length, cards.length, history.length);
  document.getElementById('cards').innerHTML = `<section id="active-tab" class="tab-panel">${activeEvents.length ? activeEvents.map(eventCard).join('') : emptyActive()}</section><section id="library-tab" class="tab-panel hidden">${renderMemoryLibrary(cards)}</section><section id="history-tab" class="tab-panel hidden">${renderHistory(history, officialHistory)}${renderDiagnostics(payload, cards, context, activeEvents, refreshStatus, info, officialHistory)}</section>`;
  attachControls();
  maybeNotify(activeEvents);
}).catch(err=>{
  document.getElementById('summary').innerHTML = `<span class="warn">خطا در خواندن payload: ${esc(err.message)}</span>`;
});
