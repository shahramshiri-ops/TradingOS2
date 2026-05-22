
import json, shutil
from pathlib import Path
from datetime import datetime

PROGRAM='SIG-E-SHADOW-LANE1B-OVERLAP-DIAGNOSTIC1-INTEGRATION'
OUT=Path('outputs/_sig_e_shadow_detector1b_overlap/sig_e_shadow_detector1b_integration_patch_result.json')
PORTFOLIO=Path('scripts/build_sig_e_shadow_portfolio1.py')
REPORT=Path('scripts/build_sig_e_shadow_observation_report1.py')
COVERAGE=Path('scripts/build_sig_e_shadow_coverage1.py')
RESTORE=Path('scripts/restore_sig_e_shadow_persistence1.py')
SNAPSHOT=Path('scripts/build_sig_e_shadow_persistence1_snapshot.py')
WORKFLOW=Path('.github/workflows/sig_live_m5_refresh_resample_brain.yml')
COMMIT=Path('scripts/commit_sig_e_shadow_persistence_outputs.py')
LANE_ID='SIGE_SD1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15'
def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,t): p.write_text(t,encoding='utf-8')
def backup(p):
    b=p.with_suffix(p.suffix+'.bak_lane1b_overlap_diagnostic1'); shutil.copyfile(p,b); return str(b)
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding='utf-8')
def patch_text_file(path, marker, insert, reason, unique):
    item={'file':str(path),'exists':path.exists(),'patched':False,'reason':None}
    if not path.exists(): item['reason']='MISSING'; return item
    txt=read(path)
    if unique in txt: item['reason']='ALREADY_PRESENT'; return item
    if marker not in txt: item['reason']='MARKER_NOT_FOUND'; return item
    item['backup']=backup(path); write(path,txt.replace(marker,insert+marker,1)); item['patched']=True; item['reason']=reason; return item
def patch_portfolio():
    lane='''    {
        "lane_id": "SIGE_SD1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15",
        "display_name": "USDJPY Overlap Long Diagnostic H1+M15",
        "classification": "DIAGNOSTIC_SHADOW_OBSERVATION",
        "instrument": "USDJPY",
        "direction": "LONG",
        "detector_file": Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json"),
        "ledger_file": Path("runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_obsledger_current.json"),
        "expected_shadow_match_statuses": ["DIAGNOSTIC_SHADOW_MATCH_CONFIRMED"],
        "counts_as_primary": False,
    },
'''
    return patch_text_file(PORTFOLIO,']\n\nDATA_OR_FIELD_STATUSES',lane,'LANE1B_ADDED_TO_PORTFOLIO',LANE_ID)
def patch_report():
    item={'file':str(REPORT),'exists':REPORT.exists(),'patched':False,'reason':None}
    if not REPORT.exists(): item['reason']='MISSING'; return item
    txt=read(REPORT)
    if 'usdjpy_overlap_long_diagnostic_obsledger_v1.json' in txt: item['reason']='ALREADY_PRESENT'; return item
    marker='    Path("state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json"),'
    add='    Path("state/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json"),'
    if marker not in txt: item['reason']='REPORT_MARKER_NOT_FOUND'; return item
    item['backup']=backup(REPORT); write(REPORT,txt.replace(marker,marker+'\n'+add,1)); item['patched']=True; item['reason']='LANE1B_ADDED_TO_REPORT'; return item
def patch_coverage():
    block='''    {
        "lane_id": "SIGE_SD1B_USDJPY_OVERLAP_LONG_DIAGNOSTIC_H1_M15",
        "display_name": "USDJPY Overlap Long Diagnostic H1+M15",
        "state_path": Path("state/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json"),
    },
'''
    return patch_text_file(COVERAGE,']\n\nRUNTIME_OUT',block,'LANE1B_ADDED_TO_COVERAGE','usdjpy_overlap_long_diagnostic_obsledger_v1.json')
def patch_restore():
    item={'file':str(RESTORE),'exists':RESTORE.exists(),'patched':False,'reason':None}
    if not RESTORE.exists(): item['reason']='MISSING'; return item
    txt=read(RESTORE)
    if 'lane1b_overlap_obsledger_state' in txt: item['reason']='ALREADY_PRESENT'; return item
    block='''    {
        "logical_id": "lane1b_overlap_obsledger_state",
        "local_path": "state/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json",
        "counter_key": "refresh_records",
    },
    {
        "logical_id": "lane1b_overlap_detector_state",
        "local_path": "state/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json",
        "counter_key": "history",
    },
'''
    if ']\n\nOUT = Path' not in txt: item['reason']='RESTORE_MARKER_NOT_FOUND'; return item
    item['backup']=backup(RESTORE); write(RESTORE,txt.replace(']\n\nOUT = Path',block+']\n\nOUT = Path',1)); item['patched']=True; item['reason']='LANE1B_ADDED_TO_RESTORE'; return item
def patch_snapshot():
    item={'file':str(SNAPSHOT),'exists':SNAPSHOT.exists(),'patched':False,'reason':None}
    if not SNAPSHOT.exists(): item['reason']='MISSING'; return item
    txt=read(SNAPSHOT); changed=False
    if 'lane1b_overlap_obsledger_state' not in txt:
        block='''    {
        "logical_id": "lane1b_overlap_obsledger_state",
        "source": "state/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector_observation/usdjpy_overlap_long_diagnostic_obsledger_v1.json",
        "counter": "refresh_records",
    },
    {
        "logical_id": "lane1b_overlap_detector_state",
        "source": "state/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json",
        "mirror": "panel/brain4/persist/sig_e_shadow_detector1b/usdjpy_overlap_long_diagnostic_state_v1.json",
        "counter": "history",
    },
'''
        if ']\n\nCURRENT_FILES' not in txt: item['reason']='SNAPSHOT_STATE_MARKER_NOT_FOUND'; return item
        txt=txt.replace(']\n\nCURRENT_FILES',block+']\n\nCURRENT_FILES',1); changed=True
    if 'lane1b_overlap_obsledger_current' not in txt:
        block='''    {
        "logical_id": "lane1b_overlap_obsledger_current",
        "source": "runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_obsledger_current.json",
        "mirror": "panel/brain4/persist/current/shadow_detector_usdjpy_overlap_long_diagnostic_obsledger_current.json",
    },
    {
        "logical_id": "lane1b_overlap_detector_current",
        "source": "runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json",
        "mirror": "panel/brain4/persist/current/shadow_detector_usdjpy_overlap_long_diagnostic_current.json",
    },
'''
        if ']\n\nOUT = Path' not in txt: item['reason']='SNAPSHOT_CURRENT_MARKER_NOT_FOUND'; return item
        txt=txt.replace(']\n\nOUT = Path',block+']\n\nOUT = Path',1); changed=True
    if not changed: item['reason']='ALREADY_PRESENT'; return item
    item['backup']=backup(SNAPSHOT); write(SNAPSHOT,txt); item['patched']=True; item['reason']='LANE1B_ADDED_TO_SNAPSHOT'; return item
def patch_workflow():
    block='''          python scripts/create_sig_e_shadow_detector1b_overlap_diagnostic.py
          python scripts/build_sig_e_shadow_detector1b_overlap_diagnostic.py
          python scripts/validate_sig_e_shadow_detector1b_overlap_diagnostic.py
          python scripts/build_sig_e_shadow_detector1b_overlap_obsledger.py
          python scripts/validate_sig_e_shadow_detector1b_overlap_obsledger.py

'''
    return patch_text_file(WORKFLOW,'          python scripts/build_sig_e_shadow_portfolio1.py',block,'LANE1B_ADDED_TO_WORKFLOW','build_sig_e_shadow_detector1b_overlap_diagnostic.py')
def patch_commit():
    item={'file':str(COMMIT),'exists':COMMIT.exists(),'patched':False,'reason':None}
    if not COMMIT.exists(): item['reason']='MISSING'; return item
    txt=read(COMMIT)
    additions=[
        '    "runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_current.json",',
        '    "runtime/sig_e/shadow_detector_usdjpy_overlap_long_diagnostic_obsledger_current.json",',
        '    "panel/brain4/sig_e_shadow_detector1b_overlap_status_current.json",',
        '    "panel/brain4/sig_e_shadow_detector1b_overlap_obsledger_status_current.json",',
        '    "state/sig_e_shadow_detector1b",',
        '    "outputs/_sig_e_shadow_detector1b_overlap",',
        '    "outputs/_sig_e_shadow_detector1b_overlap_obsledger",',
    ]
    missing=[a for a in additions if a not in txt]
    if not missing: item['reason']='ALREADY_PRESENT'; return item
    marker='    "outputs/_sig_e_shadow_lane1_overlap_preflight1",'
    if marker not in txt: marker='    "outputs/_sig_e_shadow_coverage1",'
    if marker not in txt: marker='    "outputs/_sig_e_shadow_report1",'
    if marker not in txt: item['reason']='COMMIT_MARKER_NOT_FOUND'; return item
    item['backup']=backup(COMMIT); write(COMMIT,txt.replace(marker,marker+'\n'+'\n'.join(missing),1)); item['patched']=True; item['reason']='LANE1B_ADDED_TO_COMMIT'; return item
def main():
    res=[patch_portfolio(),patch_report(),patch_coverage(),patch_restore(),patch_snapshot(),patch_workflow(),patch_commit()]
    status='PASS' if all(x.get('patched') or x.get('reason')=='ALREADY_PRESENT' for x in res) else 'PARTIAL_OR_FAIL'
    write_json(OUT,{'program':PROGRAM,'created_utc':now(),'patch_status':status,'results':res})
    print('SIG_E_SHADOW_LANE1B_OVERLAP_DIAGNOSTIC1_INTEGRATION_'+status)
    for r in res: print(r['file'],'->',r['reason'])
    if status!='PASS': raise SystemExit(2)
if __name__=='__main__': main()
