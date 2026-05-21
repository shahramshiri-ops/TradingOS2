/* SHADOW-PANEL-02 v1.0
   OPS diagnostics + visual clarity integration for SIG Brain panel.
   Reads: panel/brain4/shadow_ops_status_current.json
   Boundary: NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_BROKER_EXECUTION / NO_AUTO_LEARNING.
*/
(function () {
  "use strict";

  const PATCH_ID = "SHADOW_PANEL_02_v1_0";
  const OPS_PATHS = [
    "shadow_ops_status_current.json",
    "./shadow_ops_status_current.json",
    "../../runtime/sig_shadow/shadow_ops_status_current.json"
  ];

  function bust(url) {
    const sep = url.includes("?") ? "&" : "?";
    return url + sep + "t=" + Date.now();
  }

  async function fetchJsonAny(paths) {
    const errors = [];
    for (const p of paths) {
      try {
        const resp = await fetch(bust(p), { cache: "no-store" });
        if (!resp.ok) {
          errors.push(`${p}: HTTP ${resp.status}`);
          continue;
        }
        return { data: await resp.json(), source: p, errors };
      } catch (e) {
        errors.push(`${p}: ${e && e.message ? e.message : String(e)}`);
      }
    }
    return { data: null, source: null, errors };
  }

  function n(v, fallback = 0) {
    const x = Number(v);
    return Number.isFinite(x) ? x : fallback;
  }

  function txt(v, fallback = "—") {
    if (v === undefined || v === null || v === "") return fallback;
    return String(v);
  }

  function clsStatus(status) {
    const s = String(status || "").toUpperCase();
    if (s === "PASS") return "ops-pass";
    if (s === "WARN") return "ops-warn";
    if (s === "FAIL" || s.includes("FAIL")) return "ops-fail";
    return "ops-neutral";
  }

  function formatPairList(list, emptyText) {
    if (!Array.isArray(list) || !list.length) {
      return `<div class="ops-empty">${emptyText || "موردی ثبت نشده است."}</div>`;
    }
    return `<div class="ops-pair-list">` + list.slice(0, 6).map((item) => {
      const key = Array.isArray(item) ? item[0] : (item && (item.reason || item.stage || item.key)) || "UNKNOWN";
      const val = Array.isArray(item) ? item[1] : (item && (item.count || item.value)) || 0;
      return `<div class="ops-pair"><span>${txt(key)}</span><b>${txt(val, "0")}</b></div>`;
    }).join("") + `</div>`;
  }

  function interpretation(data) {
    const c = n(data.candidate_count);
    const nm = n(data.near_miss_count_last_run);
    const high = n(data.near_miss_high_count_last_run);
    const blocked = n(data.blocked_candidate_count_last_run);
    const health = String(data.health_status || "").toUpperCase();

    if (health === "FAIL") {
      return "سلامت pipeline مشکل جدی دارد؛ قبل از تفسیر near-miss یا candidate باید health بررسی شود.";
    }
    if (c === 0 && high > 0) {
      return "کاندید کامل ثبت نشده، اما near-miss قوی وجود دارد؛ یعنی سیستم باید علت fail شدن stageها را بیشتر بررسی کند، نه اینکه rule را شل کند.";
    }
    if (c === 0 && nm > 0) {
      return "کاندید shadow نداریم، اما وضعیت‌های نزدیک ثبت شده‌اند؛ این برای تشخیص سخت‌گیری trigger/blocker/eligibility مفید است.";
    }
    if (c > 0) {
      return "کاندید shadow ثبت شده است؛ هنوز سیگنال نیست و فقط باید observation بعدی تکمیل شود.";
    }
    if (blocked > 0) {
      return "مورد blocked ثبت شده؛ باید بعداً بررسی شود blocker محافظ بوده یا بیش‌ازحد سخت‌گیر.";
    }
    return "فعلاً shadow event مهمی برای بررسی دیده نمی‌شود؛ این به معنی خرابی سیستم نیست.";
  }

  function ensureHost() {
    let host = document.getElementById("shadow-panel-02-ops-host");
    if (host) return host;

    host = document.createElement("section");
    host.id = "shadow-panel-02-ops-host";
    host.className = "shadow-panel-02-ops-host";

    const shadow01 = document.getElementById("shadow-panel-01-host");
    if (shadow01 && shadow01.parentNode) {
      shadow01.parentNode.insertBefore(host, shadow01.nextSibling);
      return host;
    }

    const main = document.querySelector("main") || document.querySelector(".container") || document.body;
    main.insertBefore(host, main.firstChild);
    return host;
  }

  function renderError(host, errors) {
    host.innerHTML = `
      <div class="ops-card ops-neutral" dir="rtl">
        <div class="ops-head">
          <div>
            <div class="ops-kicker">Shadow OPS</div>
            <h3>جزئیات عملیاتی Shadow در دسترس نیست</h3>
          </div>
          <span class="ops-badge">NOT A SIGNAL</span>
        </div>
        <p class="ops-muted">فایل <code>shadow_ops_status_current.json</code> پیدا نشد یا هنوز deploy نشده است.</p>
        <details class="ops-details">
          <summary>خطاهای خواندن فایل</summary>
          <pre>${(errors || []).map(String).join("\n")}</pre>
        </details>
      </div>
    `;
  }

  function render(host, data, source) {
    // Hard safety boundary guard.
    if (data.signal_authorized || data.trade_instruction_authorized || data.broker_execution_authorized || data.auto_learning_authorized || data.rule_rewrite_authorized) {
      data.health_status = "FAIL";
      data.display_badge = "BOUNDARY VIOLATION";
    }

    const health = txt(data.health_status, "UNKNOWN");
    const statusClass = clsStatus(health);
    const daily = data.daily_rollup_latest || {};
    const weekly = data.weekly_rollup_latest || {};
    const cohort = data.cohort_rollup || {};
    const topReasons = data.top_reason_breakdown || [];
    const topStages = data.top_stage_breakdown || [];
    const created = txt(data.created_utc);
    const reviewCount = n(data.review_item_count);
    const unknownReason = (Array.isArray(topReasons) && topReasons.length && String(topReasons[0][0] || "").includes("UNKNOWN"));

    host.innerHTML = `
      <div class="ops-card ${statusClass}" dir="rtl">
        <div class="ops-head">
          <div>
            <div class="ops-kicker">Shadow OPS / Diagnostics</div>
            <h3>تشخیص عملیاتی Shadow</h3>
          </div>
          <div class="ops-badges">
            <span class="ops-badge">${txt(data.display_badge, "SHADOW OPS / NOT A SIGNAL")}</span>
            <span class="ops-health">${health}</span>
          </div>
        </div>

        <div class="ops-interp">
          <span class="ops-dot"></span>
          <strong>برداشت سریع:</strong>
          <span>${interpretation(data)}</span>
        </div>

        <div class="ops-grid ops-grid-main">
          <div class="ops-metric">
            <span>کاندید shadow</span>
            <b>${n(data.candidate_count)}</b>
            <small>آخرین run</small>
          </div>
          <div class="ops-metric">
            <span>near-miss</span>
            <b>${n(data.near_miss_count_last_run)}</b>
            <small>آخرین run</small>
          </div>
          <div class="ops-metric">
            <span>near-miss قوی</span>
            <b>${n(data.near_miss_high_count_last_run)}</b>
            <small>نیازمند review</small>
          </div>
          <div class="ops-metric">
            <span>blocked</span>
            <b>${n(data.blocked_candidate_count_last_run)}</b>
            <small>آخرین run</small>
          </div>
          <div class="ops-metric">
            <span>core eligible</span>
            <b>${n(data.active_watch_core_eligible_count)}</b>
            <small>watch فعال core</small>
          </div>
          <div class="ops-metric">
            <span>extended-only</span>
            <b>${n(data.active_watch_extended_observation_only_count)}</b>
            <small>غیرمجاز برای core</small>
          </div>
        </div>

        <div class="ops-two-col">
          <div class="ops-panel">
            <h4>علت‌های اصلی near-miss</h4>
            ${formatPairList(topReasons, "علتی ثبت نشده است.")}
            ${unknownReason ? `<div class="ops-warning-note">هنوز علت اصلی بیشتر near-missها UNKNOWN است؛ یعنی upstream باید reason_code دقیق‌تر تولید کند.</div>` : ""}
          </div>
          <div class="ops-panel">
            <h4>Stageهای fail شده</h4>
            ${formatPairList(topStages, "stage مشخصی ثبت نشده است.")}
          </div>
        </div>

        <div class="ops-rollups">
          <div class="ops-roll">
            <span>امروز</span>
            <b>${n(daily.near_miss_count)}</b>
            <small>near-miss / ${n(daily.blocked_candidate_count)} blocked / ${n(daily.run_count)} run</small>
          </div>
          <div class="ops-roll">
            <span>هفته</span>
            <b>${n(weekly.near_miss_count)}</b>
            <small>near-miss / ${n(weekly.blocked_candidate_count)} blocked / ${n(weekly.run_count)} run</small>
          </div>
          <div class="ops-roll">
            <span>cohort</span>
            <b>${n(cohort.near_miss_count)}</b>
            <small>${txt(cohort.cohort_id, "cohort")} / ${n(cohort.run_count)} run</small>
          </div>
          <div class="ops-roll">
            <span>review queue</span>
            <b>${reviewCount}</b>
            <small>مورد برای PMO review</small>
          </div>
        </div>

        <details class="ops-details">
          <summary>جزئیات فنی و مرزهای مجاز</summary>
          <div class="ops-detail-grid">
            <div><span>created</span><b>${created}</b></div>
            <div><span>source</span><b>${txt(source)}</b></div>
            <div><span>signal_authorized</span><b>${txt(data.boundary && data.boundary.signal_authorized, false)}</b></div>
            <div><span>broker_execution_authorized</span><b>${txt(data.boundary && data.boundary.broker_execution_authorized, false)}</b></div>
            <div><span>auto_learning_authorized</span><b>${txt(data.boundary && data.boundary.auto_learning_authorized, false)}</b></div>
            <div><span>rule_rewrite_authorized</span><b>${txt(data.boundary && data.boundary.rule_rewrite_authorized, false)}</b></div>
          </div>
          <p class="ops-muted">${txt(data.plain_language_fa, "این بخش فقط وضعیت عملیاتی shadow را نشان می‌دهد و سیگنال نیست.")}</p>
        </details>
      </div>
    `;
  }

  async function init() {
    const host = ensureHost();
    host.innerHTML = `<div class="ops-card ops-neutral" dir="rtl"><span class="ops-muted">در حال خواندن تشخیص عملیاتی Shadow...</span></div>`;
    const result = await fetchJsonAny(OPS_PATHS);
    if (!result.data) {
      renderError(host, result.errors);
      return;
    }
    render(host, result.data, result.source);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_SHADOW_PANEL_02 = { patchId: PATCH_ID, reload: init };
})();
