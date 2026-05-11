#!/usr/bin/env python3
"""
SIG-BRAIN-OPS6 live refresh status builder.

Builds a small display-only refresh/timing diagnostic JSON for Brain4 panel.
This script is read-only with respect to market/provider data. It does not fetch,
does not trade, and never authorizes signals, entries, stops, targets, broker use,
profitability, tradability, or action surfaces.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

AUTHORITY = "SIG_BRAIN_OPS6_REFRESH_STATUS|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"
TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def utc_now_str() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> Optional[dt.datetime]:
    if value in (None, "", "—"):
        return None
    try:
        ts = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.to_pydatetime().replace(microsecond=0)
    except Exception:
        return None


def iso(d: Optional[dt.datetime]) -> Optional[str]:
    if d is None:
        return None
    return d.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timeframe_minutes(tf: str) -> int:
    s = str(tf or "").upper()
    if s.startswith("M") and s[1:].isdigit():
        return int(s[1:])
    if s.startswith("H") and s[1:].isdigit():
        return int(s[1:]) * 60
    if s.startswith("D") and s[1:].isdigit():
        return int(s[1:]) * 1440
    return 15


def floor_to_minutes(d: dt.datetime, minutes: int) -> dt.datetime:
    epoch = int(d.timestamp())
    floored = epoch - (epoch % (minutes * 60))
    return dt.datetime.fromtimestamp(floored, tz=dt.timezone.utc).replace(microsecond=0)


def expected_complete_m15_from_latest_m5(latest_m5_open: Optional[dt.datetime]) -> Optional[dt.datetime]:
    if latest_m5_open is None:
        return None
    group = floor_to_minutes(latest_m5_open, 15)
    # A 15m bar is complete when the third 5m constituent is present:
    # group_open, group_open+5m, group_open+10m.
    if latest_m5_open >= group + dt.timedelta(minutes=10):
        return group
    return group - dt.timedelta(minutes=15)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_csv_bar(path: Path, compression: Optional[str] = None) -> Dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    try:
        df = pd.read_csv(path, compression=compression)
        if df.empty or "bar_open_ts_utc" not in df.columns:
            return {"path": str(path), "exists": True, "rows": int(len(df)), "latest_bar_open_ts_utc": None}
        if "is_complete" in df.columns:
            # Keep complete rows for resampled higher-TF files. Missing column is fine for M5.
            try:
                df = df[df["is_complete"].astype(bool)]
            except Exception:
                pass
        df["bar_open_ts_utc"] = pd.to_datetime(df["bar_open_ts_utc"], utc=True, errors="coerce")
        df = df.dropna(subset=["bar_open_ts_utc"]).sort_values("bar_open_ts_utc")
        if df.empty:
            return {"path": str(path), "exists": True, "rows": 0, "latest_bar_open_ts_utc": None}
        latest = df.iloc[-1]
        ts = latest["bar_open_ts_utc"].to_pydatetime().replace(microsecond=0)
        return {
            "path": str(path),
            "exists": True,
            "rows": int(len(df)),
            "latest_bar_open_ts_utc": iso(ts),
        }
    except Exception as e:
        return {"path": str(path), "exists": True, "error": str(e)}


def latest_provider_m5_from_report(report: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for r in report.get("results", []) or []:
        d = parse_utc(r.get("latest_bar_open_ts_utc"))
        rows.append({
            "instrument": r.get("instrument"),
            "status": r.get("status"),
            "latest_bar_open_ts_utc": iso(d),
            "rows_written": r.get("rows_written"),
        })
    max_dt = max((parse_utc(r.get("latest_bar_open_ts_utc")) for r in rows), default=None)
    return {"by_instrument": rows, "max_latest_bar_open_ts_utc": iso(max_dt)}


def latest_context_surface(ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = []
    for s in ctx.get("surfaces", []) or []:
        d = parse_utc(s.get("latest_bar_open_ts_utc"))
        tf = str(s.get("timeframe") or "")
        close = d + dt.timedelta(minutes=timeframe_minutes(tf)) if d else None
        out.append({
            "instrument": s.get("instrument"),
            "timeframe": tf,
            "latest_bar_open_ts_utc": iso(d),
            "latest_bar_close_ts_utc": iso(close),
            "session_bucket": s.get("session_bucket"),
            "data_sufficiency_status": s.get("data_sufficiency_status"),
        })
    out.sort(key=lambda x: x.get("latest_bar_close_ts_utc") or "", reverse=True)
    return {"surfaces": out, "latest": out[0] if out else None}


def resampled_summary(resampled_dir: Path, instruments: List[str]) -> Dict[str, Any]:
    rows = []
    for inst in instruments:
        for tf in TIMEFRAMES:
            if tf == "M5":
                p = Path("data/live_m5/canonical") / f"{inst}_M5_canonical.csv.gz"
            else:
                p = resampled_dir / f"{inst}_{tf}_from_M5.csv.gz"
            info = latest_csv_bar(p, compression="gzip")
            info.update({"instrument": inst, "timeframe": tf})
            open_dt = parse_utc(info.get("latest_bar_open_ts_utc"))
            close_dt = open_dt + dt.timedelta(minutes=timeframe_minutes(tf)) if open_dt else None
            info["latest_bar_close_ts_utc"] = iso(close_dt)
            rows.append(info)
    return {"rows": rows}


def classify_lag(provider_max: Optional[dt.datetime], context_latest: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if provider_max is None:
        return {"lag_reason_code": "PROVIDER_M5_STATUS_UNKNOWN", "plain_language_fa": "آخرین دادهٔ خام M5 در گزارش پیدا نشد."}
    if not context_latest:
        return {"lag_reason_code": "BRAIN_CONTEXT_STATUS_UNKNOWN", "plain_language_fa": "آخرین کندل استفاده‌شده توسط مغز در context پیدا نشد."}
    tf = context_latest.get("timeframe") or "M15"
    if str(tf).upper() == "M15":
        expected_m15 = expected_complete_m15_from_latest_m5(provider_max)
        actual_m15 = parse_utc(context_latest.get("latest_bar_open_ts_utc"))
        if expected_m15 and actual_m15:
            if actual_m15 < expected_m15:
                return {
                    "lag_reason_code": "RESAMPLED_M15_BEHIND_PROVIDER_M5",
                    "plain_language_fa": "دادهٔ M5 جلوتر از آخرین M15 مغز است؛ resample/context باید جلو بیاید.",
                    "expected_m15_open_from_latest_m5_utc": iso(expected_m15),
                    "actual_context_m15_open_utc": iso(actual_m15),
                }
            if actual_m15 == expected_m15:
                return {
                    "lag_reason_code": "M15_CONTEXT_ALIGNED_WITH_PROVIDER_M5",
                    "plain_language_fa": "آخرین کندل M15 مغز با آخرین M5 قابل‌استفاده هماهنگ است.",
                    "expected_m15_open_from_latest_m5_utc": iso(expected_m15),
                    "actual_context_m15_open_utc": iso(actual_m15),
                }
    return {"lag_reason_code": "REFRESH_COMPLETED", "plain_language_fa": "بروزرسانی با داده‌های موجود کامل شد."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-report", default="data/live_m5/incremental/twelvedata_m5_incremental_fetch_report.json")
    ap.add_argument("--context", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--payload", default="runtime/sig_brain/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--resampled-dir", default="data/live_resampled")
    ap.add_argument("--instruments", default="EURUSD,USDJPY,XAUUSD")
    ap.add_argument("--out-panel", default="panel/brain4/sig_live_refresh_status_latest.json")
    ap.add_argument("--out-runtime", default="runtime/sig_brain/sig_live_refresh_status_latest.json")
    ap.add_argument("--out-proof", default="proofs/sig_live_refresh_status_latest.json")
    args = ap.parse_args()

    fetch_report = load_json(Path(args.fetch_report))
    ctx = load_json(Path(args.context))
    payload = load_json(Path(args.payload))
    instruments = [x.strip().upper() for x in args.instruments.split(",") if x.strip()]

    provider = latest_provider_m5_from_report(fetch_report)
    context = latest_context_surface(ctx)
    provider_max_dt = parse_utc(provider.get("max_latest_bar_open_ts_utc"))
    lag = classify_lag(provider_max_dt, context.get("latest"))

    status = {
        "status_version": "SIG_BRAIN_OPS6_REFRESH_STATUS_v1_0",
        "created_utc": utc_now_str(),
        "last_successful_refresh_utc": utc_now_str(),
        "authority": AUTHORITY,
        "raw_live_feed_timeframe": "M5",
        "memory_timeframe_policy": "Each memory is evaluated on its own timeframe; M5 is the live raw feed and is resampled for M15/H1/H4/D1 memory contexts.",
        "memory_timeframe_policy_fa": "دادهٔ خام زنده M5 است؛ هر memory با timeframe خودش ارزیابی می‌شود و M5 پشت صحنه برای M15/H1/H4/D1 resample می‌شود.",
        "provider_m5": provider,
        "brain_context": context,
        "resampled_data": resampled_summary(Path(args.resampled_dir), instruments),
        "lag_diagnostic": lag,
        "source_files": {
            "fetch_report": args.fetch_report,
            "context": args.context,
            "payload": args.payload,
        },
        "boundaries": {
            "signal_authorized": False,
            "action_surface_authorized": False,
            "broker_execution_authorized": False,
            "trade_instruction_authorized": False,
            "plain_language_fa": "این status فقط زمان بروزرسانی و freshness داده را نشان می‌دهد؛ سیگنال یا دستور معامله نیست.",
        },
        "payload_created_utc": payload.get("created_utc"),
        "context_created_utc": ctx.get("created_utc"),
    }

    for out in [Path(args.out_panel), Path(args.out_runtime), Path(args.out_proof)]:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "SIG_BRAIN_OPS6_REFRESH_STATUS_CREATED",
        "out_panel": args.out_panel,
        "latest_provider_m5": provider.get("max_latest_bar_open_ts_utc"),
        "latest_context_bar": (context.get("latest") or {}).get("latest_bar_open_ts_utc"),
        "lag_reason_code": lag.get("lag_reason_code"),
        "signal_authorized": False,
        "action_surface_authorized": False,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
