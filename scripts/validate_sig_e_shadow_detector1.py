import json
from pathlib import Path
from datetime import datetime

RUNTIME_OUT=Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
PANEL_OUT=Path("panel/brain4/sig_e_shadow_detector_status_current.json")
STATE_PATH=Path("state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json")
VALIDATION_OUT=Path("outputs/_sig_e_shadow_detector1/sig_e_shadow_detector1_validation_result.json")
VALID_STATUS={"INPUT_INSUFFICIENT","DATA_STALE","SESSION_NOT_MATCHED","REGIME_NOT_MATCHED","FIELD_MAPPING_INCOMPLETE","LIVE_OHLC_SOURCE_MISSING","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","SHADOW_MATCH_CONFIRMED","EXPIRED"}
FORBIDDEN=["signal_authorized","trade_proposal_authorized","entry_stop_target_authorized","risk_sizing_authorized","broker_execution_authorized","auto_execution_authorized"]
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    errors=[]; payloads={}
    for name,p in [("runtime",RUNTIME_OUT),("panel",PANEL_OUT),("state",STATE_PATH)]:
        if not p.exists(): errors.append(f"missing {name} output: {p}")
        else:
            try: payloads[name]=load(p)
            except Exception as e: errors.append(f"invalid json {name}: {e}")
    r=payloads.get("runtime",{}); p=payloads.get("panel",{})
    if r.get("program")!="SIG-E-RUNTIME-SHADOW-DETECTOR1": errors.append("runtime program mismatch")
    if p.get("program")!="SIG-E-RUNTIME-SHADOW-DETECTOR1": errors.append("panel program mismatch")
    if r.get("detector_status") not in VALID_STATUS: errors.append("invalid detector_status: "+str(r.get("detector_status")))
    if r.get("is_signal") is not False: errors.append("is_signal must be false")
    if r.get("is_trade_proposal") is not False: errors.append("is_trade_proposal must be false")
    auth=r.get("authority",{})
    for k in FORBIDDEN:
        if auth.get(k) is not False: errors.append(f"authority.{k} must be false")
    required={"SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_RISK_OR_POSITION_SIZING","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION","NO_MEMORY_PROMOTION","NO_RULE_REWRITE"}
    miss=sorted(required-set(r.get("boundary",[])))
    if miss: errors.append("missing boundary constants: "+", ".join(miss))
    sp=r.get("source_paths",{})
    for k in ["h1_ohlc_path","m15_ohlc_path"]:
        x=str(sp.get(k) or "").replace("\\","/").lower()
        if "data/canonical/" in x or "data/raw/" in x or "data/features/" in x:
            errors.append(f"{k} uses forbidden historical path: {x}")
    if r.get("is_shadow_match") is True and r.get("detector_status")!="SHADOW_MATCH_CONFIRMED": errors.append("is_shadow_match true requires SHADOW_MATCH_CONFIRMED")
    out={"program":"SIG-E-RUNTIME-SHADOW-DETECTOR1-HOTFIX1","created_utc":now(),"validation_status":"PASS" if not errors else "FAIL","errors":errors,"detector_status":r.get("detector_status"),"status_reason":r.get("status_reason"),"is_shadow_match":r.get("is_shadow_match"),"surface_snapshot":r.get("surface_snapshot"),"source_paths":r.get("source_paths"),"current_runtime_authority":auth,"next_allowed_use":"LIVE_SHADOW_OBSERVATION_ONLY","not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    VALIDATION_OUT.parent.mkdir(parents=True,exist_ok=True); VALIDATION_OUT.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print("SIG_E_SHADOW_DETECTOR1_HOTFIX1_VALIDATION_"+out["validation_status"])
    if errors:
        for e in errors: print("ERROR:",e)
        raise SystemExit(1)
if __name__=="__main__":
    main()
