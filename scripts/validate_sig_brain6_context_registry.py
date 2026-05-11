#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, csv
from pathlib import Path

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field-registry", default="sig_brain/context_field_registry_v1_0.json")
    ap.add_argument("--memory-registry", default="sig_brain/brain_memory_registry_v1_0.json")
    ap.add_argument("--builder-support", default="sig_brain/context_builder_support_registry_v1_0.json")
    ap.add_argument("--proof-out", default="proofs/sig_brain6_context_registry_validation_result.json")
    args = ap.parse_args()

    field_registry = load_json(Path(args.field_registry))
    memory_registry = load_json(Path(args.memory_registry))
    support_registry = load_json(Path(args.builder_support))

    known_fields = {f["field_id"]: f for f in field_registry.get("fields", [])}
    supported = set()
    for b in support_registry.get("builders", []):
        if b.get("status") == "ACTIVE_CURRENT":
            supported.update(b.get("supported_fields", []))

    failures, warnings, memory_rows = [], [], []

    # Field registry uniqueness
    ids = [f.get("field_id") for f in field_registry.get("fields", [])]
    if len(ids) != len(set(ids)):
        failures.append("duplicate field_id in context field registry")

    for mem in memory_registry.get("memories", []):
        mem_id = mem.get("memory_id")
        req = mem.get("required_context_fields", []) or []
        active = bool(mem.get("active_in_runtime", False))

        unknown = [f for f in req if f not in known_fields]
        unsupported = [f for f in req if f not in supported]
        if unknown:
            failures.append(f"{mem_id} has required fields not in registry: {unknown}")
        if active and unsupported:
            failures.append(f"{mem_id} is active but builder does not support required fields: {unsupported}")
        if not active and req:
            warnings.append(f"{mem_id} inactive but declares fields; OK if parked/weakened")

        memory_rows.append({
            "memory_id": mem_id,
            "active_in_runtime": active,
            "required_field_count": len(req),
            "unknown_required_fields": "|".join(unknown),
            "unsupported_required_fields": "|".join(unsupported),
            "coverage_status": "PASS" if not unknown and (not active or not unsupported) else "FAIL"
        })

    proof = {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "field_count": len(known_fields),
        "memory_count": len(memory_registry.get("memories", [])),
        "active_builder_supported_field_count": len(supported),
        "memory_rows": memory_rows,
        "signal_authorized": False,
        "action_surface_authorized": False
    }

    out = Path(args.proof_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_out = out.with_suffix(".csv")
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        if memory_rows:
            w = csv.DictWriter(f, fieldnames=list(memory_rows[0].keys()))
            w.writeheader()
            w.writerows(memory_rows)

    print(json.dumps(proof, indent=2, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
