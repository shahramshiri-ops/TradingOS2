# SIG-E-RUNTIME-SHADOW-DETECTOR1-HOTFIX2
# Surface vol + regime priority fix. Shadow/research only.
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

def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
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

def tf(s): return str(first(s.get("timeframe"),s.get("base_timeframe"),"")).upper() if isinstance(s,dict) else ""
def ts(s):
    if not isinstance(s,dict): return None
    return dt(first(s.get("bar_open_ts_utc"),s.get("latest_bar_open_ts_utc"),s.get("latest_h1_bar_open_ts_utc"),s.get("latest_m15_bar_open_ts_utc"),s.get("bar_close_ts_utc"),s.get("latest_bar_close_ts_utc")))
def surfaces(p):
    out=[]
    if isinstance(p,dict):
        if isinstance(p.get("surfaces"),list): out+=p["surfaces"]
        bc=p.get("brain_context")
        if isinstance(bc,dict) and isinstance(bc.get("surfaces"),list): out+=bc["surfaces"]
        if isinstance(p.get("latest"),dict): out.append(p["latest"])
    return out
def has(s,k):
    v=s.get(k) if isinstance(s,dict) else None
    return v is not None and not (isinstance(v,str) and not v.strip())
def score(s,inst,TF):
    if not isinstance(s,dict): return -999
    sc=0
    if str(s.get("instrument","")).upper()==inst: sc+=10
    if tf(s)==TF: sc+=10
    if ts(s): sc+=8
    for k in ["session_bucket","d1_trend_state","d1_trend_safe","h4_trend_state","h4_trend_safe","htf_alignment","volatility_state","d1_vol_bucket","range_state","current_h1_expansion_flag","h1_open","h1_high","h1_low","h1_close","m15_dir","tradeability_context"]:
        if has(s,k): sc+=2
    if isinstance(s.get("direction_inputs"),dict): sc+=4
    if isinstance(s.get("regime_metrics"),dict): sc+=3
    if s.get("h4_h1_up_context") is True: sc+=3
    return sc
def find_surface(payloads,inst="USDJPY",TF="H1"):
    c=[]
    for p in payloads:
        for s in surfaces(p):
            if isinstance(s,dict) and str(s.get("instrument","")).upper()==inst and tf(s)==TF:
                c.append(s)
    if not c: return None
    return sorted(c,key=lambda s:(score(s,inst,TF),ts(s) or datetime.min),reverse=True)[0]
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
def regime(s):
    if not s: return False, {"reason":"no_h1_surface"}
    sess=str(s.get("session_bucket","")).upper()
    d1=ndir(first(s.get("d1_trend_state"),s.get("d1_trend_safe"),dir_input(s,"d1")))
    h4=ndir(first(s.get("h4_trend_state"),s.get("h4_trend_safe"),dir_input(s,"h4")))
    htf=str(s.get("htf_alignment") or "").upper()
    vol=str(first(s.get("d1_vol_bucket"),s.get("d1_volatility_bucket"),s.get("volatility_state")) or "").upper()
    align=(d1=="UP" and h4=="UP") or ("ALIGNED_UP" in htf) or s.get("h4_h1_up_context") is True
    vol_known=vol not in ("","UNKNOWN","NONE","NULL")
    vol_ok=vol in {"LOW","NORMAL","MIXED"} if vol_known else False
    missing=[]
    if not sess: missing.append("session_bucket")
    if not (d1 or h4 or htf or s.get("h4_h1_up_context") is not None): missing.append("d1_h4_alignment_fields")
    if not vol_known: missing.append("volatility_state_or_d1_vol_bucket")
    return sess=="LONDON" and align and vol_ok and not missing, {
        "session_bucket":sess,"d1_trend_state":d1,"h4_trend_state":h4,"htf_alignment":htf,
        "volatility_state_or_d1_vol_bucket":vol,"volatility_source_policy":s.get("volatility_source_policy"),
        "tradeability_context":str(s.get("tradeability_context") or "").upper(),"range_state":str(s.get("range_state") or "").upper(),
        "h4_h1_up_context":s.get("h4_h1_up_context"),"session_ok":sess=="LONDON","alignment_ok":align,
        "vol_known":vol_known,"vol_ok":vol_ok,"missing_regime_fields":missing,
        "selected_surface_score":score(s,"USDJPY","H1"),
        "volatility_caveat":"Runtime proxy/UNKNOWN must not be treated as historical D1 LOW proof" if vol in {"NORMAL","MIXED","UNKNOWN"} else None
    }
def freshness(payloads):
    for p in payloads:
        if not isinstance(p,dict): continue
        lag=p.get("lag_diagnostic")
        if isinstance(lag,dict):
            r=str(lag.get("lag_reason_code","")).upper()
            if "STALE" in r or ("LAG" in r and "ALIGNED" not in r): return "DATA_STALE",{"lag_reason_code":r}
    return "FRESHNESS_NOT_BLOCKING",{}
def live_allowed(p):
    if not p: return False
    s=str(p).replace("\\","/").lower()
    if any(x in s for x in ["data/canonical/","data/raw/","data/features/","holdout_2020_2024","validation_2015_2019","discovery_2004_2014","future_after_2024"]): return False
    return "live" in s or s.startswith("panel/") or s.startswith("runtime/") or s.startswith("inputs/")
def resolve(p):
    if not p: return None
    q=Path(str(p).replace("/",os.sep))
    return q if q.exists() else None
def refresh_paths(inst):
    out={}
    for f in ["panel/brain4/sig_live_refresh_status_latest.json","runtime/sig_brain/sig_live_refresh_status_latest.json","data/live_m5/reports/resampled_from_m5_summary.json"]:
        x=load(f)
        if not isinstance(x,dict): continue
        rows=[]
        rd=x.get("resampled_data")
        if isinstance(rd,dict) and isinstance(rd.get("rows"),list): rows+=rd["rows"]
        if isinstance(x.get("rows"),list): rows+=x["rows"]
        for r in rows:
            if str(r.get("instrument","")).upper()==inst:
                T=str(r.get("timeframe","")).upper(); p=resolve(r.get("path"))
                if T and p and live_allowed(p): out[T]=p
    return out
def live_path(inst,T):
    rp=refresh_paths(inst)
    if T in rp: return rp[T]
    for p in [Path("data/live_resampled")/f"{inst}_{T}.csv",Path("data/live_m5/resampled")/f"{inst}_{T}.csv"]:
        if p.exists() and live_allowed(p): return p
    return None
def delim(line):
    return max([",",";","\t","|"],key=lambda c: line.count(c)) if line else ","
def col(cols,names):
    lows={c.lower().replace(" ","_"):c for c in cols}
    for n in names:
        if n.lower() in lows: return lows[n.lower()]
    for c in cols:
        for n in names:
            if n.lower() in c.lower() or c.lower() in n.lower(): return c
    return None
def num(x):
    try: return float(x)
    except Exception: return None
def read_csv_rows(p,max_tail=3000):
    if not p or not Path(p).exists(): return []
    with open(p,"r",encoding="utf-8",errors="replace") as f:
        first=f.readline(); d=delim(first); f.seek(0)
        rdr=csv.DictReader(f,delimiter=d); rows=[]
        for r in rdr:
            rows.append(r)
            if len(rows)>max_tail: rows=rows[-max_tail:]
        return rows
def ohlc(rows):
    if not rows: return []
    cols=list(rows[0].keys()); tc=col(cols,["bar_open_ts_utc","timestamp","datetime","time","date"]); oc=col(cols,["open","o"]); hc=col(cols,["high","h"]); lc=col(cols,["low","l"]); cc=col(cols,["close","c"])
    out=[]
    for r in rows:
        D=dt(r.get(tc)) if tc else None; O=num(r.get(oc)) if oc else None; H=num(r.get(hc)) if hc else None; L=num(r.get(lc)) if lc else None; C=num(r.get(cc)) if cc else None
        if D and None not in (O,H,L,C) and H>=L: out.append({"ts":D,"open":O,"high":H,"low":L,"close":C})
    return sorted(out,key=lambda x:x["ts"])
def rng(r): return r["high"]-r["low"]
def lower_reject(r):
    R=rng(r)
    if R<=0: return False,{"reason":"zero_range"}
    lw=min(r["open"],r["close"])-r["low"]; loc=(r["close"]-r["low"])/R
    return lw/R>=.30 and loc>=.55,{"range":R,"lower_wick":lw,"lower_wick_to_range":lw/R,"close_location":loc,"bullish_close":r["close"]>r["open"]}
def expanded(rows,i):
    if i<4: return False,{"reason":"not_enough_prior_h1_ranges"}
    prior=[rng(r) for r in rows[i-4:i] if rng(r)>0]
    if len(prior)<3: return False,{"reason":"not_enough_valid_prior_ranges"}
    avg=sum(prior)/len(prior); ratio=rng(rows[i])/avg if avg>0 else None
    return ratio is not None and ratio>=1.15,{"setup_range":rng(rows[i]),"prior_range_avg":avg,"range_expansion_ratio":ratio}
def m15_confirm(rows,start):
    end=start+timedelta(hours=1); inside=[r for r in rows if start<=r["ts"]<end]; conf=[r for r in inside if r["close"]>r["open"]]
    return bool(conf),{"h1_window_start":iso(start),"h1_window_end":iso(end),"m15_inside_count":len(inside),"m15_confirm_count":len(conf),"first_confirm_m15_open_ts_utc":iso(conf[0]["ts"]) if conf else None}
def load_state():
    s=load(STATE_PATH)
    if not isinstance(s,dict): s={"state_version":"sig_e_shadow_detector_state_v1","detector_id":"SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0","created_utc":now(),"history":[]}
    if not isinstance(s.get("history"),list): s["history"]=[]
    return s
def update_state(s,cur):
    hist=s.get("history",[]); key=cur.get("shadow_event_id") or cur.get("detector_run_id")
    if key not in {h.get("shadow_event_id") or h.get("detector_run_id") for h in hist if isinstance(h,dict)}:
        hist.append({k:cur.get(k) for k in ["detector_run_id","shadow_event_id","created_utc","detector_status","status_reason","setup_h1_open_ts_utc","trigger_h1_open_ts_utc","m15_confirm_ts_utc","authority"]})
    s["history"]=hist[-500:]; s["last_updated_utc"]=now(); s["last_status"]=cur.get("detector_status"); s["last_shadow_event_id"]=cur.get("shadow_event_id")
    return s
def build():
    cfg=load(CONFIG_PATH) or {}
    payloads=[]; files=[]
    for p in ["runtime/sig_e/market_state_current.json","runtime/sig_e/sig_e_regime1_market_state_current.json","panel/brain4/sig_e_market_state_current.json","runtime/sig_brain/sig_brain5_derived_context_latest.json","inputs/sig_brain4_live_context_latest.json","panel/brain4/sig_live_refresh_status_latest.json"]:
        x=load(p)
        if x is not None: payloads.append(x); files.append(p)
    h1=find_surface(payloads,"USDJPY","H1"); m15=find_surface(payloads,"USDJPY","M15")
    res={"program":"SIG-E-RUNTIME-SHADOW-DETECTOR1","detector_id":cfg.get("detector_id","SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0"),"source_spec_id":cfg.get("source_spec_id"),"detector_run_id":"SIGE_SD1_USDJPY_"+datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),"created_utc":now(),"instrument":"USDJPY","direction":"LONG","detector_status":"INPUT_INSUFFICIENT","status_reason":None,"is_shadow_match":False,"is_signal":False,"is_trade_proposal":False,"authority":{"signal_authorized":False,"trade_proposal_authorized":False,"entry_stop_target_authorized":False,"risk_sizing_authorized":False,"broker_execution_authorized":False,"auto_execution_authorized":False},"boundary":cfg.get("boundary",[]),"loaded_source_files":files,"surface_snapshot":{"h1_surface_available":h1 is not None,"m15_surface_available":m15 is not None,"h1_bar_open_ts_utc":iso(ts(h1)) if h1 else None,"m15_bar_open_ts_utc":iso(ts(m15)) if m15 else None,"h1_surface_score":score(h1,"USDJPY","H1") if h1 else None,"m15_surface_score":score(m15,"USDJPY","M15") if m15 else None},"checks":[],"not_authorized":["signal","manual trade proposal","entry/stop/target","risk sizing","broker/execution","auto execution","memory promotion"]}
    fr,fm=freshness(payloads); res["freshness_check"]={"status":fr,**fm}
    if fr=="DATA_STALE": res["detector_status"]="DATA_STALE"; res["status_reason"]="freshness_blocked"; return res
    ok,meta=regime(h1); res["checks"].append({"check_id":"REGIME","passed":ok,"details":meta})
    if h1 is None: res["status_reason"]="missing_usdjpy_h1_surface"; return res
    if meta.get("session_bucket")!="LONDON": res["detector_status"]="SESSION_NOT_MATCHED"; res["status_reason"]="session_not_london"; return res
    # Priority fix: alignment mismatch is REGIME_NOT_MATCHED even if vol missing.
    if not meta.get("alignment_ok"):
        res["detector_status"]="REGIME_NOT_MATCHED"; res["status_reason"]="d1_h4_alignment_not_matched"; return res
    # Only block missing vol after session/alignment are otherwise matched.
    if "volatility_state_or_d1_vol_bucket" in meta.get("missing_regime_fields",[]):
        res["detector_status"]="FIELD_MAPPING_INCOMPLETE"; res["status_reason"]="missing_required_volatility_field_after_session_alignment_match"; return res
    if not meta.get("vol_ok"):
        res["detector_status"]="REGIME_NOT_MATCHED"; res["status_reason"]="volatility_regime_not_matched"; return res
    hp=live_path("USDJPY","H1"); mp=live_path("USDJPY","M15")
    res["source_paths"]={"h1_ohlc_path":str(hp) if hp else None,"m15_ohlc_path":str(mp) if mp else None,"live_source_policy":"live_only_no_data_canonical_fallback"}
    if hp is None or mp is None: res["detector_status"]="LIVE_OHLC_SOURCE_MISSING"; res["status_reason"]="live_h1_or_m15_ohlc_source_missing_no_historical_fallback_allowed"; return res
    hrows=ohlc(read_csv_rows(hp)); mrows=ohlc(read_csv_rows(mp)); res["data_counts"]={"h1_rows_loaded":len(hrows),"m15_rows_loaded":len(mrows)}
    if len(hrows)<6: res["status_reason"]="not_enough_h1_rows_for_setup_trigger_window"; return res
    latest=len(hrows)-1; setup_i=latest-1; setup=hrows[setup_i]; trig=hrows[latest]
    res["setup_h1_open_ts_utc"]=iso(setup["ts"]); res["trigger_h1_open_ts_utc"]=iso(trig["ts"])
    a,b=lower_reject(setup); c,d=expanded(hrows,setup_i); setup_ok=a and c
    res["checks"].append({"check_id":"H1_SETUP_PREVIOUS_BAR","passed":setup_ok,"details":{"setup_h1_open_ts_utc":iso(setup["ts"]),"lower_rejection":b,"range_expansion":d}})
    if not setup_ok:
        a2,b2=lower_reject(trig); c2,d2=expanded(hrows,latest)
        if a2 and c2:
            res["detector_status"]="H1_TRIGGER_WAIT"; res["status_reason"]="latest_h1_bar_forms_setup_waiting_for_next_h1_close"; res["current_setup_candidate"]={"setup_h1_open_ts_utc":iso(trig["ts"]),"lower_rejection":b2,"range_expansion":d2}
        else:
            res["detector_status"]="SETUP_NOT_FORMED"; res["status_reason"]="previous_h1_bar_did_not_match_lower_rejection_expansion_setup"
        return res
    up=trig["close"]>trig["open"]; res["checks"].append({"check_id":"NEXT_H1_DIRECTION_CONFIRM","passed":up,"details":{"trigger_h1_open_ts_utc":iso(trig["ts"]),"open":trig["open"],"close":trig["close"],"direction":"UP" if up else "NOT_UP"}})
    if not up: res["detector_status"]="H1_TRIGGER_NOT_CONFIRMED"; res["status_reason"]="next_h1_bar_did_not_confirm_long_direction"; return res
    conf,mm=m15_confirm(mrows,trig["ts"]); res["checks"].append({"check_id":"M15_INSIDE_H1_DIRECTIONAL_CLOSE_CONFIRM","passed":conf,"details":mm})
    if not conf: res["detector_status"]="M15_TRIGGER_WAIT"; res["status_reason"]="h1_confirmed_but_no_inside_h1_m15_directional_close_yet"; return res
    res["detector_status"]="SHADOW_MATCH_CONFIRMED"; res["status_reason"]="regime_setup_h1_trigger_m15_trigger_all_confirmed"; res["is_shadow_match"]=True
    res["shadow_event_id"]="SIGE_SD1_USDJPY_LONDON_LONG_"+iso(trig["ts"]).replace("-","").replace(":","").replace("Z","")
    res["m15_confirm_ts_utc"]=mm.get("first_confirm_m15_open_ts_utc")
    res["observation_horizon"]={"horizon_h1_bars":16,"observation_end_ts_utc":iso(trig["ts"]+timedelta(hours=16)),"outcome_tracking_authorized":True,"trade_execution_authorized":False}
    return res
def main():
    res=build()
    if res.get("detector_status") not in VALID_STATUS: res["detector_status"]="INPUT_INSUFFICIENT"; res["status_reason"]="invalid_status_guardrail"
    st=update_state(load_state(),res)
    write(RUNTIME_OUT,res); write(PANEL_OUT,res); write(STATE_PATH,st)
    write(BUILD_RESULT,{"program":"SIG-E-RUNTIME-SHADOW-DETECTOR1-HOTFIX2","created_utc":now(),"build_status":"PASS","detector_status":res.get("detector_status"),"status_reason":res.get("status_reason"),"is_shadow_match":res.get("is_shadow_match"),"hotfixes":["surface_volatility_enrichment_compatible","regime_status_priority_fix","live_ohlc_only_no_historical_fallback"],"authority":res.get("authority")})
    print("SIG_E_SHADOW_DETECTOR1_HOTFIX2_BUILD_DONE")
    print("DETECTOR_STATUS="+str(res.get("detector_status")))
    print("STATUS_REASON="+str(res.get("status_reason")))
    print("IS_SHADOW_MATCH="+str(res.get("is_shadow_match")))
if __name__=="__main__": main()
