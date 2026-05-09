#!/usr/bin/env python3
"""
SIG-BRAIN4 runtime brain-memory matcher.

Display-only. Does not fetch data, does not call providers, does not call brokers,
and does not produce buy/sell/hold, entries, stops, targets, PnL, probabilities,
profitability claims, or tradability claims.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

AUTHORITY = "SIG_BRAIN4_RUNTIME_MEMORY_MATCHER|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_PROFITABILITY_TRADABILITY_CLAIM|NO_BROKER_EXECUTION"
BLOCKED_TERMS = [
    "BUY", "SELL", "HOLD", "ENTRY", "STOP", "TARGET", "TAKE_PROFIT", "STOP_LOSS",
    "PNL", "WIN_RATE", "EXPECTANCY", "SHARPE", "PROFITABLE", "TRADABLE",
    "EDGE_CONFIRMED", "CLEAN_VALIDATED", "BROKER", "ORDER", "EXECUTE",
    "POSITION_SIZE", "LEVERAGE"
]

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def normalize_bool(x: Any) -> Any:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
    return x

def get_surfaces(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = ctx.get("surfaces")
    if rows is None:
        rows = ctx.get("instruments")
    return rows if isinstance(rows, list) else []

def find_context_row(ctx: Dict[str, Any], instrument: str, timeframe: str) -> Dict[str, Any] | None:
    inst = instrument.upper()
    tf = timeframe.upper()
    for row in get_surfaces(ctx):
        if str(row.get("instrument", "")).upper() == inst and str(row.get("timeframe", "")).upper() == tf:
            return row
    return None

def eval_condition(row: Dict[str, Any], cond: Dict[str, Any]) -> Tuple[bool, str, bool]:
    """
    Returns: (passed, reason, missing)
    """
    op = cond.get("op")
    label = cond.get("label")
    if op == "not_pair_eq":
        lf, rf, val = cond.get("left_field"), cond.get("right_field"), cond.get("value")
        if lf not in row or rf not in row:
            return False, f"missing {lf}/{rf}", True
        passed = not (str(row.get(lf)).upper() == str(val).upper() and str(row.get(rf)).upper() == str(val).upper())
        return passed, label or f"NOT({lf} == {val} AND {rf} == {val})", False

    field = cond.get("field")
    if field not in row:
        return False, f"missing {field}", True
    raw = normalize_bool(row.get(field))
    val = cond.get("value")

    if op == "eq":
        passed = str(raw).upper() == str(val).upper()
    elif op == "not_eq":
        passed = str(raw).upper() != str(val).upper()
    elif op == "bool_eq":
        passed = bool(raw) is bool(val)
    elif op == "in":
        passed = str(raw).upper() in [str(v).upper() for v in val]
    elif op == "between":
        try:
            x = float(raw)
            lo, hi = float(val[0]), float(val[1])
            passed = lo <= x <= hi
        except Exception:
            return False, f"{field} not numeric", True
    else:
        return False, f"unknown op {op}", True

    return passed, f"{field} {op} {val} observed={raw}", False

def evaluate_memory(memory: Dict[str, Any], row: Dict[str, Any] | None) -> Dict[str, Any]:
    if not memory.get("active_in_runtime", False):
        return {
            "match_state": "INACTIVE_MEMORY_PARKED_OR_WEAKENED",
            "is_active_match": False,
            "passed_conditions": [],
            "failed_conditions": [],
            "missing_inputs": [],
            "reason": "Memory is not active in runtime registry."
        }
    if row is None:
        return {
            "match_state": "INPUT_ROW_MISSING",
            "is_active_match": False,
            "passed_conditions": [],
            "failed_conditions": [],
            "missing_inputs": memory.get("required_context_fields", []),
            "reason": "No matching runtime context row was available."
        }

    passed, failed, missing = [], [], []
    for cond in memory.get("matching_rule", {}).get("required_all", []):
        ok, reason, is_missing = eval_condition(row, cond)
        if ok:
            passed.append(reason)
        elif is_missing:
            missing.append(reason)
        else:
            failed.append(reason)

    if missing:
        state = "MEMORY_INPUT_INSUFFICIENT"
        active = False
        reason = "Required context fields are missing; memory cannot be evaluated."
    elif failed:
        state = "MEMORY_NOT_ACTIVE"
        active = False
        reason = "Context row is present but conditions are not matched."
    else:
        if "NO_TRADE" in str(memory.get("activation_status", "")).upper() or "no_trade" in str(memory.get("memory_class","")).lower():
            state = "NO_TRADE_WATCH_ACTIVE"
        else:
            state = "CAVEATED_WATCH_ACTIVE"
        active = True
        reason = "All required memory conditions are matched."

    return {
        "match_state": state,
        "is_active_match": active,
        "passed_conditions": passed,
        "failed_conditions": failed,
        "missing_inputs": missing,
        "reason": reason
    }

def make_card(memory: Dict[str, Any], row: Dict[str, Any] | None, ev: Dict[str, Any], rank: int) -> Dict[str, Any]:
    active = ev["is_active_match"]
    state = ev["match_state"]
    if active:
        headline = memory.get("plain_language_label_fa", "حافظه فعال")
    elif state == "MEMORY_INPUT_INSUFFICIENT":
        headline = "دادهٔ لازم برای ارزیابی این حافظه کامل نیست"
    elif state == "INACTIVE_MEMORY_PARKED_OR_WEAKENED":
        headline = memory.get("plain_language_label_fa", "حافظه غیرفعال/ضعیف‌شده")
    else:
        headline = "حافظه فعلاً فعال نیست"

    return {
        "card_version": "sig_brain4_memory_card_v1_0",
        "memory_id": memory.get("memory_id"),
        "instrument": memory.get("instrument"),
        "timeframe": memory.get("timeframe"),
        "memory_class": memory.get("memory_class"),
        "brain_state": state,
        "is_active_match": active,
        "status_badge": "ACTIVE WATCH / NOT SIGNAL" if active else "NOT ACTIVE / DISPLAY ONLY",
        "score_not_probability": memory.get("score_not_probability"),
        "band": memory.get("band"),
        "headline_fa": headline,
        "plain_language_summary_fa": memory.get("plain_language_summary_fa"),
        "primary_reason": ev["reason"],
        "matched_conditions": ev["passed_conditions"],
        "failed_conditions": ev["failed_conditions"],
        "missing_inputs": ev["missing_inputs"],
        "evidence_summary": memory.get("evidence_summary", {}),
        "latest_context": row or {},
        "signal_status": "NOT_SIGNAL",
        "direction_authority": "NONE_AUTHORIZED",
        "action_status": "NO_BUY_SELL_HOLD_NO_ENTRY_STOP_TARGET",
        "display_authority": "DISPLAY_ONLY_BRAIN_CONTEXT_NOT_TRADING_SIGNAL",
        "allowed_user_interpretation": "Historical brain-memory context/watch only.",
        "forbidden_user_interpretation": "Do not read this as buy/sell/hold, trade setup, entry/stop/target, probability, profitability, tradability, or broker execution authorization.",
        "mandatory_caveat": memory.get("runtime_display_caveat_required"),
        "forbidden_use": memory.get("forbidden_use", []),
        "visible_action_text_fa": "هیچ دستور معامله‌ای مجاز نیست",
        "visible_action_text_en": "No trading instruction is authorized",
        "mobile_display_allowed": True,
        "sort_rank": rank
    }

def build_payload(context_path: Path, registry_path: Path) -> Dict[str, Any]:
    ctx = load_json(context_path)
    registry = load_json(registry_path)
    cards = []
    for i, mem in enumerate(registry.get("memories", []), start=1):
        row = find_context_row(ctx, mem.get("instrument", ""), mem.get("timeframe", ""))
        ev = evaluate_memory(mem, row)
        cards.append(make_card(mem, row, ev, i))

    cards.sort(key=lambda c: (0 if c["is_active_match"] else 1, c["sort_rank"]))

    return {
        "payload_version": "SIG_BRAIN4_RUNTIME_PAYLOAD_v1_0",
        "created_utc": utc_now(),
        "adapter_version": "SIG_BRAIN4_RUNTIME_MATCHER_v1_0",
        "authority": AUTHORITY,
        "deployment_status": "DISPLAY_ONLY_RUNTIME_BRAIN_MEMORY_MATCHER_NOT_SIGNAL_NOT_BROKER",
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "trade_instruction_authorized": False,
        "source_context_summary": {
            "input_file": str(context_path),
            "context_version": ctx.get("context_version"),
            "context_created_utc": ctx.get("created_utc"),
            "source_authority": ctx.get("source_authority")
        },
        "registry_summary": {
            "registry_version": registry.get("registry_version"),
            "memory_count": len(registry.get("memories", [])),
            "active_runtime_memory_count": sum(1 for m in registry.get("memories", []) if m.get("active_in_runtime")),
            "active_match_count": sum(1 for c in cards if c["is_active_match"])
        },
        "global_boundary": {
            "plain_language_fa": "این خروجی فقط وضعیت حافظه‌های تاریخی مغز را با context زنده/خواندنی تطبیق می‌دهد. سیگنال، ورود/خروج، سودآوری، بروکر یا اجرای معامله نیست.",
            "plain_language_en": "This output matches read-only runtime context to historical brain memories only. It is not a signal, entry/exit advice, profitability claim, broker surface, or execution.",
            "no_action_surface": True
        },
        "cards": cards,
        "blocked_terms": BLOCKED_TERMS
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", default="inputs/sig_brain4_live_context_latest.json")
    ap.add_argument("--registry", default="data/sig_brain/brain_memory_registry_v1_0.json")
    ap.add_argument("--out", default="runtime/sig_brain/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--panel-out", default="panel/brain4/sig_brain4_runtime_payload_current.json")
    args = ap.parse_args()

    context_path = Path(args.context)
    registry_path = Path(args.registry)
    out_path = Path(args.out)
    panel_out = Path(args.panel_out)

    payload = build_payload(context_path, registry_path)
    write_json(out_path, payload)
    write_json(panel_out, payload)
    print(json.dumps({
        "status": "sig_brain4_runtime_payload_created",
        "out": str(out_path),
        "panel_out": str(panel_out),
        "active_match_count": payload["registry_summary"]["active_match_count"],
        "signal_authorized": payload["signal_authorized"],
        "action_surface_authorized": payload["action_surface_authorized"]
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
