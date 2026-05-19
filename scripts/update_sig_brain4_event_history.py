#!/usr/bin/env python3
"""SIG-BRAIN-OPS21 — official server-side Brain4 event history updater with event lifecycle policy.

Reads the current Brain4 runtime payload and refresh status, merges active memory events
into an official file-backed history, and applies per-memory lifecycle policy:
- display validity is memory-specific, not a global 10-minute window;
- expiry is not invalidation;
- selected level-based memories may be marked INVALIDATED when a context-lifecycle
  invalidation rule is met.

Display-only: no signal, no buy/sell, no execution.
"""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HISTORY_KEEP_DAYS = 7
HISTORY_MAX_ITEMS = 500
DEFAULT_ACTIVE_EVENT_WINDOW_MIN = 60
AUTHORITY = "SIG_BRAIN4_OFFICIAL_EVENT_HISTORY|DISPLAY_ONLY|NOT_SIGNAL|NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_BROKER_EXECUTION"


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).replace("Z", "+00:00")
    try:
        out = datetime.fromisoformat(s)
    except Exception:
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def iso(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    text = " ".join(str(card.get(k, "")) for k in ["memory_class", "brain_state", "band", "activation_status"]).upper()
    return card.get("active_in_runtime") is False or "WEAKENED" in text or "PARKED" in text or "EXTENDED_OBSERVATION" in text


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
        if side == "LONG":
            return "directional watch پژوهشی: LONG-bias context"
        if side == "SHORT":
            return "directional watch پژوهشی: SHORT-bias context"
        return "directional watch پژوهشی"
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


def lifecycle_policy(card: Dict[str, Any]) -> Dict[str, Any]:
    p = card.get("event_lifecycle_policy")
    return p if isinstance(p, dict) else {}


def session_cap_dt(cap: Any, basis: datetime) -> Optional[datetime]:
    if not cap:
        return None
    cap_s = str(cap).upper()
    hour_map = {
        "ASIA_END_UTC": 7,
        "LONDON_END_UTC": 12,
        "LONDON_NY_OVERLAP_END_UTC": 16,
        "NEW_YORK_END_UTC": 21,
        "UTC_DAY_END": 24,
    }
    if cap_s not in hour_map:
        return None
    if cap_s == "UTC_DAY_END":
        out = basis.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        out = basis.replace(hour=hour_map[cap_s], minute=0, second=0, microsecond=0)
    return out if out > basis else None


def compute_expiry(card: Dict[str, Any], bar_close: Optional[datetime], first_activated: datetime) -> Tuple[datetime, Dict[str, Any]]:
    policy = lifecycle_policy(card)
    display = policy.get("display_validity_policy") if isinstance(policy.get("display_validity_policy"), dict) else {}
    basis = str(display.get("basis") or "source_bar_close_plus_trigger_timeframe_bars")
    tf_min = timeframe_minutes(card.get("timeframe"))
    valid_bars = display.get("validity_bars")
    max_minutes = display.get("max_validity_minutes")

    try:
        valid_bars_num = int(valid_bars) if valid_bars is not None else None
    except Exception:
        valid_bars_num = None
    try:
        max_min_num = int(max_minutes) if max_minutes is not None else None
    except Exception:
        max_min_num = None

    if valid_bars_num and valid_bars_num > 0:
        duration_minutes = valid_bars_num * tf_min
    elif max_min_num and max_min_num > 0:
        duration_minutes = max_min_num
    else:
        duration_minutes = DEFAULT_ACTIVE_EVENT_WINDOW_MIN

    if max_min_num and max_min_num > 0:
        duration_minutes = min(duration_minutes, max_min_num)

    base = bar_close if (bar_close and basis.startswith("source_bar_close")) else first_activated
    expiry = base + timedelta(minutes=duration_minutes)
    cap = session_cap_dt(display.get("session_cap"), base)
    if cap and cap < expiry:
        expiry = cap
    if expiry <= first_activated:
        # Never create a zero/negative visible window. This is display validity, not trade expiry.
        expiry = first_activated + timedelta(minutes=max(15, min(duration_minutes, DEFAULT_ACTIVE_EVENT_WINDOW_MIN)))

    meta = {
        "policy_version": policy.get("lifecycle_version") or "SIG_BRAIN_EVENT_LIFECYCLE_POLICY_DEFAULT_OPS21",
        "basis": basis,
        "validity_bars": valid_bars_num,
        "max_validity_minutes": max_min_num,
        "duration_minutes_applied": int((expiry - base).total_seconds() // 60),
        "session_cap": display.get("session_cap"),
        "expiry_label_fa": display.get("expiry_label_fa") or "از بازهٔ اعتبار پژوهشی خارج شده",
        "expiry_is_invalidation": False,
        "expiry_plain_language_fa": display.get("plain_language_fa") or "پایان بازهٔ نمایش به معنی invalidation یا شکست تحلیل نیست.",
    }
    return expiry, meta


def get_current_card_by_memory(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for c in payload.get("cards", []) or []:
        if isinstance(c, dict) and c.get("memory_id"):
            out[str(c["memory_id"])] = c
    return out


def reference_value_from_card(card: Dict[str, Any], field: Any) -> Optional[float]:
    if not field:
        return None
    row = card.get("latest_context") or {}
    val = row.get(str(field))
    try:
        return float(val)
    except Exception:
        return None


def evaluate_invalidation(event: Dict[str, Any], current_card: Optional[Dict[str, Any]], now: datetime) -> Tuple[bool, Optional[str], Optional[str]]:
    if not current_card:
        return False, None, None
    policy = lifecycle_policy(current_card)
    inv = policy.get("invalidation_policy") if isinstance(policy.get("invalidation_policy"), dict) else {}
    if not inv.get("enabled"):
        return False, None, None
    latest = current_card.get("latest_context") or {}
    current_bar = parse_dt(latest.get("latest_bar_open_ts_utc") or latest.get("latest_h1_bar_open_ts_utc"))
    source_bar = parse_dt(event.get("source_bar_open_ts_utc"))
    if current_bar and source_bar and current_bar <= source_bar:
        return False, None, None
    for rule in inv.get("rules", []) or []:
        if not isinstance(rule, dict) or rule.get("type") != "h1_close_back_through_reference_level":
            continue
        ref = event.get("reference_level_value")
        if ref is None:
            ref = reference_value_from_card(current_card, rule.get("reference_field"))
        try:
            ref_f = float(ref)
            close_f = float(latest.get("h1_close"))
        except Exception:
            continue
        direction = str(rule.get("memory_direction") or event.get("direction_side") or "").upper()
        if direction == "LONG" and close_f < ref_f:
            return True, inv.get("invalidated_label_fa") or "context توسط شرط نقض سطح دیگر فعال محسوب نمی‌شود", f"h1_close {close_f} < reference {ref_f}"
        if direction == "SHORT" and close_f > ref_f:
            return True, inv.get("invalidated_label_fa") or "context توسط شرط نقض سطح دیگر فعال محسوب نمی‌شود", f"h1_close {close_f} > reference {ref_f}"
    return False, None, None


def event_status(event: Dict[str, Any], now: datetime, current_card: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    e = dict(event)
    was_invalidated = str(e.get("status", "")).upper() == "INVALIDATED" or bool(e.get("invalidated_at_utc"))
    if was_invalidated:
        e["status"] = "INVALIDATED"
        return e
    invalid, label, technical = evaluate_invalidation(e, current_card, now)
    if invalid:
        e["status"] = "INVALIDATED"
        e["invalidated_at_utc"] = iso(now)
        e["invalidation_label_fa"] = label
        e["invalidation_technical_reason"] = technical
        e["invalidation_is_not_trade_stop"] = True
        return e
    exp = parse_dt(e.get("expires_at_utc"))
    e["status"] = "ACTIVE" if exp and now <= exp else "EXPIRED"
    return e


def event_from_card(card: Dict[str, Any], activated_at: datetime, existing: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not card.get("is_active_match") or is_parked(card) or is_insufficient(card):
        return None
    latest = card.get("latest_context") or {}
    bar_open = parse_dt(latest.get("latest_bar_open_ts_utc") or latest.get("latest_h1_bar_open_ts_utc"))
    bar_close = bar_open + timedelta(minutes=timeframe_minutes(card.get("timeframe"))) if bar_open else None
    event_id = f"{card.get('memory_id','memory')}::{latest.get('latest_bar_open_ts_utc') or latest.get('latest_h1_bar_open_ts_utc') or iso(activated_at)}"

    first_activated = parse_dt((existing or {}).get("activated_at_utc")) or activated_at
    expires_at, expiry_meta = compute_expiry(card, bar_close, first_activated)

    inv = lifecycle_policy(card).get("invalidation_policy") if isinstance(lifecycle_policy(card).get("invalidation_policy"), dict) else {}
    ref_field = None
    if inv.get("enabled"):
        for rule in inv.get("rules", []) or []:
            if isinstance(rule, dict) and rule.get("reference_field"):
                ref_field = rule.get("reference_field")
                break
    ref_val = reference_value_from_card(card, ref_field)

    out = {
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
        "last_seen_utc": iso(activated_at),
        "expires_at_utc": iso(expires_at),
        "expiry_label_fa": expiry_meta.get("expiry_label_fa"),
        "expiry_is_invalidation": False,
        "expiry_plain_language_fa": expiry_meta.get("expiry_plain_language_fa"),
        "event_lifecycle_policy_applied": expiry_meta,
        "invalidation_policy": lifecycle_policy(card).get("invalidation_policy", {}),
        "reference_level_field": ref_field,
        "reference_level_value": ref_val,
        "source_bar_open_ts_utc": iso(bar_open),
        "source_bar_close_ts_utc": iso(bar_close),
        "session_bucket": latest.get("session_bucket") or "UNKNOWN",
        "score_not_probability": card.get("score_not_probability"),
        "band": card.get("band"),
        "status": "ACTIVE",
        "no_trade": is_no_trade(card),
        "forbidden": "بدون buy/sell، بدون entry/stop/target، بدون probability، بدون broker/execution.",
        "authority": AUTHORITY,
        "created_by_workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "created_by_workflow_sha": os.environ.get("GITHUB_SHA"),
    }
    return out


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
    cards_by_memory = get_current_card_by_memory(payload)

    existing_by_id = {e.get("event_id"): e for e in old.get("events", []) if e.get("event_id")}
    merged: Dict[str, Dict[str, Any]] = {}
    for e0 in old.get("events", []) or []:
        if not isinstance(e0, dict):
            continue
        eid = e0.get("event_id")
        if not eid:
            continue
        activated = parse_dt(e0.get("activated_at_utc") or e0.get("first_seen_utc"))
        if activated and activated < cutoff:
            continue
        current_card = cards_by_memory.get(str(e0.get("memory_id")))
        merged[eid] = event_status(e0, now, current_card)

    active_created = 0
    for card in payload.get("cards", []) or []:
        latest = card.get("latest_context") or {}
        eid = f"{card.get('memory_id','memory')}::{latest.get('latest_bar_open_ts_utc') or latest.get('latest_h1_bar_open_ts_utc') or iso(now)}"
        ev = event_from_card(card, now, existing_by_id.get(eid))
        if ev:
            # Preserve permanent invalidation if somehow same id was invalidated earlier.
            prior = merged.get(ev["event_id"])
            if prior and str(prior.get("status", "")).upper() == "INVALIDATED":
                merged[ev["event_id"]] = prior
            else:
                merged[ev["event_id"]] = event_status(ev, now, card)
            if merged[ev["event_id"]].get("status") == "ACTIVE":
                active_created += 1

    events = list(merged.values())
    events.sort(key=lambda e: e.get("activated_at_utc") or e.get("first_seen_utc") or "", reverse=True)
    events = events[:HISTORY_MAX_ITEMS]
    active_events = [e for e in events if e.get("status") == "ACTIVE"]
    expired_events = [e for e in events if e.get("status") == "EXPIRED"]
    invalidated_events = [e for e in events if e.get("status") == "INVALIDATED"]

    out = {
        "history_version": "SIG_BRAIN4_OFFICIAL_EVENT_HISTORY_v1_2_EVENT_LIFECYCLE_OPS21",
        "created_utc": iso(now),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "action_surface_authorized": False,
        "broker_execution_authorized": False,
        "retention_policy": {"keep_days": HISTORY_KEEP_DAYS, "max_events": HISTORY_MAX_ITEMS, "dedupe_key": "event_id"},
        "lifecycle_policy_summary": {
            "display_expiry_is_not_invalidation": True,
            "expiry_label_fa": "از بازهٔ اعتبار پژوهشی خارج شده",
            "invalidation_is_not_trade_stop": True,
            "plain_language_fa": "پایان بازهٔ نمایش به معنی باطل‌شدن الگو، شکست تحلیل یا دستور خروج نیست. Invalidation فقط نقض context پژوهشی است، نه stop-loss."
        },
        "summary": {
            "event_count": len(events),
            "active_event_count": len(active_events),
            "expired_event_count": len(expired_events),
            "invalidated_event_count": len(invalidated_events),
        },
        "active_events": active_events,
        "events": events,
        "forbidden_use": ["NO_BUY_SELL", "NO_ENTRY_STOP_TARGET", "NO_POSITION_SIZE", "NO_PROBABILITY", "NO_BROKER_EXECUTION"],
    }
    write_json(root / "panel/brain4/sig_brain4_event_history_current.json", out)
    write_json(root / "runtime/sig_brain/sig_brain4_event_history_current.json", out)
    proof = {
        "validation_status": "PASS",
        "created_utc": iso(now),
        "event_count": len(events),
        "active_event_count": len(active_events),
        "expired_event_count": len(expired_events),
        "invalidated_event_count": len(invalidated_events),
        "authority": AUTHORITY,
        "signal_authorized": False,
        "action_surface_authorized": False,
    }
    write_json(root / "proofs/sig_brain4_event_history_validation_result.json", proof)
    print(json.dumps({"status": "sig_brain4_official_event_history_updated", **proof}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
