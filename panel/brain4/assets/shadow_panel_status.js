/* SHADOW-PANEL-01 v1.0
   Panel-safe Shadow readiness card/tab.
   Boundary: NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_BROKER_EXECUTION / NO_AUTO_LEARNING.
*/
(function () {
  "use strict";

  const PATCH_ID = "SHADOW_PANEL_01_v1_0";
  const STATUS_PATHS = [
    "shadow_panel_status_current.json",
    "./shadow_panel_status_current.json",
    "../../runtime/sig_shadow/shadow_panel_status_current.json"
  ];

  function nowBust(url) {
    const sep = url.indexOf("?") === -1 ? "?" : "&";
    return url + sep + "t=" + Date.now();
  }

  async function fetchJsonAny(paths) {
    const errors = [];
    for (const p of paths) {
      try {
        const resp = await fetch(nowBust(p), { cache: "no-store" });
        if (!resp.ok) {
          errors.push(p + ": HTTP " + resp.status);
          continue;
        }
        return { data: await resp.json(), source: p, errors };
      } catch (e) {
        errors.push(p + ": " + (e && e.message ? e.message : String(e)));
      }
    }
    return { data: null, source: null, errors };
  }

  function safeText(v, fallback) {
    if (v === null || v === undefined || v === "") return fallback || "—";
    return String(v);
  }

  function num(v) {
    if (v === null || v === undefined || v === "") return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  function statusClass(status) {
    const s = String(status || "").toUpperCase();
    if (s === "PASS" || s === "READY" || s.indexOf("PASS") >= 0) return "shadow-ok";
    if (s.indexOf("WARN") >= 0 || s.indexOf("CAVEAT") >= 0) return "shadow-warn";
    if (s.indexOf("FAIL") >= 0 || s.indexOf("ERROR") >= 0) return "shadow-bad";
    return "shadow-neutral";
  }

  function ensureHost() {
    let host = document.getElementById("shadow-panel-01-host");
    if (host) return host;

    host = document.createElement("section");
    host.id = "shadow-panel-01-host";
    host.className = "shadow-panel-01-host";

    // Prefer placing after top summary/header area, otherwise at top of main/body.
    const candidates = [
      document.querySelector("[data-shadow-panel-anchor]"),
      document.querySelector("#active-events"),
      document.querySelector(".active-events"),
      document.querySelector("main"),
      document.querySelector(".container"),
      document.body
    ].filter(Boolean);

    const parent = candidates[0] || document.body;
    if (parent === document.body || parent.tagName.toLowerCase() === "main") {
      parent.insertBefore(host, parent.firstChild);
    } else if (parent.parentNode) {
      parent.parentNode.insertBefore(host, parent.nextSibling);
    } else {
      document.body.insertBefore(host, document.body.firstChild);
    }
    return host;
  }

  function renderEmpty(host, errors) {
    host.innerHTML = `
      <div class="shadow-card shadow-neutral" dir="rtl">
        <div class="shadow-card-head">
          <div>
            <div class="shadow-kicker">Live Shadow</div>
            <h3>Shadow status در دسترس نیست</h3>
          </div>
          <span class="shadow-badge">NOT A SIGNAL</span>
        </div>
        <p class="shadow-muted">فایل وضعیت shadow در پنل پیدا نشد یا هنوز deploy نشده است.</p>
        <details class="shadow-details">
          <summary>جزئیات فنی</summary>
          <pre>${(errors || []).map(String).join("\n")}</pre>
        </details>
      </div>`;
  }

  function renderStatus(host, data, source) {
    const status = safeText(data.shadow_system_status, "UNKNOWN");
    const cls = statusClass(status);
    const candidateCount = num(data.candidate_count);
    const nearMiss = num(data.near_miss_count_last_run);
    const nearMissHigh = num(data.near_miss_high_count_last_run);
    const blocked = num(data.blocked_candidate_count);
    const obs = num(data.observation_count);
    const obsPending = num(data.observation_pending_count);
    const obsComplete = num(data.observation_complete_count);
    const recent = Array.isArray(data.recent_shadow_candidates_display_only) ? data.recent_shadow_candidates_display_only : [];
    const cohort = safeText(data.cohort_id, "—");
    const created = safeText(data.created_utc, "—");
    const badge = safeText(data.display_badge, "SHADOW READY / NOT A SIGNAL");
    const fa = safeText(data.plain_language_fa, "این بخش فقط وضعیت shadow را نشان می‌دهد و سیگنال معامله نیست.");

    host.innerHTML = `
      <div class="shadow-card ${cls}" dir="rtl">
        <div class="shadow-card-head">
          <div>
            <div class="shadow-kicker">Live Shadow / Readiness</div>
            <h3>وضعیت Shadow</h3>
          </div>
          <span class="shadow-badge">${badge}</span>
        </div>

        <div class="shadow-status-line">
          <span class="shadow-dot"></span>
          <strong>${status}</strong>
          <span class="shadow-muted">آخرین ساخت: ${created}</span>
        </div>

        <div class="shadow-metrics">
          <div class="shadow-metric">
            <span class="shadow-label">کاندید shadow</span>
            <strong>${candidateCount}</strong>
          </div>
          <div class="shadow-metric">
            <span class="shadow-label">near-miss</span>
            <strong>${nearMiss}</strong>
          </div>
          <div class="shadow-metric">
            <span class="shadow-label">near-miss قوی</span>
            <strong>${nearMissHigh}</strong>
          </div>
          <div class="shadow-metric">
            <span class="shadow-label">blocked</span>
            <strong>${blocked}</strong>
          </div>
          <div class="shadow-metric">
            <span class="shadow-label">observation</span>
            <strong>${obs}</strong>
          </div>
          <div class="shadow-metric">
            <span class="shadow-label">pending / complete</span>
            <strong>${obsPending} / ${obsComplete}</strong>
          </div>
        </div>

        <p class="shadow-plain">${fa}</p>

        <details class="shadow-details">
          <summary>جزئیات shadow cohort و candidateهای اخیر</summary>
          <div class="shadow-detail-grid">
            <div><span>cohort</span><b>${cohort}</b></div>
            <div><span>source</span><b>${source || "—"}</b></div>
            <div><span>signal_authorized</span><b>${safeText(data.signal_authorized, false)}</b></div>
            <div><span>broker_execution_authorized</span><b>${safeText(data.broker_execution_authorized, false)}</b></div>
            <div><span>auto_learning_authorized</span><b>${safeText(data.auto_learning_authorized, false)}</b></div>
            <div><span>rule_rewrite_authorized</span><b>${safeText(data.rule_rewrite_authorized, false)}</b></div>
          </div>
          ${recent.length ? renderRecent(recent) : '<p class="shadow-muted">candidate اخیر برای نمایش وجود ندارد.</p>'}
        </details>
      </div>
    `;
  }

  function renderRecent(recent) {
    const rows = recent.slice(0, 5).map((r) => {
      const id = safeText(r.candidate_id || r.event_id || r.memory_id, "—");
      const inst = safeText(r.instrument, "—");
      const tf = safeText(r.timeframe, "—");
      const bias = safeText(r.directional_bias || r.direction_side, "—");
      const ts = safeText(r.created_utc || r.activated_at_utc || r.source_bar_open_ts_utc, "—");
      return `<tr><td>${id}</td><td>${inst}</td><td>${tf}</td><td>${bias}</td><td>${ts}</td></tr>`;
    }).join("");
    return `
      <div class="shadow-recent-wrap">
        <table class="shadow-recent">
          <thead><tr><th>id</th><th>instrument</th><th>tf</th><th>bias</th><th>time</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  async function init() {
    const host = ensureHost();
    host.innerHTML = `<div class="shadow-card shadow-neutral" dir="rtl"><span class="shadow-muted">در حال خواندن وضعیت Shadow...</span></div>`;

    const result = await fetchJsonAny(STATUS_PATHS);
    if (!result.data) {
      renderEmpty(host, result.errors);
      return;
    }

    // Hard safety: if a corrupted payload ever tries to authorize trading, show a warning.
    if (result.data.signal_authorized || result.data.broker_execution_authorized || result.data.trade_instruction_authorized) {
      result.data.shadow_system_status = "FAIL_BOUNDARY_VIOLATION";
      result.data.display_badge = "BOUNDARY VIOLATION / NOT TRUSTED";
      result.data.plain_language_fa = "هشدار: payload وضعیت Shadow دارای مجوزهای نامعتبر است. این خروجی نباید برای تصمیم معاملاتی استفاده شود.";
    }

    renderStatus(host, result.data, result.source);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_SHADOW_PANEL_01 = { patchId: PATCH_ID, reload: init };
})();
