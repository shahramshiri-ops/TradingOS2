/* SHADOW-PANEL-03 v1.0
   Unified Shadow card for SIG Brain panel.
   Merges SHADOW-PANEL-01 status + SHADOW-PANEL-02 OPS diagnostics into one clean card.
   Boundary: NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE.
*/
(function () {
  "use strict";

  const PATCH_ID = "SHADOW_PANEL_03_UNIFIED_v1_0";

  const STATUS_PATHS = [
    "shadow_panel_status_current.json",
    "./shadow_panel_status_current.json",
    "../../runtime/sig_shadow/shadow_panel_status_current.json"
  ];

  const OPS_PATHS = [
    "shadow_ops_status_current.json",
    "./shadow_ops_status_current.json",
    "../../runtime/sig_shadow/shadow_ops_status_current.json"
  ];

  function bust(url) {
    return url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();
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

  function hasBoundaryViolation(data) {
    return !!(data && (
      data.signal_authorized ||
      data.trade_instruction_authorized ||
      data.broker_execution_authorized ||
      data.action_surface_authorized ||
      data.auto_learning_authorized ||
      data.rule_rewrite_authorized
    ));
  }

  function statusClass(health) {
    const h = String(health || "").toUpperCase();
    if (h === "PASS") return "unified-pass";
    if (h === "WARN") return "unified-warn";
    if (h === "FAIL" || h.includes("FAIL")) return "unified-fail";
    return "unified-neutral";
  }

  function mergeData(status, ops) {
    const boundaryBad = hasBoundaryViolation(status) || hasBoundaryViolation(ops);
    const health = boundaryBad ? "FAIL" : txt((ops && ops.health_status) || (status && status.shadow_system_status), "UNKNOWN");

    return {
      health_status: health,
      created_utc: txt((ops && ops.created_utc) || (status && status.created_utc)),
      status_created_utc: txt(status && status.created_utc),
      ops_created_utc: txt(ops && ops.created_utc),
      display_badge: boundaryBad ? "BOUNDARY VIOLATION" : txt((ops && ops.display_badge) || (status && status.display_badge), "SHADOW / NOT A SIGNAL"),
      candidate_count: n((ops && ops.candidate_count), n(status && status.candidate_count)),
      near_miss_count: n((ops && ops.near_miss_count_last_run), n(status && status.near_miss_count_last_run)),
      near_miss_high_count: n((ops && ops.near_miss_high_count_last_run), n(status && status.near_miss_high_count_last_run)),
      blocked_count: n((ops && ops.blocked_candidate_count_last_run), n(status && status.blocked_candidate_count)),
      observation_count: n(status && status.observation_count),
      observation_pending_count: n(status && status.observation_pending_count),
      observation_complete_count: n(status && status.observation_complete_count),
      active_core_count: n(ops && ops.active_watch_core_eligible_count),
      active_extended_count: n(ops && ops.active_watch_extended_observation_only_count),
      top_reason_breakdown: (ops && Array.isArray(ops.top_reason_breakdown)) ? ops.top_reason_breakdown : [],
      top_stage_breakdown: (ops && Array.isArray(ops.top_stage_breakdown)) ? ops.top_stage_breakdown : [],
      daily_rollup_latest: (ops && ops.daily_rollup_latest) || null,
      weekly_rollup_latest: (ops && ops.weekly_rollup_latest) || null,
      cohort_rollup: (ops && ops.cohort_rollup) || {
        cohort_id: status && status.cohort_id,
        candidate_count: status && status.candidate_count,
        near_miss_count: status && status.near_miss_count_last_run,
        near_miss_high_count: status && status.near_miss_high_count_last_run
      },
      review_item_count: n(ops && ops.review_item_count),
      plain_language_fa: txt((ops && ops.plain_language_fa) || (status && status.plain_language_fa), "این بخش فقط وضعیت shadow را نشان می‌دهد و سیگنال معامله نیست."),
      status_source_available: !!status,
      ops_source_available: !!ops,
      boundary_violation: boundaryBad
    };
  }

  function quickInterpretation(d) {
    if (d.boundary_violation) {
      return "هشدار مرزی: یکی از payloadها مجوز نامعتبر دارد. این خروجی نباید برای تصمیم معاملاتی استفاده شود.";
    }
    const h = String(d.health_status || "").toUpperCase();
    if (h === "FAIL") {
      return "سلامت pipeline مشکل جدی دارد؛ قبل از تفسیر candidate یا near-miss باید health بررسی شود.";
    }
    if (h === "WARN") {
      return "pipeline هشدار دارد؛ عددها قابل مشاهده‌اند اما قبل از نتیجه‌گیری باید freshness و اجرای workflow بررسی شود.";
    }
    if (d.candidate_count > 0) {
      return "کاندید shadow ثبت شده است؛ هنوز سیگنال نیست و فقط باید observationهای بعدی تکمیل شوند.";
    }
    if (d.near_miss_high_count > 0) {
      return "کاندید کامل نداریم، اما near-miss قوی وجود دارد؛ یعنی باید علت fail شدن stageها بررسی شود، نه اینکه ruleها شل شوند.";
    }
    if (d.near_miss_count > 0) {
      return "کاندید shadow نداریم، اما وضعیت‌های نزدیک ثبت شده‌اند؛ این برای تشخیص سخت‌گیری trigger/blocker/eligibility مفید است.";
    }
    return "فعلاً candidate یا near-miss مهمی دیده نمی‌شود؛ این به معنی خرابی سیستم نیست.";
  }

  function formatPairs(list, empty) {
    if (!Array.isArray(list) || !list.length) {
      return `<div class="shadow-unified-empty">${empty || "موردی ثبت نشده است."}</div>`;
    }
    return `<div class="shadow-unified-pairs">` + list.slice(0, 5).map((x) => {
      const k = Array.isArray(x) ? x[0] : (x && (x.key || x.reason || x.stage)) || "UNKNOWN";
      const v = Array.isArray(x) ? x[1] : (x && (x.count || x.value)) || 0;
      return `<div class="shadow-unified-pair"><span>${txt(k)}</span><b>${txt(v, "0")}</b></div>`;
    }).join("") + `</div>`;
  }

  function rollupBlock(title, roll, fallbackLabel) {
    const r = roll || {};
    return `
      <div class="shadow-unified-roll">
        <span>${title}</span>
        <b>${n(r.near_miss_count)}</b>
        <small>${txt(r.period || r.cohort_id, fallbackLabel)} · ${n(r.run_count)} run · ${n(r.blocked_candidate_count)} blocked</small>
      </div>`;
  }

  function removeOldHosts() {
    const oldHosts = [
      "shadow-panel-01-host",
      "shadow-panel-02-ops-host"
    ];
    oldHosts.forEach((id) => {
      const el = document.getElementById(id);
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    });
  }

  function ensureHost() {
    removeOldHosts();
    let host = document.getElementById("shadow-panel-03-unified-host");
    if (host) return host;

    host = document.createElement("section");
    host.id = "shadow-panel-03-unified-host";
    host.className = "shadow-panel-03-unified-host";

    // Prefer a placement after the hero/header and before active event cards.
    const anchors = [
      document.querySelector("[data-shadow-panel-anchor]"),
      document.querySelector("#active-events"),
      document.querySelector(".active-events"),
      document.querySelector("main"),
      document.querySelector(".container"),
      document.body
    ].filter(Boolean);

    const parent = anchors[0] || document.body;
    if (parent === document.body || parent.tagName.toLowerCase() === "main") {
      parent.insertBefore(host, parent.firstChild);
    } else if (parent.parentNode) {
      parent.parentNode.insertBefore(host, parent.nextSibling);
    } else {
      document.body.insertBefore(host, document.body.firstChild);
    }
    return host;
  }

  function renderLoading(host) {
    host.innerHTML = `
      <div class="shadow-unified-card unified-neutral" dir="rtl">
        <div class="shadow-unified-muted">در حال خواندن وضعیت Shadow...</div>
      </div>`;
  }

  function renderMissing(host, statusResult, opsResult) {
    const errors = []
      .concat((statusResult && statusResult.errors) || [])
      .concat((opsResult && opsResult.errors) || []);

    host.innerHTML = `
      <div class="shadow-unified-card unified-neutral" dir="rtl">
        <div class="shadow-unified-head">
          <div>
            <div class="shadow-unified-kicker">Shadow / Diagnostics</div>
            <h3>وضعیت Shadow در دسترس نیست</h3>
          </div>
          <span class="shadow-unified-badge">NOT A SIGNAL</span>
        </div>
        <p class="shadow-unified-muted">فایل‌های وضعیت shadow هنوز deploy نشده‌اند یا در دسترس نیستند.</p>
        <details class="shadow-unified-details">
          <summary>خطاهای خواندن فایل</summary>
          <pre>${errors.map(String).join("\n")}</pre>
        </details>
      </div>`;
  }

  function render(host, d, sources) {
    const cls = statusClass(d.health_status);
    const unknownTop = Array.isArray(d.top_reason_breakdown) &&
      d.top_reason_breakdown.length &&
      String(d.top_reason_breakdown[0][0] || "").includes("UNKNOWN");

    host.innerHTML = `
      <div class="shadow-unified-card ${cls}" dir="rtl">
        <div class="shadow-unified-head">
          <div>
            <div class="shadow-unified-kicker">Live Shadow / OPS Diagnostics</div>
            <h3>Shadow زنده</h3>
          </div>
          <div class="shadow-unified-badges">
            <span class="shadow-unified-badge">${txt(d.display_badge, "SHADOW / NOT A SIGNAL")}</span>
            <span class="shadow-unified-health">${txt(d.health_status, "UNKNOWN")}</span>
          </div>
        </div>

        <div class="shadow-unified-quick">
          <span class="shadow-unified-dot"></span>
          <strong>برداشت سریع:</strong>
          <span>${quickInterpretation(d)}</span>
        </div>

        <div class="shadow-unified-metrics">
          <div class="shadow-unified-metric primary">
            <span>کاندید shadow</span>
            <b>${d.candidate_count}</b>
            <small>آخرین run</small>
          </div>
          <div class="shadow-unified-metric">
            <span>near-miss</span>
            <b>${d.near_miss_count}</b>
            <small>آخرین run</small>
          </div>
          <div class="shadow-unified-metric attention">
            <span>near-miss قوی</span>
            <b>${d.near_miss_high_count}</b>
            <small>نیازمند review</small>
          </div>
          <div class="shadow-unified-metric">
            <span>blocked</span>
            <b>${d.blocked_count}</b>
            <small>آخرین run</small>
          </div>
          <div class="shadow-unified-metric">
            <span>observation</span>
            <b>${d.observation_count}</b>
            <small>${d.observation_pending_count} pending / ${d.observation_complete_count} complete</small>
          </div>
          <div class="shadow-unified-metric">
            <span>eligibility</span>
            <b>${d.active_core_count}/${d.active_extended_count}</b>
            <small>core / extended-only</small>
          </div>
        </div>

        <div class="shadow-unified-split">
          <div class="shadow-unified-panel">
            <h4>علت‌های اصلی near-miss</h4>
            ${formatPairs(d.top_reason_breakdown, "علتی ثبت نشده است.")}
            ${unknownTop ? `<div class="shadow-unified-warning">علت بیشتر near-missها هنوز UNKNOWN است؛ یعنی upstream باید reason_code دقیق‌تر تولید کند.</div>` : ""}
          </div>
          <div class="shadow-unified-panel">
            <h4>Stageهای fail شده</h4>
            ${formatPairs(d.top_stage_breakdown, "stage مشخصی ثبت نشده است.")}
          </div>
        </div>

        <details class="shadow-unified-details" open>
          <summary>Rollup و review</summary>
          <div class="shadow-unified-rollups">
            ${rollupBlock("امروز", d.daily_rollup_latest, "today")}
            ${rollupBlock("هفته", d.weekly_rollup_latest, "week")}
            ${rollupBlock("cohort", d.cohort_rollup, "cohort")}
            <div class="shadow-unified-roll">
              <span>review queue</span>
              <b>${d.review_item_count}</b>
              <small>مورد برای PMO review</small>
            </div>
          </div>
        </details>

        <details class="shadow-unified-details">
          <summary>جزئیات فنی و مرزها</summary>
          <div class="shadow-unified-detail-grid">
            <div><span>created</span><b>${txt(d.created_utc)}</b></div>
            <div><span>status source</span><b>${txt(sources.status)}</b></div>
            <div><span>ops source</span><b>${txt(sources.ops)}</b></div>
            <div><span>status available</span><b>${txt(d.status_source_available)}</b></div>
            <div><span>ops available</span><b>${txt(d.ops_source_available)}</b></div>
            <div><span>boundary</span><b>NO_SIGNAL / NO_EXECUTION</b></div>
          </div>
          <p class="shadow-unified-muted">${txt(d.plain_language_fa)}</p>
        </details>
      </div>
    `;
  }

  async function init() {
    const host = ensureHost();
    renderLoading(host);

    const [statusResult, opsResult] = await Promise.all([
      fetchJsonAny(STATUS_PATHS),
      fetchJsonAny(OPS_PATHS)
    ]);

    if (!statusResult.data && !opsResult.data) {
      renderMissing(host, statusResult, opsResult);
      return;
    }

    const d = mergeData(statusResult.data, opsResult.data);
    render(host, d, { status: statusResult.source, ops: opsResult.source });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SIG_SHADOW_PANEL_03 = { patchId: PATCH_ID, reload: init };
})();
