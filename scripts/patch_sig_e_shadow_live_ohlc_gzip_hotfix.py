
import re, json
from pathlib import Path
from datetime import datetime

OUT = Path("outputs/_sig_e_shadow_live_ohlc_gzip_hotfix/sig_e_shadow_live_ohlc_gzip_hotfix_patch_result.json")

READ_CSV_ROWS_REPLACEMENT = '''def read_csv_rows(path, max_tail=10000):
    if not path or not Path(path).exists():
        return []
    p = Path(path)
    try:
        if str(p).lower().endswith(".gz"):
            import gzip
            opener = lambda: gzip.open(p, "rt", encoding="utf-8", errors="replace", newline="")
            fmt = "csv.gz"
        else:
            opener = lambda: open(p, "r", encoding="utf-8", errors="replace", newline="")
            fmt = "csv"
        with opener() as f:
            first = f.readline()
            delim = detect_delimiter(first)
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delim)
            rows = []
            for r in reader:
                if isinstance(r, dict) and any(v not in (None, "") for v in r.values()):
                    r["_sig_e_source_file_format"] = fmt
                    rows.append(r)
                if len(rows) > max_tail:
                    rows = rows[-max_tail:]
            return rows
    except Exception:
        return []

def standardize_ohlc'''

READ_ROWS_REPLACEMENT = '''def read_rows(p, max_tail=3000):
    if not p or not Path(p).exists():
        return []
    path = Path(p)
    try:
        if str(path).lower().endswith(".gz"):
            import gzip
            opener = lambda: gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
        else:
            opener = lambda: open(path, "r", encoding="utf-8", errors="replace", newline="")
        with opener() as f:
            first = f.readline()
            d = delim(first)
            f.seek(0)
            rdr = csv.DictReader(f, delimiter=d)
            rows = []
            for r in rdr:
                if isinstance(r, dict) and any(v not in (None, "") for v in r.values()):
                    rows.append(r)
                if len(rows) > max_tail:
                    rows = rows[-max_tail:]
            return rows
    except Exception:
        return []

def ohlc'''

TARGETS = [
    {
        "name": "detector1",
        "path": Path("scripts/build_sig_e_shadow_detector1_usdjpy_london_long.py"),
        "regex": r"def read_csv_rows\(path,\s*max_tail=\d+\):.*?\ndef standardize_ohlc",
        "replacement": READ_CSV_ROWS_REPLACEMENT,
    },
    {
        "name": "detector2",
        "path": Path("scripts/build_sig_e_shadow_detector2_usdjpy_asia_short.py"),
        "regex": r"def read_rows\(p,\s*max_tail=\d+\):.*?\ndef ohlc",
        "replacement": READ_ROWS_REPLACEMENT,
    },
]

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def ensure_gzip_import(txt):
    if re.search(r"^\s*import gzip\s*$", txt, flags=re.M):
        return txt
    if re.search(r"^\s*import csv\s*$", txt, flags=re.M):
        return re.sub(r"(^\s*import csv\s*$)", r"\1\nimport gzip", txt, count=1, flags=re.M)
    return "import gzip\n" + txt

def patch_one(t):
    p = t["path"]
    item = {"name": t["name"], "path": str(p), "exists": p.exists(), "patched": False, "reason": None}
    if not p.exists():
        item["reason"] = "TARGET_FILE_MISSING"
        return item
    txt = ensure_gzip_import(p.read_text(encoding="utf-8"))
    new, n = re.subn(t["regex"], t["replacement"], txt, count=1, flags=re.S)
    if n == 0:
        item["reason"] = "FUNCTION_PATTERN_NOT_FOUND"
        p.write_text(txt, encoding="utf-8")
        return item
    p.write_text(new, encoding="utf-8")
    item["patched"] = True
    item["reason"] = "PATCHED_OK"
    return item

def main():
    res = [patch_one(t) for t in TARGETS]
    status = "PASS" if all(x["patched"] for x in res) else "FAIL_OR_PARTIAL"
    out = {
        "program": "SIG-E-SHADOW-LIVE-OHLC-GZIP-HOTFIX",
        "created_utc": now(),
        "patch_status": status,
        "targets": res,
        "authority": {"signal_authorized": False, "trade_proposal_authorized": False, "entry_stop_target_authorized": False, "risk_sizing_authorized": False, "broker_execution_authorized": False, "auto_execution_authorized": False},
        "boundary": ["LIVE_OHLC_READER_HOTFIX_ONLY", "SHADOW_RESEARCH_ONLY", "NOT_SIGNAL", "NO_TRADE_PROPOSAL", "NO_ENTRY_STOP_TARGET", "NO_RISK_OR_POSITION_SIZING", "NO_BROKER_EXECUTION", "NO_AUTO_EXECUTION", "NO_MEMORY_PROMOTION", "NO_RULE_REWRITE"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("SIG_E_SHADOW_LIVE_OHLC_GZIP_HOTFIX_" + status)
    for x in res:
        print(x["name"], x["reason"])
    if status != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
