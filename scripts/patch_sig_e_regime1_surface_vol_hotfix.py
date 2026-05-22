import json
from pathlib import Path
from datetime import datetime

TARGET_FILES = [
    Path("runtime/sig_e/market_state_current.json"),
    Path("runtime/sig_e/sig_e_regime1_market_state_current.json"),
    Path("panel/brain4/sig_e_market_state_current.json"),
    Path("runtime/sig_brain/sig_brain5_derived_context_latest.json"),
    Path("inputs/sig_brain4_live_context_latest.json"),
]

OUT = Path("outputs/_sig_e_regime1_vol_hotfix/sig_e_regime1_surface_vol_hotfix_result.json")

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None

def normalize_vol(v):
    s = str(v or "").strip().upper()
    if not s:
        return None
    if s in {"LOW", "NORMAL", "HIGH", "SHOCK", "MIXED", "UNKNOWN"}:
        return s
    if "LOW" in s:
        return "LOW"
    if "HIGH" in s:
        return "HIGH"
    if "SHOCK" in s:
        return "SHOCK"
    if "NORMAL" in s:
        return "NORMAL"
    if "MIX" in s:
        return "MIXED"
    return s

def derive_vol_from_metrics(surface):
    metrics = surface.get("regime_metrics") if isinstance(surface, dict) else None
    if not isinstance(metrics, dict):
        return None, None
    ratio = metrics.get("h1_range_to_atr_proxy")
    try:
        ratio = float(ratio)
    except Exception:
        return None, None
    if ratio < 0.65:
        return "LOW", "DERIVED_FROM_H1_RANGE_TO_ATR_PROXY_NOT_D1_VOL"
    if ratio > 1.60:
        return "HIGH", "DERIVED_FROM_H1_RANGE_TO_ATR_PROXY_NOT_D1_VOL"
    return "NORMAL", "DERIVED_FROM_H1_RANGE_TO_ATR_PROXY_NOT_D1_VOL"

def patch_surface(surface):
    if not isinstance(surface, dict):
        return False, None

    before = json.dumps({
        "d1_vol_bucket": surface.get("d1_vol_bucket"),
        "volatility_state": surface.get("volatility_state"),
        "volatility_source_policy": surface.get("volatility_source_policy")
    }, sort_keys=True)

    existing = normalize_vol(first_nonempty(
        surface.get("d1_vol_bucket"),
        surface.get("d1_volatility_bucket"),
        surface.get("volatility_state")
    ))

    if existing:
        vol = existing
        source = "EXISTING_RUNTIME_FIELD"
    else:
        vol, source = derive_vol_from_metrics(surface)
        if not vol:
            vol = "UNKNOWN"
            source = "MISSING_SET_EXPLICIT_UNKNOWN"

    # Always make both names explicit so downstream detectors do not see blanks.
    surface["d1_vol_bucket"] = vol
    surface["volatility_state"] = vol
    surface["volatility_source_policy"] = source
    surface["volatility_runtime_caveat"] = (
        "D1 historical vol bucket was not directly available; UNKNOWN/proxy must not be treated as historical D1 LOW proof."
        if source != "EXISTING_RUNTIME_FIELD" else None
    )

    after = json.dumps({
        "d1_vol_bucket": surface.get("d1_vol_bucket"),
        "volatility_state": surface.get("volatility_state"),
        "volatility_source_policy": surface.get("volatility_source_policy")
    }, sort_keys=True)
    return before != after, source

def surface_lists(payload):
    refs = []
    if isinstance(payload, dict):
        if isinstance(payload.get("surfaces"), list):
            refs.append(payload["surfaces"])
        bc = payload.get("brain_context")
        if isinstance(bc, dict) and isinstance(bc.get("surfaces"), list):
            refs.append(bc["surfaces"])
    return refs

def main():
    result = {
        "program": "SIG-E-REGIME1-SURFACE-VOL-HOTFIX3",
        "created_utc": now(),
        "status": "PASS",
        "files": [],
        "boundary": [
            "CONTEXT_FIELD_PATCH_ONLY",
            "NO_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_RISK_OR_POSITION_SIZING",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION"
        ]
    }

    for path in TARGET_FILES:
        payload = load(path)
        item = {
            "path": str(path),
            "exists": path.exists(),
            "json_loaded": payload is not None,
            "surfaces_seen": 0,
            "surfaces_changed": 0,
            "source_counts": {}
        }

        if payload is None:
            result["files"].append(item)
            continue

        for lst in surface_lists(payload):
            for s in lst:
                item["surfaces_seen"] += 1
                changed, source = patch_surface(s)
                if source:
                    item["source_counts"][source] = item["source_counts"].get(source, 0) + 1
                if changed:
                    item["surfaces_changed"] += 1

        write(path, payload)
        result["files"].append(item)

    write(OUT, result)
    print("SIG_E_REGIME1_SURFACE_VOL_HOTFIX3_DONE")
    print("Result:", OUT)

if __name__ == "__main__":
    main()
