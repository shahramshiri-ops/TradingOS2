
import json, os
from pathlib import Path
from datetime import datetime
from collections import Counter

PROGRAM="SIG-E-SHADOW-DETECTOR1B-OVERLAP-DIAGNOSTIC-OBSLEDGER1"
DETECTOR_ID="SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"
SOURCE_SPEC_ID="SIG_E_RUNTIME_SPEC_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"
DETECTOR=Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json")
STATE=Path("state/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json")
RUNTIME=Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_obsledger_current.json")
PANEL=Path("panel/brain4/sig_e_shadow_detector1b_overlap_obsledger_status_current.json")
OUT=Path("outputs/_sig_e_shadow_detector1b_overlap_obsledger/sig_e_shadow_detector1b_overlap_obsledger_build_result.json")
AUTH={"signal_authorized":False,"trade_proposal_authorized":False,"entry_stop_target_authorized":False,"risk_sizing_authorized":False,"broker_execution_authorized":False,"auto_execution_authorized":False,"primary_lane_authorized":False,"lane_rule_change_authorized":False}
BOUND=["OBSERVATION_LEDGER_ONLY","DIAGNOSTIC_ONLY_LANE","OVERLAP_VARIANT_RESEARCH_ONLY","DOES_NOT_CHANGE_LANE1","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_RISK_OR_POSITION_SIZING","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION","NO_MEMORY_PROMOTION","NO_RULE_REWRITE"]

def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def obsid():
    gh=os.environ.get("GITHUB_RUN_ID"); at=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    return "GH_%s_%s"%(gh,at) if gh else "LOCAL_"+datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
def load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def state():
    s=load(STATE)
    if not isinstance(s,dict):
        s={"state_version":"sig_e_shadow_detector1b_overlap_obsledger_v1","program":PROGRAM,"created_utc":now(),"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"refresh_records":[],"near_miss_records":[],"shadow_events":[],"outcome_records":[]}
    s["program"]=PROGRAM; s["detector_id"]=DETECTOR_ID; s["source_spec_id"]=SOURCE_SPEC_ID; s["authority"]=AUTH; s["boundary"]=BOUND
    for k in ["refresh_records","near_miss_records","shadow_events","outcome_records"]:
        if not isinstance(s.get(k),list): s[k]=[]
    return s
def reg(d):
    for c in d.get("checks",[]):
        cid=str(c.get("check_id") or "")
        if "REGIME" in cid: return c.get("details",{}) or {}
    return {}
def compact(d):
    r=reg(d); oid=obsid()
    return {"observation_run_id":oid,"record_id":oid+"|"+str(d.get("detector_run_id")),"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"detector_run_id":d.get("detector_run_id"),"created_utc":now(),"detector_created_utc":d.get("created_utc"),"detector_status":d.get("detector_status"),"status_reason":d.get("status_reason"),"is_shadow_match":d.get("is_shadow_match") is True,"is_diagnostic_shadow_match":d.get("is_diagnostic_shadow_match") is True,"instrument":d.get("instrument"),"direction":d.get("direction"),"classification":d.get("classification"),"session_bucket":r.get("session_bucket"),"d1_trend_state":r.get("d1_trend_state"),"h4_trend_state":r.get("h4_trend_state"),"htf_alignment":r.get("htf_alignment"),"volatility_state_or_d1_vol_bucket":r.get("volatility_state_or_d1_vol_bucket"),"range_state":r.get("range_state"),"tradeability_context":r.get("tradeability_context"),"h1_bar_open_ts_utc":(d.get("surface_snapshot") or {}).get("h1_bar_open_ts_utc"),"m15_bar_open_ts_utc":(d.get("surface_snapshot") or {}).get("m15_bar_open_ts_utc"),"setup_h1_open_ts_utc":d.get("setup_h1_open_ts_utc"),"trigger_h1_open_ts_utc":d.get("trigger_h1_open_ts_utc"),"m15_confirm_ts_utc":d.get("m15_confirm_ts_utc"),"shadow_event_id":d.get("shadow_event_id")}
def score(status):
    return {"REGIME_NOT_MATCHED":1,"SETUP_NOT_FORMED":2,"H1_TRIGGER_WAIT":3,"H1_TRIGGER_NOT_CONFIRMED":3,"M15_TRIGGER_WAIT":4,"DIAGNOSTIC_SHADOW_MATCH_CONFIRMED":5}.get(status,0)
def main():
    d=load(DETECTOR); s=state()
    if not isinstance(d,dict):
        cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"BLOCKED","reason":"detector current missing","detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"authority":AUTH,"boundary":BOUND}
        write(RUNTIME,cur); write(PANEL,cur); write(OUT,cur); return
    r=compact(d)
    if r["record_id"] not in {x.get("record_id") for x in s["refresh_records"] if isinstance(x,dict)}: s["refresh_records"].append(r)
    near={"REGIME_NOT_MATCHED","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","DIAGNOSTIC_SHADOW_MATCH_CONFIRMED"}
    if r.get("detector_status") in near:
        key=r["record_id"]+"|"+str(r.get("detector_status"))
        ex={str(x.get("record_id"))+"|"+str(x.get("detector_status")) for x in s["near_miss_records"] if isinstance(x,dict)}
        if key not in ex:
            n=dict(r); n["near_miss_score"]=score(r.get("detector_status")); s["near_miss_records"].append(n)
    if d.get("detector_status")=="DIAGNOSTIC_SHADOW_MATCH_CONFIRMED" and d.get("shadow_event_id"):
        if d.get("shadow_event_id") not in {e.get("shadow_event_id") for e in s["shadow_events"] if isinstance(e,dict)}:
            s["shadow_events"].append({"detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"shadow_event_id":d.get("shadow_event_id"),"created_utc":d.get("created_utc"),"instrument":"USDJPY","direction":"LONG","classification":"DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY","detector_status":d.get("detector_status"),"setup_h1_open_ts_utc":d.get("setup_h1_open_ts_utc"),"trigger_h1_open_ts_utc":d.get("trigger_h1_open_ts_utc"),"observation_horizon_h1_bars":12,"outcome_status":"PENDING","authority":AUTH,"boundary":BOUND})
    s["refresh_records"]=s["refresh_records"][-20000:]; s["near_miss_records"]=s["near_miss_records"][-5000:]; s["shadow_events"]=s["shadow_events"][-1000:]; s["last_updated_utc"]=now()
    counts=Counter(x.get("detector_status") for x in s["refresh_records"])
    cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"PASS","detector_id":DETECTOR_ID,"source_spec_id":SOURCE_SPEC_ID,"latest_observation_run_id":r.get("observation_run_id"),"latest_detector_run_id":r.get("detector_run_id"),"latest_detector_status":r.get("detector_status"),"latest_status_reason":r.get("status_reason"),"summary":{"refresh_count_total":len(s["refresh_records"]),"status_counts_total":dict(counts),"near_miss_count":len(s["near_miss_records"]),"diagnostic_shadow_event_count":len(s["shadow_events"]),"last_status":r.get("detector_status"),"last_status_reason":r.get("status_reason"),"last_shadow_event_id":s["shadow_events"][-1].get("shadow_event_id") if s["shadow_events"] else None},"latest_near_miss":s["near_miss_records"][-1] if s["near_miss_records"] else None,"latest_shadow_event":s["shadow_events"][-1] if s["shadow_events"] else None,"authority":AUTH,"boundary":BOUND,"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","primary lane promotion","Lane1 rule change"]}
    write(STATE,s); write(RUNTIME,cur); write(PANEL,cur); write(OUT,{"program":PROGRAM,"created_utc":now(),"build_status":"PASS","summary":cur["summary"],"authority":AUTH,"boundary":BOUND})
    print("SIG_E_SHADOW_DETECTOR1B_OVERLAP_OBSLEDGER_DONE")
    print("LATEST_STATUS="+str(cur.get("latest_detector_status")))
if __name__=="__main__": main()
