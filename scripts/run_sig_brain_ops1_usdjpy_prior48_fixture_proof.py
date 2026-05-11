#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

POLICY = "PRIOR48_LEGACY_RESEARCH_192_MIN96_CLOSED_v1_0"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(path, obj):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)

def make_m15(prior_count: int, eval_high=110.0, eval_low=98.0, eval_close=99.0):
    # End bar at 2026-05-08 16:00 UTC, a NEW_YORK session bar in the active policy.
    import datetime as dt
    end = dt.datetime(2026,5,8,16,0,tzinfo=dt.timezone.utc)
    start = end - dt.timedelta(minutes=15*prior_count)
    bars=[]
    for i in range(prior_count):
        ts = start + dt.timedelta(minutes=15*i)
        bars.append({"bar_open_ts_utc":ts.isoformat().replace('+00:00','Z'),"open":99.5,"high":100.0,"low":99.0,"close":99.6})
    bars.append({"bar_open_ts_utc":end.isoformat().replace('+00:00','Z'),"open":100.5,"high":eval_high,"low":eval_low,"close":eval_close})
    return bars

def make_h1():
    import datetime as dt
    end = dt.datetime(2026,5,8,16,0,tzinfo=dt.timezone.utc)
    start = end - dt.timedelta(hours=12)
    return [{"bar_open_ts_utc":(start+dt.timedelta(hours=i)).isoformat().replace('+00:00','Z'),"open":100.0+i*0.01,"high":100.2+i*0.01,"low":99.8+i*0.01,"close":100.05+i*0.01} for i in range(13)]

def make_raw(prior_count:int):
    m15=make_m15(prior_count)
    h1=make_h1()
    eur_m15=make_m15(96, eval_high=100.1, eval_low=99.0, eval_close=99.8)
    return {"context_version":"PATCHBUILD1_FIXTURE_RAW_BARS","created_utc":"2026-05-11T00:00:00Z","surfaces":[
        {"instrument":"EURUSD","timeframe":"M15","bars":eur_m15},
        {"instrument":"EURUSD","timeframe":"H1","bars":h1},
        {"instrument":"USDJPY","timeframe":"M15","bars":m15},
        {"instrument":"USDJPY","timeframe":"H1","bars":h1},
    ],"global_boundary":{"signal_authorized":False,"action_surface_authorized":False}}

def make_test_registry(base_registry):
    mem={
        "memory_id":"USDJPY_PRIOR48_NY_UPSIDE_SWEEP_REJECTION_FADE_DOWN_TEST_ACTIVE_FIXTURE_ONLY",
        "instrument":"USDJPY","timeframe":"M15",
        "memory_class":"caveated_brain_watch_fixture_only_not_production",
        "activation_status":"ACTIVE_FIXTURE_ONLY_NOT_PRODUCTION",
        "active_in_runtime":True,
        "score_not_probability":76,
        "band":"FIXTURE_ONLY_NOT_PROBABILITY",
        "plain_language_label_fa":"USDJPY fixture only",
        "plain_language_summary_fa":"Fixture only; not production memory.",
        "required_context_fields":["session_bucket","upside_sweep_flag","sweep_then_reject_back_inside_up_flag","sweep_reference_type_up","sweep_reference_policy_up"],
        "matching_rule":{"required_all":[
            {"field":"session_bucket","op":"eq","value":"NEW_YORK"},
            {"field":"upside_sweep_flag","op":"bool_eq","value":True},
            {"field":"sweep_then_reject_back_inside_up_flag","op":"bool_eq","value":True},
            {"field":"sweep_reference_type_up","op":"eq","value":"PRIOR48"},
            {"field":"sweep_reference_policy_up","op":"eq","value":POLICY}
        ]},
        "evidence_summary":{"fixture_only":True},
        "forbidden_use":["signal","entry","stop","target","profitability","tradability"],
        "runtime_display_caveat_required":"Fixture-only memory for integration proof; not production, not signal."
    }
    return {"registry_version":"PATCHBUILD1_TEST_REGISTRY_FIXTURE_ONLY","memories":[mem]}

def main():
    root=Path.cwd()
    proofs=[]
    # 96 prior bars: should evaluate and match true.
    write("inputs/patchbuild1_fixture_96_prior.json", make_raw(96))
    run([sys.executable,"scripts/build_sig_brain5_live_context.py","--raw-bars","inputs/patchbuild1_fixture_96_prior.json","--out","inputs/patchbuild1_context_96.json","--runtime-copy","runtime/sig_brain/patchbuild1_context_96.json"])
    ctx96=load("inputs/patchbuild1_context_96.json")
    row96=[r for r in ctx96["surfaces"] if r.get("instrument")=="USDJPY"][0]
    proofs.append({"gate":"G3_BRAIN5_DERIVATION_96_PRIOR","status":"PASS" if row96.get("upside_sweep_flag") is True and row96.get("sweep_then_reject_back_inside_up_flag") is True and row96.get("sweep_reference_type_up")=="PRIOR48" and row96.get("sweep_reference_policy_up")==POLICY else "FAIL", "observed": row96})
    # 95 prior bars: should be insufficient, not fake inactive.
    write("inputs/patchbuild1_fixture_95_prior.json", make_raw(95))
    run([sys.executable,"scripts/build_sig_brain5_live_context.py","--raw-bars","inputs/patchbuild1_fixture_95_prior.json","--out","inputs/patchbuild1_context_95.json","--runtime-copy","runtime/sig_brain/patchbuild1_context_95.json"])
    ctx95=load("inputs/patchbuild1_context_95.json")
    row95=[r for r in ctx95["surfaces"] if r.get("instrument")=="USDJPY"][0]
    proofs.append({"gate":"G4_INSUFFICIENT_HISTORY_95_PRIOR","status":"PASS" if row95.get("data_sufficiency_status")=="MISSING_REQUIRED_BARS" and row95.get("upside_sweep_flag") is None else "FAIL", "observed": row95})
    # current bar exclusion: ref should be 100 not 110.
    proofs.append({"gate":"G5_CURRENT_BAR_EXCLUSION","status":"PASS" if abs(float(row96.get("sweep_reference_value_up"))-100.0)<1e-9 else "FAIL", "observed_ref": row96.get("sweep_reference_value_up")})
    # Brain4 fixture true and missing policy proof.
    base=load("sig_brain/brain_memory_registry_v1_0.json")
    testreg=make_test_registry(base)
    write("sig_brain/patchbuild1_test_registry_active_fixture_only.json", testreg)
    run([sys.executable,"scripts/build_sig_brain4_runtime_payload.py","--context","inputs/patchbuild1_context_96.json","--registry","sig_brain/patchbuild1_test_registry_active_fixture_only.json","--out","runtime/sig_brain/patchbuild1_payload_96.json","--panel-out","panel/brain4/patchbuild1_payload_96.json"])
    payload96=load("runtime/sig_brain/patchbuild1_payload_96.json")
    card96=payload96["cards"][0]
    proofs.append({"gate":"G7_BRAIN4_REQUIRED_FIELDS_MATCH_TRUE","status":"PASS" if card96.get("brain_state")=="CAVEATED_WATCH_ACTIVE" and card96.get("is_active_match") is True else "FAIL", "observed_state":card96.get("brain_state")})
    ctx_missing=ctx96.copy()
    ctx_missing["surfaces"]=[dict(r) for r in ctx96["surfaces"]]
    for r in ctx_missing["surfaces"]:
        if r.get("instrument")=="USDJPY":
            r.pop("sweep_reference_policy_up", None)
    write("inputs/patchbuild1_context_missing_policy.json", ctx_missing)
    run([sys.executable,"scripts/build_sig_brain4_runtime_payload.py","--context","inputs/patchbuild1_context_missing_policy.json","--registry","sig_brain/patchbuild1_test_registry_active_fixture_only.json","--out","runtime/sig_brain/patchbuild1_payload_missing_policy.json","--panel-out","panel/brain4/patchbuild1_payload_missing_policy.json"])
    payload_missing=load("runtime/sig_brain/patchbuild1_payload_missing_policy.json")
    card_missing=payload_missing["cards"][0]
    proofs.append({"gate":"G7_BRAIN4_REQUIRED_FIELDS_MISSING_POLICY","status":"PASS" if card_missing.get("brain_state")=="MEMORY_INPUT_INSUFFICIENT" and "sweep_reference_policy_up" in card_missing.get("missing_inputs",[]) else "FAIL", "observed_state":card_missing.get("brain_state"), "missing_inputs":card_missing.get("missing_inputs")})
    # Standard validators no-action surface.
    run([sys.executable,"scripts/build_sig_brain5_live_context.py","--raw-bars","inputs/patchbuild1_fixture_96_prior.json"])
    run([sys.executable,"scripts/validate_sig_brain5_context_builder.py"])
    val5=load("proofs/sig_brain5_context_validation_result.json")
    val4=load("proofs/sig_brain4_validation_result.json")
    proofs.append({"gate":"G9_NO_ACTION_SURFACE_VALIDATORS","status":"PASS" if val5.get("validation_status")=="PASS" and val4.get("validation_status")=="PASS" else "FAIL", "brain5_validation":val5, "brain4_validation":val4})
    overall="PASS" if all(p.get("status")=="PASS" for p in proofs) else "FAIL"
    out={"program":"SIG-DISCOVERY-FACTORY1-W1-BRAININTEG1-PATCHBUILD1","proof_type":"FIXTURE_PROOF_ONLY_NOT_HOLDOUT_NOT_MEMORY_ACTIVATION","validation_status":overall,"gates":proofs,"signal_authorized":False,"action_surface_authorized":False,"holdout_opened":False,"memory_activation_authorized":False}
    write("proofs/patchbuild1_fixture_validation_result.json", out)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if overall=="PASS" else 1
if __name__ == "__main__":
    raise SystemExit(main())
