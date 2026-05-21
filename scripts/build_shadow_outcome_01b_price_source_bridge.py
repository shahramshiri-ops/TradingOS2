#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-OUTCOME-01B — H1 Price Source Bridge

Builds normalized H1 files from existing repo OHLC sources:
runtime/sig_shadow/price_bridge_h1/{INSTRUMENT}_H1.csv

Observation-only. Not signal, not PnL, not execution.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict
import csv, json, math, os, re

ROOT = Path.cwd()
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"
OUT_DIR = RUNTIME_SHADOW / "price_bridge_h1"
for p in [RUNTIME_SHADOW, PANEL, PROOFS, OUT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = ["EURUSD", "USDJPY", "XAUUSD"]
MAX_FILE_BYTES = int(os.environ.get("SHADOW_PRICE_BRIDGE_MAX_FILE_MB", "250")) * 1024 * 1024
MAX_CANDIDATE_FILES = int(os.environ.get("SHADOW_PRICE_BRIDGE_MAX_FILES", "500"))
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}

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

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_instrument(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper().replace("/", "").replace("-", "").replace(".", "")
    if s in {"GOLD", "XAU"}:
        return "XAUUSD"
    for inst in INSTRUMENTS:
        if inst in s:
            return inst
    return None

def infer_instruments_from_path(path: Path) -> List[str]:
    s = str(path).upper().replace("/", "_").replace("\\", "_").replace("-", "_").replace(".", "_")
    return [inst for inst in INSTRUMENTS if inst in s]

def infer_tf_from_name(path: Path) -> Optional[str]:
    s = str(path).upper()
    checks = [
        ("H1", [r"(^|[_\-/\.])H1([_\-/\.]|$)", r"(^|[_\-/\.])1H([_\-/\.]|$)", r"HOURLY"]),
        ("M5", [r"(^|[_\-/\.])M5([_\-/\.]|$)", r"(^|[_\-/\.])5M([_\-/\.]|$)", r"5MIN"]),
        ("M15", [r"(^|[_\-/\.])M15([_\-/\.]|$)", r"(^|[_\-/\.])15M([_\-/\.]|$)", r"15MIN"]),
        ("M1", [r"(^|[_\-/\.])M1([_\-/\.]|$)", r"(^|[_\-/\.])1M([_\-/\.]|$)"]),
    ]
    for tf, pats in checks:
        if any(re.search(p, s) for p in pats):
            return tf
    return None

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

def inspect_csv(path: Path) -> Dict[str, Any]:
    info = {
        "path": str(path).replace("\\", "/"),
        "candidate": False,
        "reason": None,
        "tf_name": infer_tf_from_name(path),
        "tf_sample": None,
        "tf_effective": None,
        "instrument_from_path": infer_instruments_from_path(path),
        "instrument_from_column_sample": [],
        "score": 0,
        "columns": {},
        "file_size": path.stat().st_size if path.exists() else None,
    }
    if info["file_size"] is not None and info["file_size"] > MAX_FILE_BYTES:
        info["reason"] = "FILE_TOO_LARGE_SKIPPED"
        return info
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if not headers:
                info["reason"] = "NO_HEADER"
                return info
            ts_col = pick_col(headers, ["bar_open_ts_utc", "timestamp", "datetime", "date_time", "time", "date", "ts", "start_time", "open_time"])
            o_col = pick_col(headers, ["open", "o"])
            h_col = pick_col(headers, ["high", "h"])
            l_col = pick_col(headers, ["low", "l"])
            c_col = pick_col(headers, ["close", "c"])
            sym_col = pick_col(headers, ["instrument", "symbol", "pair", "asset", "ticker"])
            info["columns"] = {"timestamp": ts_col, "open": o_col, "high": h_col, "low": l_col, "close": c_col, "symbol": sym_col}
            if not all([ts_col, o_col, h_col, l_col, c_col]):
                info["reason"] = "MISSING_OHLC_OR_TIMESTAMP_COLUMNS"
                return info
            sample_ts, instruments = [], set()
            for i, row in enumerate(reader):
                if i >= 500:
                    break
                dt = parse_ts(row.get(ts_col))
                if dt:
                    sample_ts.append(dt)
                if sym_col:
                    inst = normalize_instrument(row.get(sym_col))
                    if inst:
                        instruments.add(inst)
            info["instrument_from_column_sample"] = sorted(instruments)
            if len(sample_ts) >= 3:
                sample_ts = sorted(sample_ts)
                diffs = [(b-a).total_seconds() for a,b in zip(sample_ts, sample_ts[1:]) if (b-a).total_seconds() > 0]
                if diffs:
                    med = sorted(diffs)[len(diffs)//2]
                    if 3300 <= med <= 3900: info["tf_sample"] = "H1"
                    elif 240 <= med <= 360: info["tf_sample"] = "M5"
                    elif 840 <= med <= 960: info["tf_sample"] = "M15"
                    elif 50 <= med <= 90: info["tf_sample"] = "M1"
            insts = set(info["instrument_from_path"]) | set(info["instrument_from_column_sample"])
            if not insts:
                info["reason"] = "NO_TARGET_INSTRUMENT"
                return info
            tf = info["tf_name"] or info["tf_sample"]
            if tf not in {"H1", "M5", "M15", "M1"}:
                info["reason"] = "NO_INTRADAY_TF"
                return info
            info["candidate"] = True
            info["tf_effective"] = tf
            tf_score = {"H1": 100, "M5": 80, "M15": 70, "M1": 60}.get(tf, 0)
            low = str(path).lower()
            bonus = sum(5 for token in ["runtime", "live", "canonical", "resample", "twelvedata", "m5", "h1"] if token in low)
            if "factory" in low or "_factory_registry" in low:
                bonus -= 50
            info["score"] = tf_score + bonus
            info["reason"] = "OK"
            return info
    except Exception as e:
        info["reason"] = "READ_ERROR_" + str(e)[:80]
        return info

def iter_csv_files() -> List[Path]:
    roots = [ROOT / "runtime", ROOT / "data", ROOT / "outputs", ROOT / "panel"]
    found = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if not fn.lower().endswith(".csv"):
                    continue
                p = Path(dirpath) / fn
                low = str(p).lower()
                if any(tok in low for tok in ["h1", "m5", "m15", "m1", "canonical", "resample", "live", "twelvedata", "bar"]) or any(inst.lower() in low for inst in INSTRUMENTS):
                    found.append(p)
                if len(found) >= MAX_CANDIDATE_FILES:
                    return found
    seen, out = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def read_ohlc_rows(path: Path, info: Dict[str, Any], target_instrument: str) -> List[Dict[str, Any]]:
    rows = []
    cols = info.get("columns") or {}
    ts_col, o_col, h_col, l_col, c_col, sym_col = cols.get("timestamp"), cols.get("open"), cols.get("high"), cols.get("low"), cols.get("close"), cols.get("symbol")
    inst_from_path = set(info.get("instrument_from_path") or [])
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if sym_col:
                    inst = normalize_instrument(row.get(sym_col))
                    if inst != target_instrument:
                        continue
                elif target_instrument not in inst_from_path:
                    continue
                dt = parse_ts(row.get(ts_col))
                o, h, l, c = parse_float(row.get(o_col)), parse_float(row.get(h_col)), parse_float(row.get(l_col)), parse_float(row.get(c_col))
                if dt and o is not None and h is not None and l is not None and c is not None:
                    rows.append({"ts": dt, "open": o, "high": h, "low": l, "close": c})
    except Exception:
        return []
    rows.sort(key=lambda x: x["ts"])
    return rows

def h1_bucket(dt: datetime) -> datetime:
    d = dt.astimezone(timezone.utc)
    return d.replace(minute=0, second=0, microsecond=0)

def resample_to_h1(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets = defaultdict(list)
    for r in rows:
        buckets[h1_bucket(r["ts"])].append(r)
    out = []
    for bucket, brs in sorted(buckets.items(), key=lambda x: x[0]):
        brs = sorted(brs, key=lambda x: x["ts"])
        out.append({"ts": bucket, "open": brs[0]["open"], "high": max(x["high"] for x in brs), "low": min(x["low"] for x in brs), "close": brs[-1]["close"], "bars_in_bucket": len(brs)})
    return out

def write_h1(instrument: str, bars: List[Dict[str, Any]], source_info: Dict[str, Any], method: str) -> Path:
    path = OUT_DIR / f"{instrument}_H1.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        fields = ["bar_open_ts_utc", "open", "high", "low", "close", "bars_in_bucket", "bridge_method", "source_tf", "source_path", "bridge_created_utc"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        created = now_utc()
        for b in bars:
            w.writerow({"bar_open_ts_utc": iso(b["ts"]), "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"], "bars_in_bucket": b.get("bars_in_bucket", 1), "bridge_method": method, "source_tf": source_info.get("tf_effective"), "source_path": source_info.get("path"), "bridge_created_utc": created})
    return path

def build_bridge() -> Dict[str, Any]:
    created = now_utc()
    csv_files = iter_csv_files()
    inspections = [inspect_csv(p) for p in csv_files]
    candidates = [x for x in inspections if x.get("candidate")]
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    by_inst = {inst: [] for inst in INSTRUMENTS}
    for info in candidates:
        insts = set(info.get("instrument_from_path") or []) | set(info.get("instrument_from_column_sample") or [])
        for inst in insts:
            if inst in by_inst:
                by_inst[inst].append(info)
    bridges, failures = {}, {}
    for inst in INSTRUMENTS:
        infos = by_inst.get(inst) or []
        infos.sort(key=lambda x: (0 if x.get("tf_effective") == "H1" else 1 if x.get("tf_effective") == "M5" else 2, -int(x.get("score", 0))))
        built, tried = False, []
        for info in infos[:20]:
            p = Path(info["path"])
            rows = read_ohlc_rows(p, info, inst)
            tried.append({"path": info["path"], "tf": info.get("tf_effective"), "row_count": len(rows), "score": info.get("score")})
            if not rows:
                continue
            tf = info.get("tf_effective")
            if tf == "H1":
                h1 = []
                for r in rows:
                    h1.append({**r, "ts": h1_bucket(r["ts"]), "bars_in_bucket": 1})
                dedup = {}
                for r in h1:
                    dedup[r["ts"]] = r
                h1 = [dedup[k] for k in sorted(dedup)]
                out_path = write_h1(inst, h1, info, "NATIVE_H1_NORMALIZED")
            else:
                h1 = resample_to_h1(rows)
                out_path = write_h1(inst, h1, info, f"RESAMPLED_{tf}_TO_H1")
            bridges[inst] = {"status": "BRIDGED", "instrument": inst, "output_path": str(out_path).replace("\\", "/"), "source_path": info.get("path"), "source_tf": tf, "bridge_method": "NATIVE_H1_NORMALIZED" if tf == "H1" else f"RESAMPLED_{tf}_TO_H1", "h1_row_count": len(h1), "first_bar_open_ts_utc": iso(h1[0]["ts"]) if h1 else None, "last_bar_open_ts_utc": iso(h1[-1]["ts"]) if h1 else None}
            built = True
            break
        if not built:
            failures[inst] = {"status": "NOT_BRIDGED", "candidate_source_count": len(infos), "tried": tried[:10], "reason": "NO_READABLE_H1_OR_INTRADAY_OHLC_SOURCE_FOUND"}
    return {"payload_version": "SHADOW_OUTCOME_01B_H1_PRICE_SOURCE_BRIDGE_v1_0", "created_utc": created, "scan_root": str(ROOT).replace("\\", "/"), "scanned_csv_count": len(csv_files), "candidate_csv_count": len(candidates), "bridge_output_dir": str(OUT_DIR).replace("\\", "/"), "bridges": bridges, "failures": failures, "top_candidates": candidates[:30], "boundary": BOUNDARY}

def main() -> None:
    catalog = build_bridge()
    write_json(RUNTIME_SHADOW / "price_source_bridge_catalog_current.json", catalog)
    write_json(PANEL / "price_source_bridge_catalog_current.json", catalog)
    write_json(PROOFS / "shadow_outcome_01b_price_source_bridge_result.json", {"validation_name": "SHADOW_OUTCOME_01B_PRICE_SOURCE_BRIDGE_BUILD", "created_utc": now_utc(), "bridged_instrument_count": len(catalog.get("bridges") or {}), "bridges": catalog.get("bridges"), "failures": catalog.get("failures"), "boundary": BOUNDARY})
    print(json.dumps({"status": "SHADOW_OUTCOME_01B_PRICE_SOURCE_BRIDGE_BUILT", "bridged_instrument_count": len(catalog.get("bridges") or {}), "bridges": catalog.get("bridges"), "failures": catalog.get("failures"), "signal_authorized": False, "pnl_authorized": False}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
