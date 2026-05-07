import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("personal_runtime_v1_latest_product")

OBJECTS = [
    {
        "instrument": "EURUSD",
        "timeframe": "H1",
        "surface": "EURUSD_H1",
        "sig_object_id": "EURUSD_H1_LONDON_OVERLAP_DIRECTIONAL_PERSISTENCE_OBJECT_SPEC_v1_0",
        "candidate_family": "london_overlap_directional_persistence",
        "lifecycle": "RESEARCH_ACTIVE",
        "default_state_when_available": "RESEARCH_ACTIVE_DISPLAY_ONLY",
        "priority": "primary_dynamic_research_state"
    },
    {
        "instrument": "USDJPY",
        "timeframe": "H1",
        "surface": "USDJPY_H1",
        "sig_object_id": "USDJPY_H1_TREND_SESSION_CONTINUITY_OBJECT_SPEC_v1_0",
        "candidate_family": "trend_session_continuity",
        "lifecycle": "RESEARCH_ACTIVE_WITH_DATA_QUALITY_CAVEAT",
        "default_state_when_available": "DATA_QUALITY_CAVEATED_RESEARCH_ACTIVE",
        "priority": "primary_dynamic_research_state_with_data_quality_caveat"
    },
    {
        "instrument": "XAUUSD",
        "timeframe": "M15",
        "surface": "XAUUSD_M15",
        "sig_object_id": "XAUUSD_M15_EVENT_SESSION_RANGE_EXPANSION_CANDIDATE_LIKE_OBJECT_v1_0",
        "candidate_family": "event_session_range_expansion",
        "lifecycle": "PARKED_FOR_PORTFOLIO_BALANCE",
        "default_state_when_available": "PARKED_NOT_ACTIVE",
        "priority": "parked_display_context_only"
    },
    {
        "instrument": "EURUSD",
        "timeframe": "M15",
        "surface": "EURUSD_M15",
        "sig_object_id": "EURUSD_M15_LOW_VOL_COMPRESSION_FULL_DOMAIN_DisplayContract_v0_3",
        "candidate_family": "low_vol_compression_full_domain_display_contract",
        "lifecycle": "PARKED_DISPLAY_CONTRACT_CLOSED",
        "default_state_when_available": "PARKED_NOT_ACTIVE",
        "priority": "parked_display_context_only"
    },
    {
        "instrument": "USDJPY",
        "timeframe": "M15",
        "surface": "USDJPY_M15",
        "sig_object_id": "USDJPY_M15_ASIA_RANGE_NEUTRAL_FULL_ASIA_v1_0",
        "candidate_family": "asia_range_neutral_full_asia",
        "lifecycle": "PARKED_DIAGNOSTIC_COMPLETE_FOR_NOW",
        "default_state_when_available": "PARKED_NOT_ACTIVE",
        "priority": "parked_display_context_only"
    },
    {
        "instrument": "XAUUSD",
        "timeframe": "H1",
        "surface": "XAUUSD_H1",
        "sig_object_id": "XAU_H1_RISK_OFF_CANDIDATE_FLOW_CONTEXT_v1_0",
        "candidate_family": "risk_off_candidate_flow_context",
        "lifecycle": "SUPPORT_CONTEXT_ONLY",
        "default_state_when_available": "SUPPORT_CONTEXT_ONLY",
        "priority": "support_context_only"
    }
]

def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def flatten_strings(obj, limit=20000):
    out = []

    def walk(x):
        if len(out) > limit:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                out.append(str(k))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        else:
            out.append(str(x))

    walk(obj)
    return " ".join(out)

def read_provider_evidence():
    paths = [
        ROOT / "reports/staged_provider_fetch_report.json",
        Path("reports/staged_provider_fetch_report.json"),
        ROOT / "reports/staged_cache_update_report.json",
        Path("reports/staged_cache_update_report.json"),
        ROOT / "reports/candidate_detection_report.json",
        Path("reports/candidate_detection_report.json"),
        ROOT / "panel/panel_payload_current.json",
        Path("panel/panel_payload_current.json")
    ]

    evidence = []
    used = []

    for p in paths:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                evidence.append((str(p), data, flatten_strings(data)))
                used.append(str(p))
            except Exception as exc:
                evidence.append((str(p), {"_read_error": str(exc)}, ""))
                used.append(str(p))

    return evidence, used

def cache_file_candidates(instrument, timeframe):
    names = [
        f"{instrument}_{timeframe}.json",
        f"{instrument.lower()}_{timeframe.lower()}.json",
        f"{instrument}-{timeframe}.json",
        f"{instrument.lower()}-{timeframe.lower()}.json"
    ]

    bases = [
        ROOT / "data/provider_cache/twelve_data",
        Path("data/provider_cache/twelve_data"),
        ROOT / "cache/twelve_data",
        Path("cache/twelve_data"),
        ROOT / "outputs",
        Path("outputs")
    ]

    out = []
    for b in bases:
        for n in names:
            out.append(Path(b) / n)
    return out

def surface_available(obj, evidence):
    inst = obj["instrument"]
    tf = obj["timeframe"]
    surface = obj["surface"]

    for _, _, text in evidence:
        text_l = text.lower()
        if inst.lower() in text_l and (tf.lower() in text_l or surface.lower() in text_l):
            return True, "found_in_prv1_report_text"

    for p in cache_file_candidates(inst, tf):
        if p.exists():
            return True, f"cache_file_present:{p}"

    return False, "not_found_in_prv1_outputs"

def derive_freshness(available):
    if not available:
        return "UNAVAILABLE"
    return "AVAILABLE_TIMESTAMP_NOT_NORMALIZED_BY_RUNTIME1"

def build_card(obj, evidence):
    available, source_reason = surface_available(obj, evidence)
    state = obj["default_state_when_available"]

    blockers = []
    caveats = [
        "DISPLAY_ONLY_NOT_SIGNAL",
        "NO_BUY_SELL_HOLD",
        "NO_ENTRY_STOP_TARGET",
        "NO_BROKER_EXECUTION",
        "NO_SHADOW_ACTIVATION"
    ]

    if obj["lifecycle"].startswith("PARKED"):
        state = "PARKED_NOT_ACTIVE"

    elif obj["lifecycle"] == "SUPPORT_CONTEXT_ONLY":
        state = "SUPPORT_CONTEXT_ONLY"

    elif not available:
        state = "DATA_UNAVAILABLE_NO_SIGNAL"
        blockers.append("PRV1_LIVE_OR_CACHE_EVIDENCE_NOT_FOUND_FOR_SURFACE")

    elif obj["instrument"] == "USDJPY" and obj["timeframe"] == "H1":
        state = "DATA_QUALITY_CAVEATED_RESEARCH_ACTIVE"
        caveats.append("USDJPY_H1_DATA_QUALITY_CAVEAT_CARRIED_FORWARD")

    elif obj["instrument"] == "EURUSD" and obj["timeframe"] == "H1":
        state = "RESEARCH_ACTIVE_DISPLAY_ONLY"

    if obj["instrument"] == "XAUUSD" and obj["timeframe"] == "M15":
        caveats.append("XAU_M15_PARKED_AFTER_PORTFOLIO_REASSESSMENT")

    if "PARKED" in state:
        blockers.append("SIG_LIFECYCLE_PARKED_OR_COMPLETE_FOR_NOW")

    if state in {"RESEARCH_ACTIVE_DISPLAY_ONLY", "DATA_QUALITY_CAVEATED_RESEARCH_ACTIVE"}:
        caveats.append("RESEARCH_ACTIVE_DOES_NOT_MEAN_SIGNAL_AUTHORIZED")
        caveats.append("EVENT_AND_COST_CONTEXT_REMAIN_CAVEATED_UNLESS_RUNTIME_OUTPUT_PROVES_OTHERWISE")

    return {
        "instrument": obj["instrument"],
        "timeframe": obj["timeframe"],
        "surface": obj["surface"],
        "sig_object_id": obj["sig_object_id"],
        "candidate_family": obj["candidate_family"],
        "sig_lifecycle": obj["lifecycle"],
        "brain_state": state,
        "surface_evidence_available": available,
        "surface_evidence_reason": source_reason,
        "freshness_status": derive_freshness(available),
        "display_authority": "DISPLAY_ONLY_NOT_TRADE_SIGNAL",
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "forward_shadow_authorized": False,
        "action_surface_authorized": False,
        "blockers": blockers,
        "caveats": caveats
    }

def write_panel():
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PRV1 + SIG Brain Runtime</title>
  <style>
    body { margin:0; font-family: Arial, sans-serif; background:#0f172a; color:#e5e7eb; }
    .wrap { max-width: 820px; margin: 0 auto; padding: 18px; }
    .hero { padding: 18px; border-radius: 18px; background:#111827; border:1px solid #334155; }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; background:#1e293b; color:#93c5fd; font-size:12px; margin-bottom:10px; }
    .card { margin-top:14px; padding:14px; border-radius:16px; background:#020617; border:1px solid #334155; overflow:hidden; }
    .muted { color:#94a3b8; font-size:13px; }
    .state { font-weight:bold; color:#facc15; overflow-wrap:anywhere; }
    .danger { color:#fca5a5; }
    .ok { color:#86efac; }
    .grid { display:grid; grid-template-columns: 1fr; gap:8px; }
    .small { font-size:12px; }
    code { color:#c4b5fd; overflow-wrap:anywhere; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="badge">DYNAMIC DISPLAY ONLY / NOT SIGNAL</div>
      <h1>PRV1 + SIG Brain Runtime</h1>
      <p class="muted">Reads existing PRV1 live/cache/report evidence when available. No buy/sell/hold, no broker execution, no shadow activation.</p>
      <p class="muted" id="meta"></p>
    </div>

    <div id="cards"></div>

    <div class="card">
      <div class="danger">Forbidden interpretation:</div>
      <p class="muted">This panel is not a trading signal, not validation, not profitability evidence, and not broker-realistic guidance.</p>
    </div>
  </div>

  <script>
    async function main() {
      const res = await fetch('../../payloads/sig_brain_state_current.json?ts=' + Date.now());
      const data = await res.json();

      document.getElementById('meta').textContent =
        'Updated: ' + data.created_at_utc +
        ' | Evidence files: ' + (data.prv1_evidence_files || []).length;

      const root = document.getElementById('cards');

      root.innerHTML = data.cards.map(c => `
        <div class="card">
          <h2>${c.instrument} — ${c.timeframe}</h2>
          <div class="grid">
            <div>Brain State:<br><span class="state">${c.brain_state}</span></div>
            <div class="muted">Candidate Family: ${c.candidate_family}</div>
            <div class="muted">Surface Evidence:
              <span class="${c.surface_evidence_available ? 'ok' : 'danger'}">${c.surface_evidence_available}</span>
              — ${c.surface_evidence_reason}
            </div>
            <div class="muted">Freshness: ${c.freshness_status}</div>
            <div class="muted">Authority: ${c.display_authority}</div>
            <div class="muted small">Blockers: ${(c.blockers || []).join(', ') || 'none listed'}</div>
            <div class="muted small">Caveats: ${(c.caveats || []).join(', ')}</div>
          </div>
        </div>
      `).join('');
    }

    main().catch(err => {
      document.getElementById('cards').innerHTML =
        '<div class="card danger">Failed to load dynamic SIG Brain payload.</div>';
    });
  </script>
</body>
</html>"""

    (ROOT / "panel/sigbrain/index.html").write_text(html, encoding="utf-8")

def main():
    evidence, used_files = read_provider_evidence()
    cards = [build_card(o, evidence) for o in OBJECTS]

    payload = {
        "program": "SIG_BRAIN_RUNTIME1_DYNAMIC_DISPLAY_ONLY",
        "created_at_utc": now_utc(),
        "authority": "DISPLAY_ONLY_NOT_SIGNAL",
        "runtime_mode": "dynamic_from_existing_prv1_outputs_when_available",
        "prv1_evidence_files": used_files,
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "forward_shadow_authorized": False,
        "action_surface_authorized": False,
        "cards": cards
    }

    proof = {
        "status": "PASS",
        "program": "SIG_BRAIN_RUNTIME1_DYNAMIC_DISPLAY_ONLY",
        "created_at_utc": payload["created_at_utc"],
        "cards_checked": len(cards),
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "forward_shadow_authorized": False,
        "action_surface_authorized": False,
        "forbidden_state_count": 0,
        "prv1_evidence_file_count": len(used_files),
        "notes": [
            "Dynamic state is display-only.",
            "Missing live/cache evidence produces no-signal states, not static bullish/bearish claims.",
            "No buy/sell/hold, entry/stop/target, broker execution, or shadow activation is generated."
        ]
    }

    forbidden = {
        "BUY",
        "SELL",
        "HOLD",
        "ENTRY",
        "STOP",
        "TARGET",
        "BROKER_EXECUTION",
        "SIGNAL_AUTHORIZED"
    }

    for c in cards:
        if c.get("brain_state") in forbidden:
            proof["status"] = "FAIL"
            proof["forbidden_state_count"] += 1

    (ROOT / "payloads/sig_brain_state_current.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8"
    )

    (ROOT / "proofs/sig_brain_runtime1_proof.json").write_text(
        json.dumps(proof, indent=2),
        encoding="utf-8"
    )

    runtime_report = {
        "payload_summary": {
            "created_at_utc": payload["created_at_utc"],
            "cards": len(cards),
            "evidence_files": used_files
        },
        "card_states": [
            {
                "surface": c["surface"],
                "state": c["brain_state"],
                "evidence": c["surface_evidence_reason"]
            }
            for c in cards
        ],
        "proof": proof
    }

    (ROOT / "reports/sig_brain_runtime1_runtime_report.json").write_text(
        json.dumps(runtime_report, indent=2),
        encoding="utf-8"
    )

    write_panel()

    if proof["status"] != "PASS":
        raise SystemExit("SIG Brain Runtime1 proof failed")

if __name__ == "__main__":
    main()
