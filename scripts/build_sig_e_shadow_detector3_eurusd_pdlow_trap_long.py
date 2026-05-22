
import csv, gzip, json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROGRAM="SIG-E-RUNTIME-SHADOW-DETECTOR3"
DETECTOR_ID="SIG_E_SHADOW_DETECTOR_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15_v1_0"
SOURCE_SPEC_ID="SIG_E_RUNTIME_SPEC_EURUSD_LONDON_PDLOW_TRAP_LONG_H1_M15_v1_0"
CONFIG=Path("config/sig_e/shadow_detectors/eurusd_london_pdlow_trap_long_h1_m15_v1_0.json")
RUNTIME=Path("runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json")
PANEL=Path("panel/brain4/sig_e_shadow_detector3_status_current.json")
STATE=Path("state/sig_e_shadow_detector3/eurusd_london_pdlow_trap_long_state_v1.json")
OUT=Path("outputs/_sig_e_shadow_detector3/sig_e_shadow_detector3_build_result.json")
AUTH={"signal_authorized":False,"trade_proposal_authorized":False,"entry_stop_target_authorized":False,"risk_sizing_authorized":False,"broker_execution_authorized":False,"auto_execution_authorized":False}
BOUND=["SHADOW_RESEARCH_ONLY","NOT_SIGNAL","NO_TRADE_PROPOSAL","NO_ENTRY_STOP_TARGET","NO_RISK_OR_POSITION_SIZING","NO_BROKER_EXECUTION","NO_AUTO_EXECUTION","NO_MEMORY_PROMOTION","NO_RULE_REWRITE"]
VALID={"INPUT_INSUFFICIENT","DATA_STALE","SESSION_NOT_MATCHED","REGIME_NOT_MATCHED","LIVE_OHLC_SOURCE_MISSING","LIVE_H1_HISTORY_INSUFFICIENT","LIVE_M15_HISTORY_INSUFFICIENT","REFERENCE_LEVEL_UNAVAILABLE","SETUP_NOT_FORMED","H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT","SHADOW_MATCH_CONFIRMED","EXPIRED"}

def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def dt(x):
    if x is None: return None
    s=str(x).strip()
    if not s: return None
    try:
        if s.endswith("Z"): return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception: pass
    for f in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y.%m.%d %H:%M:%S","%Y.%m.%d %H:%M"):
        try: return datetime.strptime(s,f)
        except Exception: pass
    return None
def iso(x): return None if not x else x.replace(microsecond=0).isoformat()+"Z"
def load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def first(*vals):
    for v in vals:
        if v is None: continue
        if isinstance(v,str) and not v.strip(): continue
        return v
    return None

def tf(s): return str(first(s.get("timeframe"),s.get("base_timeframe"),"")).upper() if isinstance(s,dict) else ""
def surf_ts(s):
    if not isinstance(s,dict): return None
    return dt(first(s.get("bar_open_ts_utc"),s.get("latest_bar_open_ts_utc"),s.get("latest_h1_bar_open_ts_utc"),s.get("latest_m15_bar_open_ts_utc")))
def surfaces(payload, src):
    out=[]
    if isinstance(payload,dict):
        if isinstance(payload.get("surfaces"),list): out += [(x,src) for x in payload["surfaces"]]
        bc=payload.get("brain_context")
        if isinstance(bc,dict) and isinstance(bc.get("surfaces"),list): out += [(x,src) for x in bc["surfaces"]]
        if isinstance(payload.get("latest"),dict): out.append((payload["latest"],src))
    return out
def priority(src):
    s=str(src).replace("\\","/")
    if s=="runtime/sig_e/market_state_current.json": return 300
    if s=="runtime/sig_e/sig_e_regime1_market_state_current.json": return 290
    if s=="panel/brain4/sig_e_market_state_current.json": return 280
    if "sig_brain5_derived_context_latest" in s: return 100
    if "sig_brain4_live_context_latest" in s: return 90
    return 0
def score(s, inst, T, src):
    if not isinstance(s,dict): return -999
    sc=priority(src)
    if str(s.get("instrument","")).upper()==inst: sc+=10
    if tf(s)==T: sc+=10
    if surf_ts(s): sc+=8
    for k in ["session_bucket","d1_trend_state","d1_trend_safe","h4_trend_state","h4_trend_safe","htf_alignment","volatility_state","d1_vol_bucket","range_state","tradeability_context"]:
        if s.get(k) not in (None,""): sc+=2
    return sc
def find_surface(pairs, inst, T):
    c=[]
    for payload,src in pairs:
        for s,sp in surfaces(payload,src):
            if isinstance(s,dict) and str(s.get("instrument","")).upper()==inst and tf(s)==T:
                c.append((s,sp))
    if not c: return None,None
    return sorted(c,key=lambda x:(score(x[0],inst,T,x[1]), surf_ts(x[0]) or datetime.min), reverse=True)[0]

def dir_input(s,k):
    di=s.get("direction_inputs") if isinstance(s,dict) else None
    if isinstance(di,dict):
        v=di.get(k)
        if isinstance(v,dict): return first(v.get("dir"),v.get("direction"),v.get("trend_state"),v.get("state"))
        return v
    return None
def ndir(v):
    S=str(v or "").upper()
    if S in ("1","UP","BULL","BULLISH","LONG") or "UP" in S or "BULL" in S: return "UP"
    if S in ("-1","DOWN","BEAR","BEARISH","SHORT") or "DOWN" in S or "BEAR" in S: return "DOWN"
    return S
def regime(s,src):
    if not s: return False, {"reason":"no_eurusd_h1_surface"}
    sess=str(s.get("session_bucket","")).upper()
    d1=ndir(first(s.get("d1_trend_state"),s.get("d1_trend_safe"),dir_input(s,"d1")))
    h4=ndir(first(s.get("h4_trend_state"),s.get("h4_trend_safe"),dir_input(s,"h4")))
    htf=str(s.get("htf_alignment") or "").upper()
    vol=str(first(s.get("d1_vol_bucket"),s.get("d1_volatility_bucket"),s.get("volatility_state")) or "").upper()
    sess_ok=sess in {"LONDON","LONDON_NY_OVERLAP"}
    align_ok=(d1=="UP" and h4=="UP") or ("ALIGNED_UP" in htf) or (d1=="NEUTRAL" and h4=="UP")
    vol_ok=vol not in ("","UNKNOWN","NONE","NULL")
    return sess_ok and align_ok and vol_ok, {"selected_surface_source":src,"source_priority":priority(src),"session_bucket":sess,"d1_trend_state":d1,"h4_trend_state":h4,"htf_alignment":htf,"volatility_state_or_d1_vol_bucket":vol,"tradeability_context":str(s.get("tradeability_context") or "").upper(),"range_state":str(s.get("range_state") or "").upper(),"session_ok":sess_ok,"alignment_ok":align_ok,"vol_ok":vol_ok,"selected_surface_score":score(s,"EURUSD","H1",src)}
def freshness(payloads):
    for p in payloads:
        lag=p.get("lag_diagnostic") if isinstance(p,dict) else None
        if isinstance(lag,dict):
            r=str(lag.get("lag_reason_code","")).upper()
            if "STALE" in r or ("LAG" in r and "ALIGNED" not in r): return "DATA_STALE",{"lag_reason_code":r}
    return "FRESHNESS_NOT_BLOCKING",{}

def forbidden(path):
    s=str(path or "").replace("\\","/").lower()
    return any(x in s for x in ["data/canonical/","data/raw/","data/features/","holdout_2020_2024","validation_2015_2019","discovery_2004_2014","future_after_2024"])
def allowed(path):
    s=str(path or "").replace("\\","/").lower()
    return bool(path) and not forbidden(s) and ("live" in s or s.startswith("runtime/") or s.startswith("panel/") or s.startswith("inputs/") or s.startswith("data/"))
def resolve(p):
    if not p: return None
    q=Path(str(p).replace("/",os.sep))
    return q if q.exists() and allowed(str(q)) else None
def delim(line): return max([",",";","\t","|"], key=lambda c: line.count(c)) if line else ","
def col(cols,names):
    low={c.lower().replace(" ","_"):c for c in cols}
    for n in names:
        k=n.lower().replace(" ","_")
        if k in low: return low[k]
    for c in cols:
        for n in names:
            if n.lower() in c.lower() or c.lower() in n.lower(): return c
    return None
def num(x):
    try:
        if x is None or str(x).strip()=="": return None
        return float(x)
    except Exception: return None
def read_rows(path, max_tail=12000):
    p=Path(path) if path else None
    if not p or not p.exists(): return []
    try:
        if str(p).lower().endswith(".gz"):
            opener=lambda: gzip.open(p,"rt",encoding="utf-8",errors="replace",newline="")
        else:
            opener=lambda: open(p,"r",encoding="utf-8",errors="replace",newline="")
        with opener() as f:
            firstline=f.readline(); d=delim(firstline); f.seek(0)
            rdr=csv.DictReader(f,delimiter=d); rows=[]
            for r in rdr:
                if isinstance(r,dict) and any(v not in (None,"") for v in r.values()): rows.append(r)
                if len(rows)>max_tail: rows=rows[-max_tail:]
            return rows
    except Exception: return []
def ohlc(rows):
    if not rows: return []
    cols=list(rows[0].keys()); tc=col(cols,["bar_open_ts_utc","timestamp","datetime","time","date"]); oc=col(cols,["open","o"]); hc=col(cols,["high","h"]); lc=col(cols,["low","l"]); cc=col(cols,["close","c"])
    out=[]
    for r in rows:
        D=dt(r.get(tc)) if tc else None; O=num(r.get(oc)) if oc else None; H=num(r.get(hc)) if hc else None; L=num(r.get(lc)) if lc else None; C=num(r.get(cc)) if cc else None
        if D and None not in (O,H,L,C) and H>=L: out.append({"ts":D,"open":O,"high":H,"low":L,"close":C})
    return sorted(out,key=lambda x:x["ts"])

def report_paths(inst,T):
    found=[]
    for f in ["panel/brain4/sig_live_refresh_status_latest.json","runtime/sig_brain/sig_live_refresh_status_latest.json","data/live_m5/reports/resampled_from_m5_summary.json","data/live_m5/reports/resample_report.json","outputs/live_m5/resampled_from_m5_summary.json"]:
        payload=load(f)
        if not isinstance(payload,dict): continue
        rows=[]
        rd=payload.get("resampled_data")
        if isinstance(rd,dict) and isinstance(rd.get("rows"),list): rows+=rd["rows"]
        if isinstance(payload.get("rows"),list): rows+=payload["rows"]
        if isinstance(payload.get("files"),list): rows+=payload["files"]
        for r in rows:
            if not isinstance(r,dict): continue
            if str(first(r.get("instrument"),r.get("symbol"),"")).upper()==inst and str(first(r.get("timeframe"),r.get("tf"),"")).upper()==T:
                p=resolve(first(r.get("path"),r.get("file"),r.get("filepath"),r.get("output_path")))
                if p: found.append(("refresh_report",p))
    return found
def glob_paths(inst,T):
    pats=[f"data/live*/**/*{inst}*{T}*.csv",f"data/live*/**/*{inst}*{T}*.csv.gz",f"data/**/live*/**/*{inst}*{T}*.csv",f"data/**/live*/**/*{inst}*{T}*.csv.gz",f"runtime/**/*{inst}*{T}*.csv",f"runtime/**/*{inst}*{T}*.csv.gz"]
    out=[]; seen=set()
    for pat in pats:
        for p in Path(".").glob(pat):
            sp=str(p).replace("\\","/")
            if p.is_file() and sp not in seen and allowed(sp):
                seen.add(sp); out.append(("glob_live",p))
    return out
def candidates(inst,T):
    raw=report_paths(inst,T)+glob_paths(inst,T)
    best=None; diag=[]; seen=set()
    for source,p in raw:
        sp=str(p).replace("\\","/")
        if sp in seen: continue
        seen.add(sp)
        rows=ohlc(read_rows(p)); latest=rows[-1]["ts"] if rows else None
        sc=len(rows)+(1000000 if latest else 0)
        low=sp.lower()
        if "resampled" in low or "live_m5" in low or low.endswith(".gz"): sc+=5000
        if "current" in low or "latest" in low: sc-=250
        item={"source":source,"path":sp,"rows":len(rows),"latest_bar_open_ts_utc":iso(latest),"score":sc,"forbidden":forbidden(sp)}
        diag.append(item)
        if rows and not item["forbidden"] and (best is None or sc>best["score"]): best={"path":p,"rows":rows,"score":sc}
    diag.sort(key=lambda x:(x.get("score") or 0,x.get("rows") or 0), reverse=True)
    return best, diag[:20]

def rng(r): return r["high"]-r["low"]
def prior_day_low(rows, setup_dt):
    day=setup_dt.date()-timedelta(days=1)
    rs=[r for r in rows if r["ts"].date()==day]
    if not rs: return None, {"target_prior_utc_date":str(day),"prior_day_h1_count":0}
    lvl=min(r["low"] for r in rs)
    return lvl, {"target_prior_utc_date":str(day),"prior_day_h1_count":len(rs),"prior_day_low":lvl}
def setup_ok(row, level):
    R=rng(row)
    if R<=0 or level is None: return False, {"reason":"zero_range_or_missing_level"}
    lower=min(row["open"],row["close"])-row["low"]; loc=(row["close"]-row["low"])/R
    swept=row["low"]<level; reclaimed=row["close"]>level
    ok=swept and reclaimed and lower/R>=0.25 and loc>=0.50
    return ok, {"reference_level":level,"low_below_level":swept,"close_back_above_level":reclaimed,"range":R,"lower_wick":lower,"lower_wick_to_range":lower/R,"close_location":loc,"bullish_close":row["close"]>row["open"]}
def m15_ok(rows,start,level):
    end=start+timedelta(hours=1)
    inside=[r for r in rows if start<=r["ts"]<end]
    conf=[r for r in inside if r["close"]>r["open"] and r["close"]>level]
    return bool(conf), {"h1_window_start":iso(start),"h1_window_end":iso(end),"m15_inside_count":len(inside),"m15_confirm_count":len(conf),"first_confirm_m15_open_ts_utc":iso(conf[0]["ts"]) if conf else None}

def load_state():
    s=load(STATE)
    if not isinstance(s,dict): s={"state_version":"sig_e_shadow_detector3_state_v1","detector_id":DETECTOR_ID,"created_utc":now(),"history":[]}
    if not isinstance(s.get("history"),list): s["history"]=[]
    return s
def update_state(s,cur):
    key=cur.get("shadow_event_id") or cur.get("detector_run_id")
    ex={h.get("shadow_event_id") or h.get("detector_run_id") for h in s.get("history",[]) if isinstance(h,dict)}
    if key not in ex:
        s["history"].append({k:cur.get(k) for k in ["detector_run_id","shadow_event_id","created_utc","detector_status","status_reason","setup_h1_open_ts_utc","trigger_h1_open_ts_utc","authority"]})
    s["history"]=s["history"][-500:]; s["last_updated_utc"]=now(); s["last_status"]=cur.get("detector_status")
    return s

def build():
    cfg=load(CONFIG) or {}
    pairs=[]; payloads=[]; loaded=[]
    for p in ["runtime/sig_e/market_state_current.json","runtime/sig_e/sig_e_regime1_market_state_current.json","panel/brain4/sig_e_market_state_current.json","runtime/sig_brain/sig_brain5_derived_context_latest.json","inputs/sig_brain4_live_context_latest.json","panel/brain4/sig_live_refresh_status_latest.json"]:
        x=load(p)
        if x is not None: pairs.append((x,p)); payloads.append(x); loaded.append(p)
    h1,h1src=find_surface(pairs,"EURUSD","H1"); m15,m15src=find_surface(pairs,"EURUSD","M15")
    res={"program":PROGRAM,"detector_id":cfg.get("detector_id",DETECTOR_ID),"source_spec_id":SOURCE_SPEC_ID,"detector_run_id":"SIGE_SD3_EURUSD_"+datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),"created_utc":now(),"instrument":"EURUSD","direction":"LONG","detector_status":"INPUT_INSUFFICIENT","status_reason":None,"is_shadow_match":False,"is_signal":False,"is_trade_proposal":False,"authority":AUTH,"boundary":cfg.get("boundary",BOUND),"loaded_source_files":loaded,"surface_snapshot":{"h1_surface_available":h1 is not None,"m15_surface_available":m15 is not None,"h1_surface_source":h1src,"m15_surface_source":m15src,"h1_bar_open_ts_utc":iso(surf_ts(h1)) if h1 else None,"m15_bar_open_ts_utc":iso(surf_ts(m15)) if m15 else None,"h1_surface_score":score(h1,"EURUSD","H1",h1src) if h1 else None,"m15_surface_score":score(m15,"EURUSD","M15",m15src) if m15 else None},"checks":[],"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    fr,fm=freshness(payloads); res["freshness_check"]={"status":fr,**fm}
    if fr=="DATA_STALE": res["detector_status"]="DATA_STALE"; res["status_reason"]="freshness_blocked"; return res
    ok,meta=regime(h1,h1src); res["checks"].append({"check_id":"REGIME","passed":ok,"details":meta})
    if h1 is None: res["status_reason"]="missing_eurusd_h1_surface"; return res
    if not meta.get("session_ok"): res["detector_status"]="SESSION_NOT_MATCHED"; res["status_reason"]="session_not_london_or_overlap"; return res
    if not meta.get("alignment_ok") or not meta.get("vol_ok"): res["detector_status"]="REGIME_NOT_MATCHED"; res["status_reason"]="eurusd_long_trap_regime_not_matched"; return res
    hbest,hdiag=candidates("EURUSD","H1"); mbest,mdiag=candidates("EURUSD","M15")
    hrows=hbest["rows"] if hbest else []; mrows=mbest["rows"] if mbest else []
    res["source_paths"]={"h1_ohlc_path":str(hbest["path"]) if hbest else None,"m15_ohlc_path":str(mbest["path"]) if mbest else None,"live_source_policy":"live_only_no_data_canonical_fallback","h1_selection_policy":"prefer_live_accumulated_resampled_store_with_most_rows","m15_selection_policy":"prefer_live_accumulated_resampled_store_with_most_rows"}
    res["ohlc_source_diagnostics"]={"h1_candidates_top":hdiag,"m15_candidates_top":mdiag}
    res["data_counts"]={"h1_rows_loaded":len(hrows),"m15_rows_loaded":len(mrows),"h1_latest_bar_open_ts_utc":iso(hrows[-1]["ts"]) if hrows else None,"m15_latest_bar_open_ts_utc":iso(mrows[-1]["ts"]) if mrows else None}
    if not hbest or not mbest: res["detector_status"]="LIVE_OHLC_SOURCE_MISSING"; res["status_reason"]="live_eurusd_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed"; return res
    if len(hrows)<48: res["detector_status"]="LIVE_H1_HISTORY_INSUFFICIENT"; res["status_reason"]="h1_rows_lt_48_for_prior_day_low_reference"; return res
    if len(mrows)<4: res["detector_status"]="LIVE_M15_HISTORY_INSUFFICIENT"; res["status_reason"]="m15_rows_lt_4_for_trigger_window"; return res
    latest=len(hrows)-1; si=latest-1; setup=hrows[si]; trigger=hrows[latest]
    level,lmeta=prior_day_low(hrows,setup["ts"]); res["reference_level"]={"type":"prior_utc_day_low",**lmeta}
    if level is None: res["detector_status"]="REFERENCE_LEVEL_UNAVAILABLE"; res["status_reason"]="prior_utc_day_low_unavailable_from_live_h1"; return res
    sok,smeta=setup_ok(setup,level)
    res["setup_h1_open_ts_utc"]=iso(setup["ts"]); res["trigger_h1_open_ts_utc"]=iso(trigger["ts"])
    res["checks"].append({"check_id":"H1_SETUP_PREVIOUS_BAR_PRIOR_DAY_LOW_TRAP_RECLAIM","passed":sok,"details":{"setup_h1_open_ts_utc":iso(setup["ts"]),**smeta}})
    if not sok:
        cok,cmeta=setup_ok(trigger,level)
        if cok:
            res["detector_status"]="H1_TRIGGER_WAIT"; res["status_reason"]="latest_h1_bar_forms_prior_day_low_trap_setup_waiting_for_next_h1_close"; res["current_setup_candidate"]={"setup_h1_open_ts_utc":iso(trigger["ts"]),**cmeta}
        else:
            res["detector_status"]="SETUP_NOT_FORMED"; res["status_reason"]="previous_h1_bar_did_not_form_prior_day_low_failed_breakdown_reclaim"
        return res
    hconfirm=trigger["close"]>trigger["open"] and trigger["close"]>level
    res["checks"].append({"check_id":"NEXT_H1_BULLISH_RECLAIM_CONFIRM","passed":hconfirm,"details":{"trigger_h1_open_ts_utc":iso(trigger["ts"]),"open":trigger["open"],"close":trigger["close"],"reference_level":level}})
    if not hconfirm: res["detector_status"]="H1_TRIGGER_NOT_CONFIRMED"; res["status_reason"]="next_h1_bar_did_not_confirm_bullish_reclaim_above_prior_day_low"; return res
    mok,mmeta=m15_ok(mrows,trigger["ts"],level)
    res["checks"].append({"check_id":"M15_BULLISH_CLOSE_ABOVE_PRIOR_DAY_LOW_INSIDE_TRIGGER_H1","passed":mok,"details":mmeta})
    if not mok: res["detector_status"]="M15_TRIGGER_WAIT"; res["status_reason"]="h1_confirmed_but_no_inside_h1_m15_bullish_close_above_prior_day_low"; return res
    res["detector_status"]="SHADOW_MATCH_CONFIRMED"; res["status_reason"]="eurusd_prior_day_low_trap_reclaim_h1_m15_shadow_match_confirmed"; res["is_shadow_match"]=True
    res["m15_confirm_ts_utc"]=mmeta.get("first_confirm_m15_open_ts_utc")
    res["shadow_event_id"]="SIGE_SD3_EURUSD_PDLOW_TRAP_LONG_"+iso(trigger["ts"]).replace("-","").replace(":","").replace("Z","")
    res["observation_horizon"]={"horizon_h1_bars":12,"observation_end_ts_utc":iso(trigger["ts"]+timedelta(hours=12)),"outcome_tracking_authorized":True,"trade_execution_authorized":False}
    return res

def main():
    res=build()
    if res.get("detector_status") not in VALID:
        res["detector_status"]="INPUT_INSUFFICIENT"; res["status_reason"]="invalid_status_guardrail"
    write(RUNTIME,res); write(PANEL,res); write(STATE,update_state(load_state(),res))
    write(OUT,{"program":PROGRAM,"created_utc":now(),"build_status":"PASS","detector_status":res.get("detector_status"),"status_reason":res.get("status_reason"),"is_shadow_match":res.get("is_shadow_match"),"data_counts":res.get("data_counts"),"source_paths":res.get("source_paths"),"authority":AUTH,"boundary":BOUND})
    print("SIG_E_SHADOW_DETECTOR3_BUILD_DONE")
    print("DETECTOR_STATUS="+str(res.get("detector_status")))
    print("STATUS_REASON="+str(res.get("status_reason")))
if __name__=="__main__": main()
