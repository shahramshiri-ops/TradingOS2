#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("package_root", nargs="?", default=".")
    args=ap.parse_args(); root=Path(args.package_root).resolve()
    required=[
      "reports/provider_read_only_fetch_report.json",
      "reports/cache_update_report.json",
      "reports/row_level_ledger_refresh_report.json",
      "panel/panel_payload_after_credentialed_refresh.json",
      "logs/last_run_status_after_credentialed_refresh.json",
      "logs/runtime_heartbeat_after_credentialed_refresh.json",
      "proofs/secret_redaction_proof.json",
      "proofs/no_action_surface_proof.json",
      "proofs/credentialed_refresh_boundary_proof.json",
    ]
    missing=[f for f in required if not (root/f).exists()]
    secret=load(root/"proofs/secret_redaction_proof.json") if (root/"proofs/secret_redaction_proof.json").exists() else {}
    action=load(root/"proofs/no_action_surface_proof.json") if (root/"proofs/no_action_surface_proof.json").exists() else {}
    bound=load(root/"proofs/credentialed_refresh_boundary_proof.json") if (root/"proofs/credentialed_refresh_boundary_proof.json").exists() else {}
    ok=not missing and secret.get("api_key_value_written") is False and action.get("action_surface_absent") is True and bound.get("status") == "passed_with_caveats"
    result={
      "program":"PRV1B-01",
      "artifact":"credentialed_refresh_local_validation_result",
      "validation_passed": ok,
      "missing_files": missing,
      "secret_redaction_passed": secret.get("api_key_value_written") is False,
      "no_action_surface_passed": action.get("action_surface_absent") is True,
      "boundary_status": bound.get("status"),
    }
    out=root/"proofs/credentialed_refresh_local_validation_result.json"
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 2
if __name__ == "__main__": raise SystemExit(main())
