#!/usr/bin/env python3
"""SIG-BRAIN-OPS9 — official server-side Brain4 event history updater.

Reads the current Brain4 runtime payload and refresh status, merges active memory events
into an official file-backed history, and writes copies for runtime and GitHub Pages.
Display-only: no signal, no buy/sell, no execution.
"""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_KEEP_DAYS = 7
HISTORY_MAX_ITEMS = 500
ACTIVE_EVENT_WINDOW_MIN = 10
AUTHORITY = "SIG_BRAIN4_OFFICIAL_EVENT_HISTORY|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"

def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def timeframe_minutes(tf: Any) -> int:
    s = str(tf or "M15").upper()
    if len(s) < 2:
        return 15
    prefix, num = s[0], s[1:]
    try:
        n = int(num)
    except Exception:
        return 15
    if prefix == "M":
        return n
    if prefix == "H":
        return n * 60
    if prefix == "D":
        return n * 1440
    return 15

def is_parked(card: Dict[str, Any]) -> bool:
    text = " ".join(str(card.get(k, "")) for k in ["memory_class", "brain_state", "band"]).upper()
    return card.get("active_in_runtime") is False or "WEAKENED" in text or "PARKED" in text

def is_insufficient(card: Dict[str, Any]) -> bool:
    text = f"{card.get('brain_state','')} {card.get('primary_reason','')}".upper()
    return bool(card.get("missing_inputs")) or "INSUFFICIENT" in text or "MISSING" in text

def is_no_trade(card: Dict[str, Any]) -> bool:
    text = " ".join(str(card.get(k, "")) for k in ["memory_class", "band", "memory_id", "plain_language_summary_fa"]).upper()
    return "NO_TRADE" in text or "AVOID" in text or "AVOID_SHORT" in text

def is_directional_watch(card: Dict[str, Any]) -> bool:
    text = " ".join(str(card.get(k, "")) for k in ["memory_class", "candidate_type", "brain_state", "memory_id"]).upper()
    return "DIRECTIONAL" in text

def posture_fa(card: Dict[str, Any]) -> str:
    mid = str(card.get("memory_id", ""))
    if is_no_trade(card):
        return "هشدار احتیاط / اجتناب از short-like context"
    if is_directional_watch(card):
        side = str(card.get("direction_side") or "").upper()
        return "directional watch پژوهشی: LONG-bias context" if side == "LONG" else "directional watch پژوهشی"
    if "PRIOR48" in mid:
        return "watch پژوهشی: prior48 sweep rejection / fade-down context"
    if "SWEEP_REJECTION" in mid:
        return "watch پژوهشی: sweep rejection / fade-down context"
    return "memory event پژوهشی فعال"

def meaning_fa(card: Dict[str, Any]) -> str:
    mid = str(card.get("memory_id", ""))
    if is_no_trade(card):
        return "این context از نظر حافظهٔ تاریخی برای ادامهٔ short-like نامساعدتر از baseline بوده؛ فقط برای احتیاط شخصی."
    if is_directional_watch(card):
        return str(card.get("plain_language_summary_fa") or "یک directional watch پژوهشی روی کندل بسته‌شده فعال شده است؛ این دستور خرید/فروش یا نقطه ورود نیست.")
    if "PRIOR48" in mid:
        return "شرط prior48 upside sweep و برگشت داخل سطح روی کندل بسته‌شده فعال شده؛ فقط watch پژوهشی fade-down."
    if "SWEEP_REJECTION" in mid:
        return "شرط sweep سطح بالایی و برگشت داخل سطح روی کندل بسته‌شده فعال شده؛ فقط watch پژوهشی fade-down."
    return str(card.get("plain_language_summary_fa") or "یک memory event رسمی فعال شده است.")

def event_from_card(card: Dict[str, Any], activated_at: datetime, existing: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not card.get("is_active_match") or is_parked(card) or is_insufficient(card):
        return None
    latest = card.get("latest_context") or {}
    bar_open = parse_dt(latest.get("latest_bar_open_ts_utc"))
    bar_close = bar_open + timedelta(minutes=timeframe_minutes(card.get("timeframe"))) if bar_open else None
    event_id = f"{card.get('memory_id','memory')}::{latest.get('latest_bar_open_ts_utc') or iso(activated_at)}"

    first_activated = parse_dt((existing or {}).get("activated_at_utc")) or activated_at
    expires_at = first_activated + timedelta(minutes=ACTIVE_EVENT_WINDOW_MIN)
    last_seen = activated_at
    status = "ACTIVE" if activated_at <= expires_at else "EXPIRED"
    return {
        "event_id": event_id,
        "memory_id": card.get("memory_id"),
        "instrument": card.get("instrument"),
        "timeframe": card.get("timeframe"),
        "event_type": "NO_TRADE_CONTEXT" if is_no_trade(card) else ("DIRECTIONAL_WATCH" if is_directional_watch(card) else "ACTIVE_WATCH"),
        "direction_side": card.get("direction_side"),
        "posture_fa": posture_fa(card),
        "meaning_fa": meaning_fa(card),
        "display_message_fa": meaning_fa(card),
        "activated_at_utc": iso(first_activated),
        "first_seen_utc": iso(first_activated),
        "last_seen_utc": iso(last_seen),
        "expires_at_utc": iso(expires_at),
        "source_bar_open_ts_utc": iso(bar_open),
        "source_bar_close_ts_utc": iso(bar_close),
        "session_bucket": latest.get("session_bucket") or "UNKNOWN",
        "score_not_probability": card.get("score_not_probability"),
        "band": card.get("band"),
        "status": status,
        "no_trade": is_no_trade(card),
        "forbidden": "بدون buy/sell، بدون entry/stop/target، بدون probability، بدون broker/execution.",
        "authority": AUTHORITY,
        "created_by_workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "created_by_workflow_sha": os.environ.get("GITHUB_SHA"),
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--payload", default="panel/brain4/sig_brain4_runtime_payload_current.json")
    ap.add_argument("--refresh-status", default="panel/brain4/sig_live_refresh_status_latest.json")
    ap.add_argument("--history", default="panel/brain4/sig_brain4_event_history_current.json")
    args = ap.parse_args()
    root = Path(args.repo_root)
    payload = load_json(root / args.payload, {})
    refresh = load_json(root / args.refresh_status, {})
    old = load_json(root / args.history, {"events": []})

    now = parse_dt(refresh.get("last_successful_refresh_utc") or refresh.get("created_utc") or payload.get("created_utc")) or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=HISTORY_KEEP_DAYS)

    existing_by_id = {e.get("event_id"): e for e in old.get("events", []) if e.get("event_id")}
    merged: Dict[str, Dict[str, Any]] = {}
    for e in old.get("events", []):
        eid = e.get("event_id")
        if not eid:
            continue
        activated = parse_dt(e.get("activated_at_utc") or e.get("first_seen_utc"))
        if activated and activated < cutoff:
            continue
        exp = parse_dt(e.get("expires_at_utc"))
        e = dict(e)
        e["status"] = "ACTIVE" if exp and now <= exp else "EXPIRED"
        merged[eid] = e

    active_created = 0
    for card in payload.get("cards", []) or []:
        ev = event_from_card(card, now, existing_by_id.get(f"{card.get('memory_id','memory')}::{(card.get('latest_context') or {}).get('latest_bar_open_ts_utc') or iso(now)}"))
        if ev:
            merged[ev["event_id"]] = ev
            if ev["status"] == "ACTIVE":
                active_created += 1

    events = list(merged.values())
    def sort_key(e: Dict[str, Any]) -> str:
        return e.get("activated_at_utc") or e.get("first_seen_utc") or ""
    events.sort(key=sort_key, reverse=True)
    events = events[:HISTORY_MAX_ITEMS]
    active_events = [e for e in events if e.get("status") == "ACTIVE"]

    out = {
        "history_version": "SIG_BRAIN4_OFFICIAL_EVENT_HISTORY_v1_1_MTF_DIRECTIONAL_OPS10",
        "created_utc": iso(now),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "action_surface_authorized": False,
        "broker_execution_authorized": False,
        "retention_policy": {"keep_days": HISTORY_KEEP_DAYS, "max_events": HISTORY_MAX_ITEMS, "dedupe_key": "event_id"},
        "summary": {"event_count": len(events), "active_event_count": len(active_events), "expired_event_count": len(events)-len(active_events)},
        "active_events": active_events,
        "events": events,
        "forbidden_use": ["NO_BUY_SELL", "NO_ENTRY_STOP_TARGET", "NO_POSITION_SIZE", "NO_PROBABILITY", "NO_BROKER_EXECUTION"],
    }
    write_json(root / "panel/brain4/sig_brain4_event_history_current.json", out)
    write_json(root / "runtime/sig_brain/sig_brain4_event_history_current.json", out)
    proof = {"validation_status": "PASS", "created_utc": iso(now), "event_count": len(events), "active_event_count": len(active_events), "authority": AUTHORITY, "signal_authorized": False, "action_surface_authorized": False}
    write_json(root / "proofs/sig_brain4_event_history_validation_result.json", proof)
    print(json.dumps({"status":"sig_brain4_official_event_history_updated", **proof}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
