#!/usr/bin/env python3
"""
SIG-LIVE-M5BASE1 canonical market-hours purge v1.4.

Purpose:
  Remove already-merged weekend/market-closed M5 rows from canonical M5 store,
  then regenerate resampled bars, Brain5 raw bars, Brain5 context, and Brain4 payload.

Why:
  If Twelve Data returned Sunday daytime bars before the v1.3 market-hours filter,
  those rows may already exist in canonical M5 and can continue to pollute payloads
  even after future fetches are filtered.

Boundary:
  Read-only data quality repair only.
  Not signal. No buy/sell/hold. No entry/stop/target. No broker/execution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def parse_hhmm(value: str) -> dt.time:
    hour, minute = value.split(":")
    return dt.time(int(hour), int(minute), tzinfo=dt.timezone.utc)


def is_market_open_bar(
    bar_open_ts: dt.datetime,
    sunday_open_utc: dt.time,
    friday_close_utc: dt.time,
) -> bool:
    ts = bar_open_ts.astimezone(dt.timezone.utc)
    bar_close = ts + dt.timedelta(minutes=5)
    wd = ts.weekday()

    if wd == 5:  # Saturday
        return False
    if wd == 6:  # Sunday
        return ts.time().replace(tzinfo=dt.timezone.utc) >= sunday_open_utc
    if wd == 4:  # Friday
        return bar_close.time().replace(tzinfo=dt.timezone.utc) <= friday_close_utc
    return True


def utc_now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def purge_file(path: Path, sunday_open_utc: dt.time, friday_close_utc: dt.time, dry_run: bool) -> dict:
    if not path.exists():
        return {"file": str(path), "status": "MISSING"}

    df = pd.read_csv(path, compression="gzip")
    if df.empty:
        return {"file": str(path), "status": "EMPTY", "rows_before": 0, "rows_after": 0, "removed_rows": 0}

    df["bar_open_ts_utc"] = pd.to_datetime(df["bar_open_ts_utc"], utc=True, errors="coerce")
    before = len(df)

    mask = df["bar_open_ts_utc"].apply(
        lambda x: False if pd.isna(x) else is_market_open_bar(x.to_pydatetime(), sunday_open_utc, friday_close_utc)
    )
    removed = df[~mask].copy()
    kept = df[mask].copy().sort_values("bar_open_ts_utc")

    if not dry_run:
        backup = path.with_suffix(path.suffix + ".pre_market_hours_purge_backup")
        if not backup.exists():
            path.replace(backup)
        kept.to_csv(path, index=False, compression="gzip")

    return {
        "file": str(path),
        "status": "PURGED" if not dry_run else "DRY_RUN",
        "rows_before": int(before),
        "rows_after": int(len(kept)),
        "removed_rows": int(len(removed)),
        "removed_start_utc": removed["bar_open_ts_utc"].min().isoformat() if not removed.empty else None,
        "removed_end_utc": removed["bar_open_ts_utc"].max().isoformat() if not removed.empty else None,
        "latest_remaining_bar_open_ts_utc": kept["bar_open_ts_utc"].max().isoformat() if not kept.empty else None,
    }


def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run([sys.executable] + cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-dir", default="data/live_m5/canonical")
    ap.add_argument("--instruments", default="EURUSD,USDJPY,XAUUSD")
    ap.add_argument("--sunday-open-utc", default="21:00")
    ap.add_argument("--friday-close-utc", default="21:00")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-regenerate", action="store_true")
    ap.add_argument("--report-out", default="data/live_m5/reports/m5_canonical_market_hours_purge_report.json")
    args = ap.parse_args()

    sunday_open = parse_hhmm(args.sunday_open_utc)
    friday_close = parse_hhmm(args.friday_close_utc)

    canonical_dir = Path(args.canonical_dir)
    results = []
    for inst in [x.strip().upper() for x in args.instruments.split(",") if x.strip()]:
        path = canonical_dir / f"{inst}_M5_canonical.csv.gz"
        results.append(purge_file(path, sunday_open, friday_close, args.dry_run))

    report = {
        "created_utc": utc_now_str(),
        "authority": "READ_ONLY_CANONICAL_M5_MARKET_HOURS_PURGE_NOT_SIGNAL",
        "sunday_open_utc": args.sunday_open_utc,
        "friday_close_utc": args.friday_close_utc,
        "dry_run": args.dry_run,
        "results": results,
        "signal_authorized": False,
        "action_surface_authorized": False,
    }

    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.dry_run or args.skip_regenerate:
        return 0

    # Regenerate downstream outputs from cleaned canonical store.
    run(["scripts/resample_m5_to_higher_timeframes.py"])
    run(["scripts/build_brain5_raw_bars_from_resampled.py"])
    run(["scripts/build_sig_brain5_live_context.py"])
    run(["scripts/build_sig_brain4_runtime_payload.py"])
    run(["scripts/validate_sig_live_m5base1_outputs.py"])
    run(["scripts/validate_sig_brain5_context_builder.py"])
    run(["scripts/validate_sig_brain6_context_registry.py"])
    run(["scripts/check_sig_brain6_runtime_context_coverage.py"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
