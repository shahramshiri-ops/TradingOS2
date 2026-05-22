import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

PROGRAM = "SIG-E-SHADOW-DETECTOR1-OBSLEDGER1"
DETECTOR_ID = "SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0"
SOURCE_SPEC_ID = "SIG_E_RUNTIME_SPEC_USDJPY_LONDON_LONG_H1_M15_v1_0"

DETECTOR_CURRENT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
LEDGER_STATE = Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_obsledger_status_current.json")
BUILD_OUT = Path("outputs/_sig_e_shadow_detector_obsledger1/sig_e_shadow_detector_obsledger1_build_result.json")

AUTHORITY = {
    "signal_authorized": False, "trade_proposal_authorized": False, "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False, "broker_execution_authorized": False, "auto_execution_authorized": False
}
BOUNDARY = ["OBSERVATION_LEDGER_ONLY","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_RISK_OR_POSITION_SIZING","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION","NO_MEMORY_PROMOTION","NO_RULE_REWRITE"]

STATUS_ORDER = ["INPUT_INSUFFICIENT","DATA_STALE","SESSION_NOT_MATCHED","REGIME_NOT_MATCHED","FIELD_MAPPING_INCOMPLETE","LIVE_OHLC_SOURCE_MISSING","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","SHADOW_MATCH_CONFIRMED","EXPIRED"]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def observation_run_id():
    gh = os.environ.get("GITHUB_RUN_ID")
    att = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    if gh:
        return f"GH_{gh}_{att}"
    return "LOCAL_" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def load_json(path):
    p=Path(path)
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None

def write_json(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def parse_dt(x):
    if x is None: return None
    s=str(x).strip()
    if not s: return None
    try:
        if s.endswith("Z"): return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception: return None

def detect_delimiter(line):
    return max([",",";","\t","|"],key=lambda c: line.count(c)) if line else ","

def pick_col(cols,names):
    low={c.lower().replace(" ","_"):c for c in cols}
    for n in names:
        k=n.lower().replace(" ","_")
        if k in low: return low[k]
    for c in cols:
        for n in names:
            if n.lower() in c.lower() or c.lower() in n.lower(): return c
    return None

def to_float(x):
    try:
        if x is None or str(x).strip()=="": return None
        return float(x)
    except Exception: return None

def read_csv_tail(path,max_tail=5000):
    if not path or not Path(path).exists(): return []
    with open(path,"r",encoding="utf-8",errors="replace") as f:
        first=f.readline(); delim=detect_delimiter(first); f.seek(0)
        rdr=csv.DictReader(f,delimiter=delim); rows=[]
        for row in rdr:
            rows.append(row)
            if len(rows)>max_tail: rows=rows[-max_tail:]
        return rows

def normalize_ohlc(rows):
    if not rows: return []
    cols=list(rows[0].keys())
    tc=pick_col(cols,["bar_open_ts_utc","timestamp","datetime","time","date"]); oc=pick_col(cols,["open","o"]); hc=pick_col(cols,["high","h"]); lc=pick_col(cols,["low","l"]); cc=pick_col(cols,["close","c"])
    out=[]
    for r in rows:
        ts=parse_dt(r.get(tc)) if tc else None; o=to_float(r.get(oc)) if oc else None; h=to_float(r.get(hc)) if hc else None; l=to_float(r.get(lc)) if lc else None; c=to_float(r.get(cc)) if cc else None
        if ts and None not in (o,h,l,c) and h>=l: out.append({"ts":ts,"open":o,"high":h,"low":l,"close":c})
    return sorted(out,key=lambda x:x["ts"])

def path_is_live_allowed(path):
    if not path: return False
    s=str(path).replace("\\","/").lower()
    if any(x in s for x in ["data/canonical/","data/raw/","data/features/","holdout_2020_2024","validation_2015_2019","discovery_2004_2014","future_after_2024"]): return False
    return "live" in s or s.startswith("panel/") or s.startswith("runtime/") or s.startswith("inputs/")

def load_state():
    s=load_json(LEDGER_STATE)
    if not isinstance(s,dict):
        s={"state_version":"sig_e_shadow_detector_obsledger_v1","program":PROGRAM,"created_utc":now(),"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"refresh_records":[],"near_miss_records":[],"shadow_events":[],"outcome_records":[]}
    s["program"]=PROGRAM; s["detector_id"]=DETECTOR_ID; s["source_spec_id"]=SOURCE_SPEC_ID; s["authority"]=AUTHORITY; s["boundary"]=BOUNDARY
    for k in ["refresh_records","near_miss_records","shadow_events","outcome_records"]:
        if not isinstance(s.get(k),list): s[k]=[]
    return s

def regime_details(det):
    for c in det.get("checks",[]):
        if c.get("check_id")=="REGIME": return c.get("details",{}) or {}
    return {}

def compact_record(det):
    rg=regime_details(det)
    obs_id=observation_run_id()
    return {
        "observation_run_id": obs_id,
        "record_id": obs_id + "|" + str(det.get("detector_run_id")),
        "detector_id": det.get("detector_id") or DETECTOR_ID,
        "source_spec_id": det.get("source_spec_id") or SOURCE_SPEC_ID,
        "detector_run_id": det.get("detector_run_id"),
        "created_utc": now(),
        "detector_created_utc": det.get("created_utc"),
        "detector_status": det.get("detector_status"),
        "status_reason": det.get("status_reason"),
        "is_shadow_match": det.get("is_shadow_match") is True,
        "instrument": det.get("instrument"),
        "direction": det.get("direction"),
        "session_bucket": rg.get("session_bucket"),
        "d1_trend_state": rg.get("d1_trend_state"),
        "h4_trend_state": rg.get("h4_trend_state"),
        "htf_alignment": rg.get("htf_alignment"),
        "volatility_state_or_d1_vol_bucket": rg.get("volatility_state_or_d1_vol_bucket"),
        "range_state": rg.get("range_state"),
        "tradeability_context": rg.get("tradeability_context"),
        "h1_bar_open_ts_utc": (det.get("surface_snapshot") or {}).get("h1_bar_open_ts_utc"),
        "m15_bar_open_ts_utc": (det.get("surface_snapshot") or {}).get("m15_bar_open_ts_utc"),
        "setup_h1_open_ts_utc": det.get("setup_h1_open_ts_utc"),
        "trigger_h1_open_ts_utc": det.get("trigger_h1_open_ts_utc"),
        "m15_confirm_ts_utc": det.get("m15_confirm_ts_utc"),
        "shadow_event_id": det.get("shadow_event_id"),
    }

def near_score(status):
    return {"REGIME_NOT_MATCHED":1,"SETUP_NOT_FORMED":2,"H1_TRIGGER_WAIT":3,"H1_TRIGGER_NOT_CONFIRMED":3,"M15_TRIGGER_WAIT":4,"SHADOW_MATCH_CONFIRMED":5}.get(status,0)

def maybe_event(det):
    if det.get("detector_status")!="SHADOW_MATCH_CONFIRMED" or not det.get("shadow_event_id"): return None
    trigger=det.get("trigger_h1_open_ts_utc")
    end=None
    t=parse_dt(trigger)
    if t: end=(t+timedelta(hours=16)).replace(microsecond=0).isoformat()+"Z"
    sp=det.get("source_paths") or {}
    return {"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"shadow_event_id":det.get("shadow_event_id"),"created_utc":det.get("created_utc"),"instrument":"USDJPY","direction":"LONG","detector_status":"SHADOW_MATCH_CONFIRMED","setup_h1_open_ts_utc":det.get("setup_h1_open_ts_utc"),"trigger_h1_open_ts_utc":trigger,"m15_confirm_ts_utc":det.get("m15_confirm_ts_utc"),"observation_horizon_h1_bars":16,"observation_end_ts_utc":end,"outcome_status":"PENDING","source_paths":{"h1_ohlc_path":sp.get("h1_ohlc_path"),"m15_ohlc_path":sp.get("m15_ohlc_path"),"live_source_policy":sp.get("live_source_policy")},"authority":AUTHORITY,"boundary":BOUNDARY}

def close_event(ev):
    if ev.get("outcome_status")=="CLOSED": return None
    h1=ev.get("source_paths",{}).get("h1_ohlc_path")
    if not path_is_live_allowed(h1): return None
    rows=normalize_ohlc(read_csv_tail(h1))
    trigger=parse_dt(ev.get("trigger_h1_open_ts_utc"))
    if not rows or not trigger: return None
    horizon=trigger+timedelta(hours=int(ev.get("observation_horizon_h1_bars",16)))
    tb=hb=None; highs=[]; lows=[]
    for r in rows:
        if r["ts"]==trigger: tb=r
        if r["ts"]==horizon: hb=r
        if trigger<=r["ts"]<=horizon:
            highs.append(r["high"]); lows.append(r["low"])
    if not tb or not hb: return None
    start=tb["close"]; end=hb["close"]; move=end-start
    out={"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"shadow_event_id":ev.get("shadow_event_id"),"closed_utc":now(),"trigger_h1_open_ts_utc":ev.get("trigger_h1_open_ts_utc"),"observation_end_ts_utc":horizon.replace(microsecond=0).isoformat()+"Z","direction":"LONG","trigger_close":start,"horizon_close":end,"close_to_close_move":move,"max_favorable_excursion":max(highs)-start if highs else None,"max_adverse_excursion":min(lows)-start if lows else None,"outcome_label":"FAVORABLE" if move>0 else ("ADVERSE" if move<0 else "NEUTRAL"),"authority":AUTHORITY,"boundary":BOUNDARY}
    ev["outcome_status"]="CLOSED"; ev["outcome_closed_utc"]=out["closed_utc"]; ev["outcome_label"]=out["outcome_label"]
    return out

def aggregate(s):
    refresh=s.get("refresh_records",[]); events=s.get("shadow_events",[]); outcomes=s.get("outcome_records",[])
    sc=Counter(r.get("detector_status") for r in refresh)
    last100=Counter(r.get("detector_status") for r in refresh[-100:])
    reasons=Counter(r.get("status_reason") for r in refresh if r.get("status_reason"))
    ec=Counter(e.get("outcome_status") for e in events); oc=Counter(o.get("outcome_label") for o in outcomes)
    return {"refresh_count_total":len(refresh),"status_counts_total":{k:v for k,v in sc.items() if k},"status_counts_last_100":{k:v for k,v in last100.items() if k},"top_status_reasons":dict(reasons.most_common(12)),"near_miss_count":len(s.get("near_miss_records",[])),"shadow_event_count":len(events),"pending_shadow_event_count":ec.get("PENDING",0),"closed_shadow_event_count":ec.get("CLOSED",0),"outcome_counts":dict(oc),"last_status":refresh[-1].get("detector_status") if refresh else None,"last_status_reason":refresh[-1].get("status_reason") if refresh else None,"last_shadow_event_id":events[-1].get("shadow_event_id") if events else None}

def main():
    det=load_json(DETECTOR_CURRENT); s=load_state()
    if not isinstance(det,dict):
        cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"BLOCKED","reason":"current detector json missing or invalid","detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"authority":AUTHORITY,"boundary":BOUNDARY}
        write_json(RUNTIME_OUT,cur); write_json(PANEL_OUT,cur); write_json(BUILD_OUT,cur); return
    rec=compact_record(det)
    existing={r.get("record_id") for r in s["refresh_records"] if isinstance(r,dict)}
    if rec.get("record_id") not in existing:
        s["refresh_records"].append(rec)
    if rec.get("detector_status") in {"REGIME_NOT_MATCHED","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","SHADOW_MATCH_CONFIRMED"}:
        n=dict(rec); n["near_miss_score"]=near_score(rec.get("detector_status"))
        nkey=n.get("record_id")+"|"+str(n.get("detector_status"))
        existing_n={str(x.get("record_id"))+"|"+str(x.get("detector_status")) for x in s["near_miss_records"] if isinstance(x,dict)}
        if nkey not in existing_n: s["near_miss_records"].append(n)
    ev=maybe_event(det)
    if ev and ev.get("shadow_event_id") not in {e.get("shadow_event_id") for e in s["shadow_events"] if isinstance(e,dict)}:
        s["shadow_events"].append(ev)
    existing_out={o.get("shadow_event_id") for o in s["outcome_records"] if isinstance(o,dict)}
    new_out=[]
    for ev in s["shadow_events"]:
        if isinstance(ev,dict) and ev.get("outcome_status")=="PENDING":
            out=close_event(ev)
            if out and out.get("shadow_event_id") not in existing_out:
                s["outcome_records"].append(out); existing_out.add(out.get("shadow_event_id")); new_out.append(out)
    s["refresh_records"]=s["refresh_records"][-20000:]; s["near_miss_records"]=s["near_miss_records"][-5000:]; s["shadow_events"]=s["shadow_events"][-1000:]; s["outcome_records"]=s["outcome_records"][-1000:]
    s["last_updated_utc"]=now(); s["authority"]=AUTHORITY; s["boundary"]=BOUNDARY
    summary=aggregate(s)
    cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"PASS","detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"latest_observation_run_id":rec.get("observation_run_id"),"latest_detector_run_id":rec.get("detector_run_id"),"latest_detector_status":rec.get("detector_status"),"latest_status_reason":rec.get("status_reason"),"summary":summary,"new_outcomes_closed_this_run":new_out,"latest_near_miss":s["near_miss_records"][-1] if s["near_miss_records"] else None,"latest_shadow_event":s["shadow_events"][-1] if s["shadow_events"] else None,"latest_outcome":s["outcome_records"][-1] if s["outcome_records"] else None,"authority":AUTHORITY,"boundary":BOUNDARY,"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    write_json(LEDGER_STATE,s); write_json(RUNTIME_OUT,cur); write_json(PANEL_OUT,cur); write_json(BUILD_OUT,{"program":"SIG-E-SHADOW-DETECTOR1-OBSLEDGER1-PERSIST1","created_utc":now(),"build_status":"PASS","summary":summary,"authority":AUTHORITY,"boundary":BOUNDARY})
    print("SIG_E_SHADOW_DETECTOR1_OBSLEDGER1_PERSIST1_DONE")
    print("REFRESH_COUNT_TOTAL="+str(summary.get("refresh_count_total")))
if __name__=="__main__":
    main()
