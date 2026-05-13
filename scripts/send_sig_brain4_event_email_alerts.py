#!/usr/bin/env python3
"""SIG-BRAIN-OPS16 — Resend email alerts for new official Brain4 active memory events.

Reads the official file-backed Brain4 event history, sends a concise email alert only for
ACTIVE events that have not been alerted before, and writes a notification state/proof.

Display-only: no signal, no buy/sell/hold, no entry/stop/target, no probability claim,
no broker/execution.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

AUTHORITY = (
    "SIG_BRAIN4_ACTIVE_EVENT_EMAIL_ALERT|DISPLAY_ONLY|NOT_SIGNAL|"
    "NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_PROBABILITY|NO_BROKER_EXECUTION"
)
STATE_KEEP_DAYS = 14
STATE_MAX_ITEMS = 1000
RESEND_ENDPOINT = "https://api.resend.com/emails"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


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


def env_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def split_recipients(value: str) -> List[str]:
    return [x.strip() for x in (value or "").replace(";", ",").split(",") if x.strip()]


def compact_event(e: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": e.get("event_id"),
        "memory_id": e.get("memory_id"),
        "instrument": e.get("instrument"),
        "timeframe": e.get("timeframe"),
        "event_type": e.get("event_type"),
        "direction_side": e.get("direction_side"),
        "session_bucket": e.get("session_bucket"),
        "activated_at_utc": e.get("activated_at_utc"),
        "expires_at_utc": e.get("expires_at_utc"),
        "source_bar_open_ts_utc": e.get("source_bar_open_ts_utc"),
        "source_bar_close_ts_utc": e.get("source_bar_close_ts_utc"),
        "score_not_probability": e.get("score_not_probability"),
        "band": e.get("band"),
        "posture_fa": e.get("posture_fa"),
    }


def event_status_is_active(e: Dict[str, Any], now: datetime) -> bool:
    if str(e.get("status", "")).upper() != "ACTIVE":
        return False
    exp = parse_dt(e.get("expires_at_utc"))
    return bool(exp and now <= exp)


def get_active_events(history: Dict[str, Any], now: datetime) -> List[Dict[str, Any]]:
    source = history.get("active_events") if isinstance(history.get("active_events"), list) else history.get("events", [])
    out: List[Dict[str, Any]] = []
    for e in source or []:
        if isinstance(e, dict) and e.get("event_id") and event_status_is_active(e, now):
            out.append(e)
    out.sort(key=lambda x: str(x.get("activated_at_utc") or ""), reverse=True)
    return out


def cleanup_state(state: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    cutoff = now - timedelta(days=STATE_KEEP_DAYS)
    sent = []
    seen = set()
    for row in state.get("sent_event_alerts", []) or []:
        if not isinstance(row, dict):
            continue
        eid = row.get("event_id")
        if not eid or eid in seen:
            continue
        sent_at = parse_dt(row.get("sent_at_utc"))
        if sent_at and sent_at < cutoff:
            continue
        seen.add(eid)
        sent.append(row)
    sent.sort(key=lambda x: str(x.get("sent_at_utc") or ""), reverse=True)
    sent = sent[:STATE_MAX_ITEMS]
    return {
        "state_version": "SIG_BRAIN4_EMAIL_ALERT_STATE_v1_0_OPS16",
        "updated_utc": iso(now),
        "authority": AUTHORITY,
        "sent_event_alerts": sent,
        "retention_policy": {"keep_days": STATE_KEEP_DAYS, "max_items": STATE_MAX_ITEMS, "dedupe_key": "event_id"},
        "signal_authorized": False,
        "action_surface_authorized": False,
        "broker_execution_authorized": False,
    }


def minutes_remaining(e: Dict[str, Any], now: datetime) -> Optional[int]:
    exp = parse_dt(e.get("expires_at_utc"))
    if not exp:
        return None
    return max(0, int((exp - now).total_seconds() // 60))


def build_text(events: List[Dict[str, Any]], now: datetime) -> str:
    lines = [
        f"SIG Brain active memory event alert — {len(events)} new event(s)",
        "",
        "Display-only / personal research posture / NOT a signal engine.",
        "No buy/sell, no entry/stop/target, no probability claim, no broker/execution.",
        "",
    ]
    for idx, e in enumerate(events, 1):
        remaining = minutes_remaining(e, now)
        rem_text = f"{remaining} minutes remaining" if remaining is not None else "expiry available in panel"
        lines.extend([
            f"{idx}) {e.get('instrument','?')} · {e.get('timeframe','?')} — {e.get('event_type','ACTIVE_MEMORY_EVENT')}",
            f"Posture: {e.get('posture_fa') or 'memory event پژوهشی فعال'}",
            f"Meaning: {e.get('meaning_fa') or e.get('display_message_fa') or 'A historical context memory became active.'}",
            f"Activated UTC: {e.get('activated_at_utc')}",
            f"Valid until UTC: {e.get('expires_at_utc')} ({rem_text})",
            f"Source bar UTC: {e.get('source_bar_open_ts_utc')}",
            f"Session: {e.get('session_bucket') or 'UNKNOWN'}",
            f"Research strength: {e.get('score_not_probability')}/100 · not probability",
            f"Memory: {e.get('memory_id')}",
            "Boundary: no buy/sell, no entry/stop/target, no probability, no broker/execution.",
            "",
        ])
    return "\n".join(lines)


def build_html(events: List[Dict[str, Any]], now: datetime) -> str:
    cards = []
    for e in events:
        remaining = minutes_remaining(e, now)
        rem_text = f"{remaining} دقیقه باقی‌مانده" if remaining is not None else "اعتبار در پنل قابل مشاهده است"
        cards.append(f"""
        <div style="border:1px solid #d8e0ea;border-radius:14px;padding:16px;margin:14px 0;background:#ffffff;">
          <div style="font-size:13px;color:#667085;">{html.escape(str(e.get('event_type') or 'ACTIVE_MEMORY_EVENT'))}</div>
          <h2 style="margin:6px 0 10px 0;font-size:22px;color:#101828;">{html.escape(str(e.get('instrument') or '?'))} · {html.escape(str(e.get('timeframe') or '?'))}</h2>
          <p style="margin:6px 0;font-size:15px;color:#344054;"><strong>معنی ساده:</strong> {html.escape(str(e.get('posture_fa') or 'memory event پژوهشی فعال'))}</p>
          <p style="margin:6px 0;font-size:15px;color:#344054;">{html.escape(str(e.get('meaning_fa') or e.get('display_message_fa') or 'یک context تاریخی فعال شده است.'))}</p>
          <table style="margin-top:12px;width:100%;border-collapse:collapse;font-size:14px;color:#344054;">
            <tr><td style="padding:4px 0;color:#667085;">فعال‌شده UTC</td><td style="padding:4px 0;text-align:right;">{html.escape(str(e.get('activated_at_utc') or ''))}</td></tr>
            <tr><td style="padding:4px 0;color:#667085;">اعتبار تا UTC</td><td style="padding:4px 0;text-align:right;">{html.escape(str(e.get('expires_at_utc') or ''))} · {html.escape(rem_text)}</td></tr>
            <tr><td style="padding:4px 0;color:#667085;">session</td><td style="padding:4px 0;text-align:right;">{html.escape(str(e.get('session_bucket') or 'UNKNOWN'))}</td></tr>
            <tr><td style="padding:4px 0;color:#667085;">قدرت پژوهشی</td><td style="padding:4px 0;text-align:right;">{html.escape(str(e.get('score_not_probability') or '—'))}/100 · نه احتمال</td></tr>
          </table>
          <div style="margin-top:12px;padding-top:10px;border-top:1px solid #eef2f6;font-size:12px;color:#667085;">memory_id: {html.escape(str(e.get('memory_id') or ''))}</div>
        </div>
        """)
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#f6f8fb;padding:24px;color:#101828;">
      <div style="max-width:720px;margin:0 auto;">
        <h1 style="font-size:24px;margin:0 0 8px 0;">SIG Brain — active memory event</h1>
        <p style="font-size:14px;color:#667085;margin:0 0 18px 0;">{len(events)} رویداد فعال جدید ثبت شد. این ایمیل فقط نمایش پژوهشی است.</p>
        {''.join(cards)}
        <div style="font-size:13px;color:#8a94a6;margin-top:18px;line-height:1.6;">
          مرز: بدون buy/sell، بدون entry/stop/target، بدون probability، بدون broker/execution.<br />
          score_not_probability احتمال نیست و فقط قدرت/اولویت پژوهشی را نشان می‌دهد.
        </div>
      </div>
    </div>
    """


def send_resend(api_key: str, sender: str, recipients: List[str], subject: str, text: str, html_body: str, reply_to: Optional[str]) -> Tuple[bool, int, str]:
    payload: Dict[str, Any] = {
        "from": sender,
        "to": recipients,
        "subject": subject,
        "text": text,
        "html": html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TradingOS-SIG-Brain-Email-Alerts",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return 200 <= resp.status < 300, int(resp.status), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, int(e.code), body
    except Exception as e:
        return False, 0, repr(e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--history", default="panel/brain4/sig_brain4_event_history_current.json")
    ap.add_argument("--state", default="runtime/sig_brain/sig_brain4_email_alert_state_current.json")
    ap.add_argument("--proof", default="proofs/sig_brain4_email_alert_result.json")
    args = ap.parse_args()

    root = Path(args.repo_root)
    now = now_utc()
    enabled = env_bool(os.environ.get("SIG_ALERT_EMAIL_ENABLED"))
    proof: Dict[str, Any] = {
        "program": "SIG-BRAIN-OPS16_ACTIVE_EVENT_EMAIL_ALERT",
        "created_utc": iso(now),
        "authority": AUTHORITY,
        "enabled": enabled,
        "provider": "resend",
        "signal_authorized": False,
        "action_surface_authorized": False,
        "broker_execution_authorized": False,
        "email_sent": False,
        "new_event_count": 0,
        "skipped_reason": None,
        "failures": [],
    }

    old_state = load_json(root / args.state, {})
    state = cleanup_state(old_state, now)

    if not enabled:
        proof["skipped_reason"] = "SIG_ALERT_EMAIL_ENABLED is not true"
        write_json(root / args.state, state)
        write_json(root / args.proof, proof)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("RESEND_API_KEY") or ""
    sender = os.environ.get("SIG_ALERT_EMAIL_FROM") or ""
    to_value = os.environ.get("SIG_ALERT_EMAIL_TO") or ""
    reply_to = os.environ.get("SIG_ALERT_EMAIL_REPLY_TO") or None
    recipients = split_recipients(to_value)

    missing = [name for name, value in [("RESEND_API_KEY", api_key), ("SIG_ALERT_EMAIL_FROM", sender), ("SIG_ALERT_EMAIL_TO", to_value)] if not value]
    if missing:
        proof["failures"].append({"type": "missing_email_configuration", "missing": missing})
        proof["skipped_reason"] = "missing_email_configuration"
        write_json(root / args.state, state)
        write_json(root / args.proof, proof)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 0

    history = load_json(root / args.history, {})
    active_events = get_active_events(history, now)
    sent_ids = {row.get("event_id") for row in state.get("sent_event_alerts", []) if row.get("event_id")}
    new_events = [e for e in active_events if e.get("event_id") not in sent_ids]
    proof["active_event_count"] = len(active_events)
    proof["new_event_count"] = len(new_events)
    proof["new_events"] = [compact_event(e) for e in new_events]

    if not new_events:
        proof["skipped_reason"] = "no_new_active_events"
        write_json(root / args.state, state)
        write_json(root / args.proof, proof)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 0

    subject = f"SIG Brain: {len(new_events)} active memory event{'s' if len(new_events) != 1 else ''}"
    text = build_text(new_events, now)
    html_body = build_html(new_events, now)
    ok, status_code, response_body = send_resend(api_key, sender, recipients, subject, text, html_body, reply_to)
    proof["resend_status_code"] = status_code
    proof["resend_response_excerpt"] = response_body[:500]

    if ok:
        proof["email_sent"] = True
        sent = list(state.get("sent_event_alerts", []) or [])
        for e in new_events:
            sent.insert(0, {
                "event_id": e.get("event_id"),
                "memory_id": e.get("memory_id"),
                "instrument": e.get("instrument"),
                "timeframe": e.get("timeframe"),
                "activated_at_utc": e.get("activated_at_utc"),
                "expires_at_utc": e.get("expires_at_utc"),
                "sent_at_utc": iso(now),
                "provider": "resend",
                "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
                "workflow_sha": os.environ.get("GITHUB_SHA"),
            })
        state["sent_event_alerts"] = sent
        state = cleanup_state(state, now)
    else:
        proof["failures"].append({"type": "resend_send_failed", "status_code": status_code, "response_excerpt": response_body[:500]})
        proof["skipped_reason"] = "resend_send_failed"

    write_json(root / args.state, state)
    write_json(root / args.proof, proof)
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    # Do not fail the live data refresh/deploy path because alerting is auxiliary.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
