#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, json, datetime as dt
def run(cmd): print("RUN:"," ".join(cmd)); subprocess.run([sys.executable]+cmd,check=True)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--fetch-live",action="store_true"); a=ap.parse_args()
    if a.fetch_live:
        run(["scripts/fetch_twelvedata_m5_incremental.py"]); run(["scripts/merge_m5_canonical_store.py"])
    run(["scripts/resample_m5_to_higher_timeframes.py"]); run(["scripts/build_brain5_raw_bars_from_resampled.py"])
    for cmd in [["scripts/build_sig_brain5_live_context.py"],["scripts/validate_sig_brain5_context_builder.py"],["scripts/validate_sig_brain6_context_registry.py"],["scripts/check_sig_brain6_runtime_context_coverage.py"]]:
        run(cmd)
    print(json.dumps({"status":"SIG_LIVE_M5BASE1_PIPELINE_COMPLETED","fetch_live":a.fetch_live,"created_utc":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"signal_authorized":False},indent=2))
if __name__=="__main__": main()
