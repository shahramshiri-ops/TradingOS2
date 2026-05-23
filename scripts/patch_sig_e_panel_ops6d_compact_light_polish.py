import json, shutil
from pathlib import Path
from datetime import datetime

PROGRAM="SIG-E-PANEL-OPS6D-COMPACT-LIGHT-POLISH"
INDEX=Path("panel/brain4/index.html")
CSS=Path("panel/brain4/assets/sig_e_panel_ops6b.css")
JS=Path("panel/brain4/assets/sig_e_panel_ops6b.js")
OUT=Path("outputs/_sig_e_panel_ops6d/sig_e_panel_ops6d_compact_light_result.json")
CSS_APPEND='\n/* SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0 */\n:root{\n  --bg:#f5f8fb!important;--bg-soft:#fff!important;--panel:rgba(255,255,255,.86)!important;\n  --panel-strong:rgba(255,255,255,.96)!important;--line:rgba(30,64,89,.12)!important;\n  --line-strong:rgba(30,64,89,.20)!important;--text:#152536!important;--muted:#607386!important;\n  --faint:#8395a6!important;--ink-strong:#071725!important;--accent:#0ea5b7!important;\n  --accent-2:#22c55e!important;--ok:#16a34a!important;--warn:#b7791f!important;--danger:#dc2626!important;\n  --shadow:0 16px 40px rgba(22,55,78,.10)!important;--radius-xl:22px!important;--radius-lg:18px!important;\n}\nhtml,html[data-panel]{color-scheme:light!important;background:\n  radial-gradient(circle at 12% 0%,rgba(14,165,183,.12),transparent 34rem),\n  radial-gradient(circle at 88% 10%,rgba(34,197,94,.10),transparent 30rem),\n  linear-gradient(145deg,#f5f8fb 0%,#eef6f9 50%,#fbfdff 100%)!important}\nbody{background:transparent!important;color:var(--text)!important;-webkit-font-smoothing:antialiased}\n.app-shell{width:min(1120px,calc(100% - 32px))!important;padding-top:20px!important;padding-bottom:28px!important}\n.topbar{padding:4px 0 14px!important}.brand-mark{width:42px!important;height:42px!important;border-radius:16px!important;padding:10px!important;background:linear-gradient(145deg,rgba(14,165,183,.10),rgba(34,197,94,.06))!important;border-color:rgba(14,165,183,.16)!important;box-shadow:0 10px 24px rgba(18,54,74,.08)!important}\nh1{font-size:clamp(1.45rem,2.2vw,1.9rem)!important;letter-spacing:-.045em!important}h2{font-size:clamp(1.12rem,1.9vw,1.45rem)!important}h3{font-size:.98rem!important}\nh1,h2,h3,.hero-status h2,.metric-card strong,.ops-card strong,.debug-card strong,.memory-card strong,.diagnostic-card strong{color:var(--ink-strong)!important;text-shadow:none!important}\n.eyebrow,.label,.lane-kicker{color:var(--faint)!important;font-size:.68rem!important;letter-spacing:.10em!important}\n.hero-card,.metric-card,.focus-card,.lane-card,.ops-card,.boundary-card,.debug-card,.memory-card,.history-card,.diagnostic-card{color:var(--text)!important;background:linear-gradient(145deg,rgba(255,255,255,.94),rgba(245,250,253,.88))!important;border-color:var(--line)!important;box-shadow:0 16px 40px rgba(22,55,78,.10),inset 0 1px 0 rgba(255,255,255,.74)!important}\n.hero-card,.focus-card,.boundary-card{border-radius:22px!important}.metric-card,.ops-card,.debug-card,.memory-card,.diagnostic-card,.lane-card,.history-card{border-radius:20px!important}\n.hero-grid{gap:12px!important;grid-template-columns:minmax(0,1.55fr) repeat(3,minmax(118px,.48fr))!important}\n.hero-card,.metric-card{min-height:162px!important;padding:18px 20px!important}\n.hero-status h2{margin:22px 0 8px!important;max-width:460px!important;font-size:clamp(2rem,4vw,3.15rem)!important;line-height:.98!important;letter-spacing:-.065em!important}\n.hero-status .muted,.metric-card span,.ops-card span,.debug-card span,.memory-card span,.diagnostic-card span,.lane-reason,.boundary-card p,.section-lead{color:var(--muted)!important}\n.metric-card strong,.ops-card strong,.debug-card strong,.memory-card strong,.diagnostic-card strong{margin-top:14px!important;font-size:clamp(1.85rem,3.8vw,2.55rem)!important;letter-spacing:-.06em!important}\n.hero-meta{margin-top:14px!important}.hero-meta span,.lane-meta span,.mini-meta span{color:#44586b!important;background:rgba(255,255,255,.76)!important;border-color:rgba(26,57,82,.10)!important;font-size:.74rem!important;padding:6px 9px!important;box-shadow:0 4px 12px rgba(22,55,78,.05)}\n.tabbar-shell{gap:10px!important;padding:7px!important;margin:0 0 14px!important;border:1px solid rgba(26,57,82,.12)!important;border-radius:24px!important;background:rgba(255,255,255,.70)!important;box-shadow:0 12px 32px rgba(22,55,78,.08)!important;backdrop-filter:blur(18px)}\n.tabbar-shell .tabbar{flex:1;min-width:0;margin:0!important;padding:0!important;border:0!important;background:transparent!important;box-shadow:none!important}\n.tab{min-height:36px!important;padding:0 13px!important;color:#486074!important;font-size:.78rem!important;font-weight:900!important}.tab:hover{color:var(--ink-strong)!important;background:rgba(14,165,183,.08)!important}.tab.active{color:#06252b!important;background:linear-gradient(145deg,#8ff3e6,#6ee7b7)!important;box-shadow:0 8px 20px rgba(14,165,183,.16),inset 0 1px 0 rgba(255,255,255,.72)!important}\n.tab-update-age,.tab-update-time,.system-pill,.section-badge,.safety-chip,.lane-badge,.icon-button,.boundary-tags span{min-height:30px!important;background:rgba(255,255,255,.78)!important;border-color:rgba(26,57,82,.10)!important;color:#2f485d!important;box-shadow:0 4px 14px rgba(22,55,78,.06);font-size:.74rem!important}\n.system-pill.ok{color:#14532d!important;background:rgba(220,252,231,.82)!important;border-color:rgba(22,163,74,.20)!important}.tab-update-age:before{background:var(--ok)!important;box-shadow:0 0 0 4px rgba(22,163,74,.12)!important}.tab-update-age.warn:before{background:var(--warn)!important}.tab-update-age.danger:before{background:var(--danger)!important}\n.focus-card,.lane-section,.boundary-card{padding:18px 20px!important;margin-top:12px!important}.active-events{margin-top:14px!important}.empty-state{padding:14px!important;background:rgba(255,255,255,.52)!important;border-color:rgba(26,57,82,.16)!important}.empty-icon{width:40px!important;height:40px!important;border-radius:14px!important;color:#5d7082!important;background:rgba(255,255,255,.72)!important;border-color:rgba(26,57,82,.10)!important}\n.lane-grid,.memory-grid,.debug-grid,.diagnostics-grid{gap:12px!important;margin-top:14px!important}.lane-card{min-height:210px!important;padding:16px!important}.lane-status-row{margin:16px 0 6px!important}.lane-status{font-size:1rem!important}.lane-reason{min-height:38px!important;font-size:.82rem!important;line-height:1.38!important}\n.stage-rail{margin:14px 0 12px!important;gap:4px!important}.stage-rail span{min-height:6px!important;background:rgba(26,57,82,.08)!important;border-color:rgba(26,57,82,.04)!important}.stage-rail span.done{background:rgba(34,197,94,.65)!important}.stage-rail span.current{background:rgba(217,119,6,.70)!important}.stage-rail span.blocked{background:rgba(220,38,38,.62)!important}.status-dot{width:10px!important;height:10px!important}\n.ops-grid{gap:12px!important;margin-top:12px!important}.ops-card,.debug-card,.memory-card,.diagnostic-card{min-height:136px!important;padding:16px 18px!important}.debug-card strong,.memory-card strong,.diagnostic-card strong{font-size:clamp(1.75rem,3.5vw,2.35rem)!important}\n.boundary-card{background:linear-gradient(145deg,rgba(255,255,255,.88),rgba(255,247,247,.76))!important;border-color:rgba(220,38,38,.12)!important}.boundary-tags span{color:#7f1d1d!important;border-color:rgba(220,38,38,.16)!important;background:rgba(254,226,226,.74)!important}\n@media (prefers-color-scheme:dark){:root{--bg:#f5f8fb!important;--text:#152536!important;--muted:#607386!important;--faint:#8395a6!important}html,html[data-panel]{color-scheme:light!important;background:radial-gradient(circle at 12% 0%,rgba(14,165,183,.12),transparent 34rem),radial-gradient(circle at 88% 10%,rgba(34,197,94,.10),transparent 30rem),linear-gradient(145deg,#f5f8fb 0%,#eef6f9 50%,#fbfdff 100%)!important}}\n@media (max-width:1040px){.hero-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important}.hero-status{grid-column:1/-1!important}}\n@media (max-width:820px){.tabbar-shell{align-items:stretch;flex-direction:column;border-radius:22px!important}.tab-meta{justify-content:space-between}.tabbar-shell .tabbar{width:100%}}\n@media (max-width:680px){.app-shell{width:min(100% - 18px,1120px)!important;padding-top:16px!important}.hero-card,.metric-card{min-height:130px!important}.hero-status h2{font-size:clamp(1.9rem,11vw,2.7rem)!important}.tab-update-time{display:none}}\n'

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def backup(path):
    b=path.with_suffix(path.suffix+".bak_ops6d")
    shutil.copyfile(path,b)
    return str(b)

def patch_index():
    item={"file":str(INDEX),"exists":INDEX.exists(),"patched":False,"reason":None}
    if not INDEX.exists():
        item["reason"]="MISSING"; return item
    text=INDEX.read_text(encoding="utf-8"); old=text
    text=text.replace("SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0","SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0")
    text=text.replace("SIG-E-PANEL-OPS6B_TABBED_RESEARCH_CONSOLE_v1_0","SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0")
    text=text.replace("TradingOS · SIG-E Research Console · OPS6C","TradingOS · SIG-E Research Console · OPS6D")
    text=text.replace("TradingOS · SIG-E Research Console","TradingOS · SIG-E Research Console · OPS6D")
    if text!=old:
        item["backup"]=backup(INDEX); INDEX.write_text(text,encoding="utf-8"); item["patched"]=True; item["reason"]="INDEX_VERSION_UPDATED"
    else:
        item["reason"]="ALREADY_PRESENT"
    return item

def patch_css():
    item={"file":str(CSS),"exists":CSS.exists(),"patched":False,"reason":None}
    if not CSS.exists():
        item["reason"]="MISSING"; return item
    text=CSS.read_text(encoding="utf-8")
    if "SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0" in text:
        item["reason"]="ALREADY_PRESENT"; return item
    item["backup"]=backup(CSS)
    CSS.write_text(text.rstrip()+"\n\n"+CSS_APPEND+"\n",encoding="utf-8")
    item["patched"]=True; item["reason"]="CSS_COMPACT_LIGHT_POLISH_APPENDED"
    return item

def patch_js():
    item={"file":str(JS),"exists":JS.exists(),"patched":False,"reason":None}
    if not JS.exists():
        item["reason"]="MISSING"; return item
    text=JS.read_text(encoding="utf-8"); old=text
    text=text.replace("SIG-E-PANEL-OPS6C_VISUAL_POLISH_v1_0","SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0")
    text=text.replace("SIG-E-PANEL-OPS6B_TABBED_RESEARCH_CONSOLE_v1_0","SIG-E-PANEL-OPS6D_COMPACT_LIGHT_POLISH_v1_0")
    if text!=old:
        item["backup"]=backup(JS); JS.write_text(text,encoding="utf-8"); item["patched"]=True; item["reason"]="JS_VERSION_UPDATED"
    else:
        item["reason"]="ALREADY_PRESENT"
    return item

def main():
    results=[patch_index(),patch_css(),patch_js()]
    status="PASS" if all(r.get("patched") or r.get("reason")=="ALREADY_PRESENT" for r in results) else "PARTIAL_OR_FAIL"
    result={"program":PROGRAM,"created_utc":now(),"patch_status":status,"results":results,"changes":["light-first UI","smaller hero fonts","smaller cards","compact modern hierarchy"],"boundary":["PANEL_VISUAL_POLISH_ONLY","DISPLAY_ONLY","SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION"]}
    write_json(OUT,result)
    print("SIG_E_PANEL_OPS6D_COMPACT_LIGHT_POLISH_"+status)
    for r in results: print(r["file"]+" -> "+str(r["reason"]))
    if status!="PASS": raise SystemExit(2)
if __name__=="__main__": main()
