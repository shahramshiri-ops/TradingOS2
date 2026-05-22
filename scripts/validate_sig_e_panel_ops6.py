import json
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-PANEL-OPS6-VALIDATION"
FILES = {"index": Path("panel/brain4/index.html"), "css": Path("panel/brain4/assets/sig_e_panel_ops6.css"), "js": Path("panel/brain4/assets/sig_e_panel_ops6.js")}
OUT = Path("outputs/_sig_e_panel_ops6/sig_e_panel_ops6_validation_result.json")
REQ = {
    "index": ["SIG-E-PANEL-OPS6_ACTIVE_SHADOW_COCKPIT_v1_0","Shadow Research Cockpit","NOT A SIGNAL","NO ENTRY","sig_e_panel_ops6.js","sig_e_panel_ops6.css"],
    "css": ["--bg:",".lanes",".boundary","@media(max-width:680px)"],
    "js": ["SIG-E-PANEL-OPS6_ACTIVE_SHADOW_COCKPIT_v1_0","shadow_portfolio_current.json","shadow_coverage1_current.json","DIAGNOSTIC","NOT A SIGNAL","NO ENTRY","statusStage","renderLanes"],
}
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def main():
    errors=[]; checks={}
    for k,p in FILES.items():
        item={"path":str(p),"exists":p.exists(),"missing_markers":[]}
        if not p.exists(): errors.append(f"missing {k}: {p}")
        else:
            t=p.read_text(encoding="utf-8")
            for m in REQ[k]:
                if m not in t:
                    item["missing_markers"].append(m); errors.append(f"{k} missing marker: {m}")
        checks[k]=item
    res={"program":PROGRAM,"created_utc":now(),"validation_status":"PASS" if not errors else "FAIL","errors":errors,"checks":checks,"boundary":["DISPLAY_ONLY","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION"]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SIG_E_PANEL_OPS6_VALIDATION_"+res["validation_status"])
    if errors:
        for e in errors: print("ERROR:",e)
        raise SystemExit(1)
if __name__=="__main__": main()
