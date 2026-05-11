#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
from typing import Any, Dict, List, Optional

AUTHORITY = "SIG_BRAIN5_UPSTREAM_CONTEXT_BUILDER|READ_ONLY_DERIVED_CONTEXT|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"
ACTIVE_SESSIONS = ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]

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
    if h < 7: return "ASIA"
    if h < 12: return "LONDON"
    if h < 16: return "LONDON_NY_OVERLAP"
    if h < 21: return "NEW_YORK"
    return "ROLLOVER_THIN"
def find_surface(raw: Dict[str, Any], instrument: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
    for s in raw.get("surfaces", []):
        if str(s.get("instrument","")).upper() == instrument and str(s.get("timeframe","")).upper() == timeframe:
            return sorted(s.get("bars", []), key=lambda b: b.get("bar_open_ts_utc", ""))
    return None
def fnum(x: Any) -> float: return float(x)
def latest(bars): return bars[-1]
def closes(bars): return [fnum(b["close"]) for b in bars]
def change_pct(vals, periods):
    if len(vals) <= periods or vals[-1-periods] == 0: return None
    return (vals[-1] / vals[-1-periods] - 1.0) * 100.0
def dir_from_change(chg, threshold):
    if chg is None: return "UNKNOWN"
    if chg > threshold: return "UP"
    if chg < -threshold: return "DOWN"
    return "FLAT"
def aggregate_h4_from_h1(h1_bars):
    buckets = {}
    for b in h1_bars:
        ts = parse_ts(b["bar_open_ts_utc"])
        kts = ts.replace(hour=(ts.hour//4)*4, minute=0, second=0, microsecond=0)
        key = kts.isoformat().replace("+00:00", "Z")
        buckets.setdefault(key, []).append(b)
    out = []
    for key, rows in sorted(buckets.items()):
        rows = sorted(rows, key=lambda b: b["bar_open_ts_utc"])
        out.append({"bar_open_ts_utc": key, "open": rows[0]["open"], "high": max(fnum(r["high"]) for r in rows), "low": min(fnum(r["low"]) for r in rows), "close": rows[-1]["close"]})
    return out
def h1_dir(h1): return dir_from_change(change_pct(closes(h1), 3), 0.04)
def h4_dir_from_h1(h1): return dir_from_change(change_pct(closes(aggregate_h4_from_h1(h1)), 3), 0.08)
def m15_dir(m15): return dir_from_change(change_pct(closes(m15), 4), 0.03)
def range_ratio_12(m15):
    if len(m15) < 5: return None
    rngs = [fnum(b["high"]) - fnum(b["low"]) for b in m15]
    avg = sum(rngs[-12:]) / len(rngs[-12:])
    return None if avg == 0 else rngs[-1] / avg
def stack_conflict_severity(h1d, h4d, m15d):
    vals = [h1d, h4d, m15d]
    if "UNKNOWN" in vals: return "UNKNOWN"
    if "UP" in vals and "DOWN" in vals: return "HIGH"
    if vals.count("FLAT") >= 2: return "LOW"
    if h1d == h4d and h1d in ("UP", "DOWN"): return "NONE"
    return "MEDIUM"
def high_for_date(m15, day, hours):
    rows = [b for b in m15 if parse_ts(b["bar_open_ts_utc"]).date() == day and parse_ts(b["bar_open_ts_utc"]).hour in hours]
    return max((fnum(b["high"]) for b in rows), default=None)
def prior_48_high(m15):
    prior = m15[-49:-1] if len(m15) >= 49 else m15[:-1]
    return max((fnum(b["high"]) for b in prior), default=None)
def previous_day_high(m15, day):
    rows = [b for b in m15 if parse_ts(b["bar_open_ts_utc"]).date() == day - dt.timedelta(days=1)]
    return max((fnum(b["high"]) for b in rows), default=None)

def eurusd_context(m15, h1):
    lb, ts = latest(m15), parse_ts(latest(m15)["bar_open_ts_utc"])
    sess = session_bucket(ts)
    high, close, low, open_ = fnum(lb["high"]), fnum(lb["close"]), fnum(lb["low"]), fnum(lb["open"])
    rng = high - low
    close_loc = (close - low) / rng if rng else None
    upper_wick = (high - max(open_, close)) / rng if rng else None
    tol = abs(close) * 0.00003
    refs = []
    if ts.hour >= 7: refs.append(("ASIA", high_for_date(m15, ts.date(), range(0,7))))
    if ts.hour >= 9: refs.append(("LONDON_EARLY", high_for_date(m15, ts.date(), range(7,9))))
    refs.append(("PREVIOUS_DAY", previous_day_high(m15, ts.date())))
    refs.append(("PRIOR48", prior_48_high(m15)))
    upside, reject, ref_type = False, False, "NONE"
    for name, ref in refs:
        if ref is not None and high > ref + tol:
            upside, ref_type = True, name
            reject = close <= ref and ((upper_wick is not None and upper_wick >= 0.45) or (close_loc is not None and close_loc <= 0.50))
            break
    h1d, h4d, m15d = h1_dir(h1), h4_dir_from_h1(h1), m15_dir(m15)
    return {"instrument":"EURUSD","timeframe":"M15","latest_bar_open_ts_utc":lb.get("bar_open_ts_utc"),"session_bucket":sess,"upside_sweep_flag":upside,"sweep_then_reject_back_inside_up_flag":reject,"sweep_reference_type_up":ref_type,"h1_dir":h1d,"h4_dir":h4d,"m15_dir":m15d,"conflict_severity":stack_conflict_severity(h1d,h4d,m15d),"m15_range_ratio_12":range_ratio_12(m15),"context_builder_status":"DERIVED_FROM_READ_ONLY_RECENT_BARS","data_sufficiency_status":"OK" if len(m15)>=12 and len(h1)>=8 else "LIMITED_HISTORY","signal_authorized":False}
def usdjpy_context(m15, h1):
    lb, ts = latest(m15), parse_ts(latest(m15)["bar_open_ts_utc"])
    sess = session_bucket(ts)
    h1d, h4d, m15d = h1_dir(h1), h4_dir_from_h1(h1), m15_dir(m15)
    rr = range_ratio_12(m15)
    up = h4d == "UP" and h1d == "UP" and sess in ACTIVE_SESSIONS
    down = h4d == "DOWN" and h1d == "DOWN" and sess in ACTIVE_SESSIONS
    chop = sess in ACTIVE_SESSIONS and not up and not down and rr is not None and 0.65 <= rr <= 1.20 and m15d in ("FLAT","UNKNOWN")
    return {"instrument":"USDJPY","timeframe":"M15","latest_bar_open_ts_utc":lb.get("bar_open_ts_utc"),"session_bucket":sess,"h1_dir":h1d,"h4_dir":h4d,"m15_dir":m15d,"h4_h1_up_context":up,"h4_h1_down_context":down,"m15_range_ratio_12":rr,"alignment_absent_chop":chop,"context_builder_status":"DERIVED_FROM_READ_ONLY_RECENT_BARS","data_sufficiency_status":"OK" if len(m15)>=12 and len(h1)>=8 else "LIMITED_HISTORY","signal_authorized":False}
def build_context(raw):
    surfaces = []
    for inst, builder in [("EURUSD", eurusd_context), ("USDJPY", usdjpy_context)]:
        m15, h1 = find_surface(raw, inst, "M15"), find_surface(raw, inst, "H1")
        if m15 and h1:
            surfaces.append(builder(m15, h1))
        else:
            surfaces.append({"instrument":inst,"timeframe":"M15","context_builder_status":"MISSING_REQUIRED_BARS","missing":[x for x, ok in [(f"{inst} M15", bool(m15)), (f"{inst} H1", bool(h1))] if not ok],"signal_authorized":False})
    return {"context_version":"SIG_BRAIN5_DERIVED_LIVE_CONTEXT_v1_0","created_utc":utc_now(),"source_authority":AUTHORITY,"input_context_version":raw.get("context_version"),"input_created_utc":raw.get("created_utc"),"surfaces":surfaces,"global_boundary":{"display_only":True,"signal_authorized":False,"action_surface_authorized":False,"broker_execution_authorized":False,"plain_language_fa":"این فایل فقط context مشتق‌شده برای matcher مغز است؛ سیگنال، ورود، خروج، سودآوری یا اجرا نیست."}}
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-bars", default="inputs/sig_brain5_raw_bars_latest.json")
    ap.add_argument("--out", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--runtime-copy", default="runtime/sig_brain/sig_brain5_derived_context_latest.json")
    args = ap.parse_args()
    ctx = build_context(load_json(Path(args.raw_bars)))
    write_json(Path(args.out), ctx)
    write_json(Path(args.runtime_copy), ctx)
    print(json.dumps({"status":"sig_brain5_context_created","out":args.out,"runtime_copy":args.runtime_copy,"surface_count":len(ctx["surfaces"]),"signal_authorized":False,"action_surface_authorized":False}, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    main()
