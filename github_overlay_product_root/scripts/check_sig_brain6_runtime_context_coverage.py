#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def surface_fields(context, instrument, timeframe):
    for row in context.get("surfaces", []):
        if str(row.get("instrument","")).upper() == instrument.upper() and str(row.get("timeframe","")).upper() == timeframe.upper():
            return set(row.keys()), row
    return set(), None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory-registry", default="data/sig_brain/brain_memory_registry_v1_0.json")
    ap.add_argument("--context", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--out", default="proofs/sig_brain6_runtime_context_coverage_result.json")
    args = ap.parse_args()

    memreg = load_json(Path(args.memory_registry))
    ctx_path = Path(args.context)
    failures = []
    rows = []
    if not ctx_path.exists():
        failures.append(f"context file missing: {ctx_path}")
        context = {"surfaces": []}
    else:
        context = load_json(ctx_path)

    for mem in memreg.get("memories", []):
        if not mem.get("active_in_runtime", False):
            continue
        req = set(mem.get("required_context_fields", []) or [])
        fields, row = surface_fields(context, mem.get("instrument",""), mem.get("timeframe",""))
        missing = sorted(req - fields)
        status = "PASS" if not missing else "FAIL"
        if missing:
            failures.append(f"{mem.get('memory_id')} missing runtime fields: {missing}")
        rows.append({
            "memory_id": mem.get("memory_id"),
            "instrument": mem.get("instrument"),
            "timeframe": mem.get("timeframe"),
            "required_field_count": len(req),
            "available_field_count": len(fields),
            "missing_fields": missing,
            "coverage_status": status
        })

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "rows": rows,
        "signal_authorized": False,
        "action_surface_authorized": False
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
