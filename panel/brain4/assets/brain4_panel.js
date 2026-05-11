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
async function loadPayload(){
  return await loadJson('sig_brain4_runtime_payload_current.json', true);
}
async function loadContext(){
  return await loadJson('../../inputs/sig_brain4_live_context_latest.json', false);
}
function esc(x){ return String(x ?? '—').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' }[m])); }
function asArray(x){ return Array.isArray(x) ? x : []; }
function numberFmt(x){
  if(x === null || x === undefined || x === '') return '—';
  if(typeof x === 'number') return Number.isInteger(x) ? String(x) : x.toFixed(5).replace(/0+$/,'').replace(/\.$/,'');
  return String(x);
}
function surfaceFor(context, instrument, timeframe){
  return asArray(context?.surfaces).find(s => s.instrument === instrument && s.timeframe === timeframe) || null;
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
  const text = `${c.memory_class||''} ${c.band||''} ${c.plain_language_summary_fa||''}`.toUpperCase();
  return text.includes('NO_TRADE') || text.includes('AVOID') || (c.plain_language_summary_fa||'').includes('no-trade') || (c.plain_language_summary_fa||'').includes('avoid-short');
}
function postureLabel(c){
  if(isParked(c)) return 'آرشیو / تضعیف‌شده';
  if(isNoTrade(c)) return 'هشدار no-trade / avoid-short';
  if((c.memory_id||'').includes('PRIOR48')) return 'watch تاریخی: fade-down بعد از prior48 rejection';
  if((c.memory_id||'').includes('SWEEP_REJECTION')) return 'watch تاریخی: fade-down بعد از sweep rejection';
  return 'watch تاریخی caveated';
}
function stateLabel(c){
  if(c.is_active_match) return 'فعال روی کندل بسته‌شدهٔ فعلی';
  if(isParked(c)) return 'آرشیو؛ در runtime فعال نمی‌شود';
  if(isInsufficient(c)) return 'داده یا field کافی نیست';
  return 'در watchlist؛ هنوز trigger کامل نشده';
}
function conditionHuman(raw){
  const s = String(raw || '');
  const observed = (s.match(/observed=([^\s]+)/)||[])[1];
  const observedText = observed ? `مشاهده: ${observed}` : '';
  if(s.startsWith('session_bucket eq NEW_YORK')) return `جلسه باید New York باشد؛ ${observedText}`;
  if(s.startsWith('session_bucket in')) return `جلسه باید London / London-NY / New York باشد؛ ${observedText}`;
  if(s.startsWith('upside_sweep_flag bool_eq True')) return `sweep سقف هنوز کامل نشده؛ ${observedText}`;
  if(s.startsWith('sweep_then_reject_back_inside_up_flag bool_eq True')) return `بسته‌شدن M15 دوباره داخل سطح هنوز تأیید نشده؛ ${observedText}`;
  if(s.startsWith('sweep_reference_type_up eq PRIOR48')) return `سطح reference هنوز PRIOR48 نشده؛ ${observedText}`;
  if(s.startsWith('sweep_reference_policy_up eq')) return `سیاست reference prior48 درست است؛ ${observedText}`;
  if(s.startsWith('data_sufficiency_status eq OK')) return `کفایت داده OK است`;
  if(s.startsWith('instrument eq')) return `instrument درست است؛ ${observedText}`;
  if(s.startsWith('timeframe eq')) return `timeframe درست است؛ ${observedText}`;
  if(s.startsWith('h4_h1_up_context bool_eq False')) return `هم‌راستایی صعودی H4/H1 غایب است؛ ${observedText || 'پاس'}`;
  if(s.startsWith('h4_h1_down_context bool_eq False')) return `هم‌راستایی نزولی H4/H1 غایب است؛ ${observedText || 'پاس'}`;
  if(s.startsWith('m15_range_ratio_12 between')) return `M15 در محدودهٔ chop/range-neutral است؛ ${observedText}`;
  if(s.startsWith('m15_dir in')) return `جهت M15 خنثی/نامشخص است؛ ${observedText}`;
  if(s.startsWith('NOT(h1_dir == UP AND h4_dir == UP)')) return `H1 و H4 همزمان up نیستند`;
  if(s.startsWith('conflict_severity not_eq HIGH')) return `تضاد شدید context وجود ندارد؛ ${observedText}`;
  return s;
}
function mainBlocker(c){
  const missing = asArray(c.missing_inputs);
  const failed = asArray(c.failed_conditions);
  if(missing.length) return `field ناقص: ${conditionHuman(missing[0])}`;
  if(failed.length) return conditionHuman(failed[0]);
  if(isParked(c)) return 'این حافظه بعد از evidence جدید parked/weak شده است.';
  if(c.is_active_match) return 'مانع فعلی ندارد؛ context روی کندل بسته‌شده match شده است.';
  return c.primary_reason || 'هنوز trigger کامل نشده است.';
}
function nextWatch(c){
  const id = c.memory_id || '';
  if(isParked(c)) return 'فقط برای سابقه و audit نگه داشته شده؛ مگر review جدید بیاید.';
  if(id.includes('USDJPY_PRIOR48')) return 'منتظر New York + sweep سقف ۴۸ ساعت گذشته + بسته‌شدن M15 دوباره داخل سطح.';
  if(id.includes('EURUSD_SESSION_UPSIDE')) return 'منتظر London/NY + sweep یک سطح بالایی مهم + بسته‌شدن M15 دوباره داخل سطح.';
  if(id.includes('ALIGNMENT_ABSENT_CHOP')) return 'منتظر London/NY با نبود هم‌راستایی واضح H4/H1 و حالت chop/range-neutral در M15.';
  return 'منتظر کامل‌شدن همهٔ شرط‌های matching rule روی کندل بسته‌شده.';
}
function readiness(c){
  const matched = asArray(c.matched_conditions).length;
  const failed = asArray(c.failed_conditions).length;
  const missing = asArray(c.missing_inputs).length;
  const total = matched + failed + missing;
  if(total === 0) return {matched:0,total:0,pct:0,label:'—'};
  return {matched,total,pct:Math.round((matched/total)*100),label:`${matched}/${total}`};
}
function listConditions(items, kind){
  const arr = asArray(items);
  if(!arr.length) return '<div class="muted">—</div>';
  return '<ul class="condition-list">' + arr.slice(0,10).map(x=>`<li class="${kind}">${esc(conditionHuman(x))}</li>`).join('') + '</ul>';
}
function contextMini(surface){
  if(!surface) return '<div class="mini-grid"><div><b>context</b><span>در payload جداگانه پیدا نشد</span></div></div>';
  const prior = surface.sweep_reference_value_up !== undefined ? `<div><b>prior48 ref</b><span>${esc(numberFmt(surface.sweep_reference_value_up))}</span></div>` : '';
  return `<div class="mini-grid">
    <div><b>session</b><span>${esc(surface.session_bucket)}</span></div>
    <div><b>bar UTC</b><span>${esc(surface.latest_bar_open_ts_utc)}</span></div>
    <div><b>data</b><span>${esc(surface.data_sufficiency_status)}</span></div>
    <div><b>H1/H4</b><span>${esc(surface.h1_dir)} / ${esc(surface.h4_dir)}</span></div>
    <div><b>M15</b><span>${esc(surface.m15_dir)} · ratio ${esc(numberFmt(surface.m15_range_ratio_12))}</span></div>
    ${prior}
  </div>`;
}
function badgeClass(c){
  if(c.is_active_match) return 'active-now';
  if(isParked(c)) return 'parked';
  if(isInsufficient(c)) return 'insufficient';
  if(isNoTrade(c)) return 'notrade';
  return 'watching';
}
function card(c, context){
  const r = readiness(c);
  const surface = surfaceFor(context, c.instrument, c.timeframe);
  const failedAndMissing = [...asArray(c.failed_conditions), ...asArray(c.missing_inputs)];
  return `<article class="card ${badgeClass(c)}">
    <div class="card-topline">
      <div class="badge">${esc(stateLabel(c))}</div>
      <div class="readiness"><span>${esc(r.label)}</span><em>readiness</em></div>
    </div>
    <h2>${esc(postureLabel(c))}</h2>
    <div class="meta">
      <span class="pill strong">${esc(c.instrument)} ${esc(c.timeframe)}</span>
      <span class="pill">score ${esc(c.score_not_probability)}/100</span>
      <span class="pill">${esc(c.band)}</span>
    </div>
    <p class="summary-text">${esc(c.plain_language_summary_fa)}</p>
    <div class="posture-box">
      <div><b>مانع اصلی فعلی</b><span>${esc(mainBlocker(c))}</span></div>
      <div><b>چیزی که باید زیر نظر باشد</b><span>${esc(nextWatch(c))}</span></div>
    </div>
    ${contextMini(surface)}
    <details class="details">
      <summary>جزئیات شرط‌ها</summary>
      <div class="two-col">
        <div class="block pass"><h3>پاس‌شده</h3>${listConditions(c.matched_conditions, 'ok')}</div>
        <div class="block fail"><h3>فعال‌نشده / ناقص</h3>${listConditions(failedAndMissing, 'bad')}</div>
      </div>
    </details>
    <div class="mini-caveat">${esc(c.mandatory_caveat)}</div>
  </article>`;
}
function summaryPanel(p, cards, context){
  const active = cards.filter(c=>c.is_active_match).length;
  const parked = cards.filter(isParked).length;
  const insufficient = cards.filter(c=>!isParked(c) && isInsufficient(c)).length;
  const noTrade = cards.filter(c=>!isParked(c) && isNoTrade(c)).length;
  const watch = cards.filter(c=>!isParked(c) && !c.is_active_match && !isInsufficient(c)).length;
  const sessions = [...new Set(asArray(context?.surfaces).map(s=>s.session_bucket).filter(Boolean))].join(' / ') || '—';
  const contextUtc = context?.created_utc || p.source_context_summary?.context_created_utc || '—';
  return `<div class="summary-grid">
    <div><b>${active}</b><span>match فعال اکنون</span></div>
    <div><b>${watch}</b><span>watch نزدیک/منتظر trigger</span></div>
    <div><b>${noTrade}</b><span>حافظهٔ no-trade در registry</span></div>
    <div><b>${parked}</b><span>آرشیو / weak شده</span></div>
  </div>
  <div class="summary-note">
    session فعلی: <strong>${esc(sessions)}</strong> · context UTC: <strong>${esc(contextUtc)}</strong><br>
    ${esc(p.global_boundary?.plain_language_fa || 'نمایش پژوهشی فقط برای context historical memory.')}
  </div>`;
}
function contextStrip(context){
  const surfaces = asArray(context?.surfaces);
  if(!surfaces.length) return '<div class="context-card muted">context زندهٔ جداگانه در دسترس نبود؛ کارت‌ها همچنان از payload اصلی ساخته شدند.</div>';
  return surfaces.map(s=>`<div class="context-card">
    <div class="ctx-title">${esc(s.instrument)} ${esc(s.timeframe)}</div>
    <div class="ctx-line">session: <b>${esc(s.session_bucket)}</b> · data: <b>${esc(s.data_sufficiency_status)}</b></div>
    <div class="ctx-line">bar: ${esc(s.latest_bar_open_ts_utc || '—')}</div>
    ${s.sweep_reference_value_up !== undefined ? `<div class="ctx-line">prior48 reference: ${esc(numberFmt(s.sweep_reference_value_up))}</div>` : ''}
  </div>`).join('');
}
function groupedCards(cards, context){
  const active = cards.filter(c=>c.is_active_match);
  const upcoming = cards.filter(c=>!c.is_active_match && !isParked(c) && !isInsufficient(c));
  const insufficient = cards.filter(c=>!c.is_active_match && !isParked(c) && isInsufficient(c));
  const archived = cards.filter(isParked);
  const section = (title, subtitle, arr) => arr.length ? `<section class="card-section"><h2 class="section-title">${esc(title)}</h2><p class="section-subtitle">${esc(subtitle)}</p>${arr.map(c=>card(c, context)).join('')}</section>` : '';
  return [
    section('فعال اکنون', 'فقط اگر همه شرط‌ها روی کندل بسته‌شده match شده باشند.', active),
    section('watchهای بعدی', 'این‌ها active نیستند، اما نشان می‌دهند چه contextهایی را باید زیر نظر گرفت.', upcoming),
    section('دادهٔ ناقص', 'اگر required field ناقص باشد، حافظه فعال جعلی نمی‌شود.', insufficient),
    section('آرشیو / weak شده', 'برای سابقه نگه داشته شده و در runtime فعال نمی‌شود.', archived)
  ].join('') || '<div class="empty">هیچ کارت حافظه‌ای در payload نبود.</div>';
}
Promise.all([loadPayload(), loadContext()]).then(([p, context])=>{
  const cards = asArray(p.cards);
  document.getElementById('summary').classList.remove('skeleton');
  document.getElementById('summary').innerHTML = summaryPanel(p, cards, context);
  document.getElementById('context-strip').innerHTML = contextStrip(context);
  document.getElementById('cards').innerHTML = groupedCards(cards, context);
}).catch(err=>{
  document.getElementById('summary').innerHTML = '<span class="warn">خطا در خواندن payload: '+esc(err.message)+'</span>';
});
