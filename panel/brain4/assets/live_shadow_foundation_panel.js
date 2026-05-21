/* LIVE-SHADOW-FOUNDATION-01 compact panel strip
   Shows append-only log status. Not a signal.
*/
(function () {
  "use strict";

  const PATHS = [
    "live_shadow_foundation_status_current.json",
    "./live_shadow_foundation_status_current.json",
    "../../runtime/sig_shadow/live_shadow_foundation_status_current.json"
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
    let host = document.getElementById("live-shadow-foundation-01-host");
    if (host) return host;
    host = document.createElement("section");
    host.id = "live-shadow-foundation-01-host";
    host.className = "live-shadow-foundation-01-host";

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
    host.innerHTML = `
      <div class="live-shadow-foundation-strip" dir="rtl">
        <div>
          <strong>Live Shadow Logging</strong>
          <span>append-only / not a signal</span>
        </div>
        <div class="lsf-metrics">
          <span>context <b>${n(d.context_snapshot_count_today)}</b></span>
          <span>setup <b>${n(d.setup_shadow_count_today)}</b></span>
          <span>trigger <b>${n(d.trigger_shadow_count_today)}</b></span>
          <span>blocker <b>${n(d.blocker_shadow_count_today)}</b></span>
          <span>candidate <b>${n(d.candidate_shadow_count_today)}</b></span>
          <span>diagnostic <b>${n(d.diagnostic_record_count_today)}</b></span>
        </div>
      </div>
    `;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_LIVE_SHADOW_FOUNDATION_01 = { reload: init };
})();
