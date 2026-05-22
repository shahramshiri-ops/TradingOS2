import csv, json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

CONFIG_PATH = Path("config/sig_e/shadow_detectors/usdjpy_london_long_h1_m15_v1_0.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_detector_status_current.json")
STATE_PATH = Path("state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json")
BUILD_RESULT = Path("outputs/_sig_e_shadow_detector1/sig_e_shadow_detector1_build_result.json")

VALID_STATUS = {
    "INPUT_INSUFFICIENT","DATA_STALE","SESSION_NOT_MATCHED","REGIME_NOT_MATCHED",
    "FIELD_MAPPING_INCOMPLETE","LIVE_OHLC_SOURCE_MISSING","SETUP_NOT_FORMED",
    "H1_TRIGGER_WAIT","H1_TRIGGER_NOT_CONFIRMED","M15_TRIGGER_WAIT",
    "SHADOW_MATCH_CONFIRMED","EXPIRED"
}

def utc_now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def parse_dt(x):
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

def iso(dt): return None if not dt else dt.replace(microsecond=0).isoformat()+"Z"

def load_json(p):
    p=Path(p)
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None

def write_json(p,obj):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def first_nonempty(*vals):
    for v in vals:
        if v is None: continue
        if isinstance(v,str) and not v.strip(): continue
        return v
    return None

def nested(d,*keys):
    cur=d
    for k in keys:
        if not isinstance(cur,dict): return None
        cur=cur.get(k)
    return cur

def tf_of(s):
    return str(first_nonempty(s.get("timeframe"),s.get("base_timeframe"),"")).upper() if isinstance(s,dict) else ""

def surface_ts(s):
    if not isinstance(s,dict): return None
    return parse_dt(first_nonempty(
        s.get("bar_open_ts_utc"),s.get("latest_bar_open_ts_utc"),
        s.get("latest_h1_bar_open_ts_utc"),s.get("latest_m15_bar_open_ts_utc"),
        s.get("bar_close_ts_utc"),s.get("latest_bar_close_ts_utc")
    ))

def surfaces(payload):
    out=[]
    if isinstance(payload,dict):
        if isinstance(payload.get("surfaces"),list): out+=payload["surfaces"]
        bc=payload.get("brain_context")
        if isinstance(bc,dict) and isinstance(bc.get("surfaces"),list): out+=bc["surfaces"]
        if isinstance(payload.get("latest"),dict): out.append(payload["latest"])
    return out

def hasval(s,k):
    v=s.get(k) if isinstance(s,dict) else None
    return v is not None and not (isinstance(v,str) and not v.strip())

def score_surface(s, inst, tf):
    if not isinstance(s,dict): return -999
    score=0
    if str(s.get("instrument","")).upper()==inst: score+=10
    if tf_of(s)==tf: score+=10
    if surface_ts(s): score+=8
    for k in ["session_bucket","d1_trend_state","d1_trend_safe","h4_trend_state","h4_trend_safe",
              "htf_alignment","volatility_state","d1_vol_bucket","range_state","current_h1_expansion_flag",
              "h1_open","h1_high","h1_low","h1_close","m15_dir","tradeability_context"]:
        if hasval(s,k): score+=2
    if isinstance(s.get("direction_inputs"),dict): score+=4
    if isinstance(s.get("regime_metrics"),dict): score+=3
    if s.get("h4_h1_up_context") is True: score+=3
    return score

def find_surface(payloads, inst="USDJPY", tf="H1"):
    c=[]
    for p in payloads:
        for s in surfaces(p):
            if isinstance(s,dict) and str(s.get("instrument","")).upper()==inst and tf_of(s)==tf:
                c.append(s)
    if not c: return None
    return sorted(c, key=lambda s:(score_surface(s,inst,tf), surface_ts(s) or datetime.min), reverse=True)[0]

def norm_dir(v):
    s=str(v or "").upper()
    if s in ("1","UP","BULL","BULLISH","LONG") or "UP" in s or "BULL" in s: return "UP"
    if s in ("-1","DOWN","BEAR","BEARISH","SHORT") or "DOWN" in s or "BEAR" in s: return "DOWN"
    return s

def dir_input(s,key):
    di=s.get("direction_inputs") if isinstance(s,dict) else None
    if isinstance(di,dict):
        v=di.get(key)
        if isinstance(v,dict): return first_nonempty(v.get("dir"),v.get("direction"),v.get("trend_state"),v.get("state"))
        return v
    return None

def regime_check(s):
    if not s: return False, {"reason":"no_h1_surface"}
    session=str(s.get("session_bucket","")).upper()
    d1=norm_dir(first_nonempty(s.get("d1_trend_state"),s.get("d1_trend_safe"),dir_input(s,"d1")))
    h4=norm_dir(first_nonempty(s.get("h4_trend_state"),s.get("h4_trend_safe"),dir_input(s,"h4")))
    htf=str(s.get("htf_alignment") or "").upper()
    vol=str(first_nonempty(s.get("d1_vol_bucket"),s.get("d1_volatility_bucket"),s.get("volatility_state")) or "").upper()
    missing=[]
    if not session: missing.append("session_bucket")
    if not (d1 or h4 or htf or s.get("h4_h1_up_context") is not None): missing.append("d1_h4_alignment_fields")
    if not vol: missing.append("volatility_state_or_d1_vol_bucket")
    session_ok=session=="LONDON"
    align_ok=(d1=="UP" and h4=="UP") or ("ALIGNED_UP" in htf) or s.get("h4_h1_up_context") is True
    vol_ok=vol in {"LOW","NORMAL","MIXED"} if vol else False
    return session_ok and align_ok and vol_ok and not missing, {
        "session_bucket":session, "d1_trend_state":d1, "h4_trend_state":h4, "htf_alignment":htf,
        "volatility_state_or_d1_vol_bucket":vol, "tradeability_context":str(s.get("tradeability_context") or "").upper(),
        "range_state":str(s.get("range_state") or "").upper(), "h4_h1_up_context":s.get("h4_h1_up_context"),
        "session_ok":session_ok, "alignment_ok":align_ok, "vol_ok":vol_ok,
        "missing_regime_fields":missing, "selected_surface_score":score_surface(s,"USDJPY","H1"),
        "volatility_caveat":"Runtime proxy accepted; historical spec preferred LOW D1 vol bucket" if vol in {"NORMAL","MIXED"} else None
    }

def freshness(payloads):
    for p in payloads:
        if not isinstance(p,dict): continue
        lag=p.get("lag_diagnostic")
        if isinstance(lag,dict):
            r=str(lag.get("lag_reason_code","")).upper()
            if "STALE" in r or ("LAG" in r and "ALIGNED" not in r): return "DATA_STALE", {"lag_reason_code":r}
        rs=nested(p,"source_context","refresh_status_summary")
        if isinstance(rs,dict):
            r=str(rs.get("lag_reason_code","")).upper()
            if "STALE" in r: return "DATA_STALE", {"lag_reason_code":r}
    return "FRESHNESS_NOT_BLOCKING", {}

def allowed_live_path(p):
    if not p: return False
    s=str(p).replace("\\","/").lower()
    if any(x in s for x in ["data/canonical/","data/raw/","data/features/","holdout_2020_2024","validation_2015_2019","discovery_2004_2014","future_after_2024"]):
        return False
    return "live" in s or s.startswith("panel/") or s.startswith("runtime/") or s.startswith("inputs/")

def resolve(p):
    if not p: return None
    p=Path(str(p).replace("/",os.sep))
    return p if p.exists() else None

def refresh_paths(inst):
    paths={}
    for f in ["panel/brain4/sig_live_refresh_status_latest.json","runtime/sig_brain/sig_live_refresh_status_latest.json","data/live_m5/reports/resampled_from_m5_summary.json"]:
        x=load_json(f)
        if not isinstance(x,dict): continue
        rows=[]
        rd=x.get("resampled_data")
        if isinstance(rd,dict) and isinstance(rd.get("rows"),list): rows+=rd["rows"]
        if isinstance(x.get("rows"),list): rows+=x["rows"]
        for r in rows:
            if str(r.get("instrument","")).upper()==inst:
                tf=str(r.get("timeframe","")).upper(); p=r.get("path")
                rp=resolve(p)
                if tf and rp and allowed_live_path(rp): paths[tf]=rp
    return paths

def live_ohlc_path(inst,tf):
    rp=refresh_paths(inst)
    if tf in rp: return rp[tf]
    for p in [Path("data/live_resampled")/f"{inst}_{tf}.csv", Path("data/live_m5/resampled")/f"{inst}_{tf}.csv"]:
        if p.exists() and allowed_live_path(p): return p
    return None

def detect_delim(line):
    cs=[",",";","\t","|"]; return max(cs, key=lambda c: line.count(c)) if line else ","

def pick_col(cols, names):
    low={c.lower().replace(" ","_"):c for c in cols}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    for c in cols:
        nc=c.lower()
        for n in names:
            if n.lower() in nc or nc in n.lower(): return c
    return None

def fnum(v):
    try: return float(v)
    except Exception: return None

def read_rows(path, max_tail=3000):
    if not path or not Path(path).exists(): return []
    with open(path,"r",encoding="utf-8",errors="replace") as f:
        first=f.readline(); delim=detect_delim(first); f.seek(0)
        rdr=csv.DictReader(f, delimiter=delim)
        rows=[]
        for r in rdr:
            rows.append(r)
            if len(rows)>max_tail: rows=rows[-max_tail:]
        return rows

def ohlc(rows):
    if not rows: return []
    cols=list(rows[0].keys())
    tc=pick_col(cols,["bar_open_ts_utc","timestamp","datetime","time","date"])
    oc=pick_col(cols,["open","o"]); hc=pick_col(cols,["high","h"]); lc=pick_col(cols,["low","l"]); cc=pick_col(cols,["close","c"])
    out=[]
    for r in rows:
        dt=parse_dt(r.get(tc)) if tc else None
        o=fnum(r.get(oc)) if oc else None; h=fnum(r.get(hc)) if hc else None; l=fnum(r.get(lc)) if lc else None; c=fnum(r.get(cc)) if cc else None
        if dt and None not in (o,h,l,c) and h>=l: out.append({"ts":dt,"open":o,"high":h,"low":l,"close":c})
    return sorted(out,key=lambda x:x["ts"])

def rng(r): return r["high"]-r["low"]

def lower_reject(r, wick_min=.30, close_min=.55):
    rr=rng(r)
    if rr<=0: return False, {"reason":"zero_range"}
    lw=min(r["open"],r["close"])-r["low"]; loc=(r["close"]-r["low"])/rr
    return lw/rr>=wick_min and loc>=close_min, {"range":rr,"lower_wick":lw,"lower_wick_to_range":lw/rr,"close_location":loc,"bullish_close":r["close"]>r["open"]}

def expanded(rows,i,min_ratio=1.15):
    if i<4: return False, {"reason":"not_enough_prior_h1_ranges"}
    prior=[rng(r) for r in rows[i-4:i] if rng(r)>0]
    if len(prior)<3: return False, {"reason":"not_enough_valid_prior_ranges"}
    avg=sum(prior)/len(prior); ratio=rng(rows[i])/avg if avg>0 else None
    return ratio is not None and ratio>=min_ratio, {"setup_range":rng(rows[i]),"prior_range_avg":avg,"range_expansion_ratio":ratio}

def m15_confirm(rows,h1_start):
    end=h1_start+timedelta(hours=1)
    inside=[r for r in rows if h1_start<=r["ts"]<end]
    conf=[r for r in inside if r["close"]>r["open"]]
    return bool(conf), {"h1_window_start":iso(h1_start),"h1_window_end":iso(end),"m15_inside_count":len(inside),"m15_confirm_count":len(conf),"first_confirm_m15_open_ts_utc":iso(conf[0]["ts"]) if conf else None}

def state_load():
    s=load_json(STATE_PATH)
    if not isinstance(s,dict): s={"state_version":"sig_e_shadow_detector_state_v1","detector_id":"SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0","created_utc":utc_now(),"history":[]}
    if not isinstance(s.get("history"),list): s["history"]=[]
    return s

def state_update(s,cur):
    key=cur.get("shadow_event_id") or cur.get("detector_run_id")
    hist=s.get("history",[])
    if key not in {h.get("shadow_event_id") or h.get("detector_run_id") for h in hist if isinstance(h,dict)}:
        hist.append({k:cur.get(k) for k in ["detector_run_id","shadow_event_id","created_utc","detector_status","status_reason","setup_h1_open_ts_utc","trigger_h1_open_ts_utc","m15_confirm_ts_utc","authority"]})
    s["history"]=hist[-500:]; s["last_updated_utc"]=utc_now(); s["last_status"]=cur.get("detector_status"); s["last_shadow_event_id"]=cur.get("shadow_event_id")
    return s

def build():
    cfg=load_json(CONFIG_PATH) or {}
    payloads=[]; loaded=[]
    for p in ["runtime/sig_e/market_state_current.json","runtime/sig_e/sig_e_regime1_market_state_current.json","panel/brain4/sig_e_market_state_current.json","runtime/sig_brain/sig_brain5_derived_context_latest.json","inputs/sig_brain4_live_context_latest.json","panel/brain4/sig_live_refresh_status_latest.json"]:
        x=load_json(p)
        if x is not None: payloads.append(x); loaded.append(p)
    h1=find_surface(payloads,"USDJPY","H1"); m15=find_surface(payloads,"USDJPY","M15")
    run_id="SIGE_SD1_USDJPY_"+datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    res={"program":"SIG-E-RUNTIME-SHADOW-DETECTOR1","detector_id":cfg.get("detector_id","SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0"),"source_spec_id":cfg.get("source_spec_id"),"detector_run_id":run_id,"created_utc":utc_now(),"instrument":"USDJPY","direction":"LONG","detector_status":"INPUT_INSUFFICIENT","status_reason":None,"is_shadow_match":False,"is_signal":False,"is_trade_proposal":False,"authority":{"signal_authorized":False,"trade_proposal_authorized":False,"entry_stop_target_authorized":False,"risk_sizing_authorized":False,"broker_execution_authorized":False,"auto_execution_authorized":False},"boundary":cfg.get("boundary",[]),"loaded_source_files":loaded,"surface_snapshot":{"h1_surface_available":h1 is not None,"m15_surface_available":m15 is not None,"h1_bar_open_ts_utc":iso(surface_ts(h1)) if h1 else None,"m15_bar_open_ts_utc":iso(surface_ts(m15)) if m15 else None,"h1_surface_score":score_surface(h1,"USDJPY","H1") if h1 else None,"m15_surface_score":score_surface(m15,"USDJPY","M15") if m15 else None},"checks":[],"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    fr, fm=freshness(payloads); res["freshness_check"]={"status":fr,**fm}
    if fr=="DATA_STALE": res["detector_status"]="DATA_STALE"; res["status_reason"]="freshness_blocked"; return res
    ok, meta=regime_check(h1); res["checks"].append({"check_id":"REGIME","passed":ok,"details":meta})
    if h1 is None: res["status_reason"]="missing_usdjpy_h1_surface"; return res
    if meta.get("missing_regime_fields"): res["detector_status"]="FIELD_MAPPING_INCOMPLETE"; res["status_reason"]="missing_required_regime_field_mapping"; return res
    if meta.get("session_bucket")!="LONDON": res["detector_status"]="SESSION_NOT_MATCHED"; res["status_reason"]="session_not_london"; return res
    if not ok: res["detector_status"]="REGIME_NOT_MATCHED"; res["status_reason"]="d1_h4_vol_regime_not_matched"; return res
    hp=live_ohlc_path("USDJPY","H1"); mp=live_ohlc_path("USDJPY","M15")
    res["source_paths"]={"h1_ohlc_path":str(hp) if hp else None,"m15_ohlc_path":str(mp) if mp else None,"live_source_policy":"live_only_no_data_canonical_fallback"}
    if hp is None or mp is None: res["detector_status"]="LIVE_OHLC_SOURCE_MISSING"; res["status_reason"]="live_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed"; return res
    hrows=ohlc(read_rows(hp)); mrows=ohlc(read_rows(mp)); res["data_counts"]={"h1_rows_loaded":len(hrows),"m15_rows_loaded":len(mrows)}
    if len(hrows)<6: res["status_reason"]="not_enough_h1_rows_for_setup_trigger_window"; return res
    latest=len(hrows)-1; setup_i=latest-1; setup=hrows[setup_i]; trig=hrows[latest]
    res["setup_h1_open_ts_utc"]=iso(setup["ts"]); res["trigger_h1_open_ts_utc"]=iso(trig["ts"])
    setup_ok1,rej=lower_reject(setup); setup_ok2,exp=expanded(hrows,setup_i); setup_ok=setup_ok1 and setup_ok2
    res["checks"].append({"check_id":"H1_SETUP_PREVIOUS_BAR","passed":setup_ok,"details":{"setup_h1_open_ts_utc":iso(setup["ts"]),"lower_rejection":rej,"range_expansion":exp}})
    if not setup_ok:
        cur1,currej=lower_reject(trig); cur2,curexp=expanded(hrows,latest)
        if cur1 and cur2:
            res["detector_status"]="H1_TRIGGER_WAIT"; res["status_reason"]="latest_h1_bar_forms_setup_waiting_for_next_h1_close"; res["current_setup_candidate"]={"setup_h1_open_ts_utc":iso(trig["ts"]),"lower_rejection":currej,"range_expansion":curexp}
        else:
            res["detector_status"]="SETUP_NOT_FORMED"; res["status_reason"]="previous_h1_bar_did_not_match_lower_rejection_expansion_setup"
        return res
    h1conf=trig["close"]>trig["open"]; res["checks"].append({"check_id":"NEXT_H1_DIRECTION_CONFIRM","passed":h1conf,"details":{"trigger_h1_open_ts_utc":iso(trig["ts"]),"open":trig["open"],"close":trig["close"],"direction":"UP" if h1conf else "NOT_UP"}})
    if not h1conf: res["detector_status"]="H1_TRIGGER_NOT_CONFIRMED"; res["status_reason"]="next_h1_bar_did_not_confirm_long_direction"; return res
    if not mrows: res["status_reason"]="m15_ohlc_rows_missing"; return res
    mconf,mm=m15_confirm(mrows,trig["ts"]); res["checks"].append({"check_id":"M15_INSIDE_H1_DIRECTIONAL_CLOSE_CONFIRM","passed":mconf,"details":mm})
    if not mconf: res["detector_status"]="M15_TRIGGER_WAIT"; res["status_reason"]="h1_confirmed_but_no_inside_h1_m15_directional_close_yet"; return res
    res["detector_status"]="SHADOW_MATCH_CONFIRMED"; res["status_reason"]="regime_setup_h1_trigger_m15_trigger_all_confirmed"; res["is_shadow_match"]=True
    res["shadow_event_id"]="SIGE_SD1_USDJPY_LONDON_LONG_"+iso(trig["ts"]).replace("-","").replace(":","").replace("Z","")
    res["m15_confirm_ts_utc"]=mm.get("first_confirm_m15_open_ts_utc")
    res["observation_horizon"]={"horizon_h1_bars":16,"observation_end_ts_utc":iso(trig["ts"]+timedelta(hours=16)),"outcome_tracking_authorized":True,"trade_execution_authorized":False}
    return res

def main():
    res=build()
    if res.get("detector_status") not in VALID_STATUS:
        res["detector_status"]="INPUT_INSUFFICIENT"; res["status_reason"]="invalid_status_guardrail"
    st=state_update(state_load(),res)
    write_json(RUNTIME_OUT,res); write_json(PANEL_OUT,res); write_json(STATE_PATH,st)
    write_json(BUILD_RESULT,{"program":"SIG-E-RUNTIME-SHADOW-DETECTOR1-HOTFIX1","created_utc":utc_now(),"build_status":"PASS","detector_status":res.get("detector_status"),"status_reason":res.get("status_reason"),"is_shadow_match":res.get("is_shadow_match"),"runtime_out":str(RUNTIME_OUT),"panel_out":str(PANEL_OUT),"state_path":str(STATE_PATH),"authority":res.get("authority"),"hotfixes":["richest_surface_selection","timestamp_fallbacks","expanded_regime_field_mapping","live_ohlc_only_no_data_canonical_fallback","field_mapping_incomplete_and_live_source_missing_statuses"]})
    print("SIG_E_SHADOW_DETECTOR1_HOTFIX1_BUILD_DONE")
    print("DETECTOR_STATUS="+str(res.get("detector_status")))
    print("STATUS_REASON="+str(res.get("status_reason")))
    print("IS_SHADOW_MATCH="+str(res.get("is_shadow_match")))

if __name__=="__main__":
    main()
