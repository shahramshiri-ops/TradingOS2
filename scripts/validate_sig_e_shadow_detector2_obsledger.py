import json
from pathlib import Path
from datetime import datetime
PROGRAM="SIG-E-SHADOW-DETECTOR2-OBSLEDGER1"
RUNTIME=Path("runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json")
PANEL=Path("panel/brain4/sig_e_shadow_detector2_obsledger_status_current.json")
STATE=Path("state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json")
OUT=Path("outputs/_sig_e_shadow_detector2_obsledger/sig_e_shadow_detector2_obsledger_validation_result.json")
FORBID=["signal_authorized","trade_proposal_authorized","entry_stop_target_authorized","risk_sizing_authorized","broker_execution_authorized","auto_execution_authorized"]
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    errors=[]; payload={}
    for n,p in [("runtime",RUNTIME),("panel",PANEL),("state",STATE)]:
        if not p.exists(): errors.append(f"missing {n}: {p}")
        else:
            try: payload[n]=load(p)
            except Exception as e: errors.append(f"bad json {n}: {e}")
    for n,o in payload.items():
        if o.get("program")!=PROGRAM: errors.append(f"{n} program mismatch")
        for k in FORBID:
            if (o.get("authority") or {}).get(k) is not False: errors.append(f"{n}.authority.{k} must be false")
    out={"program":PROGRAM,"created_utc":now(),"validation_status":"PASS" if not errors else "FAIL","errors":errors,"summary":(payload.get("runtime") or {}).get("summary"),"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print("SIG_E_SHADOW_DETECTOR2_OBSLEDGER_VALIDATION_"+out["validation_status"])
    if errors:
        for e in errors: print("ERROR:",e)
        raise SystemExit(1)
if __name__=="__main__": main()
