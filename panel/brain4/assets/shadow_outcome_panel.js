/* SHADOW-OUTCOME-01 compact panel strip
   Shows path observation status. Not signal, not PnL.
*/
(function () {
  "use strict";

  const PATHS = [
    "shadow_outcome_status_current.json",
    "./shadow_outcome_status_current.json",
    "../../runtime/sig_shadow/shadow_outcome_status_current.json"
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
    let host = document.getElementById("shadow-outcome-01-host");
    if (host) return host;
    host = document.createElement("section");
    host.id = "shadow-outcome-01-host";
    host.className = "shadow-outcome-01-host";

    const foundation = document.getElementById("live-shadow-foundation-01-host");
    if (foundation && foundation.parentNode) {
      foundation.parentNode.insertBefore(host, foundation.nextSibling);
      return host;
    }
    const unified = document.getElementById("shadow-panel-03-unified-host");
    if (unified && unified.parentNode) {
      unified.parentNode.insertBefore(host, unified.nextSibling);
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
    const statusBreakdown = d.observation_status_breakdown || {};
    const complete = n(d.complete_horizon_result_count);
    const pending = n(d.pending_horizon_result_count);
    const subjects = n(d.subject_count);
    const notObs = Object.keys(statusBreakdown).filter(k => k.indexOf("NOT_OBSERVABLE") >= 0).reduce((a, k) => a + n(statusBreakdown[k]), 0);

    host.innerHTML = `
      <div class="shadow-outcome-strip" dir="rtl">
        <div>
          <strong>Shadow Outcome Observer</strong>
          <span>path-only / not PnL / not a signal</span>
        </div>
        <div class="so-metrics">
          <span>subjects <b>${subjects}</b></span>
          <span>complete horizons <b>${complete}</b></span>
          <span>pending horizons <b>${pending}</b></span>
          <span>not observable <b>${notObs}</b></span>
        </div>
      </div>
    `;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_SHADOW_OUTCOME_01 = { reload: init };
})();
