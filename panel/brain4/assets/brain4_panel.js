async function loadPayload(){
  const res = await fetch('sig_brain4_runtime_payload_current.json?ts=' + Date.now());
  if(!res.ok) throw new Error('payload not found');
  return await res.json();
}
function esc(x){ return String(x ?? '—').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' }[m])); }
function list(items){
  if(!items || !items.length) return '<div class="footer">—</div>';
  return '<ul>' + items.slice(0,8).map(x=>`<li>${esc(x)}</li>`).join('') + '</ul>';
}
function card(c){
  return `<article class="card ${c.is_active_match ? 'active':''}">
    <div class="badge">${esc(c.status_badge)}</div>
    <h2>${esc(c.headline_fa)}</h2>
    <div class="meta">
      <span class="pill">${esc(c.instrument)} ${esc(c.timeframe)}</span>
      <span class="pill">${esc(c.brain_state)}</span>
      <span class="pill">score ${esc(c.score_not_probability)}/100</span>
      <span class="pill">${esc(c.band)}</span>
    </div>
    <p>${esc(c.plain_language_summary_fa)}</p>
    <div class="block"><h3>چرا؟</h3><div class="reason">${esc(c.primary_reason)}</div></div>
    <div class="block"><h3>شرط‌های پاس‌شده</h3>${list(c.matched_conditions)}</div>
    <div class="block"><h3>شرط‌های فعال‌نشده / دادهٔ ناقص</h3>${list([...(c.failed_conditions||[]), ...(c.missing_inputs||[])])}</div>
    <div class="block caveat">${esc(c.mandatory_caveat)}</div>
    <div class="footer">هیچ دستور معامله‌ای مجاز نیست.</div>
  </article>`;
}
loadPayload().then(p=>{
  document.getElementById('summary').innerHTML =
    `<strong>${esc(p.registry_summary.active_match_count)}</strong> حافظه فعال از ${esc(p.registry_summary.memory_count)} حافظه.
     <br><span class="caveat">${esc(p.global_boundary.plain_language_fa)}</span>`;
  document.getElementById('cards').innerHTML = (p.cards||[]).map(card).join('');
}).catch(err=>{
  document.getElementById('summary').innerHTML = '<span class="caveat">خطا در خواندن payload: '+esc(err.message)+'</span>';
});
