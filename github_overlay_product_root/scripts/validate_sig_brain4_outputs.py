#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

FORBIDDEN_ACTION_FIELDS = [
    "signal_authorized", "broker_execution_authorized", "action_surface_authorized", "trade_instruction_authorized"
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", default="runtime/sig_brain/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--proof-out", default="proofs/sig_brain4_validation_result.json")
    args = ap.parse_args()

    path = Path(args.payload)
    data = json.loads(path.read_text(encoding="utf-8"))
    failures = []

    for f in FORBIDDEN_ACTION_FIELDS:
        if data.get(f) is not False:
            failures.append(f"{f} must be false")

    if not isinstance(data.get("cards"), list):
        failures.append("cards must be a list")
    else:
        for i, card in enumerate(data["cards"]):
            if card.get("signal_status") != "NOT_SIGNAL":
                failures.append(f"card {i} signal_status must be NOT_SIGNAL")
            if card.get("action_status") != "NO_BUY_SELL_HOLD_NO_ENTRY_STOP_TARGET":
                failures.append(f"card {i} action_status boundary missing")
            if not card.get("mandatory_caveat"):
                failures.append(f"card {i} mandatory_caveat missing")

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "payload": str(path),
        "failures": failures,
        "signal_authorized": data.get("signal_authorized"),
        "action_surface_authorized": data.get("action_surface_authorized"),
        "card_count": len(data.get("cards", [])) if isinstance(data.get("cards"), list) else None
    }
    out = Path(args.proof_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
