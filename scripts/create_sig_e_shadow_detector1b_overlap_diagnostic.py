
import re
from pathlib import Path
from datetime import datetime
import json

SRC = Path("scripts/build_sig_e_shadow_detector1_usdjpy_london_long.py")
DST = Path("scripts/build_sig_e_shadow_detector1b_overlap_diagnostic.py")
OUT = Path("outputs/_sig_e_shadow_detector1b_overlap/create_detector1b_result.json")

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def main():
    if not SRC.exists():
        res = {"program":"CREATE_SIG_E_DETECTOR1B","created_utc":now(),"status":"FAIL_SOURCE_DETECTOR1_MISSING","source":str(SRC)}
        write_json(OUT,res)
        print("CREATE_DETECTOR1B_FAIL_SOURCE_MISSING")
        raise SystemExit(1)

    text = SRC.read_text(encoding="utf-8")
    replacements = [
        ("SIG-E-RUNTIME-SHADOW-DETECTOR1-H1-OHLC-HISTORY-HOTFIX", "SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1"),
        ("SIG-E-RUNTIME-SHADOW-DETECTOR1", "SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1"),
        ("SIG_E_SHADOW_DETECTOR_USDJPY_LONDON_LONG_H1_M15_v1_0", "SIG_E_SHADOW_DETECTOR1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15_v1_0"),
        ("SIGE_SD1_USDJPY_", "SIGE_SD1B_USDJPY_OVERLAP_"),
        ("config/sig_e/shadow_detectors/usdjpy_london_long_h1_m15_v1_0.json", "config/sig_e/shadow_detectors/usdjpy_overlap_long_diagnostic_h1_m15_v1_0.json"),
        ("runtime/sig_e/shadow_detector_usdjpy_london_long_current.json", "runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json"),
        ("panel/brain4/sig_e_shadow_detector_status_current.json", "panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json"),
        ("state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json", "state/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json"),
        ("outputs/_sig_e_shadow_detector1/sig_e_shadow_detector1_build_result.json", "outputs/_sig_e_shadow_detector1b_overlap/sig_e_shadow_detector1b_overlap_build_result.json"),
        ("SHADOW_MATCH_CONFIRMED", "DIAGNOSTIC_SHADOW_MATCH_CONFIRMED"),
        ("session_not_london", "session_not_london_ny_overlap"),
        ("session == \"LONDON\"", "session == \"LONDON_NY_OVERLAP\""),
        ("session_bucket\": session == \"LONDON\"", "session_bucket\": session == \"LONDON_NY_OVERLAP\""),
        ("USDJPY London Long", "USDJPY Overlap Long Diagnostic"),
    ]
    for a,b in replacements:
        text = text.replace(a,b)

    text = text.replace(
        '"broker_execution_authorized": False,\n    "auto_execution_authorized": False,',
        '"broker_execution_authorized": False,\n    "auto_execution_authorized": False,\n    "primary_lane_authorized": False,\n    "lane_rule_change_authorized": False,'
    )
    text = text.replace(
        '"NO_RULE_REWRITE"', 
        '"NO_RULE_REWRITE", "DIAGNOSTIC_ONLY_LANE", "OVERLAP_VARIANT_RESEARCH_ONLY", "DOES_NOT_CHANGE_LANE1"'
    )
    text = text.replace(
        '"is_trade_proposal": False,',
        '"is_trade_proposal": False,\n        "classification": "DIAGNOSTIC_ONLY_SHADOW_LANE_NOT_PRIMARY",\n        "is_diagnostic_shadow_match": False,'
    )
    if 'result["is_shadow_match"] = True' in text and 'result["is_diagnostic_shadow_match"] = True' not in text:
        text = text.replace(
            'result["is_shadow_match"] = True',
            'result["is_shadow_match"] = True\n    result["is_diagnostic_shadow_match"] = True'
        )
    DST.write_text(text, encoding="utf-8")
    res = {"program":"CREATE_SIG_E_DETECTOR1B","created_utc":now(),"status":"PASS","source":str(SRC),"destination":str(DST)}
    write_json(OUT,res)
    print("CREATE_DETECTOR1B_OVERLAP_DIAGNOSTIC_PASS")

if __name__ == "__main__":
    main()
