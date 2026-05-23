import json
from pathlib import Path
from datetime import datetime
PROGRAM="SIG-E-PANEL-OPS6D-COMPACT-LIGHT-POLISH-VALIDATION"
FILES={"index":Path("panel/brain4/index.html"),"css":Path("panel/brain4/assets/sig_e_panel_ops6b.css"),"js":Path("panel/brain4/assets/sig_e_panel_ops6b.js")}
OUT=Path("outputs/_sig_e_panel_ops6d/sig_e_panel_ops6d_validation_result.json")
MARKERS={"index":["SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0","Shadow Research Console","tabUpdateAge","Cockpit","Diagnostics"],"css":["SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0","Light, compact, modern UI polish","color-scheme:light","Force light UI","min-height:162px"],"js":["SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0","function updateTabRefreshAge","tabUpdateAge","NOT A SIGNAL","NO ENTRY"]}
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def main():
    errors=[]; checks={}
    for k,p in FILES.items():
        item={"path":str(p),"exists":p.exists(),"missing_markers":[]}
        if not p.exists(): errors.append(f"missing {k}: {p}")
        else:
            text=p.read_text(encoding="utf-8")
            for m in MARKERS[k]:
                if m not in text:
                    item["missing_markers"].append(m); errors.append(f"{k} missing marker: {m}")
        checks[k]=item
    result={"program":PROGRAM,"created_utc":now(),"validation_status":"PASS" if not errors else "FAIL","errors":errors,"checks":checks,"boundary":["PANEL_VISUAL_POLISH_ONLY","DISPLAY_ONLY","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION"]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SIG_E_PANEL_OPS6D_VALIDATION_"+result["validation_status"])
    if errors:
        for e in errors: print("ERROR:",e)
        raise SystemExit(1)
if __name__=="__main__": main()
