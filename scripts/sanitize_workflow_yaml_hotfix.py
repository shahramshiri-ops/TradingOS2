
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

PROGRAM = "TRADINGOS-WORKFLOW-YAML-SANITIZE-HOTFIX-PY38-FIX"

WORKFLOW = Path(".github/workflows/sig_live_m5_refresh_resample_brain.yml")
OUT = Path("outputs/_workflow_yaml_sanitize_hotfix/workflow_yaml_sanitize_hotfix_result.json")

def now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def write_text_lf(path, text):
    # Python 3.8 compatible replacement for Path.write_text(..., newline="\n")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def count_bad_chars(text):
    bad = []
    for idx, ch in enumerate(text):
        o = ord(ch)
        if (o < 32 and ch not in "\n\r\t") or (0x80 <= o <= 0x9F):
            bad.append({"index": idx, "ord_hex": hex(o), "repr": repr(ch)})
    return bad

def sanitize_text(text):
    replacements = {
        "Ã¢â‚¬â€\x9d": " - ",
        "Ã¢â‚¬â€œ": " - ",
        "Ã¢â‚¬â€”": " - ",
        "â€”": " - ",
        "â€“": " - ",
        "—": " - ",
        "–": " - ",
        "\ufeff": "",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)

    cleaned = []
    removed = []
    for idx, ch in enumerate(text):
        o = ord(ch)
        if (o < 32 and ch not in "\n\r\t") or (0x80 <= o <= 0x9F):
            removed.append({"index": idx, "ord_hex": hex(o), "repr": repr(ch)})
            continue
        cleaned.append(ch)
    text = "".join(cleaned)

    text = text.replace("Ã¢â‚¬", "-")
    text = text.replace("â‚¬", "")
    text = text.replace("â€", "-")
    text = text.replace("Ã", "")
    return text, removed

def structural_checks(text):
    errors = []
    if not text.startswith("name: SIG Live M5 Refresh Resample Brain"):
        errors.append("workflow_name_missing_or_changed")

    for marker in [
        "\non:",
        "\njobs:",
        "Build SIG-E shadow detector portfolio and persistence chain",
        "build_sig_e_shadow_detector3_eurusd_pdlow_trap_long.py",
        "build_sig_e_shadow_portfolio1.py",
        "Trigger static Pages deploy after live refresh",
    ]:
        if marker not in text:
            errors.append("missing_marker:" + marker.strip())

    bad_after = count_bad_chars(text)
    if bad_after:
        errors.append("yaml_forbidden_control_chars_remaining")
    return errors, bad_after

def optional_pyyaml_parse(text):
    try:
        import yaml
    except Exception:
        return {"attempted": False, "status": "SKIPPED_PYYAML_NOT_INSTALLED"}
    try:
        yaml.safe_load(text)
        return {"attempted": True, "status": "PASS"}
    except Exception as e:
        return {"attempted": True, "status": "FAIL", "error": type(e).__name__ + ": " + str(e)}

def main():
    result = {
        "program": PROGRAM,
        "created_utc": now(),
        "workflow_path": str(WORKFLOW),
        "workflow_exists": WORKFLOW.exists(),
        "status": "UNKNOWN",
        "python_compatibility_fix": "Path.write_text newline arg removed; open(..., newline='\\n') used instead",
        "bad_chars_before_count": None,
        "bad_chars_after_count": None,
        "removed_chars_count": None,
        "structural_errors": [],
        "pyyaml_parse": None,
    }

    if not WORKFLOW.exists():
        result["status"] = "FAIL_WORKFLOW_NOT_FOUND"
        write_json(OUT, result)
        print("WORKFLOW_YAML_SANITIZE_HOTFIX_FAIL_WORKFLOW_NOT_FOUND")
        raise SystemExit(1)

    original = WORKFLOW.read_text(encoding="utf-8-sig", errors="replace")
    before_bad = count_bad_chars(original)
    result["bad_chars_before_count"] = len(before_bad)
    result["bad_chars_before_sample"] = before_bad[:20]

    sanitized, removed = sanitize_text(original)

    backup = WORKFLOW.with_suffix(WORKFLOW.suffix + ".bak_yaml_sanitize_hotfix_py38")
    shutil.copyfile(WORKFLOW, backup)
    result["backup"] = str(backup)

    write_text_lf(WORKFLOW, sanitized)

    errors, after_bad = structural_checks(sanitized)
    result["bad_chars_after_count"] = len(after_bad)
    result["bad_chars_after_sample"] = after_bad[:20]
    result["removed_chars_count"] = len(removed)
    result["removed_chars_sample"] = removed[:20]
    result["structural_errors"] = errors
    result["pyyaml_parse"] = optional_pyyaml_parse(sanitized)

    if not errors and result["pyyaml_parse"].get("status") in ("PASS", "SKIPPED_PYYAML_NOT_INSTALLED"):
        result["status"] = "PASS"
    elif not errors and result["pyyaml_parse"].get("status") == "FAIL":
        result["status"] = "FAIL_YAML_PARSE"
    else:
        result["status"] = "FAIL_STRUCTURAL"

    write_json(OUT, result)

    print("WORKFLOW_YAML_SANITIZE_HOTFIX_" + result["status"])
    print("bad_chars_before:", result["bad_chars_before_count"])
    print("bad_chars_after:", result["bad_chars_after_count"])
    print("removed_chars:", result["removed_chars_count"])
    print("pyyaml:", result["pyyaml_parse"])
    print("result:", OUT)

    if result["status"] != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
