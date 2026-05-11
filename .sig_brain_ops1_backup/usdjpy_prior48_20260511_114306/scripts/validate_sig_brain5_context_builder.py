#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
REQUIRED = {
    "EURUSD": ["session_bucket", "upside_sweep_flag", "sweep_then_reject_back_inside_up_flag", "h1_dir", "h4_dir", "conflict_severity"],
    "USDJPY": ["session_bucket", "h4_h1_up_context", "h4_h1_down_context", "m15_range_ratio_12", "m15_dir"],
}
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--proof-out", default="proofs/sig_brain5_context_validation_result.json")
    args = ap.parse_args()
    ctx = load(args.context)
    failures = []
    gb = ctx.get("global_boundary", {})
    if gb.get("signal_authorized") is not False: failures.append("global signal_authorized must be false")
    if gb.get("action_surface_authorized") is not False: failures.append("global action_surface_authorized must be false")
    rows = {str(s.get("instrument","")).upper(): s for s in ctx.get("surfaces", [])}
    for inst, fields in REQUIRED.items():
        row = rows.get(inst)
        if not row:
            failures.append(f"missing surface {inst}")
            continue
        for f in fields:
            if f not in row:
                failures.append(f"missing {inst}.{f}")
    brain4_result = None
    try:
        proc = subprocess.run([sys.executable, "scripts/build_sig_brain4_runtime_payload.py"], check=True, capture_output=True, text=True)
        brain4_result = proc.stdout.strip()
        subprocess.run([sys.executable, "scripts/validate_sig_brain4_outputs.py"], check=True, capture_output=True, text=True)
    except Exception as e:
        failures.append(f"brain4 end-to-end failed: {e}")
    proof = {"validation_status":"PASS" if not failures else "FAIL","context":args.context,"failures":failures,"derived_surface_count":len(ctx.get("surfaces", [])),"signal_authorized":False,"action_surface_authorized":False,"brain4_result":brain4_result}
    out = Path(args.proof_out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0 if not failures else 1
if __name__ == "__main__":
    raise SystemExit(main())
