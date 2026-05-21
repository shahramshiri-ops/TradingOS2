#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate SIG-E-REGIME1 market state payload.

Boundary validation is intentionally strict: REGIME1 is market-state context only.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List
from collections import Counter
import json

ROOT = Path.cwd()
TAXONOMY_PATH = ROOT / "config" / "sig_e" / "regime_taxonomy_v1_0.json"
SCHEMA_PATH = ROOT / "schemas" / "sig_e" / "market_state_schema_v1_0.json"
PAYLOADS = [
    ROOT / "runtime" / "sig_e" / "market_state_current.json",
    ROOT / "runtime" / "sig_e" / "sig_e_regime1_market_state_current.json",
    ROOT / "panel" / "brain4" / "sig_e_market_state_current.json",
]
OUT = ROOT / "outputs" / "_sig_e_regime1" / "sig_e_regime1_validation_result.json"

FORBIDDEN_KEY_FRAGMENTS = [
    "entry", "stop", "target", "take_profit", "position_size", "risk_percent", "order", "broker", "execution", "trade_instruction"
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def flatten_keys(obj: Any, prefix: str = "") -> List[str]:
    keys: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            keys.append(p)
            keys.extend(flatten_keys(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            keys.extend(flatten_keys(v, f"{prefix}[{i}]"))
    return keys


def validate_boundary(payload: Dict[str, Any], problems: List[str]) -> None:
    b = payload.get("boundary", {})
    false_fields = [
        "signal_authorized", "trade_proposal_authorized", "entry_stop_target_authorized",
        "risk_or_position_sizing_authorized", "broker_execution_authorized", "auto_execution_authorized"
    ]
    for f in false_fields:
        if b.get(f) is not False:
            problems.append(f"boundary.{f}_must_be_false")
    if b.get("manual_review_required_for_future_trade_plan") is not True:
        problems.append("boundary.manual_review_required_for_future_trade_plan_must_be_true")
    summary = payload.get("summary", {})
    if summary.get("signal_authorized") is not False:
        problems.append("summary.signal_authorized_must_be_false")
    if summary.get("trade_plan_authorized") is not False:
        problems.append("summary.trade_plan_authorized_must_be_false")


def validate_one(path: Path, taxonomy: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    problems: List[str] = []
    if not path.exists():
        return {"path": path.as_posix(), "status": "FAIL", "problems": ["missing_payload"]}
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {"path": path.as_posix(), "status": "FAIL", "problems": ["payload_not_object"]}

    for field in schema.get("required_top_level_fields", []):
        if field not in payload:
            problems.append(f"missing_top_level_field:{field}")
    if payload.get("status_version") != "SIG_E_REGIME1_MARKET_STATE_v1_0":
        problems.append("unexpected_status_version")
    validate_boundary(payload, problems)

    allowed = {
        "trend_state": set(taxonomy.get("trend_state", [])),
        "range_state": set(taxonomy.get("range_state", [])),
        "volatility_state": set(taxonomy.get("volatility_state", [])),
        "htf_alignment": set(taxonomy.get("htf_alignment", [])),
        "tradeability_context": set(taxonomy.get("tradeability_context", [])),
        "setup_relevance_hints": set(taxonomy.get("setup_relevance_hints", [])),
        "liquidity_tags": set(taxonomy.get("liquidity_tags", [])),
    }

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        problems.append("surfaces_not_list")
        surfaces = []
    for idx, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            problems.append(f"surface_{idx}_not_object")
            continue
        for field in schema.get("required_surface_fields", []):
            if field not in surface:
                problems.append(f"surface_{idx}_missing_field:{field}")
        for field, allowed_values in [
            ("trend_state", allowed["trend_state"]),
            ("range_state", allowed["range_state"]),
            ("volatility_state", allowed["volatility_state"]),
            ("htf_alignment", allowed["htf_alignment"]),
            ("tradeability_context", allowed["tradeability_context"]),
        ]:
            if allowed_values and surface.get(field) not in allowed_values:
                problems.append(f"surface_{idx}_{field}_not_allowed:{surface.get(field)}")
        liq = (surface.get("liquidity_context") or {}).get("tags", [])
        if not isinstance(liq, list):
            problems.append(f"surface_{idx}_liquidity_tags_not_list")
        else:
            for tag in liq:
                if allowed["liquidity_tags"] and tag not in allowed["liquidity_tags"]:
                    problems.append(f"surface_{idx}_liquidity_tag_not_allowed:{tag}")
        hints = surface.get("setup_relevance_hints", [])
        if not isinstance(hints, list):
            problems.append(f"surface_{idx}_setup_hints_not_list")
        else:
            for h in hints:
                if allowed["setup_relevance_hints"] and h not in allowed["setup_relevance_hints"]:
                    problems.append(f"surface_{idx}_setup_hint_not_allowed:{h}")
        sb = surface.get("boundary", {})
        if sb.get("signal_authorized") is not False or sb.get("entry_stop_target_authorized") is not False or sb.get("broker_execution_authorized") is not False:
            problems.append(f"surface_{idx}_boundary_authority_violation")

    # Guard against accidental trade-plan fields in surface-level payloads. We allow the top-level boundary
    # field named entry_stop_target_authorized, but do not allow actual trade-plan key fragments inside surfaces.
    for idx, surface in enumerate(surfaces):
        for key in flatten_keys(surface):
            key_lower = key.lower()
            for frag in FORBIDDEN_KEY_FRAGMENTS:
                if frag in key_lower and "authorized" not in key_lower and "boundary" not in key_lower:
                    problems.append(f"surface_{idx}_forbidden_trade_key:{key}")
                    break

    return {
        "path": path.as_posix(),
        "status": "PASS" if not problems else "FAIL",
        "surface_count": len(surfaces),
        "problems": problems[:200],
    }


def main() -> None:
    taxonomy = read_json(TAXONOMY_PATH) if TAXONOMY_PATH.exists() else {}
    schema = read_json(SCHEMA_PATH) if SCHEMA_PATH.exists() else {}
    results = [validate_one(p, taxonomy, schema) for p in PAYLOADS]
    status = "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL"
    surface_counts = Counter(str(r.get("surface_count", 0)) for r in results)
    result = {
        "status": status,
        "created_utc": now_utc(),
        "program": "SIG-E-REGIME1",
        "payload_results": results,
        "surface_count_consistency": dict(surface_counts),
        "boundary": {
            "signal_authorized": False,
            "trade_proposal_authorized": False,
            "entry_stop_target_authorized": False,
            "broker_execution_authorized": False,
            "auto_execution_authorized": False,
        },
    }
    write_json(OUT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit("SIG-E-REGIME1 validation failed")


if __name__ == "__main__":
    main()
