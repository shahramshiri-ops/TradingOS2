#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-OUTCOME-01D — Freshness / Closed-H1 / Pending Completion Guard

Purpose:
- Do not let live outcome use incomplete H1 buckets.
- Classify live M5 source freshness.
- Preserve only closed H1 bars in runtime/sig_shadow/price_bridge_h1/{INSTRUMENT}_H1.csv.
- Produce a quality status for panel/review.

Boundary:
NOT_SIGNAL / NO_BUY_SELL / NO_ENTRY_STOP_TARGET / NO_POSITION_SIZE /
NO_BROKER_EXECUTION / NO_AUTO_LEARNING / NO_RULE_REWRITE / NO_PNL
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import csv
import json
import math

ROOT = Path.cwd()
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"
BRIDGE_DIR = RUNTIME_SHADOW / "price_bridge_h1"

for p in [RUNTIME_SHADOW, PANEL, PROOFS, BRIDGE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

CATALOG_PATH = RUNTIME_SHADOW / "price_source_bridge_catalog_current.json"
GUARD_STATUS_RUNTIME = RUNTIME_SHADOW / "shadow_outcome_01d_guard_status_current.json"
GUARD_STATUS_PANEL = PANEL / "shadow_outcome_01d_guard_status_current.json"

FRESH_MINUTES = 30
LAGGING_MINUTES = 90
STALE_MINUTES = 360

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
        return None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_freshness(age_minutes: Optional[float]) -> str:
    if age_minutes is None:
        return "LIVE_BROKEN_NO_SOURCE_TIME"
    if age_minutes <= FRESH_MINUTES:
        return "LIVE_FRESH"
    if age_minutes <= LAGGING_MINUTES:
        return "LIVE_LAGGING"
    if age_minutes <= STALE_MINUTES:
        return "LIVE_STALE"
    return "LIVE_BROKEN"


def parse_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        x = float(str(v).replace(",", ""))
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_bridge_csv(path: Path) -> List[Dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_ts(row.get("bar_open_ts_utc"))
            o = parse_float(row.get("open"))
            h = parse_float(row.get("high"))
            l = parse_float(row.get("low"))
            c = parse_float(row.get("close"))
            if ts and o is not None and h is not None and l is not None and c is not None:
                rr = dict(row)
                rr["_ts"] = ts
                rows.append(rr)
    rows.sort(key=lambda x: x["_ts"])
    return rows


def write_bridge_csv(path: Path, rows: List[Dict[str, Any]], freshness_tier: str, source_last_m5_ts: Optional[datetime]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "bar_open_ts_utc", "open", "high", "low", "close", "bars_in_bucket",
        "bridge_method", "source_tf", "source_path", "source_last_m5_ts_utc",
        "source_staleness_hours", "live_recency_status", "h1_closed_status",
        "freshness_tier_01d", "guard_01d_created_utc", "bridge_created_utc"
    ]
    created = now_utc()
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = {k: r.get(k) for k in fields}
            out["bar_open_ts_utc"] = iso(r["_ts"])
            out["h1_closed_status"] = "CLOSED_H1_ONLY"
            out["freshness_tier_01d"] = freshness_tier
            out["guard_01d_created_utc"] = created
            if source_last_m5_ts:
                out["source_last_m5_ts_utc"] = iso(source_last_m5_ts)
            w.writerow(out)


def is_closed_h1(bucket_start: datetime, source_last_m5_ts: Optional[datetime]) -> bool:
    if source_last_m5_ts is None:
        return False
    # With M5 bar-open timestamps, the last M5 bar needed to close an H1 bucket is :55.
    return source_last_m5_ts >= bucket_start + timedelta(minutes=55)


def guard_instrument(inst: str, bridge: Dict[str, Any], created: datetime) -> Dict[str, Any]:
    path = ROOT / str(bridge.get("output_path") or "")
    source_last = parse_ts(bridge.get("source_last_m5_ts_utc") or bridge.get("last_h1_bar_open_ts_utc"))
    age_minutes = ((created - source_last).total_seconds() / 60.0) if source_last else None
    freshness = classify_freshness(age_minutes)

    rows = read_bridge_csv(path)
    total = len(rows)
    closed = [r for r in rows if is_closed_h1(r["_ts"], source_last)]
    dropped = total - len(closed)

    # Backup original bridge before rewriting.
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak_shadow_outcome_01d")
        try:
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass

    if closed:
        write_bridge_csv(path, closed, freshness, source_last)

    return {
        "instrument": inst,
        "bridge_path": str(path).replace("\\", "/"),
        "source_path": bridge.get("source_path"),
        "source_last_m5_ts_utc": iso(source_last) if source_last else None,
        "source_age_minutes": round(age_minutes, 3) if age_minutes is not None else None,
        "freshness_tier": freshness,
        "h1_rows_before_guard": total,
        "closed_h1_rows_after_guard": len(closed),
        "dropped_incomplete_h1_rows": dropped,
        "latest_closed_h1_bar_open_ts_utc": iso(closed[-1]["_ts"]) if closed else None,
        "guard_status": "PASS_CLOSED_H1_AVAILABLE" if closed else "NO_CLOSED_H1_AVAILABLE",
    }


def main() -> None:
    created = now_dt()
    catalog = load_json(CATALOG_PATH, {})
    bridges = catalog.get("bridges") or {}

    reports = {}
    for inst, bridge in bridges.items():
        reports[inst] = guard_instrument(inst, bridge, created)

    freshness_counts: Dict[str, int] = {}
    for r in reports.values():
        freshness_counts[r["freshness_tier"]] = freshness_counts.get(r["freshness_tier"], 0) + 1

    status = {
        "payload_version": "SHADOW_OUTCOME_01D_GUARD_STATUS_v1_0",
        "created_utc": iso(created),
        "purpose": "freshness tiering + closed-H1-only bridge guard before outcome completion",
        "freshness_thresholds_minutes": {
            "LIVE_FRESH_MAX": FRESH_MINUTES,
            "LIVE_LAGGING_MAX": LAGGING_MINUTES,
            "LIVE_STALE_MAX": STALE_MINUTES,
        },
        "instrument_reports": reports,
        "freshness_tier_breakdown": freshness_counts,
        "bridged_instrument_count": len(bridges),
        "closed_h1_available_instrument_count": sum(1 for r in reports.values() if r["closed_h1_rows_after_guard"] > 0),
        "dropped_incomplete_h1_rows_total": sum(r["dropped_incomplete_h1_rows"] for r in reports.values()),
        "boundary": BOUNDARY,
        "plain_language_fa": (
            "01D قبل از outcome فقط کندل‌های H1 بسته‌شده را نگه می‌دارد و تازگی منبع live را طبقه‌بندی می‌کند. "
            "این خروجی سیگنال، PnL، ورود، حدضرر، تارگت یا اجرای معامله نیست."
        ),
    }

    write_json(GUARD_STATUS_RUNTIME, status)
    write_json(GUARD_STATUS_PANEL, status)
    write_json(PROOFS / "shadow_outcome_01d_guard_status_result.json", status)

    print(json.dumps({
        "status": "SHADOW_OUTCOME_01D_GUARD_BUILT",
        "freshness_tier_breakdown": freshness_counts,
        "dropped_incomplete_h1_rows_total": status["dropped_incomplete_h1_rows_total"],
        "closed_h1_available_instrument_count": status["closed_h1_available_instrument_count"],
        "signal_authorized": False,
        "pnl_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
