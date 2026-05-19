#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AUTHORITY = "SIG_BRAIN5_UPSTREAM_CONTEXT_BUILDER|READ_ONLY_DERIVED_CONTEXT|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"
ACTIVE_SESSIONS = ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]
PRIOR48_POLICY_UP = "PRIOR48_LEGACY_RESEARCH_192_MIN96_CLOSED_v1_0"
FAILED_BREAKOUT_POLICY = "PRIOR_DAY_LOW_CLOSED_D1_v1_0"
SESSION_REF_POLICY = "LONDON_MORNING_RANGE_0700_1159_CLOSED_H1_v1_0"
TARGETED_LONDON_LOW_POLICY = "SIG_MTF_DIR_W16_TARGETED_EURUSD_H1_FAILED_BREAKOUT_SESSION_SWEEP_v1_0"
STRICT_LONDON_LOW_RECLAIM_POLICY = "SIG_MTF_DIR_OVERLAP_LONDON_LOW_SWEEP_RECLAIM_D1UP_H4UP_H1_v1_0"

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_ts(x: str) -> dt.datetime:
    return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(dt.timezone.utc)

def session_bucket(ts: dt.datetime) -> str:
    h = ts.hour
    if h < 7:
        return "ASIA"
    if h < 12:
        return "LONDON"
    if h < 16:
        return "LONDON_NY_OVERLAP"
    if h < 21:
        return "NEW_YORK"
    return "ROLLOVER_THIN"

def find_surface(raw: Dict[str, Any], instrument: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
    for s in raw.get("surfaces", []):
        if str(s.get("instrument", "")).upper() == instrument.upper() and str(s.get("timeframe", "")).upper() == timeframe.upper():
            return sorted(s.get("bars", []), key=lambda b: b.get("bar_open_ts_utc", ""))
    return None

def fnum(x: Any) -> float:
    return float(x)

def latest(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    return bars[-1]

def closes(bars: List[Dict[str, Any]]) -> List[float]:
    return [fnum(b["close"]) for b in bars]

def change_pct(vals: List[float], periods: int) -> Optional[float]:
    if len(vals) <= periods or vals[-1 - periods] == 0:
        return None
    return (vals[-1] / vals[-1 - periods] - 1.0) * 100.0

def dir_from_change(chg: Optional[float], threshold: float) -> str:
    if chg is None:
        return "UNKNOWN"
    if chg > threshold:
        return "UP"
    if chg < -threshold:
        return "DOWN"
    return "FLAT"

def aggregate_h4_from_h1(h1_bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for b in h1_bars:
        ts = parse_ts(b["bar_open_ts_utc"])
        kts = ts.replace(hour=(ts.hour // 4) * 4, minute=0, second=0, microsecond=0)
        key = kts.isoformat().replace("+00:00", "Z")
        buckets.setdefault(key, []).append(b)
    out = []
    for key, rows in sorted(buckets.items()):
        rows = sorted(rows, key=lambda b: b["bar_open_ts_utc"])
        out.append({
            "bar_open_ts_utc": key,
            "open": rows[0]["open"],
            "high": max(fnum(r["high"]) for r in rows),
            "low": min(fnum(r["low"]) for r in rows),
            "close": rows[-1]["close"],
        })
    return out

def h1_dir(h1: List[Dict[str, Any]]) -> str:
    return dir_from_change(change_pct(closes(h1), 3), 0.04)

def h4_dir_from_h1(h1: List[Dict[str, Any]]) -> str:
    return dir_from_change(change_pct(closes(aggregate_h4_from_h1(h1)), 3), 0.08)

def h4_trend_state(h4: List[Dict[str, Any]]) -> str:
    # Forward-only, closed H4 bars only. Conservative threshold for runtime context.
    return dir_from_change(change_pct(closes(h4), 3), 0.08)

def d1_trend_state(d1: List[Dict[str, Any]]) -> str:
    # Forward-only, closed D1 bars only. D1 is slow; use 3-day change.
    return dir_from_change(change_pct(closes(d1), 3), 0.10)

def m15_dir(m15: List[Dict[str, Any]]) -> str:
    return dir_from_change(change_pct(closes(m15), 4), 0.03)

def range_ratio_12(m15: List[Dict[str, Any]]) -> Optional[float]:
    if len(m15) < 5:
        return None
    rngs = [fnum(b["high"]) - fnum(b["low"]) for b in m15]
    avg = sum(rngs[-12:]) / len(rngs[-12:])
    return None if avg == 0 else rngs[-1] / avg

def stack_conflict_severity(h1d: str, h4d: str, m15d: str) -> str:
    vals = [h1d, h4d, m15d]
    if "UNKNOWN" in vals:
        return "UNKNOWN"
    if "UP" in vals and "DOWN" in vals:
        return "HIGH"
    if vals.count("FLAT") >= 2:
        return "LOW"
    if h1d == h4d and h1d in ("UP", "DOWN"):
        return "NONE"
    return "MEDIUM"

def high_for_date(m15: List[Dict[str, Any]], day: dt.date, hours) -> Optional[float]:
    rows = [b for b in m15 if parse_ts(b["bar_open_ts_utc"]).date() == day and parse_ts(b["bar_open_ts_utc"]).hour in hours]
    return max((fnum(b["high"]) for b in rows), default=None)

def prior_48_high(m15: List[Dict[str, Any]]) -> Optional[float]:
    prior = m15[-49:-1] if len(m15) >= 49 else m15[:-1]
    return max((fnum(b["high"]) for b in prior), default=None)

def previous_day_high(m15: List[Dict[str, Any]], day: dt.date) -> Optional[float]:
    rows = [b for b in m15 if parse_ts(b["bar_open_ts_utc"]).date() == day - dt.timedelta(days=1)]
    return max((fnum(b["high"]) for b in rows), default=None)

def previous_closed_d1_low(d1: List[Dict[str, Any]], eval_ts: dt.datetime) -> Optional[float]:
    rows = [b for b in d1 if parse_ts(b["bar_open_ts_utc"]).date() < eval_ts.date()]
    if not rows:
        return None
    return fnum(rows[-1]["low"])

def london_morning_low_closed_h1(h1: List[Dict[str, Any]], eval_ts: dt.datetime) -> Optional[float]:
    # 07:00-11:59 UTC completed H1 bars only, same UTC day, never including current/incomplete bar.
    rows = []
    for b in h1:
        ts = parse_ts(b["bar_open_ts_utc"])
        if ts.date() == eval_ts.date() and 7 <= ts.hour <= 11 and ts < eval_ts:
            rows.append(b)
    return min((fnum(b["low"]) for b in rows), default=None)


def london_morning_range_closed_h1(h1: List[Dict[str, Any]], eval_ts: dt.datetime) -> Dict[str, Any]:
    """Same-UTC-date London H1 range, using only closed 07:00-11:59 UTC H1 bars.

    This is a read-only reference-range helper for caveated memory matching. It
    never uses the current/incomplete bar and never creates a trade signal.
    """
    rows = []
    for b in h1:
        ts = parse_ts(b["bar_open_ts_utc"])
        if ts.date() == eval_ts.date() and 7 <= ts.hour <= 11 and ts < eval_ts:
            rows.append(b)
    if not rows:
        return {"available": False, "low": None, "high": None, "bar_count": 0}
    return {
        "available": len(rows) >= 4,
        "low": min(fnum(b["low"]) for b in rows),
        "high": max(fnum(b["high"]) for b in rows),
        "bar_count": len(rows),
    }

def h1_atr20_prior_closed(h1: List[Dict[str, Any]]) -> Optional[float]:
    """20-period H1 ATR from bars before the latest trigger bar.

    Excludes the latest H1 bar so the sweep/reclaim trigger bar does not alter
    its own threshold. This is a diagnostic/runtime context field only.
    """
    if len(h1) < 22:
        return None
    prior = h1[:-1]
    trs = []
    prev_close = None
    for b in prior:
        high, low, close = fnum(b["high"]), fnum(b["low"]), fnum(b["close"])
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    if len(trs) < 20:
        return None
    return sum(trs[-20:]) / 20.0

def evaluate_strict_london_low_sweep_reclaim(h1: List[Dict[str, Any]]) -> Dict[str, Any]:
    """OPS17 strict London-low sweep/reclaim fields for EURUSD H1 overlap memory.

    Event rule: same-day closed London H1 range exists; latest closed H1 low <=
    london_session_low - 0.10 * prior H1 ATR20, and latest closed H1 close >
    london_session_low. Display-only context; not a signal.
    """
    lb = latest(h1)
    ts = parse_ts(lb["bar_open_ts_utc"])
    london = london_morning_range_closed_h1(h1, ts)
    atr = h1_atr20_prior_closed(h1)
    low, close = fnum(lb["low"]), fnum(lb["close"])
    available = bool(london["available"] and atr is not None)
    swept_reclaimed = None
    if available:
        swept_reclaimed = bool(low <= london["low"] - 0.10 * atr and close > london["low"])
    return {
        "base_timeframe": "H1",
        "same_utc_date_london_range_available": bool(london["available"]),
        "london_session_low": london["low"],
        "london_session_high": london["high"],
        "london_session_bar_count": london["bar_count"],
        "h1_quality_tier": "HIGH" if len(h1) >= 24 and atr is not None else "LIMITED",
        "h1_atr20": atr,
        "h1_low": low,
        "h1_close": close,
        "london_low_swept_and_reclaimed_by_closed_h1": swept_reclaimed,
        "strict_london_low_reclaim_policy_id": STRICT_LONDON_LOW_RECLAIM_POLICY,
    }

def prior_window_high_closed(m15: List[Dict[str, Any]], window_bars: int = 192, min_bars: int = 96) -> Tuple[Optional[float], Dict[str, Any]]:
    prior = m15[:-1]
    available = len(prior)
    if available < min_bars:
        return None, {"reference_available": False, "prior_bars_available": available, "required_min_bars": min_bars, "window_bars": window_bars, "policy": PRIOR48_POLICY_UP, "insufficiency_reason": "INSUFFICIENT_PRIOR_CLOSED_M15_BARS_FOR_PRIOR48_POLICY"}
    win = prior[-window_bars:]
    return max((fnum(b["high"]) for b in win), default=None), {"reference_available": True, "prior_bars_available": available, "bars_used": len(win), "required_min_bars": min_bars, "window_bars": window_bars, "policy": PRIOR48_POLICY_UP}

def evaluate_usdjpy_prior48_upside_sweep_reject(m15: List[Dict[str, Any]], tolerance_multiplier: float) -> Dict[str, Any]:
    lb = latest(m15)
    high, close, low, open_ = fnum(lb["high"]), fnum(lb["close"]), fnum(lb["low"]), fnum(lb["open"])
    rng = high - low
    close_loc = (close - low) / rng if rng else None
    upper_wick = (high - max(open_, close)) / rng if rng else None
    tol = abs(close) * tolerance_multiplier
    ref, meta = prior_window_high_closed(m15, window_bars=192, min_bars=96)
    if ref is None:
        return {"upside_sweep_flag": None, "sweep_then_reject_back_inside_up_flag": None, "sweep_reference_type_up": "UNKNOWN", "sweep_reference_policy_up": PRIOR48_POLICY_UP, "sweep_reference_value_up": None, "sweep_reference_meta_up": meta, "data_sufficiency_status": "MISSING_REQUIRED_BARS"}
    upside = high > ref + tol
    reject = bool(upside and close <= ref and ((upper_wick is not None and upper_wick >= 0.45) or (close_loc is not None and close_loc <= 0.50)))
    return {"upside_sweep_flag": bool(upside), "sweep_then_reject_back_inside_up_flag": reject, "sweep_reference_type_up": "PRIOR48" if upside else "NONE", "sweep_reference_policy_up": PRIOR48_POLICY_UP, "sweep_reference_value_up": ref, "sweep_reference_meta_up": meta, "data_sufficiency_status": "OK"}

def evaluate_failed_breakout_prior_day_low(h1: List[Dict[str, Any]], d1: List[Dict[str, Any]]) -> Dict[str, Any]:
    lb = latest(h1)
    ts = parse_ts(lb["bar_open_ts_utc"])
    ref = previous_closed_d1_low(d1, ts)
    if ref is None:
        return {"failed_breakout_event_type": "UNKNOWN", "failed_breakout_level_type": "UNKNOWN", "failed_breakout_reference_policy_id": FAILED_BREAKOUT_POLICY, "failed_breakout_reference_value": None, "data_sufficiency_status": "MISSING_REQUIRED_BARS"}
    low, close = fnum(lb["low"]), fnum(lb["close"])
    tol = abs(close) * 0.00003
    event = low < ref - tol and close >= ref
    return {"failed_breakout_event_type": "FAILED_DOWNSIDE_BREAKOUT_RECLAIM_INSIDE" if event else "NONE", "failed_breakout_level_type": "PRIOR_DAY_LOW" if event else "NONE", "failed_breakout_reference_policy_id": FAILED_BREAKOUT_POLICY, "failed_breakout_reference_value": ref}

def evaluate_london_low_sweep_reject(h1: List[Dict[str, Any]]) -> Dict[str, Any]:
    lb = latest(h1)
    ts = parse_ts(lb["bar_open_ts_utc"])
    ref = london_morning_low_closed_h1(h1, ts)
    if ref is None:
        return {"session_reference_range_type": "UNKNOWN", "session_reference_break_event_type": "UNKNOWN", "session_reference_policy_id": SESSION_REF_POLICY, "session_reference_low_value": None, "data_sufficiency_status": "MISSING_REQUIRED_BARS"}
    low, close = fnum(lb["low"]), fnum(lb["close"])
    tol = abs(close) * 0.00003
    event = low < ref - tol and close >= ref
    return {"session_reference_range_type": "LONDON_MORNING_RANGE", "session_reference_break_event_type": "LONDON_LOW_SWEEP_REJECT_LONG" if event else "NONE", "session_reference_policy_id": SESSION_REF_POLICY, "session_reference_low_value": ref}

def evaluate_targeted_london_morning_low_failed_downside(h1: List[Dict[str, Any]]) -> Dict[str, Any]:
    """OPS11 targeted H1 London-morning-low failed downside/reclaim context.

    This uses only closed H1 bars and the same London-morning reference window as
    evaluate_london_low_sweep_reject. It emits generic matching fields required by
    the W16 delivery pack. These are display-only context fields and do not create
    a signal, entry, stop, target, or probability.
    """
    lb = latest(h1)
    ts = parse_ts(lb["bar_open_ts_utc"])
    ref = london_morning_low_closed_h1(h1, ts)
    base = {
        "h1_failed_breakout_or_session_sweep_state": "UNKNOWN",
        "failed_breakout_failure_side": "UNKNOWN",
        "directional_side": "UNKNOWN",
        "policy_id": TARGETED_LONDON_LOW_POLICY,
        "targeted_london_morning_low_reference_value": ref,
    }
    if ref is None:
        base["data_sufficiency_status"] = "MISSING_REQUIRED_BARS"
        return base
    low, close = fnum(lb["low"]), fnum(lb["close"])
    tol = abs(close) * 0.00003
    event = low < ref - tol and close >= ref
    if event:
        base.update({
            "h1_failed_breakout_or_session_sweep_state": "LONDON_MORNING_LOW_FAILED_DOWNSIDE_RECLAIM_INSIDE",
            "failed_breakout_level_type": "LONDON_MORNING_LOW",
            "failed_breakout_failure_side": "FAILED_DOWNSIDE",
            "directional_side": "LONG",
            "policy_id": TARGETED_LONDON_LOW_POLICY,
        })
    else:
        base.update({
            "h1_failed_breakout_or_session_sweep_state": "NONE",
            "failed_breakout_failure_side": "NONE",
            "directional_side": "NONE",
            "policy_id": TARGETED_LONDON_LOW_POLICY,
        })
    return base

def eurusd_context(m15: List[Dict[str, Any]], h1: List[Dict[str, Any]]) -> Dict[str, Any]:
    lb, ts = latest(m15), parse_ts(latest(m15)["bar_open_ts_utc"])
    sess = session_bucket(ts)
    high, close, low, open_ = fnum(lb["high"]), fnum(lb["close"]), fnum(lb["low"]), fnum(lb["open"])
    rng = high - low
    close_loc = (close - low) / rng if rng else None
    upper_wick = (high - max(open_, close)) / rng if rng else None
    tol = abs(close) * 0.00003
    refs = []
    if ts.hour >= 7:
        refs.append(("ASIA", high_for_date(m15, ts.date(), range(0, 7))))
    if ts.hour >= 9:
        refs.append(("LONDON_EARLY", high_for_date(m15, ts.date(), range(7, 9))))
    refs.append(("PREVIOUS_DAY", previous_day_high(m15, ts.date())))
    refs.append(("PRIOR48", prior_48_high(m15)))
    upside, reject, ref_type = False, False, "NONE"
    for name, ref in refs:
        if ref is not None and high > ref + tol:
            upside, ref_type = True, name
            reject = close <= ref and ((upper_wick is not None and upper_wick >= 0.45) or (close_loc is not None and close_loc <= 0.50))
            break
    h1d, h4d, m15d = h1_dir(h1), h4_dir_from_h1(h1), m15_dir(m15)
    return {"instrument": "EURUSD", "timeframe": "M15", "latest_bar_open_ts_utc": lb.get("bar_open_ts_utc"), "session_bucket": sess, "upside_sweep_flag": upside, "sweep_then_reject_back_inside_up_flag": reject, "sweep_reference_type_up": ref_type, "h1_dir": h1d, "h4_dir": h4d, "m15_dir": m15d, "conflict_severity": stack_conflict_severity(h1d, h4d, m15d), "m15_range_ratio_12": range_ratio_12(m15), "context_builder_status": "DERIVED_FROM_READ_ONLY_RECENT_BARS", "data_sufficiency_status": "OK" if len(m15) >= 12 and len(h1) >= 8 else "LIMITED_HISTORY", "signal_authorized": False}

def usdjpy_context(m15: List[Dict[str, Any]], h1: List[Dict[str, Any]]) -> Dict[str, Any]:
    lb, ts = latest(m15), parse_ts(latest(m15)["bar_open_ts_utc"])
    sess = session_bucket(ts)
    h1d, h4d, m15d = h1_dir(h1), h4_dir_from_h1(h1), m15_dir(m15)
    rr = range_ratio_12(m15)
    up = h4d == "UP" and h1d == "UP" and sess in ACTIVE_SESSIONS
    down = h4d == "DOWN" and h1d == "DOWN" and sess in ACTIVE_SESSIONS
    chop = sess in ACTIVE_SESSIONS and not up and not down and rr is not None and 0.65 <= rr <= 1.20 and m15d in ("FLAT", "UNKNOWN")
    sweep = evaluate_usdjpy_prior48_upside_sweep_reject(m15, tolerance_multiplier=0.00002)
    data_suff = "OK" if len(m15) >= 12 and len(h1) >= 8 else "LIMITED_HISTORY"
    if sweep.get("data_sufficiency_status") == "MISSING_REQUIRED_BARS":
        data_suff = "MISSING_REQUIRED_BARS"
    return {"instrument": "USDJPY", "timeframe": "M15", "latest_bar_open_ts_utc": lb.get("bar_open_ts_utc"), "session_bucket": sess, "h1_dir": h1d, "h4_dir": h4d, "m15_dir": m15d, "h4_h1_up_context": up, "h4_h1_down_context": down, "m15_range_ratio_12": rr, "alignment_absent_chop": chop, "upside_sweep_flag": sweep.get("upside_sweep_flag"), "sweep_then_reject_back_inside_up_flag": sweep.get("sweep_then_reject_back_inside_up_flag"), "sweep_reference_type_up": sweep.get("sweep_reference_type_up"), "sweep_reference_policy_up": sweep.get("sweep_reference_policy_up"), "sweep_reference_value_up": sweep.get("sweep_reference_value_up"), "sweep_reference_meta_up": sweep.get("sweep_reference_meta_up"), "context_builder_status": "DERIVED_FROM_READ_ONLY_RECENT_BARS", "data_sufficiency_status": data_suff, "signal_authorized": False}

def eurusd_h1_mtf_context(h1: List[Dict[str, Any]], h4: List[Dict[str, Any]], d1: List[Dict[str, Any]]) -> Dict[str, Any]:
    lb, ts = latest(h1), parse_ts(latest(h1)["bar_open_ts_utc"])
    sess = session_bucket(ts)
    d1_state = d1_trend_state(d1)
    h4_state = h4_trend_state(h4)
    failed = evaluate_failed_breakout_prior_day_low(h1, d1)
    session_ref = evaluate_london_low_sweep_reject(h1)
    targeted_failed = evaluate_targeted_london_morning_low_failed_downside(h1)
    strict_reclaim = evaluate_strict_london_low_sweep_reclaim(h1)
    data_suff = "OK" if len(h1) >= 24 and len(h4) >= 8 and len(d1) >= 5 else "LIMITED_HISTORY"
    if failed.get("data_sufficiency_status") == "MISSING_REQUIRED_BARS" or session_ref.get("data_sufficiency_status") == "MISSING_REQUIRED_BARS" or targeted_failed.get("data_sufficiency_status") == "MISSING_REQUIRED_BARS":
        # Keep the row evaluable when one family is insufficient only if the active memory family still has fields.
        # Field-level UNKNOWN/NONE prevents false activation; global status stays LIMITED_HISTORY unless all core bars are missing.
        data_suff = "LIMITED_HISTORY" if data_suff == "OK" else data_suff
    row = {"instrument": "EURUSD", "timeframe": "H1", "base_timeframe": "H1", "latest_bar_open_ts_utc": lb.get("bar_open_ts_utc"), "session_bucket": sess, "d1_trend_state": d1_state, "h4_trend_state": h4_state, "context_builder_status": "DERIVED_FROM_READ_ONLY_CLOSED_H1_H4_D1_BARS_OPS17", "data_sufficiency_status": data_suff, "signal_authorized": False}
    row.update(failed)
    row.update(session_ref)
    row.update(strict_reclaim)
    # OPS11 targeted London-morning-low failed downside fields are overlaid last.
    # This only changes generic failed_breakout_level_type when the targeted event
    # is actually present; otherwise prior-day fields from OPS10 stay intact.
    if targeted_failed.get("h1_failed_breakout_or_session_sweep_state") == "LONDON_MORNING_LOW_FAILED_DOWNSIDE_RECLAIM_INSIDE":
        row.update(targeted_failed)
    else:
        for k, v in targeted_failed.items():
            if k not in row:
                row[k] = v
    return row

def build_context(raw: Dict[str, Any]) -> Dict[str, Any]:
    surfaces: List[Dict[str, Any]] = []
    # Legacy archived M15 context is still emitted for diagnostics/provenance and future comparison.
    for inst, builder in [("EURUSD", eurusd_context), ("USDJPY", usdjpy_context)]:
        m15, h1 = find_surface(raw, inst, "M15"), find_surface(raw, inst, "H1")
        if m15 and h1 and len(m15) >= 5 and len(h1) >= 5:
            surfaces.append(builder(m15, h1))
    # OPS10 H1 MTF directional-watch context.
    eur_h1 = find_surface(raw, "EURUSD", "H1")
    eur_h4 = find_surface(raw, "EURUSD", "H4")
    eur_d1 = find_surface(raw, "EURUSD", "D1")
    if eur_h1 and eur_h4 and eur_d1 and len(eur_h1) >= 5 and len(eur_h4) >= 4 and len(eur_d1) >= 4:
        surfaces.append(eurusd_h1_mtf_context(eur_h1, eur_h4, eur_d1))
    return {"context_version": "SIG_BRAIN5_LIVE_CONTEXT_v1_4_MTF_H1_DIRECTIONAL_OPS17", "created_utc": utc_now(), "source_authority": AUTHORITY, "surfaces": surfaces, "global_boundary": {"signal_authorized": False, "action_surface_authorized": False, "broker_execution_authorized": False, "plain_language": "Read-only multi-timeframe context only. Not a signal."}}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="inputs/sig_brain5_raw_bars_latest.json")
    ap.add_argument("--out", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--runtime-copy", default="runtime/sig_brain/sig_brain5_derived_context_latest.json")
    args = ap.parse_args()
    payload = build_context(load_json(Path(args.raw)))
    write_json(Path(args.out), payload)
    write_json(Path(args.runtime_copy), payload)
    print(json.dumps({"status": "sig_brain5_context_created", "out": args.out, "runtime_copy": args.runtime_copy, "surface_count": len(payload.get("surfaces", [])), "signal_authorized": False, "action_surface_authorized": False}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
