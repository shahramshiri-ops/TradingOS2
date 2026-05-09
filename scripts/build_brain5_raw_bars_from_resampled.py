#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
import pandas as pd
def utc_now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def bars(path,n):
    if not path.exists(): return []
    df=pd.read_csv(path,compression="gzip"); df["bar_open_ts_utc"]=pd.to_datetime(df["bar_open_ts_utc"],utc=True,errors="coerce")
    if "is_complete" in df.columns: df=df[df["is_complete"].astype(bool)]
    df=df.dropna(subset=["bar_open_ts_utc","open","high","low","close"]).sort_values("bar_open_ts_utc").tail(n)
    return [{"bar_open_ts_utc":r["bar_open_ts_utc"].isoformat().replace("+00:00","Z"),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"])} for _,r in df.iterrows()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--resampled-dir",default="data/live_resampled"); ap.add_argument("--out",default="inputs/sig_brain5_raw_bars_latest.json"); ap.add_argument("--instruments",default="EURUSD,USDJPY,XAUUSD"); a=ap.parse_args()
    surfaces=[]; rd=Path(a.resampled_dir)
    for inst in [x.strip().upper() for x in a.instruments.split(",") if x.strip()]:
        for tf in ["M15","H1","H4","D1"]:
            n=160 if tf=="M15" else (100 if tf=="H1" else 80)
            surfaces.append({"instrument":inst,"timeframe":tf,"bars":bars(rd/f"{inst}_{tf}_from_M5.csv.gz",n),"source":"internal_resampled_from_M5"})
    payload={"context_version":"SIG_M5BASE1_BRAIN5_RAW_BARS_FROM_INTERNAL_RESAMPLER_v1_0","created_utc":utc_now(),"source_authority":"INTERNAL_M5_CANONICAL_RESAMPLED_READ_ONLY_NOT_SIGNAL","surfaces":surfaces,"global_boundary":"Read-only OHLC context only. Not signal. No broker/execution."}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); print(json.dumps({"status":"brain5_raw_bars_created_from_resampled_m5","out":str(out),"surfaces":len(surfaces),"signal_authorized":False},indent=2))
if __name__=="__main__": main()
