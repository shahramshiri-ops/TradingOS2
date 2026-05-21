/*
 BRAIN4-UI-OPS-01 — panel/brain4 visual & UX polish
 Boundary: UI-only patch. No signal, no execution, no authority change.
*/
(function () {
  "use strict";

  const PATCH_ID = "BRAIN4_UI_OPS_01_v1_0";

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function normalize(s) {
    return (s || "").replace(/\s+/g, " ").trim();
  }

  function text(el) {
    return normalize(el ? el.textContent : "");
  }

  function containsAny(el, arr) {
    const t = text(el);
    return arr.some(x => t.includes(x));
  }

  function looksBlock(el) {
    if (!el || !(el instanceof HTMLElement)) return false;
    const t = text(el);
    if (t.length < 24) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'inline' || cs.display === 'contents') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 240 && rect.height > 40;
  }

  function closestCard(el) {
    let cur = el;
    let best = null;
    while (cur && cur !== document.body) {
      if (looksBlock(cur)) best = cur;
      const cs = getComputedStyle(cur);
      if ((parseFloat(cs.borderRadius || '0') >= 12) || cs.boxShadow !== 'none' || /border-box|flex|grid|block/.test(cs.display)) {
        if (looksBlock(cur)) return cur;
      }
      cur = cur.parentElement;
    }
    return best || el;
  }

  function markCardByText(texts, className, options) {
    const nodes = qsa('section, article, div');
    const candidates = [];
    nodes.forEach(node => {
      if (containsAny(node, texts)) {
        const card = closestCard(node);
        if (card && !candidates.includes(card)) candidates.push(card);
      }
    });
    candidates.forEach(card => card.classList.add(className));
    if (options && options.firstOnly && candidates[0]) return [candidates[0]];
    return candidates;
  }

  function findLabelRow() {
    const rows = qsa('div, section').filter(el => {
      const t = text(el);
      return t.includes('رویدادها') && t.includes('کتابخانه الگوها') && t.includes('History');
    });
    return rows[0] ? closestCard(rows[0]) : null;
  }

  function enhancePatternCards() {
    const instruments = ['EURUSD', 'USDJPY', 'XAUUSD', 'SPX', 'NQ'];
    qsa('div, article, section').forEach(el => {
      const t = text(el);
      if (!instruments.some(x => t.includes(x))) return;
      if (!(t.includes('directional watch') || t.includes('watch') || t.includes('risk-off') || t.includes('no-trade'))) return;
      const card = closestCard(el);
      if (!card || card.classList.contains('brain4-ui-pattern-card')) return;
      card.classList.add('brain4-ui-card', 'brain4-ui-pattern-card');

      const paras = qsa('p, div, span', card).filter(n => {
        const tx = text(n);
        return tx.length > 120 && !n.classList.contains('brain4-ui-mutated');
      });
      paras.slice(0, 3).forEach(p => p.classList.add('brain4-ui-clamp-4'));

      const footerLike = qsa('div, span', card).find(n => {
        const tx = text(n);
        return tx.includes('جزئیات فنی') || tx.includes('شناسه') || tx.includes('قدرت پژوهشی');
      });
      if (footerLike) footerLike.classList.add('brain4-ui-muted-link');
    });
  }

  function enhanceChips() {
    qsa('div, section').forEach(el => {
      const t = text(el);
      if (t.includes('diagnostic') && t.includes('candidate') && t.includes('blocker') && t.includes('trigger')) {
        const card = closestCard(el);
        if (card) card.classList.add('brain4-ui-chipbar-host');
      }
    });
  }

  function addSectionEyebrow(card, label) {
    if (!card || card.querySelector('.brain4-ui-eyebrow')) return;
    const node = document.createElement('div');
    node.className = 'brain4-ui-eyebrow';
    node.textContent = label;
    card.insertBefore(node, card.firstChild);
  }

  function styleDetails() {
    qsa('details').forEach(d => d.classList.add('brain4-ui-details'));
  }

  function softenDuplicatedBadges() {
    qsa('div, span').forEach(el => {
      const t = text(el);
      if (t === 'در حال پایش' || t === 'آرشیو/غیرفعال' || t === 'directional watch') {
        el.classList.add('brain4-ui-pill');
      }
    });
  }

  function init() {
    document.documentElement.classList.add('brain4-ui-ops01-root');
    document.body.classList.add('brain4-ui-ops01-body');

    const shadowCards = markCardByText(['Shadow زنده', 'SHADOW OPS / NOT A SIGNAL', 'LIVE SHADOW / COUNT SEMANTICS'], 'brain4-ui-card brain4-ui-shadow-card'.split(' '));
    shadowCards.forEach(c => addSectionEyebrow(c, 'Shadow / Research Diagnostics'));

    const heroCards = markCardByText(['فعلاً رویداد فعال نداریم', 'رویدادهای فعال مغز'], 'brain4-ui-card brain4-ui-hero-card'.split(' '));
    heroCards.forEach(c => addSectionEyebrow(c, 'Live View'));

    const libraryCards = markCardByText(['الگو در مغز', 'کتابخانه ساده الگوها'], 'brain4-ui-card brain4-ui-library-card'.split(' '));
    libraryCards.forEach(c => addSectionEyebrow(c, 'Memory Library'));

    const emptyCards = markCardByText(['هیچ memory event معتبر و فعال', 'فعلاً رویداد فعال نداریم'], 'brain4-ui-card brain4-ui-empty-state'.split(' '));
    emptyCards.forEach(c => addSectionEyebrow(c, 'No Active Event'));

    const tabRow = findLabelRow();
    if (tabRow) tabRow.classList.add('brain4-ui-tabrow');

    enhancePatternCards();
    enhanceChips();
    softenDuplicatedBadges();
    styleDetails();

    qsa('button, a').forEach(el => {
      const t = text(el);
      if (['بروزرسانی', 'اعلان فعال است', 'رویدادها', 'کتابخانه الگوها', 'History'].some(x => t.includes(x))) {
        el.classList.add('brain4-ui-btn');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.BRAIN4_UI_OPS_01 = { patchId: PATCH_ID, init };
})();
