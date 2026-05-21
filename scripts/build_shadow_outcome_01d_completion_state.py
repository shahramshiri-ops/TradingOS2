#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHADOW-OUTCOME-01D completion state:
- stable subject/horizon keys
- duplicate-inflation control
- carry-forward completed horizons
- completion ladder H1+1/H1+2/H1+4/H1+8
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict
from collections import Counter, defaultdict
import json
import hashlib

ROOT = Path.cwd()
RUNTIME_SHADOW = ROOT / "runtime" / "sig_shadow"
PANEL = ROOT / "panel" / "brain4"
PROOFS = ROOT / "proofs"
for p in [RUNTIME_SHADOW, PANEL, PROOFS]:
    p.mkdir(parents=True, exist_ok=True)

LEDGER = RUNTIME_SHADOW / "shadow_outcome_observation_ledger_current.json"
STATE_RUNTIME = RUNTIME_SHADOW / "shadow_outcome_completion_state_current.json"
STATE_PANEL = PANEL / "shadow_outcome_completion_state_current.json"
STATUS_RUNTIME = RUNTIME_SHADOW / "shadow_outcome_status_current.json"
STATUS_PANEL = PANEL / "shadow_outcome_status_current.json"
GUARD_STATUS = RUNTIME_SHADOW / "shadow_outcome_01d_guard_status_current.json"

BOUNDARY = {
    "signal_authorized": False,
    "trade_instruction_authorized": False,
    "broker_execution_authorized": False,
    "action_surface_authorized": False,
    "auto_learning_authorized": False,
    "rule_rewrite_authorized": False,
    "pnl_authorized": False,
    "entry_stop_target_authorized": False,
}

HORIZONS = ["H1+1", "H1+2", "H1+4", "H1+8"]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def h(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def stable_subject_key(obs: Dict[str, Any]) -> str:
    return "SUBJ_" + h([
        obs.get("subject_type"),
        obs.get("memory_id"),
        obs.get("instrument"),
        obs.get("timeframe"),
        obs.get("direction_side"),
        obs.get("anchor_h1_bar_open_ts_utc") or obs.get("anchor_ts_utc"),
        obs.get("reason_code"),
    ])


def stable_horizon_key(subject_key: str, horizon: str) -> str:
    return "HOR_" + h([subject_key, horizon])


def merge_horizon(prev: Dict[str, Any], cur: Dict[str, Any]) -> Dict[str, Any]:
    # Never downgrade a completed horizon to pending/not-observable.
    if prev and prev.get("completion_status") == "COMPLETE" and cur.get("completion_status") != "COMPLETE":
        return prev
    # Prefer complete over anything else.
    if cur.get("completion_status") == "COMPLETE":
        return cur
    if not prev:
        return cur
    # Prefer newer pending with more available bars.
    try:
        if int(cur.get("available_future_bars") or 0) >= int(prev.get("available_future_bars") or 0):
            return cur
    except Exception:
        pass
    return prev


def main() -> None:
    created = now_utc()
    ledger = load_json(LEDGER, {})
    prev_state = load_json(STATE_RUNTIME, {})
    guard = load_json(GUARD_STATUS, {})
    observations = ledger.get("observations") or []

    prev_subjects = prev_state.get("subjects") or {}
    subjects = dict(prev_subjects)

    raw_subject_count = len(observations)
    current_subject_keys = []
    raw_horizon_rows = 0
    current_complete = 0
    current_pending = 0
    current_not_observable = 0

    for obs in observations:
        sk = stable_subject_key(obs)
        current_subject_keys.append(sk)
        subject = subjects.get(sk, {
            "stable_subject_key": sk,
            "subject_type": obs.get("subject_type"),
            "memory_id": obs.get("memory_id"),
            "instrument": obs.get("instrument"),
            "timeframe": obs.get("timeframe"),
            "direction_side": obs.get("direction_side"),
            "anchor_h1_bar_open_ts_utc": obs.get("anchor_h1_bar_open_ts_utc"),
            "anchor_ts_utc": obs.get("anchor_ts_utc"),
            "reason_code": obs.get("reason_code"),
            "first_seen_utc": created,
            "horizons": {},
        })
        subject["last_seen_utc"] = created
        subject["latest_observation_status"] = obs.get("observation_status")
        subject["latest_price_data_status"] = obs.get("price_data_status")
        subject["anchor_resolution_status"] = obs.get("anchor_resolution_status")
        subject["anchor_basis_resolved"] = obs.get("anchor_basis_resolved")

        hrs = obs.get("horizon_results") or []
        if not hrs:
            current_not_observable += 1

        for hr in hrs:
            raw_horizon_rows += 1
            horizon = hr.get("horizon")
            if not horizon:
                continue
            hk = stable_horizon_key(sk, horizon)
            cur = dict(hr)
            cur["stable_horizon_key"] = hk
            cur["last_observed_utc"] = created
            prev = subject["horizons"].get(horizon)
            subject["horizons"][horizon] = merge_horizon(prev, cur)
            if cur.get("completion_status") == "COMPLETE":
                current_complete += 1
            elif cur.get("completion_status") == "PENDING":
                current_pending += 1

        subjects[sk] = subject

    current_unique_subject_count = len(set(current_subject_keys))
    duplicate_subject_count_current = raw_subject_count - current_unique_subject_count

    horizon_ladder = {}
    state_complete = 0
    state_pending = 0
    state_other = 0
    outcome_counts = Counter()

    for horizon in HORIZONS:
        total = complete = pending = other = 0
        for subj in subjects.values():
            hr = (subj.get("horizons") or {}).get(horizon)
            if not hr:
                continue
            total += 1
            cs = hr.get("completion_status")
            if cs == "COMPLETE":
                complete += 1
                state_complete += 1
            elif cs == "PENDING":
                pending += 1
                state_pending += 1
            else:
                other += 1
                state_other += 1
            outcome_counts[str(hr.get("directional_outcome") or "UNKNOWN")] += 1
        horizon_ladder[horizon] = {"total": total, "complete": complete, "pending": pending, "other": other}

    status_payload = {
        "payload_version": "SHADOW_OUTCOME_01D_COMPLETION_STATE_v1_0",
        "created_utc": created,
        "raw_subject_count_current": raw_subject_count,
        "unique_subject_count_current": current_unique_subject_count,
        "duplicate_subject_count_current": duplicate_subject_count_current,
        "raw_horizon_rows_current": raw_horizon_rows,
        "current_complete_horizon_rows": current_complete,
        "current_pending_horizon_rows": current_pending,
        "current_not_observable_subject_rows": current_not_observable,
        "carry_forward_subject_count_total": len(subjects),
        "carry_forward_complete_horizon_count_total": state_complete,
        "carry_forward_pending_horizon_count_total": state_pending,
        "carry_forward_other_horizon_count_total": state_other,
        "horizon_completion_ladder": horizon_ladder,
        "directional_outcome_breakdown_carry_forward": dict(outcome_counts.most_common()),
        "freshness_tier_breakdown": guard.get("freshness_tier_breakdown"),
        "dropped_incomplete_h1_rows_total": guard.get("dropped_incomplete_h1_rows_total"),
        "subjects": subjects,
        "boundary": BOUNDARY,
        "plain_language_fa": (
            "01D وضعیت outcome را با کلیدهای پایدار نگه می‌دارد تا pendingها در refreshهای بعدی کامل شوند و duplicate inflation ایجاد نشود. "
            "این فقط مشاهده است، نه PnL و نه سیگنال."
        ),
    }

    write_json(STATE_RUNTIME, status_payload)
    write_json(STATE_PANEL, status_payload)

    # Add compact fields to existing outcome status for the current panel.
    for path in [STATUS_RUNTIME, STATUS_PANEL]:
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            payload = {}
        payload["outcome_completion_guard_version"] = "SHADOW_OUTCOME_01D_v1_0"
        payload["unique_subject_count_current"] = current_unique_subject_count
        payload["duplicate_subject_count_current"] = duplicate_subject_count_current
        payload["carry_forward_subject_count_total"] = len(subjects)
        payload["carry_forward_complete_horizon_count_total"] = state_complete
        payload["carry_forward_pending_horizon_count_total"] = state_pending
        payload["horizon_completion_ladder"] = horizon_ladder
        payload["freshness_tier_breakdown"] = guard.get("freshness_tier_breakdown")
        payload["dropped_incomplete_h1_rows_total"] = guard.get("dropped_incomplete_h1_rows_total")
        payload.setdefault("boundary", {}).update(BOUNDARY)
        write_json(path, payload)

    write_json(PROOFS / "shadow_outcome_01d_completion_state_result.json", {
        "validation_name": "SHADOW_OUTCOME_01D_COMPLETION_STATE_BUILD",
        "created_utc": created,
        "unique_subject_count_current": current_unique_subject_count,
        "duplicate_subject_count_current": duplicate_subject_count_current,
        "carry_forward_subject_count_total": len(subjects),
        "horizon_completion_ladder": horizon_ladder,
        "boundary": BOUNDARY,
    })

    print(json.dumps({
        "status": "SHADOW_OUTCOME_01D_COMPLETION_STATE_BUILT",
        "unique_subject_count_current": current_unique_subject_count,
        "duplicate_subject_count_current": duplicate_subject_count_current,
        "carry_forward_subject_count_total": len(subjects),
        "carry_forward_complete_horizon_count_total": state_complete,
        "carry_forward_pending_horizon_count_total": state_pending,
        "signal_authorized": False,
        "pnl_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
