#!/usr/bin/env python3
"""SIG-BRAIN-OPS16A — Send a Resend TEST email for alert plumbing only.

This script intentionally does NOT read or mutate official Brain event history, alert state,
runtime payloads, or panel files. It sends a clearly marked TEST email so the Resend/GitHub
Secrets/email path can be verified without waiting for a real active memory event.

Display-only boundary: no signal, no buy/sell/hold, no entry/stop/target, no probability claim,
no broker/execution.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RESEND_ENDPOINT = "https://api.resend.com/emails"
AUTHORITY = (
    "SIG_BRAIN4_EMAIL_ALERT_TEST|TEST_ONLY|NOT_MARKET_EVENT|NOT_SIGNAL|"
    "NO_BUY_SELL_HOLD|NO_ENTRY_STOP_TARGET|NO_PROBABILITY|NO_BROKER_EXECUTION"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def env_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def split_recipients(value: str) -> List[str]:
    return [x.strip() for x in (value or "").replace(";", ",").split(",") if x.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
            "User-Agent": "TradingOS-SIG-Brain-Email-Alert-Test",
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


def build_test_text(note: str, created_utc: str) -> str:
    return f"""SIG Brain TEST email alert — no market event

This is a plumbing test for the SIG Brain email notification path.

No memory event was activated.
No official event history was modified.
No email alert state was modified.
No buy/sell signal.
No entry/stop/target.
No probability claim.
No broker/execution.

Created UTC: {created_utc}
Note: {note}
"""


def build_test_html(note: str, created_utc: str) -> str:
    safe_note = (note or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#f6f8fb;padding:24px;color:#101828;">
      <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #d8e0ea;border-radius:16px;padding:22px;">
        <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#b42318;font-weight:700;">TEST ONLY — NOT A MARKET EVENT</div>
        <h1 style="font-size:24px;margin:10px 0 12px 0;">SIG Brain email alert test</h1>
        <p style="font-size:15px;line-height:1.6;color:#344054;margin:0 0 12px 0;">This email confirms that GitHub Actions secrets, the Resend API key, sender, recipient, and email delivery path are working.</p>
        <div style="border-radius:12px;background:#fff4ed;border:1px solid #fed7aa;padding:12px 14px;margin:14px 0;color:#7c2d12;font-size:14px;line-height:1.6;">
          No memory event was activated. No official history or alert state was modified. No signal, no buy/sell, no entry/stop/target, no probability, no broker/execution.
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:14px;color:#344054;margin-top:14px;">
          <tr><td style="padding:6px 0;color:#667085;">Created UTC</td><td style="padding:6px 0;text-align:right;">{created_utc}</td></tr>
          <tr><td style="padding:6px 0;color:#667085;">Note</td><td style="padding:6px 0;text-align:right;">{safe_note}</td></tr>
        </table>
      </div>
    </div>
    """


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proof", default="proofs/sig_brain4_email_alert_test_result.json")
    args = ap.parse_args()

    created_utc = now_iso()
    enabled = env_bool(os.environ.get("SIG_ALERT_EMAIL_ENABLED"))
    proof: Dict[str, Any] = {
        "program": "SIG-BRAIN-OPS16A_RESEND_EMAIL_ALERT_TEST",
        "created_utc": created_utc,
        "authority": AUTHORITY,
        "enabled": enabled,
        "provider": "resend",
        "test_only": True,
        "official_history_modified": False,
        "alert_state_modified": False,
        "signal_authorized": False,
        "action_surface_authorized": False,
        "broker_execution_authorized": False,
        "email_sent": False,
        "failures": [],
    }

    if not enabled:
        proof["skipped_reason"] = "SIG_ALERT_EMAIL_ENABLED is not true"
        write_json(Path(args.proof), proof)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("RESEND_API_KEY") or ""
    sender = os.environ.get("SIG_ALERT_EMAIL_FROM") or ""
    to_value = os.environ.get("SIG_ALERT_EMAIL_TO") or ""
    reply_to = os.environ.get("SIG_ALERT_EMAIL_REPLY_TO") or None
    note = os.environ.get("SIG_ALERT_TEST_NOTE") or "Manual SIG Brain email alert plumbing test"
    recipients = split_recipients(to_value)

    missing = [name for name, value in [
        ("RESEND_API_KEY", api_key),
        ("SIG_ALERT_EMAIL_FROM", sender),
        ("SIG_ALERT_EMAIL_TO", to_value),
    ] if not value]
    if missing:
        proof["skipped_reason"] = "missing_email_configuration"
        proof["failures"].append({"type": "missing_email_configuration", "missing": missing})
        write_json(Path(args.proof), proof)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 0

    subject = "SIG Brain TEST alert — no market event"
    text = build_test_text(note, created_utc)
    html_body = build_test_html(note, created_utc)
    ok, status_code, response_body = send_resend(api_key, sender, recipients, subject, text, html_body, reply_to)
    proof["resend_status_code"] = status_code
    proof["resend_response_excerpt"] = response_body[:500]
    proof["recipients_count"] = len(recipients)
    proof["from_configured"] = bool(sender)
    proof["reply_to_configured"] = bool(reply_to)

    if ok:
        proof["email_sent"] = True
        proof["status"] = "test_email_sent"
    else:
        proof["status"] = "test_email_failed"
        proof["failures"].append({"type": "resend_send_failed", "status_code": status_code, "response_excerpt": response_body[:500]})

    write_json(Path(args.proof), proof)
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    # Fail the test workflow if Resend rejected the message; this is a dedicated test workflow.
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
