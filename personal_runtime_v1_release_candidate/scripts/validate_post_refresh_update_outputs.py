#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime, timezone

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

def utc_now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write_json(p, obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    root = Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    required = [
        'reports/post_refresh_update_plan.json',
        'reports/post_refresh_candidate_detection_report.json',
        'reports/post_refresh_lifecycle_update_report.json',
        'reports/post_refresh_outcome_observation_report.json',
        'ledger/candidate_observation_ledger_v1_post_refresh.json',
        'ledger/candidate_lifecycle_rows_v1_post_refresh.json',
        'ledger/outcome_observation_rows_v1_post_refresh.json',
        'ledger/active_tracking_rows_v1_post_refresh.json',
        'panel/panel_payload_after_post_refresh_update.json',
        'proofs/post_refresh_secret_redaction_proof.json',
        'proofs/post_refresh_no_action_surface_proof.json',
        'proofs/post_refresh_update_boundary_proof.json',
        'logs/last_run_status_after_post_refresh_update.json',
        'logs/runtime_heartbeat_after_post_refresh_update.json',
    ]
    missing = [r for r in required if not (root/r).exists()]
    panel = read_json(root/'panel/panel_payload_after_post_refresh_update.json') if not missing else {}
    no_action = read_json(root/'proofs/post_refresh_no_action_surface_proof.json') if not missing else {}
    secret = read_json(root/'proofs/post_refresh_secret_redaction_proof.json') if not missing else {}
    boundary = read_json(root/'proofs/post_refresh_update_boundary_proof.json') if not missing else {}
    validation_passed = (not missing and no_action.get('action_surface_absent') is True and secret.get('api_key_value_written') is False and boundary.get('status') in ['passed','passed_with_caveats'] and panel.get('latest_exact_row_ledger_summary', panel.get('summary', {})).get('candidate_count', panel.get('summary',{}).get('candidate_count')) == 4)
    result = {
        'program': 'PRV1D-01',
        'artifact': 'post_refresh_update_local_validation_result_reviewed',
        'created_at_utc': utc_now(),
        'validation_passed': bool(validation_passed),
        'missing_files': missing,
        'secret_redaction_passed': secret.get('api_key_value_written') is False and secret.get('secret_hit_files', []) == [],
        'no_action_surface_passed': no_action.get('action_surface_absent') is True,
        'boundary_status': 'passed' if validation_passed else 'failed_or_requires_review',
        'boundary': BOUNDARY,
    }
    write_json(root/'proofs/post_refresh_update_local_validation_result_reviewed.json', result)
    print(json.dumps(result,indent=2))
    return 0 if validation_passed else 1
if __name__ == '__main__': raise SystemExit(main())
