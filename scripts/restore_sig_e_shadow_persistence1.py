import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime

PROGRAM = "SIG-E-SHADOW-PERSIST1-RESTORE-HOTFIX1"

FILES = [
    {
        "logical_id": "lane1_obsledger_state",
        "local_path": "state/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector_observation/usdjpy_london_long_obsledger_v1.json",
        "counter_key": "refresh_records",
    },
    {
        "logical_id": "lane2_obsledger_state",
        "local_path": "state/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector_observation/usdjpy_asia_short_obsledger_v1.json",
        "counter_key": "refresh_records",
    },
    {
        "logical_id": "lane1_detector_state",
        "local_path": "state/sig_e_shadow_detector/usdjpy_london_long_state_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector/usdjpy_london_long_state_v1.json",
        "counter_key": "history",
    },
    {
        "logical_id": "lane2_detector_state",
        "local_path": "state/sig_e_shadow_detector2/usdjpy_asia_short_state_v1.json",
        "mirror_path": "persist/sig_e_shadow_detector2/usdjpy_asia_short_state_v1.json",
        "counter_key": "history",
    },
]

OUT = Path("outputs/_sig_e_shadow_persist1/sig_e_shadow_persist1_restore_result.json")
RUNTIME_OUT = Path("runtime/sig_e/shadow_persistence_restore_current.json")
PANEL_OUT = Path("panel/brain4/sig_e_shadow_persistence_restore_status_current.json")

AUTHORITY = {
    "signal_authorized": False,
    "trade_proposal_authorized": False,
    "entry_stop_target_authorized": False,
    "risk_sizing_authorized": False,
    "broker_execution_authorized": False,
    "auto_execution_authorized": False,
}

BOUNDARY = [
    "PERSISTENCE_RESTORE_ONLY",
    "OFFLINE_SAFE_RESTORE",
    "SHADOW_RESEARCH_ONLY",
    "NOT_SIGNAL",
    "NO_TRADE_PROPOSAL",
    "NO_ENTRY_STOP_TARGET",
    "NO_RISK_OR_POSITION_SIZING",
    "NO_BROKER_EXECUTION",
    "NO_AUTO_EXECUTION",
    "NO_MEMORY_PROMOTION",
    "NO_RULE_REWRITE",
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def load_local(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def count_for(obj, key):
    if not isinstance(obj, dict):
        return 0
    value = obj.get(key)
    return len(value) if isinstance(value, list) else 0

def remote_restore_allowed():
    # Local Windows/proxy environments can hang inside urllib proxy bypass.
    # By default, remote restore is enabled only inside GitHub Actions.
    # To test locally, explicitly set SIG_E_PERSIST_ALLOW_REMOTE_RESTORE=1.
    if os.environ.get("SIG_E_PERSIST_DISABLE_REMOTE_RESTORE") == "1":
        return False
    if os.environ.get("SIG_E_PERSIST_ALLOW_REMOTE_RESTORE") == "1":
        return True
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

def github_pages_bases():
    bases = []
    env_base = os.environ.get("SIG_E_PERSIST_BASE_URL") or os.environ.get("TRADINGOS_PAGES_BASE_URL")
    if env_base:
        bases.append(env_base.rstrip("/"))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        bases.append(f"https://{owner}.github.io/{name}")
        bases.append(f"https://{owner}.github.io/{name}/panel/brain4")
    bases.append("https://shahramshiri-ops.github.io/TradingOS2")
    bases.append("https://shahramshiri-ops.github.io/TradingOS2/panel/brain4")
    out = []
    for b in bases:
        if b and b not in out:
            out.append(b)
    return out

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TradingOS-SIG-E-PERSIST1"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if getattr(resp, "status", 200) != 200:
                return None, f"http_status_{getattr(resp, 'status', 'unknown')}"
            raw = resp.read()
        return json.loads(raw.decode("utf-8")), None
    except BaseException as e:
        # Intentionally catches low-level Windows/proxy/DNS errors and prevents workflow failure.
        return None, type(e).__name__ + ": " + str(e)[:200]

def remote_candidates(base, mirror_path, local_path):
    return [
        f"{base}/{mirror_path}",
        f"{base}/panel/brain4/{mirror_path}",
        f"{base}/{local_path}",
    ]

def restore_one(item, allow_remote):
    local_obj = load_local(item["local_path"])
    local_count = count_for(local_obj, item["counter_key"])

    if not allow_remote:
        return {
            "logical_id": item["logical_id"],
            "local_path": item["local_path"],
            "mirror_path": item["mirror_path"],
            "local_count_before": local_count,
            "best_remote_count": None,
            "best_remote_url": None,
            "restored": False,
            "reason": "REMOTE_RESTORE_SKIPPED_OFFLINE_SAFE_LOCAL_MODE",
            "attempts_sample": [],
        }

    best = None
    attempts = []
    for base in github_pages_bases():
        for url in remote_candidates(base, item["mirror_path"], item["local_path"]):
            remote_obj, err = fetch_json(url)
            if remote_obj is not None:
                remote_count = count_for(remote_obj, item["counter_key"])
                attempts.append({"url": url, "status": "FETCHED", "remote_count": remote_count})
                if best is None or remote_count > best["remote_count"]:
                    best = {"url": url, "remote_obj": remote_obj, "remote_count": remote_count}
            else:
                attempts.append({"url": url, "status": "MISS", "error": err})

    restored = False
    reason = "NO_REMOTE_BETTER_THAN_LOCAL"
    remote_count = None
    remote_url = None

    if best is not None:
        remote_count = best["remote_count"]
        remote_url = best["url"]
        if remote_count > local_count or (local_obj is None and remote_count >= 0):
            Path(item["local_path"]).parent.mkdir(parents=True, exist_ok=True)
            Path(item["local_path"]).write_text(json.dumps(best["remote_obj"], indent=2, ensure_ascii=False), encoding="utf-8")
            restored = True
            reason = "REMOTE_RESTORED"
        else:
            reason = "LOCAL_ALREADY_HAS_SAME_OR_MORE_RECORDS"
    else:
        reason = "NO_REMOTE_STATE_FOUND_FIRST_RUN_OR_NOT_DEPLOYED_YET"

    return {
        "logical_id": item["logical_id"],
        "local_path": item["local_path"],
        "mirror_path": item["mirror_path"],
        "local_count_before": local_count,
        "best_remote_count": remote_count,
        "best_remote_url": remote_url,
        "restored": restored,
        "reason": reason,
        "attempts_sample": attempts[:20],
    }

def main():
    allow_remote = remote_restore_allowed()
    results = [restore_one(item, allow_remote) for item in FILES]
    restored_count = sum(1 for r in results if r["restored"])
    remote_found_count = sum(1 for r in results if r["best_remote_url"])

    current = {
        "program": PROGRAM,
        "created_utc": now(),
        "restore_status": "PASS",
        "remote_restore_allowed": allow_remote,
        "restored_count": restored_count,
        "remote_found_count": remote_found_count,
        "files": results,
        "authority": AUTHORITY,
        "boundary": BOUNDARY,
        "not_authorized": [
            "signal", "manual trade proposal", "entry/stop/target", "risk sizing",
            "broker/execution", "auto execution", "memory promotion", "rule rewrite"
        ],
    }
    write_json(OUT, current)
    write_json(RUNTIME_OUT, current)
    write_json(PANEL_OUT, current)
    print("SIG_E_SHADOW_PERSIST1_RESTORE_HOTFIX1_DONE")
    print("REMOTE_RESTORE_ALLOWED=" + str(allow_remote))
    print("RESTORED_COUNT=" + str(restored_count))
    print("REMOTE_FOUND_COUNT=" + str(remote_found_count))

if __name__ == "__main__":
    main()
