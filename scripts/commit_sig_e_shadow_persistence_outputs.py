import os
import subprocess
from pathlib import Path
from datetime import datetime
import json

PROGRAM = "SIG-E-SHADOW-PERSISTENCE-COMMIT"

OUT = Path("outputs/_sig_e_shadow_workflow_chain1/sig_e_shadow_persistence_commit_result.json")

SAFE_PATHS = [
    "runtime/sig_e/shadow_detector_usdjpy_london_long_current.json",
    "runtime/sig_e/shadow_detector_usdjpy_london_long_obsledger_current.json",
    "runtime/sig_e/shadow_detector_usdjpy_asia_short_current.json",
    "runtime/sig_e/shadow_detector_usdjpy_asia_short_obsledger_current.json",
    "runtime/sig_e/shadow_portfolio_current.json",
    "runtime/sig_e/shadow_persistence_current.json",
    "runtime/sig_e/shadow_persistence_restore_current.json",

    "panel/brain4/sig_e_shadow_detector_status_current.json",
    "panel/brain4/sig_e_shadow_detector_obsledger_status_current.json",
    "panel/brain4/sig_e_shadow_detector2_status_current.json",
    "panel/brain4/sig_e_shadow_detector2_obsledger_status_current.json",
    "panel/brain4/sig_e_shadow_portfolio_status_current.json",
    "panel/brain4/sig_e_shadow_persistence_status_current.json",
    "panel/brain4/sig_e_shadow_persistence_restore_status_current.json",
    "panel/brain4/persist",

    "state/sig_e_shadow_detector",
    "state/sig_e_shadow_detector2",
    "state/sig_e_shadow_detector_observation",

    "outputs/_sig_e_shadow_detector1",
    "outputs/_sig_e_shadow_detector2",
    "outputs/_sig_e_shadow_detector_obsledger1",
    "outputs/_sig_e_shadow_detector2_obsledger",
    "outputs/_sig_e_shadow_portfolio1",
    "outputs/_sig_e_shadow_persist1",
    "outputs/_sig_e_shadow_workflow_chain1",
    "runtime/sig_e/shadow_observation_report_current.json",
    "panel/brain4/sig_e_shadow_observation_report_current.json",
    "outputs/_sig_e_shadow_report1",
    "runtime/sig_e/shadow_coverage1_current.json",
    "panel/brain4/sig_e_shadow_coverage1_current.json",
    "outputs/_sig_e_shadow_coverage1",
    "runtime/sig_e/shadow_lane1_overlap_preflight_current.json",
    "panel/brain4/sig_e_shadow_lane1_overlap_preflight_current.json",
    "outputs/_sig_e_shadow_lane1_overlap_preflight1",
    "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_current.json",
    "runtime/sig_e/shadow_detector_eurusd_london_pdlow_trap_long_obsledger_current.json",
    "panel/brain4/sig_e_shadow_detector3_status_current.json",
    "panel/brain4/sig_e_shadow_detector3_obsledger_status_current.json",
    "state/sig_e_shadow_detector3",
    "outputs/_sig_e_shadow_detector3",
    "outputs/_sig_e_shadow_detector3_obsledger",
]

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def run(cmd, check=True):
    p = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed {cmd}\n{p.stdout}")
    return p.returncode, p.stdout

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def existing_paths():
    return [p for p in SAFE_PATHS if Path(p).exists()]

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "commit_status": "UNKNOWN",
        "paths_existing": [],
        "git_status_before": None,
        "git_status_after": None,
        "commit_attempted": False,
        "push_attempted": False,
        "authority": AUTHORITY,
        "boundary": [
            "SAFE_GENERATED_OUTPUT_COMMIT_ONLY",
            "SHADOW_RESEARCH_ONLY",
            "NOT_SIGNAL",
            "NO_TRADE_PROPOSAL",
            "NO_ENTRY_STOP_TARGET",
            "NO_RISK_OR_POSITION_SIZING",
            "NO_BROKER_EXECUTION",
            "NO_AUTO_EXECUTION",
            "NO_MEMORY_PROMOTION",
            "NO_RULE_REWRITE",
        ],
    }

    run('git config user.name "github-actions[bot]"', check=False)
    run('git config user.email "41898282+github-actions[bot]@users.noreply.github.com"', check=False)

    result["git_status_before"] = run("git status --short", check=False)[1]
    paths = existing_paths()
    result["paths_existing"] = paths

    if not paths:
        result["commit_status"] = "NO_SAFE_PATHS_FOUND"
        write_json(OUT, result)
        print("SIG_E_SHADOW_PERSISTENCE_COMMIT_NO_SAFE_PATHS_FOUND")
        return

    # Stage only known generated SIG-E shadow/persistence paths.
    quoted = " ".join('"' + p.replace('"', '\\"') + '"' for p in paths)
    run("git add " + quoted, check=True)

    code, diff = run("git diff --cached --quiet", check=False)
    if code == 0:
        result["commit_status"] = "NO_CHANGES_TO_COMMIT"
        result["git_status_after"] = run("git status --short", check=False)[1]
        write_json(OUT, result)
        print("SIG_E_SHADOW_PERSISTENCE_COMMIT_NO_CHANGES")
        return

    result["commit_attempted"] = True
    msg = "Update SIG-E shadow persistence outputs"
    run(f'git commit -m "{msg}"', check=True)

    branch = os.environ.get("GITHUB_REF_NAME") or "main"
    result["push_attempted"] = True
    run(f"git push origin HEAD:{branch}", check=True)

    result["commit_status"] = "COMMITTED_AND_PUSHED"
    result["git_status_after"] = run("git status --short", check=False)[1]
    write_json(OUT, result)
    print("SIG_E_SHADOW_PERSISTENCE_COMMIT_COMMITTED_AND_PUSHED")
    print("Branch:", branch)

if __name__ == "__main__":
    main()

