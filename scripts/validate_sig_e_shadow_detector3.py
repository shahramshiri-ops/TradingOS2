
import json
from pathlib import Path
from datetime import datetime
RUNTIME=Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json")
PANEL=Path("panel/brain4/sig_e_shadow_detector3_status_current.json")
STATE=Path("state/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json")
OUT=Path("outputs/_sig_e_shadow_detector3/sig_e_shadow_detector3_validation_result.json")
VALID={"INPUT_INSUFFICIENT","DATA_STALE","SESSION_NOT_MATCHED","REGIME_NOT_MATCHED","LIVE_OHLC_SOURCE_MISSING","LIVE_H1_HISTORY_INSUFFICIENT","LIVE_M15_HISTORY_INSUFFICIENT","REFERENCE_LEVEL_UNAVAILABLE","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","SHADOW_MATCH_CONFIRMED","EXPIRED"}
FORBID=["signal_authorized","trade_proposal_authorized","entry_stop_target_authorized","risk_sizing_authorized","broker_execution_authorized","auto_execution_authorized"]
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def forbidden(path):
    s=str(path or "").replace("\\","/").lower()
    return any(x in s for x in ["data/canonical/","data/raw/","data/features/","holdout_2020_2024","validation_2015_2019","discovery_2004_2014","future_after_2024"])
def main():
    errors=[]; payload={}
    for name,p in [("runtime",RUNTIME),("panel",PANEL),("state",STATE)]:
        if not p.exists(): errors.append(f"missing {name}: {p}")
        else:
            try: payload[name]=load(p)
            except Exception as e: errors.append(f"bad json {name}: {e}")
    r=payload.get("runtime",{})
    if r.get("program")!="SIG-E-RUNTIME-SHADOW-DETECTOR3": errors.append("runtime program mismatch")
    if r.get("detector_status") not in VALID: errors.append("invalid detector_status")
    if r.get("is_signal") is not False: errors.append("is_signal must be false")
    if r.get("is_trade_proposal") is not False: errors.append("is_trade_proposal must be false")
    for k in FORBID:
        if (r.get("authority") or {}).get(k) is not False: errors.append(f"authority.{k} must be false")
    sp=r.get("source_paths") or {}
    for k in ["h1_ohlc_path","m15_ohlc_path"]:
        if forbidden(sp.get(k)): errors.append(f"{k} forbidden source path: {sp.get(k)}")
    result={"program":"SIG-E-RUNTIME-SHADOW-DETECTOR3","created_utc":now(),"validation_status":"PASS" if not errors else "FAIL","errors":errors,"detector_status":r.get("detector_status"),"status_reason":r.get("status_reason"),"is_shadow_match":r.get("is_shadow_match"),"data_counts":r.get("data_counts"),"source_paths":r.get("source_paths"),"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SIG_E_SHADOW_DETECTOR3_VALIDATION_"+result["validation_status"])
    if errors:
        for e in errors: print("ERROR:",e)
        raise SystemExit(1)
if __name__=="__main__": main()
