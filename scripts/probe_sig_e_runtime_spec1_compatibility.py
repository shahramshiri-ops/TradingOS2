import json
from pathlib import Path
from datetime import datetime

def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json_if_exists(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def flatten_keys(obj, prefix=""):
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f"{prefix}.{k}" if prefix else str(k)
            keys.add(nk)
            keys |= flatten_keys(v, nk)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:10]):
            keys |= flatten_keys(v, f"{prefix}[]")
    return keys

def contains_key_like(keys, token):
    t = token.lower()
    return any(t in k.lower() for k in keys)

def find_text_token(obj, token):
    t = str(token).lower()
    if isinstance(obj, dict):
        return any(find_text_token(v, token) for v in obj.values())
    if isinstance(obj, list):
        return any(find_text_token(v, token) for v in obj)
    return t in str(obj).lower()

def main():
    out_dir = Path("outputs/_sig_e_runtime_spec1")
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_path = Path("config/sig_e/runtime_specs/usdjpy_london_long_h1_m15_v1_0.json")
    spec = load_json_if_exists(spec_path) or {}

    candidate_sources = [
        Path("runtime/sig_e/market_state_current.json"),
        Path("runtime/sig_e/sig_e_regime1_market_state_current.json"),
        Path("panel/brain4/sig_e_market_state_current.json"),
        Path("runtime/sig_brain/sig_brain5_derived_context_latest.json"),
        Path("inputs/sig_brain4_live_context_latest.json"),
        Path("panel/brain4/sig_live_refresh_status_latest.json"),
    ]

    loaded = []
    all_keys = set()
    source_payloads = []
    for p in candidate_sources:
        data = load_json_if_exists(p)
        item = {
            "path": str(p),
            "exists": p.exists(),
            "json_loaded": data is not None
        }
        if data is not None:
            item["top_level_type"] = type(data).__name__
            item["key_count_sample"] = len(flatten_keys(data))
            all_keys |= flatten_keys(data)
            source_payloads.append(data)
        loaded.append(item)

    requirements = [
        {"id": "DATA_USDJPY_PRESENT", "check": lambda: any(find_text_token(x, "USDJPY") for x in source_payloads), "meaning": "USDJPY appears in live context payloads."},
        {"id": "H1_CONTEXT_PRESENT", "check": lambda: any(find_text_token(x, "H1") for x in source_payloads) or contains_key_like(all_keys, "h1"), "meaning": "H1 context appears in live payloads."},
        {"id": "M15_CONTEXT_PRESENT", "check": lambda: any(find_text_token(x, "M15") for x in source_payloads) or contains_key_like(all_keys, "m15"), "meaning": "M15 context appears in live payloads."},
        {"id": "SESSION_BUCKET_PRESENT", "check": lambda: contains_key_like(all_keys, "session_bucket") or contains_key_like(all_keys, "session"), "meaning": "Session bucket is available or computable."},
        {"id": "REGIME_ALIGNMENT_PRESENT", "check": lambda: contains_key_like(all_keys, "htf_alignment") or contains_key_like(all_keys, "d1") or contains_key_like(all_keys, "h4"), "meaning": "D1/H4 regime fields are available or partly computable."},
        {"id": "OHLC_PRESENT", "check": lambda: all(contains_key_like(all_keys, k) for k in ["open", "high", "low", "close"]), "meaning": "OHLC fields are available in at least one source."},
        {"id": "BOUNDARY_PRESENT", "check": lambda: True, "meaning": "Spec hardcodes non-authority boundary."},
    ]

    checks = []
    for r in requirements:
        try:
            ok = bool(r["check"]())
        except Exception:
            ok = False
        checks.append({
            "requirement_id": r["id"],
            "status": "PASS" if ok else "MISSING_OR_CAVEATED",
            "meaning": r["meaning"]
        })

    missing = [c for c in checks if c["status"] != "PASS"]
    if not missing:
        compatibility_status = "SPEC_COMPATIBLE_READY_FOR_SHADOW_DETECTOR_DRAFT"
    elif len(missing) <= 2:
        compatibility_status = "SPEC_COMPATIBLE_WITH_FIELD_CAVEATS"
    else:
        compatibility_status = "SPEC_BLOCKED_MISSING_RUNTIME_FIELDS"

    result = {
        "program": "SIG-E-RUNTIME-SPEC1",
        "created_utc": utc_now(),
        "spec_id": spec.get("spec_id"),
        "compatibility_status": compatibility_status,
        "checks": checks,
        "source_files": loaded,
        "observed_key_sample": sorted(all_keys)[:300],
        "next_allowed_use": "SHADOW_DETECTOR_DRAFT_ONLY_IF_REVIEW_ACCEPTS" if compatibility_status != "SPEC_BLOCKED_MISSING_RUNTIME_FIELDS" else "REPAIR_RUNTIME_FIELDS_FIRST",
        "current_runtime_authority": {
            "signal_authorized": False,
            "trade_proposal_authorized": False,
            "entry_stop_target_authorized": False,
            "risk_sizing_authorized": False,
            "broker_execution_authorized": False
        }
    }

    runtime_out = Path("runtime/sig_e/spec_compatibility_usdjpy_london_long_current.json")
    panel_out = Path("panel/brain4/sig_e_runtime_spec_status_current.json")
    runtime_out.parent.mkdir(parents=True, exist_ok=True)
    panel_out.parent.mkdir(parents=True, exist_ok=True)
    runtime_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    panel_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "sig_e_runtime_spec1_compatibility_probe_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("SIG_E_RUNTIME_SPEC1_COMPATIBILITY_PROBE_DONE")
    print("COMPATIBILITY_STATUS=" + compatibility_status)
    print("Runtime out:", runtime_out)
    print("Panel out:", panel_out)

if __name__ == "__main__":
    main()
