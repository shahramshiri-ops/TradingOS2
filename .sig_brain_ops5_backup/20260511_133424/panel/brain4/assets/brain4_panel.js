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
function toNumber(x){
  if(x === null || x === undefined || x === '') return null;
  const n = Number(String(x).replace(/[,،]/g,''));
  return Number.isFinite(n) ? n : null;
}
function observedFromCondition(s){
  const m = String(s || '').match(/observed=(.+)$/);
  return m ? m[1].trim() : '';
}
function rangeFromCondition(s){
  const m = String(s || '').match(/between\s*\[\s*([\d.+-]+)\s*,\s*([\d.+-]+)\s*\]/);
  return m ? {lo:Number(m[1]), hi:Number(m[2])} : null;
}
function firstAvailable(obj, keys){
  for(const k of keys){
    if(obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== '') return {key:k, value:obj[k]};
  }
  return null;
}

function parseUtc(value){
  if(!value) return null;
  const d = new Date(String(value));
  return Number.isNaN(d.getTime()) ? null : d;
}
function isoMinute(d){
  if(!d) return '—';
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}
function minutesBetween(later, earlier){
  if(!later || !earlier) return null;
  return Math.round((later.getTime() - earlier.getTime()) / 60000);
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
function latestBarFromContext(context, cards){
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
  const latest = latestBarFromContext(context, cards);
  const contextCreated = parseUtc(context?.created_utc || payload?.source_context_summary?.context_created_utc || payload?.created_utc);
  const ageMin = latest ? minutesBetween(now, latest.date) : null;
  let status = 'UNKNOWN';
  let statusFa = 'نامشخص';
  let css = 'unknown';
  if(ageMin === null){
    status = 'UNKNOWN'; statusFa = 'زمان آخرین bar پیدا نشد'; css = 'unknown';
  }else if(ageMin <= 25){
    status = 'LIVE_OK'; statusFa = 'context تازه است'; css = 'ok';
  }else if(ageMin <= 45){
    status = 'LAGGING'; statusFa = 'context کمی عقب است؛ برای M15 با احتیاط بخوان'; css = 'lagging';
  }else if(ageMin <= 90){
    status = 'STALE'; statusFa = 'context عقب است؛ refresh را بررسی کن'; css = 'stale';
  }else{
    status = 'VERY_STALE'; statusFa = 'context خیلی عقب است؛ برای وضعیت فعلی استفاده نکن'; css = 'very-stale';
  }
  return {
    now, latest, contextCreated, ageMin, status, statusFa, css,
    expectedSession: sessionFromUtcDate(now),
    contextSession: latest?.session || [...new Set(asArray(context?.surfaces).map(s=>s.session_bucket).filter(Boolean))].join(' / ') || '—'
  };
}
function freshnessBanner(info){
  const age = info.ageMin === null ? '—' : `${info.ageMin} دقیقه`;
  const latestLabel = info.latest ? `${info.latest.ts} · ${info.latest.instrument || ''} ${info.latest.timeframe || ''}` : '—';
  const mismatch = info.contextSession && info.contextSession !== '—' && info.contextSession !== info.expectedSession;
  const note = info.css === 'ok'
    ? 'session کارت‌ها بر اساس آخرین کندل بسته‌شده محاسبه شده است.'
    : info.css === 'lagging'
      ? 'context کمی عقب است؛ برای M15 اول آخرین کندل بسته‌شده را با چارت/refresh چک کن.'
      : 'هشدار: کارت‌ها ممکن است بازار فعلی را نشان ندهند. ابتدا workflow refresh را اجرا/بررسی کن.';
  const mismatchNote = mismatch ? ` اختلاف session: context=${info.contextSession} ولی clock=${info.expectedSession}.` : '';
  return `<div class="freshness-banner ${esc(info.css)}">
    <div><b>${esc(info.status)}</b><span>${esc(info.statusFa)}</span></div>
    <div><b>آخرین کندل بسته‌شده</b><span>${esc(latestLabel)}</span></div>
    <div><b>سن داده</b><span>${esc(age)}</span></div>
    <div><b>UTC / session فعلی</b><span>${esc(isoMinute(info.now))} · ${esc(info.expectedSession)}</span></div>
  </div>
  <div class="freshness-note ${esc(info.css)}">${esc(note + mismatchNote)}</div>`;
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
  const observed = observedFromCondition(s);
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
  if(s.startsWith('h4_h1_up_context bool_eq False')){
    if(observed === 'True' || observed === 'true') return 'هم‌راستایی صعودی H4/H1 وجود دارد؛ شرط no-trade/avoid-short می‌خواهد هم‌راستایی واضح وجود نداشته باشد.';
    return `هم‌راستایی صعودی H4/H1 غایب است؛ ${observedText || 'پاس'}`;
  }
  if(s.startsWith('h4_h1_down_context bool_eq False')){
    if(observed === 'True' || observed === 'true') return 'هم‌راستایی نزولی H4/H1 وجود دارد؛ شرط no-trade/avoid-short می‌خواهد هم‌راستایی واضح وجود نداشته باشد.';
    return `هم‌راستایی نزولی H4/H1 غایب است؛ ${observedText || 'پاس'}`;
  }
  if(s.startsWith('m15_range_ratio_12 between')){
    const r = rangeFromCondition(s);
    const v = toNumber(observed);
    const rangeText = r ? `محدودهٔ لازم: ${numberFmt(r.lo)} تا ${numberFmt(r.hi)}` : 'محدودهٔ لازم نامشخص';
    if(r && v !== null && v < r.lo) return `M15 فعلاً زیر باند chop/range-neutral تعریف‌شده است؛ مشاهده: ${numberFmt(v)}، ${rangeText}`;
    if(r && v !== null && v > r.hi) return `M15 فعلاً بالاتر از باند chop/range-neutral تعریف‌شده است؛ مشاهده: ${numberFmt(v)}، ${rangeText}`;
    if(r && v !== null) return `M15 داخل باند chop/range-neutral تعریف‌شده است؛ مشاهده: ${numberFmt(v)}، ${rangeText}`;
    return `M15 باید در باند chop/range-neutral تعریف‌شده باشد؛ ${observedText}، ${rangeText}`;
  }
  if(s.startsWith('m15_dir in')) return `جهت M15 خنثی/نامشخص است؛ ${observedText}`;
  if(s.startsWith('NOT(h1_dir == UP AND h4_dir == UP)')) return `H1 و H4 همزمان up نیستند`;
  if(s.startsWith('conflict_severity not_eq HIGH')) return `تضاد شدید context وجود ندارد؛ ${observedText}`;
  return s;
}
function semanticState(c){
  const failed = asArray(c.failed_conditions).join(' | ');
  const missing = asArray(c.missing_inputs).join(' | ');
  const id = c.memory_id || '';
  if(c.is_active_match){
    return {state:'Context matched on last closed bar', posture: postureLabel(c), now:'فعال از نظر حافظهٔ تاریخی؛ هنوز دستور معامله نیست.'};
  }
  if(isParked(c)){
    return {state:'Archived / weakened', posture:'فقط audit و سابقه', now:'در runtime فعال نمی‌شود مگر review جدید بیاید.'};
  }
  if(missing){
    return {state:'Missing runtime field', posture: postureLabel(c), now:'فعال‌سازی ممنوع تا وقتی field کامل شود.'};
  }
  if(failed.includes('session_bucket eq NEW_YORK')){
    return {state:'Waiting for New York session', posture: postureLabel(c), now:'در session فعلی کاربرد مستقیم ندارد.'};
  }
  if(failed.includes('session_bucket in')){
    return {state:'Waiting for active London/NY session', posture: postureLabel(c), now:'دامنهٔ session هنوز کامل نیست.'};
  }
  if(failed.includes('upside_sweep_flag bool_eq True')){
    return {state:'Waiting for upside sweep', posture: postureLabel(c), now:'هنوز برخورد/عبور از سطح بالایی تأیید نشده.'};
  }
  if(failed.includes('sweep_then_reject_back_inside_up_flag bool_eq True')){
    return {state:'Waiting for M15 close-back-inside confirmation', posture: postureLabel(c), now:'sweep دیده شده/ممکن است، اما rejection بسته‌شده هنوز کامل نیست.'};
  }
  if(failed.includes('m15_range_ratio_12 between')){
    return {state:'Outside defined M15 chop/range-neutral band', posture: postureLabel(c), now: isNoTrade(c) ? 'no-trade warning هنوز فعال نیست.' : 'trigger هنوز کامل نیست.'};
  }
  if(id.includes('ALIGNMENT_ABSENT_CHOP')){
    return {state:'Waiting for alignment-absent chop context', posture: postureLabel(c), now:'avoid-short context هنوز فعال نیست.'};
  }
  return {state:'Trigger incomplete', posture: postureLabel(c), now:'هیچ match فعالی روی کندل بسته‌شدهٔ فعلی وجود ندارد.'};
}
function semanticStrip(c){
  const s = semanticState(c);
  return `<div class="semantic-strip">
    <div><b>State</b><span>${esc(s.state)}</span></div>
    <div><b>Posture if completed</b><span>${esc(s.posture)}</span></div>
    <div><b>Now</b><span>${esc(s.now)}</span></div>
  </div>`;
}
function prior48DistanceBox(surface){
  if(!surface || surface.sweep_reference_value_up === undefined) return '';
  const ref = toNumber(surface.sweep_reference_value_up);
  const last = firstAvailable(surface, ['latest_close','latest_close_bid','last_close','close','m15_close','latest_bar_close','current_price','last_price']);
  if(ref === null){
    return `<div class="field-gap"><b>prior48 distance</b><span>reference عددی در context پیدا نشد.</span></div>`;
  }
  if(!last){
    return `<div class="field-gap"><b>prior48 distance</b><span>در context فعلی close/last price وجود ندارد؛ builder gap برای نمایش فاصله تا سطح.</span></div>`;
  }
  const px = toNumber(last.value);
  if(px === null) return `<div class="field-gap"><b>prior48 distance</b><span>last price خوانا نیست؛ field=${esc(last.key)}</span></div>`;
  const diff = ref - px;
  const pipFactor = String(surface.instrument || '').includes('JPY') ? 100 : 10000;
  const pips = diff * pipFactor;
  const relation = diff > 0 ? 'زیر prior48 high' : diff < 0 ? 'بالای prior48 high' : 'روی prior48 high';
  return `<div class="level-distance"><b>فاصله تا prior48 high</b><span>${esc(numberFmt(Math.abs(pips)))} pip · ${esc(relation)} · last=${esc(numberFmt(px))}</span></div>`;
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
    ${prior48DistanceBox(surface)}
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
    ${semanticStrip(c)}
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
  const fresh = freshnessInfo(context, p, cards);
  return `${freshnessBanner(fresh)}
  <div class="summary-grid">
    <div><b>${active}</b><span>match فعال اکنون</span></div>
    <div><b>${watch}</b><span>watch نزدیک/منتظر trigger</span></div>
    <div><b>${noTrade}</b><span>حافظهٔ no-trade در registry</span></div>
    <div><b>${parked}</b><span>آرشیو / weak شده</span></div>
  </div>
  <div class="summary-note">
    session آخرین context: <strong>${esc(sessions)}</strong> · context UTC: <strong>${esc(contextUtc)}</strong><br>
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
  const summaryEl = document.getElementById('summary');
  const fresh = freshnessInfo(context, p, cards);
  summaryEl.classList.remove('skeleton','freshness-ok','freshness-lagging','freshness-stale','freshness-very-stale','freshness-unknown');
  summaryEl.classList.add('freshness-' + fresh.css);
  summaryEl.innerHTML = summaryPanel(p, cards, context);
  document.getElementById('context-strip').innerHTML = contextStrip(context);
  document.getElementById('cards').innerHTML = groupedCards(cards, context);
}).catch(err=>{
  document.getElementById('summary').innerHTML = '<span class="warn">خطا در خواندن payload: '+esc(err.message)+'</span>';
});
