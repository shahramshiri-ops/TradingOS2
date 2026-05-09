#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
import pandas as pd
TF={"M15":("15min",{"default":3}),"H1":("1h",{"default":12}),"H4":("4h",{"default":48}),"D1":("1D",{"default":288,"XAUUSD":276})}
def exp(inst,tf): return TF[tf][1].get(inst,TF[tf][1]["default"])
def utc_now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def resample(m5,inst,tf):
    rule=TF[tf][0]; expected=exp(inst,tf); d=m5.copy(); d["bar_open_ts_utc"]=pd.to_datetime(d["bar_open_ts_utc"],utc=True,errors="coerce"); d=d.dropna(subset=["bar_open_ts_utc","open","high","low","close"]).sort_values("bar_open_ts_utc")
    d["bucket"]=d["bar_open_ts_utc"].dt.floor("D" if tf=="D1" else rule); delta=pd.Timedelta(days=1) if tf=="D1" else pd.Timedelta(rule); g=d.groupby("bucket",sort=True)
    out=pd.DataFrame({"instrument":inst,"timeframe":tf,"bar_open_ts_utc":list(g.groups.keys()),"open":g["open"].first().values,"high":g["high"].max().values,"low":g["low"].min().values,"close":g["close"].last().values,"volume":g["volume"].sum(min_count=1).values if "volume" in d.columns else 0,"m5_count":g["close"].count().values})
    out["expected_m5_count"]=expected; out["completeness_ratio"]=out["m5_count"]/expected; out["is_complete"]=out["m5_count"]>=expected; out["bar_close_ts_utc"]=pd.to_datetime(out["bar_open_ts_utc"],utc=True)+delta; out["source"]="resampled_from_canonical_M5"
    return out[["instrument","timeframe","bar_open_ts_utc","bar_close_ts_utc","open","high","low","close","volume","m5_count","expected_m5_count","completeness_ratio","is_complete","source"]]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--canonical-dir",default="data/live_m5/canonical"); ap.add_argument("--out-dir",default="data/live_resampled"); ap.add_argument("--report-dir",default="data/live_m5/reports"); ap.add_argument("--instruments",default="EURUSD,USDJPY,XAUUSD"); a=ap.parse_args()
    out_dir=Path(a.out_dir); rep_dir=Path(a.report_dir); out_dir.mkdir(parents=True,exist_ok=True); rep_dir.mkdir(parents=True,exist_ok=True); rows=[]
    for inst in [x.strip().upper() for x in a.instruments.split(",") if x.strip()]:
        p=Path(a.canonical_dir)/f"{inst}_M5_canonical.csv.gz"
        if not p.exists(): rows.append({"instrument":inst,"status":"MISSING_CANONICAL_M5"}); continue
        m5=pd.read_csv(p,compression="gzip")
        for tf in ["M15","H1","H4","D1"]:
            r=resample(m5,inst,tf); out=out_dir/f"{inst}_{tf}_from_M5.csv.gz"; r.to_csv(out,index=False,compression="gzip")
            rows.append({"instrument":inst,"timeframe":tf,"status":"RESAMPLED","rows":len(r),"complete_rows":int(r["is_complete"].sum()),"last_complete_bar_open_utc":r.loc[r["is_complete"],"bar_open_ts_utc"].max().isoformat() if r["is_complete"].any() else None,"output_file":str(out)})
    report={"created_utc":utc_now(),"authority":"READ_ONLY_RESAMPLE_FROM_M5_NOT_SIGNAL","results":rows}; (rep_dir/"resampled_from_m5_summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8"); pd.DataFrame(rows).to_csv(rep_dir/"resampled_from_m5_summary.csv",index=False); print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
