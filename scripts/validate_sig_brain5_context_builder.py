#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def load(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def surface_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return str(row.get("instrument", "")).upper(), str(row.get("timeframe", "")).upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--memory-registry", default="sig_brain/brain_memory_registry_v1_0.json")
    ap.add_argument("--proof-out", default="proofs/sig_brain5_context_validation_result.json")
    args = ap.parse_args()

    ctx = load(args.context)
    memreg = load(args.memory_registry)
    failures: List[str] = []
    warnings: List[str] = []

    gb = ctx.get("global_boundary", {})
    if gb.get("signal_authorized") is not False:
        failures.append("global signal_authorized must be false")
    if gb.get("action_surface_authorized") is not False:
        failures.append("global action_surface_authorized must be false")

    surfaces = {surface_key(s): s for s in ctx.get("surfaces", [])}
    coverage_rows = []
    for mem in memreg.get("memories", []):
        if not mem.get("active_in_runtime", False):
            continue
        key = (str(mem.get("instrument", "")).upper(), str(mem.get("timeframe", "")).upper())
        row = surfaces.get(key)
        req = mem.get("required_context_fields", []) or []
        missing = [] if row else list(req)
        if row:
            missing = [f for f in req if f not in row]
        if not row:
            failures.append(f"missing context surface for active memory {mem.get('memory_id')}: {key}")
        elif missing:
            failures.append(f"active memory {mem.get('memory_id')} missing fields: {missing}")
        coverage_rows.append({
            "memory_id": mem.get("memory_id"),
            "instrument": key[0],
            "timeframe": key[1],
            "required_field_count": len(req),
            "missing_fields": missing,
            "coverage_status": "PASS" if row and not missing else "FAIL",
        })

    # Preserve the end-to-end Brain4 proof boundary.
    brain4_result = None
    try:
        proc = subprocess.run([sys.executable, "scripts/build_sig_brain4_runtime_payload.py"], check=True, capture_output=True, text=True)
        brain4_result = proc.stdout.strip()
        subprocess.run([sys.executable, "scripts/validate_sig_brain4_outputs.py"], check=True, capture_output=True, text=True)
    except Exception as e:
        failures.append(f"brain4 end-to-end failed: {e}")

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "context": args.context,
        "failures": failures,
        "warnings": warnings,
        "derived_surface_count": len(ctx.get("surfaces", [])),
        "active_memory_coverage_rows": coverage_rows,
        "signal_authorized": False,
        "action_surface_authorized": False,
        "brain4_result": brain4_result,
    }
    out = Path(args.proof_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
