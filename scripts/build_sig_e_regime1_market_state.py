#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIG-E-REGIME1 market state / regime runtime builder.

Builds a canonical market-state layer for Target Architecture E from existing
read-only Brain5 live context surfaces. This is context only.

Boundary: NOT_SIGNAL / NO_TRADE_PROPOSAL / NO_ENTRY_STOP_TARGET / NO_BROKER_EXECUTION.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import json

ROOT = Path.cwd()
TAXONOMY_PATH = ROOT / "config" / "sig_e" / "regime_taxonomy_v1_0.json"
INPUT_CANDIDATES = [
    ROOT / "runtime" / "sig_brain" / "sig_brain5_derived_context_latest.json",
    ROOT / "inputs" / "sig_brain4_live_context_latest.json",
]
REFRESH_STATUS = ROOT / "panel" / "brain4" / "sig_live_refresh_status_latest.json"
OUT_RUNTIME = ROOT / "runtime" / "sig_e" / "market_state_current.json"
OUT_RUNTIME_ALIAS = ROOT / "runtime" / "sig_e" / "sig_e_regime1_market_state_current.json"
OUT_PANEL = ROOT / "panel" / "brain4" / "sig_e_market_state_current.json"
OUT_DIR = ROOT / "outputs" / "_sig_e_regime1"
OUT_BUILD = OUT_DIR / "sig_e_regime1_build_result.json"

BOUNDARY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_or_position_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
    "manual_review_required_for_future_trade_plan": True,
}

TF_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm_dir(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    s = str(value).strip().upper()
    mapping = {
        "BULLISH": "UP",
        "BEARISH": "DOWN",
        "UP": "UP",
        "DOWN": "DOWN",
        "LONG": "UP",
        "SHORT": "DOWN",
        "FLAT": "NEUTRAL",
        "NEUTRAL": "NEUTRAL",
        "RANGE": "NEUTRAL",
        "RANGING": "NEUTRAL",
        "MIXED": "MIXED",
        "CONFLICT": "MIXED",
        "NONE": "UNKNOWN",
        "UNKNOWN": "UNKNOWN",
        "": "UNKNOWN",
    }
    return mapping.get(s, s if s in {"UP", "DOWN", "NEUTRAL", "MIXED", "UNKNOWN"} else "UNKNOWN")


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_close_ts(open_ts: Any, timeframe: str) -> Optional[str]:
    dt = parse_ts(open_ts)
    mins = TF_MINUTES.get(str(timeframe).upper())
    if not dt or not mins:
        return None
    return iso(dt + timedelta(minutes=mins))


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"true", "1", "yes", "y", "active", "pass"}


def first_present(surface: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in surface and surface[k] not in (None, ""):
            return surface[k]
    return None


def load_context() -> Tuple[Path, Dict[str, Any]]:
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path, read_json(path)
    raise SystemExit("No Brain5 live context found. Expected one of: " + ", ".join(p.as_posix() for p in INPUT_CANDIDATES))


def load_taxonomy() -> Dict[str, Any]:
    if TAXONOMY_PATH.exists():
        return read_json(TAXONOMY_PATH)
    return {"mechanical_thresholds": {}}


def compute_dirs(surface: Dict[str, Any]) -> Dict[str, str]:
    timeframe = str(surface.get("timeframe", "UNKNOWN")).upper()
    h1_dir = norm_dir(first_present(surface, ["h1_dir", "h1_trend_state", "h1_trend_safe", "h1_bar_direction"]))
    h4_dir = norm_dir(first_present(surface, ["h4_dir", "h4_trend_safe", "h4_trend_state"]))
    d1_dir = norm_dir(first_present(surface, ["d1_dir", "d1_trend_safe", "d1_trend_state"]))
    m15_dir = norm_dir(first_present(surface, ["m15_dir", "m15_bar_direction"]))
    current_dir = norm_dir(first_present(surface, ["directional_side", "h1_bar_direction", "m15_dir", "h1_dir"]))
    if current_dir == "UNKNOWN":
        current_dir = h1_dir if timeframe == "H1" else m15_dir
    return {"d1": d1_dir, "h4": h4_dir, "h1": h1_dir, "m15": m15_dir, "current": current_dir}


def derive_htf_alignment(dirs: Dict[str, str], timeframe: str) -> str:
    d1, h4, h1, m15 = dirs["d1"], dirs["h4"], dirs["h1"], dirs["m15"]
    if d1 == h4 == h1 == "UP":
        return "D1_H4_H1_ALIGNED_UP"
    if d1 == h4 == h1 == "DOWN":
        return "D1_H4_H1_ALIGNED_DOWN"
    if h4 == h1 == "UP":
        return "H4_H1_ALIGNED_UP"
    if h4 == h1 == "DOWN":
        return "H4_H1_ALIGNED_DOWN"
    if timeframe == "M15" and m15 in {"UP", "DOWN"} and h1 in {"UP", "DOWN"} and m15 != h1:
        return "M15_H1_CONFLICT"
    if h4 in {"UP", "DOWN"} and h1 in {"UP", "DOWN"} and h4 != h1:
        return "H4_H1_CONFLICT"
    if d1 in {"UP", "DOWN"} and h4 in {"UP", "DOWN"} and d1 != h4:
        return "D1_H4_CONFLICT"
    if "UNKNOWN" in {d1, h4, h1}:
        return "UNKNOWN"
    return "CONFLICT"


def derive_trend_state(dirs: Dict[str, str], htf_alignment: str, surface: Dict[str, Any]) -> str:
    if htf_alignment.endswith("ALIGNED_UP"):
        return "UP"
    if htf_alignment.endswith("ALIGNED_DOWN"):
        return "DOWN"
    conflict_sev = str(surface.get("conflict_severity", "")).upper()
    if conflict_sev in {"HIGH", "MEDIUM"} or "CONFLICT" in htf_alignment:
        return "MIXED"
    cur = dirs.get("current", "UNKNOWN")
    if cur in {"UP", "DOWN"}:
        return cur
    if dirs.get("h4") in {"UP", "DOWN"}:
        return dirs["h4"]
    return "UNKNOWN" if cur == "UNKNOWN" else cur


def derive_volatility_and_range(surface: Dict[str, Any], taxonomy: Dict[str, Any], trend_state: str, htf_alignment: str) -> Tuple[str, str, Dict[str, Any]]:
    th = taxonomy.get("mechanical_thresholds", {}) if isinstance(taxonomy, dict) else {}
    m15_low = float(th.get("m15_range_ratio_low_max", 0.65))
    m15_high = float(th.get("m15_range_ratio_high_min", 1.35))
    h1_low = float(th.get("h1_range_to_atr_low_max", 0.55))
    h1_high = float(th.get("h1_range_to_atr_high_min", 1.35))
    h1_shock = float(th.get("h1_range_to_atr_shock_min", 2.50))

    metrics: Dict[str, Any] = {}
    volatility = "UNKNOWN"
    range_state = "UNKNOWN"

    if truthy(surface.get("alignment_absent_chop")):
        range_state = "CHOP"
        volatility = "LOW" if surface.get("m15_range_ratio_12") is not None else "NORMAL"

    ratio = None
    try:
        ratio = float(surface.get("m15_range_ratio_12")) if surface.get("m15_range_ratio_12") is not None else None
    except Exception:
        ratio = None
    if ratio is not None:
        metrics["m15_range_ratio_12"] = ratio
        if ratio <= m15_low:
            volatility = "LOW"
            range_state = "COMPRESSION" if range_state == "UNKNOWN" else range_state
        elif ratio >= m15_high:
            volatility = "HIGH"
            range_state = "EXPANSION"
        else:
            volatility = "NORMAL" if volatility == "UNKNOWN" else volatility

    h1_range = surface.get("current_h1_range")
    h1_atr = surface.get("h1_atr20") or surface.get("d1_atr20_safe")
    try:
        if h1_range is not None and h1_atr not in (None, 0, "0"):
            r = abs(float(h1_range)) / abs(float(h1_atr))
            metrics["h1_range_to_atr_proxy"] = r
            if r >= h1_shock:
                volatility = "SHOCK"
                range_state = "EXPANSION"
            elif r >= h1_high:
                volatility = "HIGH"
                range_state = "EXPANSION"
            elif r <= h1_low:
                volatility = "LOW"
                range_state = "COMPRESSION" if range_state == "UNKNOWN" else range_state
            elif volatility == "UNKNOWN":
                volatility = "NORMAL"
    except Exception:
        pass

    if truthy(surface.get("current_h1_expansion_flag")) and truthy(surface.get("last4_h1_contraction_flag")):
        range_state = "EXPANSION_AFTER_COMPRESSION"
        if volatility == "UNKNOWN":
            volatility = "HIGH"
    elif truthy(surface.get("current_h1_expansion_flag")):
        range_state = "EXPANSION"
        if volatility == "UNKNOWN":
            volatility = "HIGH"
    elif truthy(surface.get("last4_h1_contraction_flag")) and range_state == "UNKNOWN":
        range_state = "COMPRESSION"
        if volatility == "UNKNOWN":
            volatility = "LOW"

    if range_state == "UNKNOWN":
        if trend_state in {"UP", "DOWN"} and "ALIGNED" in htf_alignment:
            range_state = "TRENDING"
        elif trend_state == "MIXED" or "CONFLICT" in htf_alignment:
            range_state = "MIXED"
        else:
            range_state = "RANGING"

    if volatility == "UNKNOWN":
        volatility = "NORMAL" if range_state not in {"UNKNOWN"} else "UNKNOWN"
    return volatility, range_state, metrics


def derive_liquidity(surface: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    failed = str(surface.get("failed_breakout_event_type", "")).upper()
    if failed and failed not in {"NONE", "UNKNOWN", "NULL"}:
        tags.append("FAILED_BREAKOUT_ACTIVE")
    session_break = str(surface.get("session_reference_break_event_type", "")).upper()
    if session_break and session_break not in {"NONE", "UNKNOWN", "NULL"}:
        tags.append("SESSION_REFERENCE_BREAK_ACTIVE")
    if truthy(surface.get("asian_high_swept_and_reclaimed_by_closed_h1")):
        tags.append("ASIAN_HIGH_SWEEP_RECLAIM_ACTIVE")
    if truthy(surface.get("asian_high_breakout_continuation_by_closed_h1")):
        tags.append("ASIAN_HIGH_BREAKOUT_CONTINUATION_ACTIVE")
    if truthy(surface.get("london_low_swept_and_reclaimed_by_closed_h1")):
        tags.append("LONDON_LOW_SWEEP_RECLAIM_ACTIVE")
    weekly = str(surface.get("weekly_open_reclaim_short_state", "")).upper()
    if weekly and weekly not in {"NONE", "UNKNOWN", "NULL"}:
        tags.append("WEEKLY_OPEN_RECLAIM_SHORT_ACTIVE")
    if truthy(surface.get("upside_sweep_flag")):
        tags.append("UPSIDE_SWEEP_ACTIVE")
    if truthy(surface.get("sweep_then_reject_back_inside_up_flag")):
        tags.append("UPSIDE_SWEEP_REJECT_ACTIVE")
    return tags or ["NONE"]


def derive_setup_hints(range_state: str, trend_state: str, htf_alignment: str, liquidity_tags: List[str]) -> List[str]:
    hints: List[str] = []
    if range_state in {"TRENDING", "EXPANSION", "EXPANSION_AFTER_COMPRESSION"} and trend_state in {"UP", "DOWN"} and "ALIGNED" in htf_alignment:
        hints.append("PULLBACK_CONTINUATION_CONTEXT_SUPPORTED")
    if range_state in {"RANGING", "CHOP", "MIXED"} or any(t in liquidity_tags for t in ["FAILED_BREAKOUT_ACTIVE", "LONDON_LOW_SWEEP_RECLAIM_ACTIVE", "ASIAN_HIGH_SWEEP_RECLAIM_ACTIVE"]):
        hints.append("FAILED_BREAKOUT_REVERSAL_CONTEXT_SUPPORTED")
    if any("SWEEP" in t or "RECLAIM" in t for t in liquidity_tags):
        hints.append("SWEEP_RECLAIM_CONTEXT_SUPPORTED")
    if range_state in {"EXPANSION", "EXPANSION_AFTER_COMPRESSION"}:
        hints.append("VOLATILITY_EXPANSION_CONTEXT_SUPPORTED")
    if range_state == "CHOP" or "CONFLICT" in htf_alignment:
        hints.append("CHOP_AVOID_TREND_FOLLOWING_CONTEXT")
    return hints or ["INSUFFICIENT_CONTEXT"]


def derive_tradeability(data_status: str, volatility_state: str, trend_state: str, range_state: str, htf_alignment: str) -> str:
    if str(data_status).upper() not in {"OK", "PASS", "SUFFICIENT", "AVAILABLE"}:
        return "DATA_INSUFFICIENT"
    if volatility_state == "SHOCK":
        return "REGIME_BLOCKED"
    if trend_state == "UNKNOWN" or range_state == "UNKNOWN":
        return "UNKNOWN"
    if "CONFLICT" in htf_alignment or trend_state == "MIXED" or range_state in {"MIXED", "CHOP"}:
        return "REGIME_MIXED"
    return "REGIME_SUPPORTIVE"


def build_surface(surface: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    instrument = str(surface.get("instrument", "UNKNOWN")).upper()
    timeframe = str(surface.get("timeframe", surface.get("base_timeframe", "UNKNOWN"))).upper()
    open_ts = first_present(surface, ["latest_bar_open_ts_utc", "latest_h1_bar_open_ts_utc", "bar_open_ts_utc"])
    session = surface.get("session_bucket", "UNKNOWN")
    data_status = str(surface.get("data_sufficiency_status", "UNKNOWN")).upper()
    dirs = compute_dirs(surface)
    htf_alignment = derive_htf_alignment(dirs, timeframe)
    trend_state = derive_trend_state(dirs, htf_alignment, surface)
    volatility_state, range_state, metrics = derive_volatility_and_range(surface, taxonomy, trend_state, htf_alignment)
    liquidity_tags = derive_liquidity(surface)
    setup_hints = derive_setup_hints(range_state, trend_state, htf_alignment, liquidity_tags)
    tradeability = derive_tradeability(data_status, volatility_state, trend_state, range_state, htf_alignment)

    explanation = []
    explanation.append(f"trend={trend_state}; range={range_state}; volatility={volatility_state}; alignment={htf_alignment}")
    if liquidity_tags != ["NONE"]:
        explanation.append("liquidity=" + ",".join(liquidity_tags))
    if tradeability != "REGIME_SUPPORTIVE":
        explanation.append(f"tradeability_context={tradeability}; this is not a trade veto by itself, only regime context")

    return {
        "surface_id": f"{instrument}_{timeframe}_{open_ts or 'UNKNOWN_TS'}",
        "instrument": instrument,
        "timeframe": timeframe,
        "bar_open_ts_utc": open_ts,
        "bar_close_ts_utc": add_close_ts(open_ts, timeframe),
        "session_bucket": session,
        "data_sufficiency_status": data_status,
        "context_builder_status": surface.get("context_builder_status", "UNKNOWN"),
        "direction_inputs": dirs,
        "trend_state": trend_state,
        "range_state": range_state,
        "volatility_state": volatility_state,
        "htf_alignment": htf_alignment,
        "liquidity_context": {
            "tags": liquidity_tags,
            "raw_reference_fields": {
                "failed_breakout_event_type": surface.get("failed_breakout_event_type"),
                "session_reference_break_event_type": surface.get("session_reference_break_event_type"),
                "weekly_open_reclaim_short_state": surface.get("weekly_open_reclaim_short_state"),
                "sweep_reference_type_up": surface.get("sweep_reference_type_up"),
            },
        },
        "tradeability_context": tradeability,
        "setup_relevance_hints": setup_hints,
        "regime_metrics": metrics,
        "regime_explanation": " | ".join(explanation),
        "authority": "SIG-E-REGIME1|MARKET_STATE_CONTEXT_ONLY|CURRENT_RUNTIME_NOT_SIGNAL|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION",
        "boundary": dict(BOUNDARY),
    }


def main() -> None:
    taxonomy = load_taxonomy()
    input_path, context = load_context()
    surfaces_raw = context.get("surfaces", []) if isinstance(context, dict) else []
    if not isinstance(surfaces_raw, list):
        raise SystemExit("Brain5 context surfaces is not a list")
    surfaces = [build_surface(s, taxonomy) for s in surfaces_raw if isinstance(s, dict)]

    by_tradeability = Counter(s["tradeability_context"] for s in surfaces)
    by_timeframe = Counter(s["timeframe"] for s in surfaces)
    by_instrument = Counter(s["instrument"] for s in surfaces)
    by_trend = Counter(s["trend_state"] for s in surfaces)
    by_range = Counter(s["range_state"] for s in surfaces)
    by_vol = Counter(s["volatility_state"] for s in surfaces)

    refresh_status_summary = None
    if REFRESH_STATUS.exists():
        try:
            rs = read_json(REFRESH_STATUS)
            refresh_status_summary = {
                "created_utc": rs.get("created_utc"),
                "last_successful_refresh_utc": rs.get("last_successful_refresh_utc"),
                "provider_max_latest_bar_open_ts_utc": (rs.get("provider_m5") or {}).get("max_latest_bar_open_ts_utc"),
                "lag_reason_code": (rs.get("lag_diagnostic") or {}).get("lag_reason_code"),
            }
        except Exception as exc:
            refresh_status_summary = {"read_error": str(exc)}

    payload = {
        "status_version": "SIG_E_REGIME1_MARKET_STATE_v1_0",
        "created_utc": now_utc(),
        "program": "SIG-E-REGIME1",
        "target_architecture": "E_MANUAL_SEMI_AUTOMATED_TRADING_DECISION_SYSTEM",
        "current_runtime_posture": "MARKET_STATE_CONTEXT_ONLY_CURRENT_RUNTIME_NOT_SIGNAL",
        "authority": "SIG-E-REGIME1|MARKET_STATE_CONTEXT_ONLY|NOT_SIGNAL|NO_TRADE_PROPOSAL|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION",
        "source_files": {
            "brain5_context": input_path.as_posix(),
            "refresh_status": REFRESH_STATUS.as_posix() if REFRESH_STATUS.exists() else None,
            "taxonomy": TAXONOMY_PATH.as_posix() if TAXONOMY_PATH.exists() else None,
        },
        "source_context": {
            "context_version": context.get("context_version") if isinstance(context, dict) else None,
            "context_created_utc": context.get("created_utc") if isinstance(context, dict) else None,
            "source_authority": context.get("source_authority") if isinstance(context, dict) else None,
            "refresh_status_summary": refresh_status_summary,
        },
        "summary": {
            "surface_count": len(surfaces),
            "by_instrument": dict(sorted(by_instrument.items())),
            "by_timeframe": dict(sorted(by_timeframe.items())),
            "by_tradeability_context": dict(sorted(by_tradeability.items())),
            "by_trend_state": dict(sorted(by_trend.items())),
            "by_range_state": dict(sorted(by_range.items())),
            "by_volatility_state": dict(sorted(by_vol.items())),
            "signal_authorized": False,
            "trade_plan_authorized": False,
        },
        "surfaces": surfaces,
        "boundary": dict(BOUNDARY),
        "notes": [
            "This payload standardizes current market regime/state for later SIG-E setup/trigger/blocker layers.",
            "It is not a signal candidate and does not authorize entry, stop, target, position sizing, broker connection, or execution.",
            "REGIME1 may be consumed by future SETUP1, but setup/signal/trade-plan gates remain inactive until separate patches."
        ],
    }

    write_json(OUT_RUNTIME, payload)
    write_json(OUT_RUNTIME_ALIAS, payload)
    write_json(OUT_PANEL, payload)

    result = {
        "status": "PASS",
        "created_utc": payload["created_utc"],
        "program": "SIG-E-REGIME1",
        "input_file": input_path.as_posix(),
        "surface_count": len(surfaces),
        "outputs": [OUT_RUNTIME.as_posix(), OUT_RUNTIME_ALIAS.as_posix(), OUT_PANEL.as_posix()],
        "boundary": dict(BOUNDARY),
    }
    write_json(OUT_BUILD, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
