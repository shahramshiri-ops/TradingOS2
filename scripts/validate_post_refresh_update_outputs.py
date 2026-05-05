#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

BOUNDARY = {
    "runtime_observation_not_signal": True,
    "candidate_not_trade_recommendation": True,
    "outcome_observation_not_win_loss": True,
    "lifecycle_tracking_not_execution_tracking": True,
    "cache_not_source_authority": True,
    "single_provider_confidence_not_source_truth": True,
    "scheduler_heartbeat_not_production_readiness": True,
    "panel_payload_not_action_surface": True,
    "no_broker": True,
    "no_order": True,
    "no_execution": True,
    "no_buy_sell_hold": True,
    "no_entry_stop_target": True,
    "no_pnl": True,
    "no_optimizer": True,
    "no_validation_verdict": True,
    "no_adaptation_decision": True,
    "no_production_readiness_claim": True,
    "spx_nq_out_of_v1_active_scope": True,
    "calendar_event_out_of_v1_scope": True,
    "second_provider_out_of_v1_scope": True,
    "row_2_retained_unopened": True,
    "rows_6_7_deferred_reentry": True,
    "matrix_complete_not_matrix_open": True,
}

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def read(p: Path, default: Any = None):
    try:
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default
    return default

def write(p: Path, obj: Any):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def parse_dt(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    s = str(raw).strip().replace('Z','')
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    required = [
        'reports/post_refresh_update_plan.json',
        'reports/post_refresh_lifecycle_update_report.json',
        'ledger/candidate_lifecycle_rows_v1_post_refresh.json',
        'panel/panel_payload_after_post_refresh_update.json',
        'proofs/post_refresh_secret_redaction_proof.json',
        'proofs/post_refresh_no_action_surface_proof.json',
        'proofs/post_refresh_update_boundary_proof.json',
        'reports/staged_cache_update_report.json',
    ]
    missing = [r for r in required if not (root / r).exists()]
    lifecycle = read(root/'reports/post_refresh_lifecycle_update_report.json', {}) if not missing else {}
    ledger = read(root/'ledger/candidate_lifecycle_rows_v1_post_refresh.json', {}) if not missing else {}
    panel = read(root/'panel/panel_payload_after_post_refresh_update.json', {}) if not missing else {}
    no_action = read(root/'proofs/post_refresh_no_action_surface_proof.json', {}) if not missing else {}
    secret = read(root/'proofs/post_refresh_secret_redaction_proof.json', {}) if not missing else {}
    boundary = read(root/'proofs/post_refresh_update_boundary_proof.json', {}) if not missing else {}
    cache = read(root/'reports/staged_cache_update_report.json', {}) if not missing else {}
    cache_by = {r.get('surface'): r for r in cache.get('surface_rows', []) if isinstance(r, dict)}
    rows = ledger.get('rows', []) if isinstance(ledger, dict) else []
    stale_active_reason_rows = []
    for r in rows:
        if r.get('lifecycle_status') != 'active_tracking':
            continue
        if r.get('latest_outcome_reason') != 'no_completed_post_trigger_bars_available_yet':
            continue
        surf = r.get('surface')
        trig = parse_dt(r.get('trigger_reference_bar_ts_utc'))
        last = parse_dt((cache_by.get(surf) or {}).get('last_provider_datetime'))
        if trig and last and last > trig:
            stale_active_reason_rows.append({
                'sot_candidate_id': r.get('sot_candidate_id'),
                'surface': surf,
                'trigger_reference_bar_ts_utc': r.get('trigger_reference_bar_ts_utc'),
                'cache_last_provider_datetime': (cache_by.get(surf) or {}).get('last_provider_datetime'),
                'reason': 'active row still says no completed post-trigger bars although refreshed cache has later bars; lifecycle reclassification must be rerun/fixed',
            })
    update_rows = lifecycle.get('update_rows', []) if isinstance(lifecycle, dict) else []
    active_update_cache_read_ok = all((u.get('valid_cache_bar_count') or 0) > 0 for u in update_rows) if update_rows else True
    validation_passed = bool(
        not missing
        and no_action.get('action_surface_absent') is True
        and secret.get('api_key_value_written') is False
        and boundary.get('status') in ['passed','passed_with_caveats']
        and (panel.get('summary') or {}).get('candidate_count') == 4
        and active_update_cache_read_ok
        and not stale_active_reason_rows
    )
    result = {
        'program': 'PRV1D-01+PRV1M-RC1',
        'artifact': 'post_refresh_update_local_validation_result_reviewed_strict',
        'created_at_utc': utc_now(),
        'validation_passed': validation_passed,
        'missing_files': missing,
        'active_update_cache_read_ok': active_update_cache_read_ok,
        'stale_active_reason_rows': stale_active_reason_rows,
        'secret_redaction_passed': secret.get('api_key_value_written') is False and secret.get('secret_hit_files', []) == [],
        'no_action_surface_passed': no_action.get('action_surface_absent') is True,
        'boundary_status': 'passed' if validation_passed else 'failed_or_requires_review',
        'note': 'Strict validator catches the specific stale Active Watch issue: no_completed_post_trigger_bars_available_yet cannot remain when refreshed cache has bars after trigger.',
        'boundary': BOUNDARY,
    }
    write(root/'proofs/post_refresh_update_local_validation_result_reviewed.json', result)
    write(root/'proofs/post_refresh_update_local_validation_result_reviewed_strict.json', result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if validation_passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
