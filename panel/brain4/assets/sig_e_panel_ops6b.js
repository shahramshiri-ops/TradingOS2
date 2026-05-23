/* SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0 */
/* Governance markers: NOT A SIGNAL | NO ENTRY | NO TRADE PROPOSAL | NO BROKER EXECUTION */
(() => {
  const VERSION = "SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0";

  const PATHS = {
    portfolio: [
      "../../runtime/sig_e/shadow_portfolio_current.json",
      "./shadow_portfolio_current.json",
      "./sig_e_shadow_portfolio_current.json",
      "/TradingOS2/runtime/sig_e/shadow_portfolio_current.json",
      "runtime/sig_e/shadow_portfolio_current.json"
    ],
    coverage: [
      "../../runtime/sig_e/shadow_coverage1_current.json",
      "./sig_e_shadow_coverage1_current.json",
      "/TradingOS2/runtime/sig_e/shadow_coverage1_current.json",
      "runtime/sig_e/shadow_coverage1_current.json"
    ],
    observation: [
      "../../runtime/sig_e/shadow_observation_report1_current.json",
      "../../runtime/sig_e/shadow_observation_report_current.json",
      "./sig_e_shadow_observation_report1_current.json",
      "/TradingOS2/runtime/sig_e/shadow_observation_report1_current.json"
    ],
    legacyShadowStatus: [
      "./shadow_panel_status_current.json",
      "../../runtime/sig_e/shadow_panel_status_current.json",
      "/TradingOS2/panel/brain4/shadow_panel_status_current.json"
    ],
    legacyOps: [
      "./shadow_ops_status_current.json",
      "../../runtime/sig_e/shadow_ops_status_current.json",
      "/TradingOS2/panel/brain4/shadow_ops_status_current.json"
    ],
    persistence: [
      "./sig_e_shadow_persistence_status_current.json",
      "../../runtime/sig_e/shadow_persistence_current.json",
      "/TradingOS2/runtime/sig_e/shadow_persistence_current.json"
    ]
  };

  const $ = (id) => document.getElementById(id);
  const state = { portfolio: null, coverage: null, observation: null, legacy: null, ops: null, persistence: null, paths: {} };

  async function fetchFirst(candidates) {
    const errors = [];
    for (const path of candidates) {
      try {
        const response = await fetch(`${path}?v=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) {
          errors.push(`${path}: ${response.status}`);
          continue;
        }
        const data = await response.json();
        return { data, path };
      } catch (error) {
        errors.push(`${path}: ${error.message}`);
      }
    }
    return { data: null, path: null, errors };
  }

  function safeText(value, fallback = "—") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function parseUtc(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function ageMinutes(value) {
    const d = parseUtc(value);
    if (!d) return null;
    return Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
  }

  function formatTime(value) {
    const d = parseUtc(value);
    if (!d) return "—";
    return d.toISOString().replace(".000Z", "Z");
  }

  function updateTabRefreshAge(createdUtc) {
    const age = ageMinutes(createdUtc);
    const ageEl = $("tabUpdateAge");
    const timeEl = $("tabUpdateTime");
    if (!ageEl || !timeEl) return;

    ageEl.classList.remove("warn", "danger");

    if (age === null) {
      ageEl.textContent = "Updated —";
      timeEl.textContent = "refresh time unavailable";
      ageEl.classList.add("warn");
      return;
    }

    const label = age <= 1 ? "Updated just now" : `Updated ${age}m ago`;
    ageEl.textContent = label;
    timeEl.textContent = formatTime(createdUtc);

    if (age > 30) ageEl.classList.add("danger");
    else if (age > 10) ageEl.classList.add("warn");
  }

  function titleCase(value) {
    const s = String(value || "UNKNOWN").replaceAll("_", " ").toLowerCase();
    return s.replace(/\b\w/g, c => c.toUpperCase());
  }

  const labelMap = new Map([
    ["SESSION_NOT_MATCHED", "Out of session"],
    ["REGIME_NOT_MATCHED", "Regime blocked"],
    ["SETUP_NOT_FORMED", "Setup not formed"],
    ["H1_TRIGGER_WAIT", "Waiting for H1 trigger"],
    ["H1_TRIGGER_NOT_CONFIRMED", "H1 trigger failed"],
    ["M15_TRIGGER_WAIT", "Waiting for M15 confirmation"],
    ["LIVE_OHLC_SOURCE_MISSING", "Live OHLC missing"],
    ["LIVE_H1_HISTORY_INSUFFICIENT", "Need more H1 history"],
    ["LIVE_M15_HISTORY_INSUFFICIENT", "Need more M15 history"],
    ["DIAGNOSTIC_SHADOW_MATCH_CONFIRMED", "Diagnostic shadow event"],
    ["SHADOW_MATCH_CONFIRMED", "Shadow event"],
    ["NO_ACTIVE_SHADOW_MATCH", "No active shadow match"],
    ["BLOCKER_DIAGNOSTIC_RECORD", "Blocker diagnostic"],
    ["INSTRUMENTATION_GAP_RECORD", "Instrumentation gap"],
    ["UPSTREAM_REASON_NOT_EMITTED", "Upstream reason not emitted"]
  ]);

  const reasonMap = new Map([
    ["session_not_london", "Current session is not London."],
    ["session_not_asia", "Current session is not Asia."],
    ["session_not_london_or_overlap", "Current session is not London or London/New York overlap."],
    ["session_not_london_ny_overlap", "Current session is not London/New York overlap."],
    ["overlap_long_diagnostic_regime_not_matched", "Overlap long context is not supported by current regime."],
    ["previous_h1_bar_did_not_match_overlap_lower_rejection_expansion_setup", "The prior H1 candle did not form the required lower-rejection expansion setup."],
    ["previous_h1_bar_did_not_match_lower_rejection_expansion_setup", "The prior H1 candle did not form the required lower-rejection expansion setup."],
    ["eurusd_long_trap_regime_not_matched", "EURUSD long-trap regime conditions are not currently aligned."],
    ["live_usdjpy_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed", "Live USDJPY H1/M15 source is missing; historical fallback is not allowed."],
    ["d1_h4_alignment_not_matched", "D1/H4 alignment does not support this lane."]
  ]);

  function humanStatus(status) {
    return labelMap.get(String(status || "").toUpperCase()) || titleCase(status);
  }

  function humanReason(reason) {
    const key = String(reason || "");
    return reasonMap.get(key) || titleCase(key || "No reason reported");
  }

  function getRegimeDetails(lane) {
    const checks = Array.isArray(lane?.checks) ? lane.checks : [];
    const regime = checks.find(x => String(x?.check_id || "").toUpperCase().includes("REGIME"));
    return regime?.details || {};
  }

  function systemClass(summary, createdUtc) {
    const attention = Number(summary?.data_or_field_attention_count || 0);
    const age = ageMinutes(createdUtc);
    if (attention > 0) return "danger";
    if (age !== null && age > 30) return "warn";
    return "ok";
  }

  function systemText(summary, createdUtc) {
    const attention = Number(summary?.data_or_field_attention_count || 0);
    const age = ageMinutes(createdUtc);
    if (attention > 0) return "Data attention";
    if (age !== null && age > 30) return "Refresh aging";
    return "Live OK";
  }

  function portfolioMeaning(status, activeCount) {
    if (activeCount > 0) return "A shadow event is active. This is still not a trade signal.";
    if (status === "NO_ACTIVE_SHADOW_MATCH") return "The system is observing; no active shadow event is present.";
    if (status === "ATTENTION") return "Review data or lane attention flags before interpretation.";
    return "Portfolio state loaded successfully.";
  }

  function statusStage(status) {
    const s = String(status || "").toUpperCase();
    if (s.includes("SHADOW_MATCH") || s.includes("DIAGNOSTIC_SHADOW_MATCH")) return { label: humanStatus(status).toUpperCase(), stage: "event", tone: "event" };
    if (s.includes("M15")) return { label: "M15 WAIT", stage: "m15", tone: "wait" };
    if (s.includes("H1_TRIGGER_WAIT")) return { label: "TRIGGER WAIT", stage: "trigger", tone: "wait" };
    if (s.includes("H1_TRIGGER_NOT")) return { label: "TRIGGER FAILED", stage: "trigger", tone: "wait" };
    if (s.includes("SETUP")) return { label: "SETUP NOT FORMED", stage: "setup", tone: "wait" };
    if (s.includes("OHLC") || s.includes("DATA") || s.includes("INSUFFICIENT") || s.includes("STALE")) return { label: "DATA CHECK", stage: "data", tone: "data" };
    if (s.includes("REGIME")) return { label: "REGIME BLOCKED", stage: "regime", tone: "wait" };
    if (s.includes("SESSION")) return { label: "OUT OF SESSION", stage: "session", tone: "neutral" };
    return { label: humanStatus(status).toUpperCase(), stage: "session", tone: "neutral" };
  }

  function markStages(card, stage) {
    const order = ["session", "regime", "setup", "trigger", "m15", "event"];
    const currentIndex = order.indexOf(stage);
    card.querySelectorAll(".stage-rail span").forEach(span => {
      const idx = order.indexOf(span.dataset.stage);
      span.classList.remove("done", "current", "blocked");
      if (stage === "event") {
        span.classList.add("done");
      } else if (idx < currentIndex && currentIndex > 0) {
        span.classList.add("done");
      } else if (idx === currentIndex) {
        span.classList.add(stage === "data" ? "blocked" : "current");
      }
    });
  }

  function laneSubtitle(lane) {
    const cls = String(lane?.classification || "");
    if (cls.includes("DIAGNOSTIC")) return "Diagnostic lane";
    if (cls.includes("CAVEATED")) return "Caveated observation";
    return "Primary shadow lane";
  }

  function emptyState(title, body) {
    return `
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">∅</div>
        <div>
          <strong>${title}</strong>
          <p>${body}</p>
        </div>
      </div>`;
  }

  function renderActiveEvents(lanes) {
    const container = $("activeEvents");
    const active = lanes.filter(lane => lane?.is_shadow_match === true || String(lane?.detector_status || "").includes("SHADOW_MATCH"));
    $("activeEventBadge").textContent = active.length ? `${active.length} active` : "No signal";

    if (!active.length) {
      container.innerHTML = emptyState("No active shadow event now", "The system is observing. Nothing here is a trade instruction.");
      return;
    }

    container.innerHTML = active.map(lane => `
      <article class="event-card">
        <strong>${safeText(lane.display_name || lane.lane_id)}</strong>
        <p>${safeText(lane.instrument)} · ${safeText(lane.direction)} · ${humanStatus(lane.detector_status)}</p>
        <p>${humanReason(lane.status_reason)}</p>
      </article>`).join("");
  }

  function renderLanes(lanes) {
    const grid = $("laneGrid");
    const template = $("laneCardTemplate");
    grid.innerHTML = "";

    lanes.forEach(lane => {
      const fragment = template.content.cloneNode(true);
      const card = fragment.querySelector(".lane-card");
      const details = getRegimeDetails(lane);
      const stage = statusStage(lane.detector_status);

      card.classList.add(`stage-${stage.tone}`);
      fragment.querySelector(".lane-kicker").textContent = `${safeText(lane.instrument)} · ${safeText(lane.direction)}`;
      fragment.querySelector("h3").textContent = safeText(lane.display_name || lane.lane_id);
      fragment.querySelector(".lane-status").textContent = stage.label;
      fragment.querySelector(".lane-reason").textContent = humanReason(lane.status_reason);

      const badge = fragment.querySelector(".lane-badge");
      badge.textContent = laneSubtitle(lane);
      if (String(lane.classification || "").includes("DIAGNOSTIC")) badge.classList.add("diagnostic");

      fragment.querySelector(".meta-session").textContent = `Session: ${safeText(details.session_bucket)}`;
      const h1 = lane?.surface_snapshot?.h1_bar_open_ts_utc || details.h1_bar_open_ts_utc;
      const m15 = lane?.surface_snapshot?.m15_bar_open_ts_utc || details.m15_bar_open_ts_utc;
      fragment.querySelector(".meta-tf").textContent = `H1 ${safeText(h1, "—").slice(11, 16)} · M15 ${safeText(m15, "—").slice(11, 16)} UTC`;

      markStages(card, stage.stage);
      grid.appendChild(fragment);
    });

    if (!lanes.length) {
      grid.innerHTML = emptyState("No lanes loaded", "Portfolio JSON did not contain lane data.");
    }
  }

  function renderMemoryBridge(lanes) {
    const grid = $("memoryGrid");
    const counts = {
      primary: lanes.filter(x => String(x.classification || "").includes("PRIMARY")).length,
      caveated: lanes.filter(x => String(x.classification || "").includes("CAVEATED")).length,
      diagnostic: lanes.filter(x => String(x.classification || "").includes("DIAGNOSTIC")).length,
      active: lanes.filter(x => x.is_shadow_match === true).length,
      archived: 0,
      rejected: 0
    };

    grid.innerHTML = [
      ["Active runtime lanes", counts.primary, "Primary lanes currently connected to live shadow observation."],
      ["Caveated watches", counts.caveated, "Observed with caveats; not a signal and not a trade instruction."],
      ["Diagnostic-only lanes", counts.diagnostic, "Research-only variants used to test coverage and behavior."],
      ["Active shadow events", counts.active, "Events active now; still no entry/stop/target authority."],
      ["Archived / weakened", counts.archived, "Not shown in the main cockpit unless reconnected by rule."],
      ["Rejected / no runtime use", counts.rejected, "Kept out of the live surface."]
    ].map(([title, value, body]) => `
      <article class="memory-card">
        <p class="label">${title}</p>
        <strong>${value}</strong>
        <span>${body}</span>
      </article>`).join("");
  }

  function renderLiveShadow(lanes, portfolio, legacy, ops) {
    const grid = $("liveShadowGrid");
    const summary = portfolio?.summary || {};
    const near = Number(summary.total_near_misses || 0);
    const records = Number(summary.total_refresh_records || 0);
    const shadow = Number(summary.total_shadow_events || 0);
    const active = Number(summary.active_shadow_match_count || 0);
    const diagnosticRows = lanes.reduce((acc, lane) => acc + (String(lane.classification || "").includes("DIAGNOSTIC") ? 1 : 0), 0);

    const legacyCards = legacy || ops ? `
      <article class="debug-card">
        <p class="label">Legacy debug payloads</p>
        <strong>${legacy ? "Loaded" : "—"}</strong>
        <span>${ops ? "OPS diagnostics also loaded." : "OPS diagnostics not found."}</span>
      </article>` : "";

    grid.innerHTML = `
      <article class="debug-card">
        <p class="label">Readable near-misses</p>
        <strong>${near}</strong>
        <span>Diagnostic records that approached a candidate gate, not real opportunities.</span>
      </article>
      <article class="debug-card">
        <p class="label">Refresh records</p>
        <strong>${records}</strong>
        <span>Observation rows recorded across live shadow lanes.</span>
      </article>
      <article class="debug-card">
        <p class="label">Confirmed shadows</p>
        <strong>${shadow}</strong>
        <span>Shadow ledger entries, still display-only and non-executable.</span>
      </article>
      <article class="debug-card">
        <p class="label">Active now</p>
        <strong>${active}</strong>
        <span>Current active shadow detections.</span>
      </article>
      <article class="debug-card">
        <p class="label">Diagnostic lanes</p>
        <strong>${diagnosticRows}</strong>
        <span>Research-only lanes separated from primary observation.</span>
      </article>
      ${legacyCards}`;
  }

  function renderHistory(lanes) {
    const list = $("historyList");
    const rows = lanes.flatMap(lane => {
      const items = [];
      if (lane.latest_near_miss) items.push({ type: "Near-miss", lane, item: lane.latest_near_miss });
      if (lane.latest_shadow_event) items.push({ type: "Shadow event", lane, item: lane.latest_shadow_event });
      if (lane.latest_outcome) items.push({ type: "Outcome", lane, item: lane.latest_outcome });
      return items;
    });

    if (!rows.length) {
      list.innerHTML = emptyState("No recent history payload", "No latest near-miss, shadow event or outcome object is available in the current portfolio payload.");
      return;
    }

    list.innerHTML = rows.slice(0, 12).map(row => `
      <article class="history-card">
        <strong>${row.type}: ${safeText(row.lane.display_name || row.lane.lane_id)}</strong>
        <p>${humanStatus(row.item.detector_status || row.item.outcome_status)} · ${safeText(row.item.created_utc || row.item.detector_created_utc)}</p>
        <p>${humanReason(row.item.status_reason || row.item.reason)}</p>
        <div class="raw-code">${safeText(row.item.record_id || row.item.shadow_event_id || row.item.detector_run_id)}</div>
      </article>`).join("");
  }

  function renderDiagnostics(portfolio, coverage, persistence) {
    const grid = $("diagnosticsGrid");
    const summary = portfolio?.summary || {};
    const coverageStatus = coverage?.coverage_status || "not loaded";
    const persistenceStatus = persistence?.validation_status || persistence?.persistence_status || persistence?.snapshot_status || "not loaded";
    $("diagnosticBadge").textContent = Number(summary.data_or_field_attention_count || 0) ? "Attention" : "Clean";
    $("coverageBadge").textContent = titleCase(coverageStatus);

    grid.innerHTML = `
      <article class="diagnostic-card">
        <p class="label">Coverage</p>
        <strong>${summary.detector_count ?? "—"}</strong>
        <span>${titleCase(coverageStatus)}</span>
      </article>
      <article class="diagnostic-card">
        <p class="label">Data attention</p>
        <strong>${summary.data_or_field_attention_count ?? 0}</strong>
        <span>Open data/field flags.</span>
      </article>
      <article class="diagnostic-card">
        <p class="label">Persistence</p>
        <strong>${titleCase(persistenceStatus).slice(0, 10)}</strong>
        <span>Snapshot / persisted observation state.</span>
      </article>
      <article class="diagnostic-card">
        <p class="label">Primary matches</p>
        <strong>${summary.active_primary_shadow_match_count ?? 0}</strong>
        <span>Active primary shadow events now.</span>
      </article>
      <article class="diagnostic-card">
        <p class="label">Caveated matches</p>
        <strong>${summary.active_caveated_shadow_match_count ?? 0}</strong>
        <span>Active caveated shadow events now.</span>
      </article>
      <article class="diagnostic-card">
        <p class="label">Panel version</p>
        <strong>OPS6B</strong>
        <span>${VERSION}</span>
      </article>`;
  }

  function renderPortfolio(portfolio, portfolioPath, coverage, observation, legacy, ops, persistence) {
    const summary = portfolio?.summary || {};
    const lanes = Array.isArray(portfolio?.lanes) ? portfolio.lanes : [];
    const createdUtc = portfolio?.created_utc;

    const cls = systemClass(summary, createdUtc);
    const pill = $("systemPill");
    pill.classList.remove("ok", "warn", "danger");
    pill.classList.add(cls);
    $("systemPillText").textContent = systemText(summary, createdUtc);

    const status = safeText(portfolio?.portfolio_status || summary?.portfolio_status);
    const active = Number(summary?.active_shadow_match_count || 0);

    $("portfolioStatus").textContent = humanStatus(status).toUpperCase();
    $("portfolioMeaning").textContent = portfolioMeaning(portfolio?.portfolio_status || summary?.portfolio_status, active);
    $("lastRefresh").textContent = `refresh ${formatTime(createdUtc)}`;
    const age = ageMinutes(createdUtc);
    $("ageBadge").textContent = age === null ? "age —" : `age ${age}m`;
    $("portfolioSource").textContent = portfolioPath ? portfolioPath.split("/").slice(-2).join("/") : "source —";
    updateTabRefreshAge(createdUtc);
    $("laneCount").textContent = safeText(summary?.detector_count ?? lanes.length);
    $("activeCount").textContent = safeText(active);
    $("attentionCount").textContent = safeText(summary?.data_or_field_attention_count ?? 0);
    $("refreshRecords").textContent = safeText(summary?.total_refresh_records ?? 0);
    $("nearMisses").textContent = safeText(summary?.total_near_misses ?? 0);
    $("shadowEvents").textContent = safeText(summary?.total_shadow_events ?? 0);

    renderActiveEvents(lanes);
    renderLanes(lanes);
    renderMemoryBridge(lanes);
    renderLiveShadow(lanes, portfolio, legacy, ops);
    renderHistory(lanes);
    renderDiagnostics(portfolio, coverage, persistence);

    document.documentElement.dataset.portfolioSource = portfolioPath || "unresolved";
    document.documentElement.dataset.panelVersion = VERSION;
  }

  function renderError(message, errors) {
    $("systemPill").classList.add("danger");
    $("systemPillText").textContent = "Panel data error";
    $("portfolioStatus").textContent = "DATA NOT LOADED";
    $("portfolioMeaning").textContent = message;
    $("laneGrid").innerHTML = emptyState("Could not load portfolio JSON", errors ? errors.slice(0, 3).join(" · ") : "No detail available.");
  }

  function switchTab(name) {
    document.querySelectorAll(".tab").forEach(btn => btn.classList.toggle("active", btn.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === `tab-${name}`));
    history.replaceState(null, "", `#${name}`);
  }

  function wireTabs() {
    document.querySelectorAll(".tab").forEach(btn => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
    const initial = (location.hash || "#cockpit").replace("#", "");
    if (document.querySelector(`[data-tab="${initial}"]`)) switchTab(initial);
  }

  async function loadAll() {
    const [portfolioResult, coverageResult, observationResult, legacyResult, opsResult, persistenceResult] = await Promise.all([
      fetchFirst(PATHS.portfolio),
      fetchFirst(PATHS.coverage),
      fetchFirst(PATHS.observation),
      fetchFirst(PATHS.legacyShadowStatus),
      fetchFirst(PATHS.legacyOps),
      fetchFirst(PATHS.persistence)
    ]);

    state.portfolio = portfolioResult.data;
    state.coverage = coverageResult.data;
    state.observation = observationResult.data;
    state.legacy = legacyResult.data;
    state.ops = opsResult.data;
    state.persistence = persistenceResult.data;
    state.paths = {
      portfolio: portfolioResult.path,
      coverage: coverageResult.path,
      observation: observationResult.path,
      legacy: legacyResult.path,
      ops: opsResult.path,
      persistence: persistenceResult.path
    };

    if (!state.portfolio) {
      renderError("The console could not read the latest shadow portfolio payload.", portfolioResult.errors);
      return;
    }

    renderPortfolio(state.portfolio, state.paths.portfolio, state.coverage, state.observation, state.legacy, state.ops, state.persistence);
  }

  async function init() {
    wireTabs();
    $("refreshButton")?.addEventListener("click", loadAll);
    await loadAll();
  }

  window.addEventListener("DOMContentLoaded", init);
})();
