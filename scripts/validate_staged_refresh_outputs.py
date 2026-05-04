#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

REQUIRED = [
    "reports/staged_refresh_plan.json",
    "reports/staged_provider_fetch_report.json",
    "reports/staged_cache_update_report.json",
    "reports/staged_row_level_ledger_refresh_report.json",
    "panel/panel_payload_after_staged_credentialed_refresh.json",
    "proofs/staged_secret_redaction_proof.json",
    "proofs/staged_no_action_surface_proof.json",
    "proofs/staged_refresh_boundary_proof.json",
    "proofs/staged_refresh_local_validation_result.json",
]

def read(path):
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    root = root.resolve()
    missing = [p for p in REQUIRED if not (root/p).exists()]
    validation = read(root/"proofs/staged_refresh_local_validation_result.json") if not missing else {}
    result = {
        "program": "PRV1C-01",
        "artifact": "staged_refresh_validation_review",
        "validation_passed": bool(validation.get("validation_passed")) if not missing else False,
        "coverage_status": validation.get("coverage_status") if validation else "missing_files",
        "missing_files": missing,
        "selected_surface_count": validation.get("selected_surface_count"),
        "successful_surface_count": validation.get("successful_surface_count"),
        "failed_surface_count": validation.get("failed_surface_count"),
        "failed_surfaces": validation.get("failed_surfaces"),
        "secret_redaction_passed": validation.get("secret_redaction_passed"),
        "no_action_surface_passed": validation.get("no_action_surface_passed"),
        "scope_ok": validation.get("scope_ok"),
        "boundary_status": validation.get("boundary_status", "failed_or_requires_review"),
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["validation_passed"] else 2)
if __name__ == "__main__": main()
