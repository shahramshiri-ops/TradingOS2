#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-OUTCOME-01C — Live-Recent Price Bridge Guard

This replaces the unsafe 01B behavior that could pick stale sample/audit H1 files.
It only bridges live/incremental M5 files to H1 for outcome observation.

Boundary: NOT_SIGNAL / NO_PNL / NO_EXECUTION / NO_RULE_REWRITE
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any, Dict, List, Optional
import csv
import json
import math
import os

ROOT = Path.cwd()
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"
OUT_DIR = RUNTIME_SHADOW / "price_bridge_h1"

for p in [RUNTIME_SHADOW, PANEL, PROOFS, OUT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = ["EURUSD", "USDJPY", "XAUUSD"]
MAX_STALENESS_HOURS = int(os.environ.get("SHADOW_OUTCOME_01C_MAX_STALENESS_HOURS", "96"))
MIN_H1_ROWS = int(os.environ.get("SHADOW_OUTCOME_01C_MIN_H1_ROWS", "1"))

FORBIDDEN_PATH_TOKENS = [
    "_mem_audit", "mem_audit", "sample", "historical", "history", "derived_rebuild",
    "_factory_registry", "factory_registry", "backtest", "discovery", "validation",
    "holdout", "archive"
]

BOUNDARY = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "pnl_authorized": False,
    "entry_stop_target_authorized": False,
}

def now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

def now_utc() -> str:
    return now_dt().isoformat().replace("+00:00", "Z")

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def parse_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        s = str(value).strip().replace(",", "")
        if not s:
            return None
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None

def norm_header(h: str) -> str:
    return str(h or "").strip().lower().replace(" ", "_").replace("-", "_")

def pick_col(headers: List[str], candidates: List[str]) -> Optional[str]:
    hmap = {norm_header(h): h for h in headers}
    for c in candidates:
        if norm_header(c) in hmap:
            return hmap[norm_header(c)]
    return None

def is_forbidden_path(path: Path) -> bool:
    low = str(path).lower().replace("\\", "/")
    return any(tok in low for tok in FORBIDDEN_PATH_TOKENS)

def live_m5_candidates(instrument: str) -> List[Path]:
    candidates = [
        ROOT / "data" / "live_m5" / "incremental" / f"{instrument}_M5_incremental_latest.csv",
        ROOT / "data" / "live_m5" / f"{instrument}_M5_incremental_latest.csv",
        ROOT / "runtime" / "live_m5" / "incremental" / f"{instrument}_M5_incremental_latest.csv",
        ROOT / "runtime" / "sig_live" / f"{instrument}_M5_incremental_latest.csv",
    ]
    # Controlled fallback only under live_m5 / sig_live paths.
    for root in [
        ROOT / "data" / "live_m5",
        ROOT / "runtime" / "live_m5",
        ROOT / "runtime" / "sig_live",
    ]:
        if root.exists():
            for pattern in [f"{instrument}*M5*latest*.csv", f"{instrument}*M5*.csv"]:
                try:
                    candidates.extend(root.rglob(pattern))
                except Exception:
                    pass
    seen = set()
    out = []
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        if not p.exists():
            continue
        if is_forbidden_path(p):
            continue
        low = str(p).lower().replace("\\", "/")
        if "live" not in low and "incremental" not in low:
            continue
        out.append(p)
    return out

def read_m5(path: Path, instrument: str) -> Dict[str, Any]:
    result = {
        "path": str(path).replace("\\", "/"),
        "status": "NOT_READ",
        "reason": None,
        "rows": [],
        "row_count": 0,
        "first_ts": None,
        "last_ts": None,
        "columns": {},
    }
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if not headers:
                result["status"] = "REJECTED"
                result["reason"] = "NO_HEADER"
                return result
            ts_col = pick_col(headers, ["bar_open_ts_utc", "timestamp", "datetime", "date_time", "time", "date", "ts", "start_time", "open_time"])
            o_col = pick_col(headers, ["open", "o"])
            h_col = pick_col(headers, ["high", "h"])
            l_col = pick_col(headers, ["low", "l"])
            c_col = pick_col(headers, ["close", "c"])
            sym_col = pick_col(headers, ["instrument", "symbol", "pair", "asset", "ticker"])
            result["columns"] = {"timestamp": ts_col, "open": o_col, "high": h_col, "low": l_col, "close": c_col, "symbol": sym_col}
            if not all([ts_col, o_col, h_col, l_col, c_col]):
                result["status"] = "REJECTED"
                result["reason"] = "MISSING_OHLC_OR_TIMESTAMP_COLUMNS"
                return result
            rows = []
            for row in reader:
                if sym_col:
                    sym = str(row.get(sym_col) or "").upper().replace("/", "").replace("-", "")
                    if instrument not in sym:
                        continue
                dt = parse_ts(row.get(ts_col))
                o = parse_float(row.get(o_col))
                h = parse_float(row.get(h_col))
                l = parse_float(row.get(l_col))
                c = parse_float(row.get(c_col))
                if dt and o is not None and h is not None and l is not None and c is not None:
                    rows.append({"ts": dt, "open": o, "high": h, "low": l, "close": c})
            rows.sort(key=lambda x: x["ts"])
            if not rows:
                result["status"] = "REJECTED"
                result["reason"] = "NO_READABLE_ROWS"
                return result
            result["rows"] = rows
            result["row_count"] = len(rows)
            result["first_ts"] = iso(rows[0]["ts"])
            result["last_ts"] = iso(rows[-1]["ts"])
            result["status"] = "OK"
            return result
    except Exception as e:
        result["status"] = "REJECTED"
        result["reason"] = "READ_ERROR_" + str(e)[:120]
        return result

def h1_bucket(dt: datetime) -> datetime:
    d = dt.astimezone(timezone.utc)
    return d.replace(minute=0, second=0, microsecond=0)

def resample_h1(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets = defaultdict(list)
    for r in rows:
        buckets[h1_bucket(r["ts"])].append(r)
    out = []
    for bucket, brs in sorted(buckets.items(), key=lambda x: x[0]):
        brs = sorted(brs, key=lambda x: x["ts"])
        out.append({
            "ts": bucket,
            "open": brs[0]["open"],
            "high": max(x["high"] for x in brs),
            "low": min(x["low"] for x in brs),
            "close": brs[-1]["close"],
            "bars_in_bucket": len(brs),
        })
    return out

def write_h1(instrument: str, h1: List[Dict[str, Any]], source_path: Path, source_last: datetime, staleness_hours: float, recency_status: str) -> Path:
    out = OUT_DIR / f"{instrument}_H1.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "bar_open_ts_utc", "open", "high", "low", "close", "bars_in_bucket",
            "bridge_method", "source_tf", "source_path", "source_last_m5_ts_utc",
            "source_staleness_hours", "live_recency_status", "bridge_created_utc"
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        created = now_utc()
        for b in h1:
            w.writerow({
                "bar_open_ts_utc": iso(b["ts"]),
                "open": b["open"],
                "high": b["high"],
                "low": b["low"],
                "close": b["close"],
                "bars_in_bucket": b.get("bars_in_bucket", 1),
                "bridge_method": "LIVE_RECENT_M5_RESAMPLED_TO_H1",
                "source_tf": "M5",
                "source_path": str(source_path).replace("\\", "/"),
                "source_last_m5_ts_utc": iso(source_last),
                "source_staleness_hours": round(staleness_hours, 3),
                "live_recency_status": recency_status,
                "bridge_created_utc": created,
            })
    return out

def build_bridge() -> Dict[str, Any]:
    created = now_dt()
    bridges = {}
    failures = {}
    inspected = {}
    for inst in INSTRUMENTS:
        inspected[inst] = []
        selected = None
        for p in live_m5_candidates(inst):
            info = read_m5(p, inst)
            public = {k: v for k, v in info.items() if k != "rows"}
            inspected[inst].append(public)
            if info["status"] != "OK":
                continue
            if selected is None or info["rows"][-1]["ts"] > selected["rows"][-1]["ts"]:
                selected = info
        if selected is None:
            failures[inst] = {
                "status": "NOT_BRIDGED",
                "reason": "NO_LIVE_M5_INCREMENTAL_SOURCE_FOUND",
                "inspected_sources": inspected[inst][:10],
            }
            continue
        source_path = Path(selected["path"])
        source_last = selected["rows"][-1]["ts"]
        staleness = (created - source_last).total_seconds() / 3600.0
        recency_status = "LIVE_RECENT_OK" if staleness <= MAX_STALENESS_HOURS else "LIVE_PRICE_STALE"
        h1 = resample_h1(selected["rows"])
        if len(h1) < MIN_H1_ROWS:
            failures[inst] = {
                "status": "NOT_BRIDGED",
                "reason": "INSUFFICIENT_H1_ROWS_AFTER_M5_RESAMPLE",
                "source_path": selected["path"],
                "m5_row_count": selected["row_count"],
                "h1_row_count": len(h1),
            }
            continue
        out_path = write_h1(inst, h1, source_path, source_last, staleness, recency_status)
        bridges[inst] = {
            "status": "BRIDGED",
            "instrument": inst,
            "output_path": str(out_path).replace("\\", "/"),
            "source_path": selected["path"],
            "source_tf": "M5",
            "bridge_method": "LIVE_RECENT_M5_RESAMPLED_TO_H1",
            "live_recency_status": recency_status,
            "source_staleness_hours": round(staleness, 3),
            "m5_row_count": selected["row_count"],
            "h1_row_count": len(h1),
            "first_h1_bar_open_ts_utc": iso(h1[0]["ts"]),
            "last_h1_bar_open_ts_utc": iso(h1[-1]["ts"]),
            "source_first_m5_ts_utc": selected["first_ts"],
            "source_last_m5_ts_utc": selected["last_ts"],
        }
    return {
        "payload_version": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_GUARD_v1_0",
        "created_utc": iso(created),
        "max_staleness_hours": MAX_STALENESS_HOURS,
        "bridge_output_dir": str(OUT_DIR).replace("\\", "/"),
        "preferred_source_policy": "ONLY_LIVE_M5_INCREMENTAL_OR_LIVE_PATHS; REJECT_SAMPLE_AUDIT_HISTORICAL_FACTORY",
        "forbidden_path_tokens": FORBIDDEN_PATH_TOKENS,
        "bridges": bridges,
        "failures": failures,
        "inspected_sources": inspected,
        "boundary": BOUNDARY,
    }

def main() -> None:
    catalog = build_bridge()
    write_json(RUNTIME_SHADOW / "price_source_bridge_catalog_current.json", catalog)
    write_json(PANEL / "price_source_bridge_catalog_current.json", catalog)
    write_json(PROOFS / "shadow_outcome_01c_live_recent_price_bridge_result.json", {
        "validation_name": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_BUILD",
        "created_utc": now_utc(),
        "bridged_instrument_count": len(catalog.get("bridges") or {}),
        "bridges": catalog.get("bridges"),
        "failures": catalog.get("failures"),
        "boundary": BOUNDARY,
    })
    print(json.dumps({
        "status": "SHADOW_OUTCOME_01C_LIVE_RECENT_PRICE_BRIDGE_BUILT",
        "bridged_instrument_count": len(catalog.get("bridges") or {}),
        "bridges": catalog.get("bridges"),
        "failures": catalog.get("failures"),
        "signal_authorized": False,
        "pnl_authorized": False,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
