#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, datetime as dt
from pathlib import Path
import pandas as pd
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--canonical-dir",default="data/live_m5/canonical"); ap.add_argument("--resampled-dir",default="data/live_resampled"); ap.add_argument("--out",default="proofs/sig_live_m5base1_validation_result.json"); a=ap.parse_args()
    failures=[]; warnings=[]; rows=[]
    for inst in ["EURUSD","USDJPY","XAUUSD"]:
        m5p=Path(a.canonical_dir)/f"{inst}_M5_canonical.csv.gz"
        if not m5p.exists(): failures.append(f"missing {m5p}"); continue
        m5=pd.read_csv(m5p,compression="gzip"); m5["bar_open_ts_utc"]=pd.to_datetime(m5["bar_open_ts_utc"],utc=True,errors="coerce"); dup=int(m5.duplicated(["instrument","timeframe","bar_open_ts_utc"]).sum())
        if dup: failures.append(f"{inst} M5 duplicates: {dup}")
        rows.append({"instrument":inst,"timeframe":"M5","rows":len(m5),"duplicates":dup})
        for tf in ["M15","H1","H4","D1"]:
            p=Path(a.resampled_dir)/f"{inst}_{tf}_from_M5.csv.gz"
            if not p.exists(): failures.append(f"missing {p}"); continue
            df=pd.read_csv(p,compression="gzip"); complete=int(df["is_complete"].astype(bool).sum()) if "is_complete" in df.columns else 0
            if complete==0: warnings.append(f"{inst} {tf} has no complete rows; allowed only if this TF is not currently consumed")
            rows.append({"instrument":inst,"timeframe":tf,"rows":len(df),"complete_rows":complete})
    if not Path("inputs/sig_brain5_raw_bars_latest.json").exists(): failures.append("missing inputs/sig_brain5_raw_bars_latest.json")
    proof={"validation_status":"PASS" if not failures else "FAIL","created_utc":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"failures":failures,"warnings":warnings,"rows":rows,"signal_authorized":False,"action_surface_authorized":False}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding="utf-8"); print(json.dumps(proof,indent=2,ensure_ascii=False)); return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(main())
