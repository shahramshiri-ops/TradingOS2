#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
import pandas as pd
def utc_now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def read_any(p): return pd.read_csv(p, compression="gzip") if str(p).endswith(".gz") else pd.read_csv(p)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--canonical-dir",default="data/live_m5/canonical"); ap.add_argument("--incremental-dir",default="data/live_m5/incremental"); ap.add_argument("--report-dir",default="data/live_m5/reports"); ap.add_argument("--instruments",default="EURUSD,USDJPY,XAUUSD"); a=ap.parse_args()
    can_dir=Path(a.canonical_dir); inc_dir=Path(a.incremental_dir); rep_dir=Path(a.report_dir); can_dir.mkdir(parents=True,exist_ok=True); rep_dir.mkdir(parents=True,exist_ok=True); results=[]
    for inst in [x.strip().upper() for x in a.instruments.split(",") if x.strip()]:
        can=can_dir/f"{inst}_M5_canonical.csv.gz"; inc=inc_dir/f"{inst}_M5_incremental_latest.csv"
        if not inc.exists(): results.append({"instrument":inst,"status":"NO_INCREMENTAL_FILE","merged_rows":0}); continue
        old=read_any(can) if can.exists() else pd.DataFrame(); new=pd.read_csv(inc)
        for df in [old,new]:
            if not df.empty: df["bar_open_ts_utc"]=pd.to_datetime(df["bar_open_ts_utc"],utc=True,errors="coerce")
        combined=pd.concat([old,new],ignore_index=True,sort=False).dropna(subset=["bar_open_ts_utc","open","high","low","close"])
        combined["instrument"]=inst; combined["timeframe"]="M5"; before=len(combined)
        combined=combined.sort_values(["bar_open_ts_utc","source"]).drop_duplicates(["instrument","timeframe","bar_open_ts_utc"],keep="last").sort_values("bar_open_ts_utc")
        combined.to_csv(can,index=False,compression="gzip")
        results.append({"instrument":inst,"status":"MERGED","old_rows":int(len(old)),"incremental_rows":int(len(new)),"canonical_rows_after":int(len(combined)),"duplicates_removed":int(before-len(combined)),"canonical_file":str(can)})
    report={"created_utc":utc_now(),"authority":"READ_ONLY_M5_MERGE_NOT_SIGNAL","results":results}; (rep_dir/"m5_incremental_merge_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8"); print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
