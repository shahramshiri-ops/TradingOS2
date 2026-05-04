/**
 * PRV1I-01 — Real Mobile Refresh Button Proxy
 * Cloudflare Worker that securely triggers a GitHub Actions workflow_dispatch.
 * It does NOT run trading logic, broker/order/execution, signals, PnL, validation verdicts, or production-readiness logic.
 * Secrets stay in Cloudflare Worker secrets.
 */

function jsonResponse(obj, status = 200, cors = {}) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...cors },
  });
}

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = env.ALLOWED_ORIGIN || "*";
  const allowOrigin = allowed === "*" || allowed === origin ? (allowed === "*" ? "*" : origin) : allowed;
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type, x-refresh-pin",
    "Access-Control-Max-Age": "86400",
  };
}

async function readJsonSafe(request) {
  try { return await request.json(); } catch (_) { return {}; }
}

function requireEnv(env, keys) {
  const missing = keys.filter((k) => !env[k]);
  return { ok: missing.length === 0, missing };
}

function verifyPin(request, body, env) {
  if (!env.REFRESH_PIN) return { ok: false, reason: "REFRESH_PIN secret is not configured on the Worker" };
  const supplied = request.headers.get("X-Refresh-Pin") || body.pin || "";
  if (!supplied) return { ok: false, reason: "Missing refresh PIN" };
  if (supplied !== env.REFRESH_PIN) return { ok: false, reason: "Invalid refresh PIN" };
  return { ok: true };
}

async function githubFetch(env, path, init = {}) {
  const base = "https://api.github.com";
  const headers = {
    "accept": "application/vnd.github+json",
    "authorization": `Bearer ${env.GITHUB_ACTIONS_DISPATCH_TOKEN}`,
    "x-github-api-version": env.GITHUB_API_VERSION || "2022-11-28",
    "user-agent": "PRV1I-mobile-refresh-worker",
    ...(init.headers || {}),
  };
  return fetch(base + path, { ...init, headers });
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    const url = new URL(request.url);
    const required = requireEnv(env, ["GITHUB_OWNER", "GITHUB_REPO", "GITHUB_WORKFLOW_ID", "GITHUB_REF", "GITHUB_ACTIONS_DISPATCH_TOKEN"]);

    if (url.pathname === "/health" && request.method === "GET") {
      return jsonResponse({
        program: "PRV1I-01", service: "mobile_refresh_proxy",
        status: required.ok ? "configured" : "missing_required_configuration",
        missing: required.missing, owner: env.GITHUB_OWNER || null, repo: env.GITHUB_REPO || null,
        workflow_id: env.GITHUB_WORKFLOW_ID || null, ref: env.GITHUB_REF || null,
        pin_required: Boolean(env.REFRESH_PIN),
        boundary: { worker_triggers_workflow_only: true, worker_does_not_run_provider_fetch: true, worker_does_not_create_signal_or_execution: true }
      }, required.ok ? 200 : 500, cors);
    }
    if (!required.ok) return jsonResponse({ program: "PRV1I-01", status: "blocked_missing_worker_configuration", missing: required.missing }, 500, cors);

    if (url.pathname === "/refresh" && request.method === "POST") {
      const body = await readJsonSafe(request);
      const pin = verifyPin(request, body, env);
      if (!pin.ok) return jsonResponse({ program: "PRV1I-01", status: "refresh_rejected", reason: pin.reason, boundary: "No workflow dispatched." }, 401, cors);
      const dispatchPath = `/repos/${encodeURIComponent(env.GITHUB_OWNER)}/${encodeURIComponent(env.GITHUB_REPO)}/actions/workflows/${encodeURIComponent(env.GITHUB_WORKFLOW_ID)}/dispatches`;
      const payload = { ref: env.GITHUB_REF, inputs: { trigger_source: "mobile_refresh_button", requested_at_utc: new Date().toISOString() } };
      const gh = await githubFetch(env, dispatchPath, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
      let ghText = ""; try { ghText = await gh.text(); } catch (_) {}
      if (!gh.ok) return jsonResponse({ program: "PRV1I-01", status: "workflow_dispatch_failed", github_status: gh.status, github_response_excerpt: ghText.slice(0, 500) }, 502, cors);
      return jsonResponse({ program: "PRV1I-01", status: "workflow_dispatch_sent", owner: env.GITHUB_OWNER, repo: env.GITHUB_REPO, workflow_id: env.GITHUB_WORKFLOW_ID, ref: env.GITHUB_REF, github_status: gh.status, message: "GitHub Actions daily runtime workflow was requested.", boundary: { worker_triggers_workflow_only: true, no_signal: true, no_execution: true, no_broker: true, no_pnl: true } }, 200, cors);
    }

    if (url.pathname === "/latest-run" && request.method === "GET") {
      const runsPath = `/repos/${encodeURIComponent(env.GITHUB_OWNER)}/${encodeURIComponent(env.GITHUB_REPO)}/actions/workflows/${encodeURIComponent(env.GITHUB_WORKFLOW_ID)}/runs?branch=${encodeURIComponent(env.GITHUB_REF)}&per_page=1`;
      const gh = await githubFetch(env, runsPath, { method: "GET" });
      const data = await gh.json().catch(() => ({}));
      if (!gh.ok) return jsonResponse({ program: "PRV1I-01", status: "latest_run_lookup_failed", github_status: gh.status, github_response: data }, 502, cors);
      const run = Array.isArray(data.workflow_runs) && data.workflow_runs.length ? data.workflow_runs[0] : null;
      return jsonResponse({ program: "PRV1I-01", status: run ? "latest_run_found" : "no_runs_found", latest_run: run ? { id: run.id, name: run.name, status: run.status, conclusion: run.conclusion, html_url: run.html_url, created_at: run.created_at, updated_at: run.updated_at, run_started_at: run.run_started_at } : null }, 200, cors);
    }
    return jsonResponse({ program: "PRV1I-01", status: "not_found", routes: ["GET /health", "POST /refresh", "GET /latest-run"] }, 404, cors);
  }
};
