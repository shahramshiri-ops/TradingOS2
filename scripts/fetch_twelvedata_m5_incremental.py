#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, os, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
SYMBOLS={"EURUSD":"EUR/USD","USDJPY":"USD/JPY","XAUUSD":"XAU/USD"}
def utc_now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
def key(): return os.environ.get("LFB_TWELVE_DATA_API_KEY") or os.environ.get("TWELVE_DATA_API_KEY")
def fetch(symbol, apikey, outputsize):
    params={"symbol":symbol,"interval":"5min","outputsize":str(outputsize),"apikey":apikey,"format":"JSON","timezone":"UTC"}
    with urllib.request.urlopen("https://api.twelvedata.com/time_series?"+urllib.parse.urlencode(params), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))
def parse(payload, inst, lag_min):
    if payload.get("status")=="error": raise RuntimeError(payload.get("message","Twelve Data error"))
    cutoff=utc_now()-dt.timedelta(minutes=lag_min); rows=[]
    for v in payload.get("values",[]):
        ts=pd.to_datetime(v.get("datetime"),utc=True,errors="coerce")
        if pd.isna(ts) or ts.to_pydatetime()+dt.timedelta(minutes=5)>cutoff: continue
        rows.append({"instrument":inst,"timeframe":"M5","bar_open_ts_utc":ts,"open":float(v["open"]),"high":float(v["high"]),"low":float(v["low"]),"close":float(v["close"]),"volume":float(v.get("volume",0) or 0),"source":"twelvedata_live_readonly_incremental","source_file":"twelvedata_time_series_5min","imported_utc":utc_now().isoformat().replace("+00:00","Z")})
    return pd.DataFrame(rows).sort_values("bar_open_ts_utc") if rows else pd.DataFrame(rows)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out-dir",default="data/live_m5/incremental"); ap.add_argument("--outputsize",type=int,default=60); ap.add_argument("--closed-lag-minutes",type=int,default=2); ap.add_argument("--instruments",default="EURUSD,USDJPY,XAUUSD"); a=ap.parse_args()
    apikey=key()
    if not apikey: raise SystemExit("Missing API key env var LFB_TWELVE_DATA_API_KEY or TWELVE_DATA_API_KEY")
    out_dir=Path(a.out_dir); out_dir.mkdir(parents=True,exist_ok=True); report={"created_utc":utc_now().isoformat().replace("+00:00","Z"),"authority":"READ_ONLY_TWELVEDATA_M5_FETCH_NOT_SIGNAL","results":[]}
    for inst in [x.strip().upper() for x in a.instruments.split(",") if x.strip()]:
        df=parse(fetch(SYMBOLS[inst],apikey,a.outputsize),inst,a.closed_lag_minutes); out=out_dir/f"{inst}_M5_incremental_latest.csv"
        if not df.empty: df.to_csv(out,index=False)
        report["results"].append({"instrument":inst,"symbol":SYMBOLS[inst],"rows_written":int(len(df)),"output_file":str(out),"latest_bar_open_ts_utc":df["bar_open_ts_utc"].max().isoformat() if not df.empty else None})
    (out_dir/"twelvedata_m5_incremental_fetch_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8"); print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
