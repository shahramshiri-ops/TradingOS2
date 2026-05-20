#!/usr/bin/env python3
"""
SHADOW-01B observation updater.

Updates shadow observation records using read-only live H1 resampled bars when
enough future bars are available.

This is observation only:
- No PnL
- No entry/stop/target
- No profitability/tradability claim
- No broker/execution
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

AUTHORITY = "SIG_SHADOW_01B_OBSERVATION_UPDATER_v1_0|OBSERVATION_ONLY|NOT_SIGNAL|NO_PNL|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"
HORIZONS = [1, 2, 4, 8]

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_ts(x: Any) -> Optional[dt.datetime]:
    try:
        return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None

def ts_out(d: dt.datetime) -> str:
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def fnum(x: Any) -> Optional[float]:
    try:
        if x in (None, ""):
            return None
        return float(x)
    except Exception:
        return None

def bar_ts(row: Dict[str, Any]) -> str:
    for k in ("bar_open_ts_utc", "timestamp_utc", "ts_utc", "datetime_utc", "timestamp", "datetime", "time"):
        if row.get(k):
            return str(row.get(k))
    return ""

def read_h1_bars(instrument: str) -> List[Dict[str, Any]]:
    candidates = [
        Path(f"data/live_resampled/{instrument.upper()}_H1_from_M5.csv.gz"),
        Path(f"data/live_resampled/{instrument.upper()}_H1.csv.gz"),
        Path(f"data/live_resampled/{instrument.upper()}_H1_from_M5.csv"),
        Path(f"data/live_resampled/{instrument.upper()}_H1.csv"),
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return []
    if path.suffix == ".gz":
        fh = gzip.open(path, "rt", encoding="utf-8", errors="ignore", newline="")
    else:
        fh = path.open("r", encoding="utf-8-sig", errors="ignore", newline="")
    with fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: bar_ts(r))
    return rows

def price(row: Dict[str, Any], key: str) -> Optional[float]:
    for k in (key, key.lower(), f"h1_{key.lower()}"):
        if k in row:
            return fnum(row.get(k))
    return None

def compute_observation(candidate: Dict[str, Any], bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    cid = candidate.get("candidate_id")
    inst = str(candidate.get("instrument", "")).upper()
    direction = str(candidate.get("directional_bias", "")).upper()
    trigger_ts = parse_ts(candidate.get("trigger_bar_open_ts_utc"))
    ref = fnum(candidate.get("observation_reference_price"))

    base = {
        "candidate_id": cid,
        "instrument": inst,
        "timeframe": candidate.get("timeframe"),
        "directional_bias": direction,
        "trigger_bar_open_ts_utc": candidate.get("trigger_bar_open_ts_utc"),
        "updated_utc": utc_now(),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "metrics_are_pnl": False,
        "observation_state": "PENDING_OBSERVATION",
        "horizons": {},
    }

    if trigger_ts is None:
        base["observation_state"] = "TRIGGER_TIME_PARSE_FAIL"
        return base
    if not bars:
        base["observation_state"] = "OBSERVATION_DATA_UNAVAILABLE"
        return base

    parsed = []
    for r in bars:
        t = parse_ts(bar_ts(r))
        if t is not None:
            parsed.append((t, r))
    future = [(t, r) for t, r in parsed if t > trigger_ts]
    trigger_rows = [r for t, r in parsed if t == trigger_ts]
    if ref is None and trigger_rows:
        ref = price(trigger_rows[-1], "close")
    if ref is None:
        base["observation_state"] = "REFERENCE_PRICE_UNAVAILABLE"
        return base

    complete = True
    for h in HORIZONS:
        if len(future) < h:
            complete = False
            base["horizons"][f"H1+{h}"] = {
                "horizon_state": "PENDING_FUTURE_BARS",
                "available_future_h1_bars": len(future),
                "required_future_h1_bars": h,
            }
            continue
        rows = [r for _, r in future[:h]]
        highs = [price(r, "high") for r in rows]
        lows = [price(r, "low") for r in rows]
        closes = [price(r, "close") for r in rows]
        highs = [x for x in highs if x is not None]
        lows = [x for x in lows if x is not None]
        closes = [x for x in closes if x is not None]
        if not highs or not lows or not closes:
            complete = False
            base["horizons"][f"H1+{h}"] = {"horizon_state": "PRICE_DATA_INCOMPLETE"}
            continue
        if direction.startswith("LONG"):
            favorable = max(highs) - ref
            adverse = ref - min(lows)
            close_move = closes[-1] - ref
        elif direction.startswith("SHORT"):
            favorable = ref - min(lows)
            adverse = max(highs) - ref
            close_move = ref - closes[-1]
        else:
            favorable = None
            adverse = None
            close_move = None
        pct = (close_move / ref * 100.0) if close_move is not None and ref else None
        base["horizons"][f"H1+{h}"] = {
            "horizon_state": "OBSERVED",
            "reference_price_observation_only": ref,
            "future_bar_count": h,
            "horizon_end_bar_open_ts_utc": bar_ts(rows[-1]),
            "favorable_excursion_price_units": favorable,
            "adverse_excursion_price_units": adverse,
            "directional_close_move_price_units": close_move,
            "directional_close_move_pct": pct,
            "pnl_claim": False,
            "profitability_claim": False,
        }

    base["observation_state"] = "OBSERVED_COMPLETE" if complete else "PENDING_OBSERVATION"
    return base

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-ledger", default="runtime/sig_shadow/shadow_candidate_ledger_current.json")
    ap.add_argument("--out", default="runtime/sig_shadow/shadow_observation_ledger_current.json")
    args = ap.parse_args()

    ledger = load_json(Path(args.candidate_ledger), {"candidates": []})
    existing = load_json(Path(args.out), {"observations": []})
    existing_by_id = {str(o.get("candidate_id")): o for o in existing.get("observations", []) if o.get("candidate_id")}
    bar_cache: Dict[str, List[Dict[str, Any]]] = {}

    for c in ledger.get("candidates", []) or []:
        inst = str(c.get("instrument", "")).upper()
        if inst not in bar_cache:
            bar_cache[inst] = read_h1_bars(inst)
        existing_by_id[str(c.get("candidate_id"))] = compute_observation(c, bar_cache[inst])

    observations = sorted(existing_by_id.values(), key=lambda x: (x.get("trigger_bar_open_ts_utc", ""), x.get("candidate_id", "")))
    complete = sum(1 for o in observations if o.get("observation_state") == "OBSERVED_COMPLETE")
    pending = sum(1 for o in observations if o.get("observation_state") == "PENDING_OBSERVATION")
    unavailable = sum(1 for o in observations if o.get("observation_state") not in ("OBSERVED_COMPLETE", "PENDING_OBSERVATION"))

    out = {
        "ledger_version": "SIG_SHADOW_OBSERVATION_LEDGER_v1_0",
        "created_utc": existing.get("created_utc") or utc_now(),
        "updated_utc": utc_now(),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "observations": observations,
        "summary": {
            "observation_count": len(observations),
            "observed_complete_count": complete,
            "pending_observation_count": pending,
            "unavailable_or_error_count": unavailable,
            "metrics_are_pnl": False,
        }
    }
    write_json(Path(args.out), out)
    print(json.dumps({
        "status": "SIG_SHADOW_01B_OBSERVATIONS_UPDATED",
        "observation_count": len(observations),
        "observed_complete_count": complete,
        "pending_observation_count": pending,
        "signal_authorized": False,
        "broker_execution_authorized": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
