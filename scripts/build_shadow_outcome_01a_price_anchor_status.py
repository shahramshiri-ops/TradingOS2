#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json

ROOT = Path.cwd()
RUNTIME = ROOT / "runtime/sig_shadow"
PANEL = ROOT / "panel/brain4"
PROOFS = ROOT / "proofs"
for p in [RUNTIME, PANEL, PROOFS]:
    p.mkdir(parents=True, exist_ok=True)

LEDGER = RUNTIME / "shadow_outcome_observation_ledger_current.json"
STATUS_RUNTIME = RUNTIME / "shadow_outcome_status_current.json"
STATUS_PANEL = PANEL / "shadow_outcome_status_current.json"

def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

ledger = load(LEDGER, {})
observations = ledger.get("observations") or []

anchor_counts = Counter()
price_status_counts = Counter()
resolved_subjects = 0
context_derived_subjects = 0
source_anchor_subjects = 0

for obs in observations:
    ars = str(obs.get("anchor_resolution_status") or "NO_RESOLVED_ANCHOR")
    ps = str(obs.get("price_data_status") or "UNKNOWN")
    anchor_counts[ars] += 1
    price_status_counts[ps] += 1
    if obs.get("anchor_h1_bar_open_ts_utc"):
        resolved_subjects += 1
    if ars == "CONTEXT_DERIVED_LATEST_CLOSED_H1_BAR":
        context_derived_subjects += 1
    if ars == "SOURCE_PRICE_BAR_ANCHOR":
        source_anchor_subjects += 1

patch_status = {
    "price_anchor_patch_version": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_v1_0",
    "price_anchor_patch_created_utc": now_utc(),
    "resolved_price_anchor_subject_count": resolved_subjects,
    "context_derived_anchor_subject_count": context_derived_subjects,
    "source_price_anchor_subject_count": source_anchor_subjects,
    "anchor_resolution_breakdown": dict(anchor_counts.most_common()),
    "price_data_status_breakdown_after_anchor_patch": dict(price_status_counts.most_common()),
    "plain_language_fa_anchor": (
        "برای رکوردهایی که timestamp کندل نداشتند، anchor محافظه‌کارانه از آخرین کندل H1 بسته‌شده قبل از زمان runtime استخراج می‌شود. "
        "این فقط مشاهده مسیر قیمت است و سیگنال، PnL، ورود، حدضرر یا تارگت نیست."
    )
}

for path in [STATUS_RUNTIME, STATUS_PANEL]:
    payload = load(path, {})
    if not isinstance(payload, dict):
        payload = {}
    payload.update(patch_status)
    payload.setdefault("boundary", {})
    payload["boundary"].update({
        "signal_authorized": False,
        "trade_instruction_authorized": False,
        "broker_execution_authorized": False,
        "action_surface_authorized": False,
        "auto_learning_authorized": False,
        "rule_rewrite_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    })
    write(path, payload)

proof = {
    "validation_name": "SHADOW_OUTCOME_01A_PRICE_ANCHOR_STATUS",
    "created_utc": now_utc(),
    **patch_status,
    "subject_count": len(observations),
    "boundary": {
        "signal_authorized": False,
        "broker_execution_authorized": False,
        "pnl_authorized": False,
        "entry_stop_target_authorized": False,
    },
}
write(PROOFS / "sig_shadow_outcome_01a_price_anchor_status_result.json", proof)
print(json.dumps(proof, ensure_ascii=False, indent=2))
