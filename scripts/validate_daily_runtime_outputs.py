#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path


def read(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    required = [
        'reports/daily_runtime_preflight_report.json',
        'reports/daily_runtime_step_report.json',
        'panel/panel_payload_after_daily_runtime.json',
        'proofs/daily_runtime_secret_redaction_proof.json',
        'proofs/daily_runtime_no_action_surface_proof.json',
        'proofs/daily_runtime_boundary_proof.json',
        'proofs/daily_runtime_local_validation_result.json',
        'logs/last_run_status_after_daily_runtime.json',
        'logs/runtime_heartbeat_after_daily_runtime.json',
    ]
    missing = [p for p in required if not (root / p).exists()]
    val = read(root / 'proofs' / 'daily_runtime_local_validation_result.json')
    boundary = read(root / 'proofs' / 'daily_runtime_boundary_proof.json')
    secret = read(root / 'proofs' / 'daily_runtime_secret_redaction_proof.json')
    action = read(root / 'proofs' / 'daily_runtime_no_action_surface_proof.json')
    panel = read(root / 'panel' / 'panel_payload_after_daily_runtime.json')
    result = {
        'program': 'PRV1F-01',
        'artifact': 'daily_runtime_external_validation_result',
        'validation_passed': (not missing and val.get('validation_passed') is True and boundary.get('status') == 'passed' and secret.get('verdict','').startswith('passed') and action.get('action_surface_absent') is True),
        'missing_files': missing,
        'daily_runtime_validation_passed': val.get('validation_passed'),
        'boundary_status': boundary.get('status'),
        'secret_redaction_verdict': secret.get('verdict'),
        'no_action_surface_passed': action.get('action_surface_absent'),
        'new_observation_candidate_count': panel.get('daily_loop_summary', {}).get('new_observation_candidate_count'),
        'staged_refresh_successful_surface_count': panel.get('daily_loop_summary', {}).get('staged_refresh_successful_surface_count'),
        'staged_refresh_failed_surface_count': panel.get('daily_loop_summary', {}).get('staged_refresh_failed_surface_count'),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['validation_passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
