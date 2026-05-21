/* SHADOW-OUTCOME-01D quality strip */
(function () {
  "use strict";

  const PATHS = [
    "shadow_outcome_completion_state_current.json",
    "./shadow_outcome_completion_state_current.json",
    "../../runtime/sig_shadow/shadow_outcome_completion_state_current.json"
  ];

  function bust(url) {
    return url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();
  }

  async function fetchJsonAny(paths) {
    for (const p of paths) {
      try {
        const r = await fetch(bust(p), { cache: "no-store" });
        if (r.ok) return { data: await r.json(), source: p };
      } catch (e) {}
    }
    return { data: null, source: null };
  }

  function n(v) {
    const x = Number(v);
    return Number.isFinite(x) ? x : 0;
  }

  function ensureHost() {
    let host = document.getElementById("shadow-outcome-01d-host");
    if (host) return host;
    host = document.createElement("section");
    host.id = "shadow-outcome-01d-host";
    host.className = "shadow-outcome-01d-host";

    const outcome = document.getElementById("shadow-outcome-01-host");
    if (outcome && outcome.parentNode) {
      outcome.parentNode.insertBefore(host, outcome.nextSibling);
      return host;
    }

    const main = document.querySelector("main") || document.querySelector(".container") || document.body;
    main.insertBefore(host, main.firstChild);
    return host;
  }

  async function init() {
    const host = ensureHost();
    const result = await fetchJsonAny(PATHS);
    if (!result.data) {
      host.innerHTML = "";
      return;
    }
    const d = result.data;
    const fresh = d.freshness_tier_breakdown || {};
    const ladder = d.horizon_completion_ladder || {};
    const h1 = ladder["H1+1"] || {};
    const h2 = ladder["H1+2"] || {};
    const h4 = ladder["H1+4"] || {};
    const h8 = ladder["H1+8"] || {};

    host.innerHTML = `
      <div class="shadow-outcome-01d-strip" dir="rtl">
        <div>
          <strong>Outcome Quality Guard</strong>
          <span>freshness / closed-H1 / dedup / carry-forward</span>
        </div>
        <div class="so1d-metrics">
          <span>unique <b>${n(d.unique_subject_count_current)}</b></span>
          <span>duplicates <b>${n(d.duplicate_subject_count_current)}</b></span>
          <span>carry <b>${n(d.carry_forward_subject_count_total)}</b></span>
          <span>H1+1 ${n(h1.complete)}/${n(h1.pending)}</span>
          <span>H1+2 ${n(h2.complete)}/${n(h2.pending)}</span>
          <span>H1+4 ${n(h4.complete)}/${n(h4.pending)}</span>
          <span>H1+8 ${n(h8.complete)}/${n(h8.pending)}</span>
          <span>fresh <b>${n(fresh.LIVE_FRESH)}</b></span>
          <span>stale <b>${n(fresh.LIVE_STALE) + n(fresh.LIVE_BROKEN)}</b></span>
        </div>
      </div>
    `;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_SHADOW_OUTCOME_01D = { reload: init };
})();
