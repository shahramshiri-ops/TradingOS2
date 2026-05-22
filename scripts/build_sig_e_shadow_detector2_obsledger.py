import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

PROGRAM="SIG-E-SHADOW-DETECTOR2-OBSLEDGER1"
DETECTOR=Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_current.json")
STATE=Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json")
RUNTIME=Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json")
PANEL=Path("panel/brain4/sig_e_shadow_detector2_obsledger_status_current.json")
OUT=Path("outputs/_sig_e_shadow_detector2_obsledger/sig_e_shadow_detector2_obsledger_build_result.json")
AUTH={"signal_authorized":False,"trade_proposal_authorized":False,"entry_stop_target_authorized":False,"risk_sizing_authorized":False,"broker_execution_authorized":False,"auto_execution_authorized":False}
BOUND=["OBSERVATION_LEDGER_ONLY","CAVEATED_OBSERVATION_ONLY","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_RISK_OR_POSITION_SIZING","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION","NO_MEMORY_PROMOTION","NO_RULE_REWRITE"]
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def state():
    s=load(STATE)
    if not isinstance(s,dict): s={"state_version":"sig_e_shadow_detector2_obsledger_v1","program":PROGRAM,"created_utc":now(),"detector_id":"SIG_E_SHADOW_DETECTOR_USDJPY_ASIA_SHORT_H1_M15_CAVEATED_v1_0","refresh_records":[],"near_miss_records":[],"shadow_events":[],"outcome_records":[]}
    for k in ["refresh_records","near_miss_records","shadow_events","outcome_records"]:
        if not isinstance(s.get(k),list): s[k]=[]
    return s
def reg_details(d):
    for c in d.get("checks",[]):
        if c.get("check_id")=="REGIME": return c.get("details",{}) or {}
    return {}
def compact(d):
    rg=reg_details(d)
    return {"detector_run_id":d.get("detector_run_id"),"created_utc":d.get("created_utc"),"detector_status":d.get("detector_status"),"status_reason":d.get("status_reason"),"is_shadow_match":d.get("is_shadow_match") is True,"instrument":d.get("instrument"),"direction":d.get("direction"),"session_bucket":rg.get("session_bucket"),"d1_trend_state":rg.get("d1_trend_state"),"h4_trend_state":rg.get("h4_trend_state"),"htf_alignment":rg.get("htf_alignment"),"range_state":rg.get("range_state"),"h1_bar_open_ts_utc":(d.get("surface_snapshot") or {}).get("h1_bar_open_ts_utc"),"m15_bar_open_ts_utc":(d.get("surface_snapshot") or {}).get("m15_bar_open_ts_utc"),"setup_h1_open_ts_utc":d.get("setup_h1_open_ts_utc"),"trigger_h1_open_ts_utc":d.get("trigger_h1_open_ts_utc"),"shadow_event_id":d.get("shadow_event_id")}
def nm_score(s): return {"REGIME_NOT_MATCHED":1,"SETUP_NOT_FORMED":2,"H1_TRIGGER_WAIT":3,"H1_TRIGGER_NOT_CONFIRMED":3,"M15_NO_FAILURE_POLICY_WAIT":4,"M15_FAILURE_BLOCKED":4,"CAVEATED_SHADOW_MATCH_CONFIRMED":5}.get(s,0)
def build():
    d=load(DETECTOR)
    s=state()
    if not isinstance(d,dict):
        cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"BLOCKED","reason":"detector current missing","authority":AUTH,"boundary":BOUND}
        write(RUNTIME,cur); write(PANEL,cur); write(OUT,cur); return cur
    r=compact(d); rid=r.get("detector_run_id")
    if rid not in {x.get("detector_run_id") for x in s["refresh_records"] if isinstance(x,dict)}: s["refresh_records"].append(r)
    if r.get("detector_status") in {"REGIME_NOT_MATCHED","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_NO_FAILURE_POLICY_WAIT","M15_FAILURE_BLOCKED","CAVEATED_SHADOW_MATCH_CONFIRMED"}:
        k=str(rid)+"|"+str(r.get("detector_status"))
        ex={str(x.get("detector_run_id"))+"|"+str(x.get("detector_status")) for x in s["near_miss_records"] if isinstance(x,dict)}
        if k not in ex:
            n=dict(r); n["near_miss_score"]=nm_score(r.get("detector_status")); s["near_miss_records"].append(n)
    if d.get("detector_status")=="CAVEATED_SHADOW_MATCH_CONFIRMED" and d.get("shadow_event_id"):
        if d.get("shadow_event_id") not in {e.get("shadow_event_id") for e in s["shadow_events"] if isinstance(e,dict)}:
            s["shadow_events"].append({"shadow_event_id":d.get("shadow_event_id"),"created_utc":d.get("created_utc"),"instrument":"USDJPY","direction":"SHORT","classification":"CAVEATED_OBSERVATION_ONLY","detector_status":d.get("detector_status"),"setup_h1_open_ts_utc":d.get("setup_h1_open_ts_utc"),"trigger_h1_open_ts_utc":d.get("trigger_h1_open_ts_utc"),"observation_horizon_h1_bars":8,"outcome_status":"PENDING","authority":AUTH})
    s["refresh_records"]=s["refresh_records"][-20000:]; s["near_miss_records"]=s["near_miss_records"][-5000:]; s["shadow_events"]=s["shadow_events"][-1000:]
    s["last_updated_utc"]=now(); s["authority"]=AUTH; s["boundary"]=BOUND
    counts=Counter(x.get("detector_status") for x in s["refresh_records"])
    cur={"program":PROGRAM,"created_utc":now(),"ledger_status":"PASS","detector_id":s.get("detector_id"),"latest_detector_run_id":rid,"latest_detector_status":r.get("detector_status"),"latest_status_reason":r.get("status_reason"),"summary":{"refresh_count_total":len(s["refresh_records"]),"status_counts_total":dict(counts),"near_miss_count":len(s["near_miss_records"]),"shadow_event_count":len(s["shadow_events"]),"last_status":r.get("detector_status"),"last_status_reason":r.get("status_reason"),"last_shadow_event_id":s["shadow_events"][-1].get("shadow_event_id") if s["shadow_events"] else None},"latest_near_miss":s["near_miss_records"][-1] if s["near_miss_records"] else None,"latest_shadow_event":s["shadow_events"][-1] if s["shadow_events"] else None,"authority":AUTH,"boundary":BOUND,"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    write(STATE,s); write(RUNTIME,cur); write(PANEL,cur); write(OUT,{"program":PROGRAM,"created_utc":now(),"build_status":"PASS","summary":cur["summary"],"authority":AUTH,"boundary":BOUND})
    return cur
def main():
    cur=build()
    print("SIG_E_SHADOW_DETECTOR2_OBSLEDGER_DONE")
    print("LEDGER_STATUS="+str(cur.get("ledger_status")))
    print("LATEST_DETECTOR_STATUS="+str(cur.get("latest_detector_status")))
if __name__=="__main__": main()
