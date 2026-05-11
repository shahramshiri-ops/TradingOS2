#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys


def run(cmd):
    print("RUN:", " ".join(cmd))
    subprocess.run([sys.executable] + cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-live", action="store_true")
    args = ap.parse_args()

    if args.fetch_live:
        run(["scripts/fetch_twelvedata_m5_incremental.py"])
        run(["scripts/merge_m5_canonical_store.py"])

    run(["scripts/resample_m5_to_higher_timeframes.py"])
    run(["scripts/build_brain5_raw_bars_from_resampled.py"])

    for cmd in [
        ["scripts/build_sig_brain5_live_context.py"],
        ["scripts/validate_sig_brain5_context_builder.py"],
        ["scripts/validate_sig_brain6_context_registry.py"],
        ["scripts/check_sig_brain6_runtime_context_coverage.py"],
        ["scripts/build_sig_live_refresh_status.py"],
    ]:
        run(cmd)

    print(json.dumps({
        "status": "SIG_LIVE_M5BASE1_PIPELINE_COMPLETED",
        "fetch_live": args.fetch_live,
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "refresh_status_out": "panel/brain4/sig_live_refresh_status_latest.json",
        "signal_authorized": False,
        "action_surface_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
