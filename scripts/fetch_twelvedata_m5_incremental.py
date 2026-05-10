#!/usr/bin/env python3
"""
SIG-LIVE-M5BASE1 Twelve Data M5 incremental fetch v1.1.

Read-only provider fetch only.
Not signal. No buy/sell/hold. No entry/stop/target. No broker/execution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

SYMBOLS = {
    "EURUSD": "EUR/USD",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD",
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def utc_now_str() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def get_api_key() -> str | None:
    return os.environ.get("LFB_TWELVE_DATA_API_KEY") or os.environ.get("TWELVE_DATA_API_KEY")


def fetch_symbol(symbol: str, apikey: str, outputsize: int) -> Dict[str, Any]:
    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": str(outputsize),
        "apikey": apikey,
        "format": "JSON",
        "timezone": "UTC",
    }
    url = "https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Twelve Data HTTPError {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Twelve Data URLError: {e}") from e


def parse_values(payload: Dict[str, Any], instrument: str, closed_lag_minutes: int) -> pd.DataFrame:
    if payload.get("status") == "error":
        raise RuntimeError(payload.get("message", "Twelve Data error"))

    values = payload.get("values", [])
    if not isinstance(values, list):
        raise RuntimeError(f"Unexpected Twelve Data payload for {instrument}: missing values list")

    cutoff = utc_now() - dt.timedelta(minutes=closed_lag_minutes)
    rows: List[Dict[str, Any]] = []

    for v in values:
        ts = pd.to_datetime(v.get("datetime"), utc=True, errors="coerce")
        if pd.isna(ts):
            continue

        # Accept only bars whose close is safely in the past.
        bar_close = ts.to_pydatetime() + dt.timedelta(minutes=5)
        if bar_close > cutoff:
            continue

        try:
            rows.append({
                "instrument": instrument,
                "timeframe": "M5",
                "bar_open_ts_utc": ts,
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                "volume": float(v.get("volume", 0) or 0),
                "source": "twelvedata_live_readonly_incremental",
                "source_file": "twelvedata_time_series_5min",
                "imported_utc": utc_now_str(),
            })
        except KeyError as e:
            raise RuntimeError(f"Missing OHLC key in Twelve Data value for {instrument}: {e}") from e

    columns = [
        "instrument", "timeframe", "bar_open_ts_utc", "open", "high", "low", "close",
        "volume", "source", "source_file", "imported_utc"
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns).sort_values("bar_open_ts_utc")


def parse_set(value: str) -> set[str]:
    return {x.strip().upper() for x in value.split(",") if x.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/live_m5/incremental")
    ap.add_argument("--outputsize", type=int, default=60)
    ap.add_argument("--closed-lag-minutes", type=int, default=5)
    ap.add_argument("--instruments", default="EURUSD,USDJPY,XAUUSD")
    ap.add_argument("--required-instruments", default="EURUSD,USDJPY")
    ap.add_argument("--optional-instruments", default="XAUUSD")
    ap.add_argument("--fail-on-optional", action="store_true")
    args = ap.parse_args()

    apikey = get_api_key()
    if not apikey:
        raise SystemExit("Missing API key env var LFB_TWELVE_DATA_API_KEY or TWELVE_DATA_API_KEY")

    instruments = parse_set(args.instruments)
    required = parse_set(args.required_instruments)
    optional = parse_set(args.optional_instruments)

    unknown = instruments - set(SYMBOLS)
    if unknown:
        raise SystemExit(f"Unknown instruments: {sorted(unknown)}. Known: {sorted(SYMBOLS)}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "created_utc": utc_now_str(),
        "authority": "READ_ONLY_TWELVEDATA_M5_FETCH_NOT_SIGNAL",
        "outputsize": args.outputsize,
        "closed_lag_minutes": args.closed_lag_minutes,
        "required_instruments": sorted(required),
        "optional_instruments": sorted(optional),
        "results": [],
        "errors": [],
        "status": "STARTED",
        "signal_authorized": False,
        "action_surface_authorized": False,
    }

    hard_failure = False

    for inst in sorted(instruments):
        symbol = SYMBOLS[inst]
        out = out_dir / f"{inst}_M5_incremental_latest.csv"
        try:
            payload = fetch_symbol(symbol, apikey, args.outputsize)
            df = parse_values(payload, inst, args.closed_lag_minutes)

            # Always write a file, even if empty, to make downstream behavior explicit.
            df.to_csv(out, index=False)

            report["results"].append({
                "instrument": inst,
                "symbol": symbol,
                "status": "OK",
                "rows_written": int(len(df)),
                "output_file": str(out),
                "latest_bar_open_ts_utc": (
                    df["bar_open_ts_utc"].max().isoformat()
                    if not df.empty else None
                ),
            })
        except Exception as e:
            is_optional = inst in optional and inst not in required
            error_status = "ERROR_OPTIONAL" if is_optional else "ERROR_REQUIRED"
            report["errors"].append({
                "instrument": inst,
                "symbol": symbol,
                "status": error_status,
                "error": str(e),
            })
            report["results"].append({
                "instrument": inst,
                "symbol": symbol,
                "status": error_status,
                "rows_written": 0,
                "output_file": str(out),
                "latest_bar_open_ts_utc": None,
            })

            if (not is_optional) or args.fail_on_optional:
                hard_failure = True

    if hard_failure:
        report["status"] = "FAILED_REQUIRED_INSTRUMENT_FETCH"
    elif report["errors"]:
        report["status"] = "PARTIAL_SUCCESS_OPTIONAL_ERRORS"
    else:
        report["status"] = "SUCCESS"

    report_path = out_dir / "twelvedata_m5_incremental_fetch_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 1 if hard_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
